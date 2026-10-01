import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/search_result.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _api = ApiService();
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _searchController = TextEditingController();

  Uint8List? _selectedImageBytes;
  String? _selectedImageName;
  String _extractedText = '';
  List<SearchResult> _results = [];
  bool _loading = false;
  String? _error;
  String? _searchType;
  String? _searchMessage;
  bool _hasSearched = false;
  final Set<int> _expandedRawTextIds = <int>{};
  final Map<int, List<RelatedImage>> _cachedRelationships = {};
  final Map<int, int?> _cachedCanonicalIds = {};
  final Set<int> _loadingRelIds = <int>{};
  final Set<int> _expandedRelIds = <int>{};
  final Map<int, String> _relErrors = {};

  Future<void> _pickImage() async {
    setState(() {
      _error = null;
      _extractedText = '';
    });
    try {
      final file = await _picker.pickImage(source: ImageSource.gallery);
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() {
        _selectedImageBytes = bytes;
        _selectedImageName = file.name;
      });
    } catch (e) {
      setState(() => _error = 'Failed to pick image: $e');
    }
  }

  Future<void> _extractText() async {
    if (_selectedImageBytes == null) return;
    setState(() {
      _loading = true;
      _error = null;
      _extractedText = '';
    });
    try {
      final res = await _api.uploadImageBytes(
        _selectedImageBytes!,
        _selectedImageName ?? 'image.jpg',
      );
      setState(() {
        _extractedText = res['text'] as String? ??
            res['extracted_text'] as String? ??
            res['cleaned_text'] as String? ??
            '(no text)';
        final hasVis = res['has_visual_objects'] as bool? ?? false;
        final visSum = res['visual_summary'] as String? ?? '';
        if (hasVis && visSum.isNotEmpty) {
          _extractedText += '\n\n👁️ Visual Objects Detected: $visSum';
        }
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _search() async {
    final q = _searchController.text.trim();
    if (q.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
      _hasSearched = true;
    });
    try {
      final response = await _api.search(q);
      setState(() {
        _results = response.results;
        _searchType = response.searchType;
        _searchMessage = response.message;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _results = [];
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  void _openImageZoom(
    BuildContext context,
    String imageUrl,
    String imageName, [
    List<VisualObject> visualObjects = const [],
    int? imageId,
  ]) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog.fullscreen(
        child: Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            foregroundColor: Colors.white,
            title: Text(
              imageName,
              style: const TextStyle(fontSize: 16),
              overflow: TextOverflow.ellipsis,
            ),
            actions: [
              if (imageId != null)
                IconButton(
                  icon: const Icon(Icons.hub_outlined),
                  tooltip: 'Related Documents',
                  onPressed: () => _showRelatedDocumentsSheet(context, imageId, imageName),
                ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(ctx).pop(),
              ),
            ],
          ),
          body: Center(
            child: InteractiveViewer(
              panEnabled: true,
              boundaryMargin: const EdgeInsets.all(20),
              minScale: 0.5,
              maxScale: 4.0,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Image.network(
                    imageUrl,
                    fit: BoxFit.contain,
                    loadingBuilder: (context, child, progress) {
                      if (progress == null) return child;
                      return const CircularProgressIndicator(color: Colors.white);
                    },
                    errorBuilder: (context, error, stackTrace) => const Icon(
                      Icons.broken_image,
                      color: Colors.white54,
                      size: 64,
                    ),
                  ),
                  if (visualObjects.isNotEmpty)
                    Positioned.fill(
                      child: CustomPaint(
                        painter: BoundingBoxOverlayPainter(visualObjects: visualObjects),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _showObjectDetailsDialog(BuildContext context, VisualObject obj, SearchResult result) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.qr_code_scanner, color: Color(0xFF0284C7)),
            const SizedBox(width: 8),
            Text(
              obj.label,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDetailRow('Location', obj.locationDesc),
            _buildDetailRow('Dimensions', '${obj.width} × ${obj.height} px'),
            _buildDetailRow('Bounding Box', '(${obj.x}, ${obj.y})'),
            _buildDetailRow('Confidence', obj.confidence),
            if (obj.data.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Decoded Payload / URL:',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF475569)),
              ),
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFCBD5E1)),
                ),
                child: SelectableText(
                  obj.data,
                  style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: Color(0xFF0F172A)),
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('CLOSE'),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A), fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _fetchRelationships(int imageId) async {
    if (_loadingRelIds.contains(imageId)) return;
    setState(() {
      _loadingRelIds.add(imageId);
      _relErrors.remove(imageId);
    });
    try {
      final res = await _api.getRelationships(imageId);
      setState(() {
        _cachedRelationships[imageId] = res.relationships;
        _cachedCanonicalIds[imageId] = res.canonicalImageId;
      });
    } catch (e) {
      setState(() {
        _relErrors[imageId] = e.toString().replaceAll('Exception: ', '');
      });
    } finally {
      setState(() {
        _loadingRelIds.remove(imageId);
      });
    }
  }

  void _toggleRelatedDocuments(int imageId) {
    setState(() {
      if (_expandedRelIds.contains(imageId)) {
        _expandedRelIds.remove(imageId);
      } else {
        _expandedRelIds.add(imageId);
        if (!_cachedRelationships.containsKey(imageId)) {
          _fetchRelationships(imageId);
        }
      }
    });
  }

  void _showRelatedDocumentsSheet(BuildContext context, int imageId, String imageName) {
    if (!_cachedRelationships.containsKey(imageId)) {
      _fetchRelationships(imageId);
    }
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (sheetContext, setSheetState) => DraggableScrollableSheet(
          initialChildSize: 0.55,
          minChildSize: 0.3,
          maxChildSize: 0.85,
          expand: false,
          builder: (_, scrollController) => Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Row(
                  children: [
                    const Icon(Icons.hub_outlined, color: Color(0xFF15803D), size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Related Documents for $imageName',
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Expanded(
                  child: _buildRelatedDocumentsContent(imageId, scrollController),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRelatedDocumentsContent(int imageId, ScrollController scrollController) {
    final isLoading = _loadingRelIds.contains(imageId);
    final error = _relErrors[imageId];
    final rels = _cachedRelationships[imageId];
    final canonicalId = _cachedCanonicalIds[imageId];

    if (isLoading && rels == null) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF15803D)),
      );
    }

    if (error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 36),
            const SizedBox(height: 8),
            Text('Error: $error', style: const TextStyle(color: Colors.red, fontSize: 13)),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () => _fetchRelationships(imageId),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (rels == null) {
      _fetchRelationships(imageId);
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF15803D)),
      );
    }

    if (rels.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.link_off, size: 48, color: Color(0xFF94A3B8)),
            SizedBox(height: 12),
            Text(
              'No related documents found.',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
            ),
            SizedBox(height: 4),
            Text(
              'This document does not share strong identifiers with other documents.',
              style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: scrollController,
      itemCount: rels.length + (canonicalId != null ? 1 : 0),
      itemBuilder: (context, idx) {
        if (canonicalId != null && idx == 0) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Variant of canonical document #$canonicalId',
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
            ),
          );
        }
        final rel = canonicalId != null ? rels[idx - 1] : rels[idx];
        return Card(
          elevation: 1,
          margin: const EdgeInsets.only(bottom: 10),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: Color(0xFFBBF7D0)),
          ),
          color: const Color(0xFFF0FDF4),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InkWell(
                  onTap: () {
                    Navigator.of(context).pop();
                    _openImageZoom(context, rel.imageUrl, rel.imageName, const [], rel.imageId);
                  },
                  borderRadius: BorderRadius.circular(6),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: Image.network(
                      rel.imageUrl,
                      width: 56,
                      height: 72,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        width: 56,
                        height: 72,
                        color: Colors.grey.shade200,
                        alignment: Alignment.center,
                        child: const Icon(Icons.broken_image, color: Colors.grey),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        rel.imageName,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF0F172A)),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFDCFCE7),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: const Color(0xFF86EFAC)),
                        ),
                        child: Text(
                          rel.readableType,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF15803D)),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Evidence: ${rel.evidence}',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
                      ),
                      if (rel.reason.isNotEmpty)
                        Text(
                          rel.reason,
                          style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                        ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.zoom_in, size: 20, color: Color(0xFF15803D)),
                  tooltip: 'Zoom document',
                  onPressed: () {
                    Navigator.of(context).pop();
                    _openImageZoom(context, rel.imageUrl, rel.imageName, const [], rel.imageId);
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Document Search'),
        centerTitle: true,
        elevation: 2,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // --- Document Ingestion Card ---
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text(
                            'Upload & OCR Document',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _pickImage,
                            icon: const Icon(Icons.photo_library_outlined),
                            label: const Text('SELECT DOCUMENT IMAGE'),
                          ),
                          if (_selectedImageBytes != null) ...[
                            const SizedBox(height: 12),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.memory(
                                _selectedImageBytes!,
                                height: 160,
                                fit: BoxFit.contain,
                              ),
                            ),
                            const SizedBox(height: 12),
                            ElevatedButton.icon(
                              onPressed: _loading ? null : _extractText,
                              icon: _loading
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.document_scanner),
                              label: Text(_loading ? 'PROCESSING OCR WITH AI...' : 'EXTRACT TEXT & INDEX'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: theme.colorScheme.primaryContainer,
                              ),
                            ),
                            if (_loading) ...[
                              const SizedBox(height: 8),
                              const Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.5)),
                                  SizedBox(width: 8),
                                  Text(
                                    'Extracting deep-learning text & indexing...',
                                    style: TextStyle(fontSize: 12, color: Colors.blueGrey, fontStyle: FontStyle.italic),
                                  ),
                                ],
                              ),
                            ],
                          ],
                          if (_extractedText.isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade100,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.grey.shade300),
                              ),
                              child: Text(
                                _extractedText,
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // --- Search Box Card ---
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text(
                            'Multi-Modal Search (Text + Visual)',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _searchController,
                            decoration: InputDecoration(
                              hintText: 'Search text, topics, or "documents with qr code"...',
                              prefixIcon: const Icon(Icons.search),
                              suffixIcon: _searchController.text.isNotEmpty
                                  ? IconButton(
                                      icon: const Icon(Icons.clear),
                                      onPressed: () {
                                        _searchController.clear();
                                        setState(() {});
                                      },
                                    )
                                  : null,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            onChanged: (_) => setState(() {}),
                            onSubmitted: (_) => _search(),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _search,
                            icon: const Icon(Icons.search),
                            label: const Text('SEARCH DOCUMENTS'),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // --- Results Section ---
                  if (_results.isNotEmpty) ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${_results.length} Relevant ${_results.length == 1 ? "Document" : "Documents"} Found',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        if (_searchType != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: _searchType == 'multimodal'
                                  ? const Color(0xFFEEF2FF)
                                  : _searchType == 'semantic'
                                      ? const Color(0xFFE0F2FE)
                                      : _searchType == 'visual'
                                          ? const Color(0xFFF3E8FF)
                                          : const Color(0xFFDCFCE7),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: _searchType == 'multimodal'
                                    ? const Color(0xFF6366F1)
                                    : _searchType == 'semantic'
                                        ? const Color(0xFF0284C7)
                                        : _searchType == 'visual'
                                            ? const Color(0xFF9333EA)
                                            : const Color(0xFF16A34A),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _searchType == 'multimodal'
                                      ? Icons.auto_awesome
                                      : _searchType == 'semantic'
                                          ? Icons.psychology
                                          : _searchType == 'visual'
                                              ? Icons.qr_code_scanner
                                              : Icons.text_fields,
                                  size: 15,
                                  color: _searchType == 'multimodal'
                                      ? const Color(0xFF4F46E5)
                                      : _searchType == 'semantic'
                                          ? const Color(0xFF0369A1)
                                          : _searchType == 'visual'
                                              ? const Color(0xFF7E22CE)
                                              : const Color(0xFF15803D),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  _searchType == 'multimodal'
                                      ? 'Multi-Modal Mode'
                                      : _searchType == 'semantic'
                                          ? 'Semantic Mode'
                                          : _searchType == 'visual'
                                              ? 'Visual Mode'
                                              : 'Keyword Mode',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: _searchType == 'multimodal'
                                        ? const Color(0xFF4F46E5)
                                        : _searchType == 'semantic'
                                            ? const Color(0xFF0369A1)
                                            : _searchType == 'visual'
                                                ? const Color(0xFF7E22CE)
                                                : const Color(0xFF15803D),
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    ..._results.take(15).map((result) => _buildResultCard(context, result)),
                    if (_results.length > 15)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Center(
                          child: Text(
                            'Showing top 15 of ${_results.length} relevant results',
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 13, fontWeight: FontWeight.w500),
                          ),
                        ),
                      ),
                  ],

                  // --- Empty State UI when 0 matches found ---
                  if (_hasSearched && _results.isEmpty && _error == null) ...[
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFFBEB),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFFDE68A)),
                      ),
                      child: Column(
                        children: [
                          const Icon(Icons.search_off_rounded, size: 52, color: Color(0xFFD97706)),
                          const SizedBox(height: 12),
                          Text(
                            _searchMessage?.isNotEmpty == true
                                ? _searchMessage!
                                : 'No relevant documents found.',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                              color: Color(0xFF92400E),
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Try rephrasing your search or checking related academic topics.',
                            style: TextStyle(fontSize: 13, color: Color(0xFF78350F)),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ],

                  // --- Error Message ---
                  if (_error != null) ...[
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline, color: Colors.red),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(_error!, style: const TextStyle(color: Colors.red)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildHighlightedText(String text, List<String> terms) {
    if (text.isEmpty) return const SizedBox.shrink();
    if (terms.isEmpty) {
      return Text(
        text,
        style: const TextStyle(fontSize: 13.5, color: Color(0xFF0F172A), height: 1.5),
      );
    }

    final searchTerms = <String>{};
    for (final t in terms) {
      final trimmed = t.trim();
      if (trimmed.isEmpty) continue;
      searchTerms.add(trimmed);
      for (final w in trimmed.split(RegExp(r'\s+'))) {
        if (w.length >= 3 && !w.toLowerCase().startsWith('the') && !w.toLowerCase().startsWith('and')) {
          searchTerms.add(w);
        }
      }
    }

    final spans = <_HighlightSpan>[];
    final textLower = text.toLowerCase();

    for (final term in searchTerms) {
      final termLower = term.toLowerCase();
      int start = 0;
      while ((start = textLower.indexOf(termLower, start)) != -1) {
        final end = start + termLower.length;
        spans.add(_HighlightSpan(start: start, end: end));
        start = end;
      }
    }

    if (spans.isEmpty) {
      return Text(
        text,
        style: const TextStyle(fontSize: 13.5, color: Color(0xFF0F172A), height: 1.5),
      );
    }

    spans.sort((a, b) => a.start.compareTo(b.start));
    final merged = <_HighlightSpan>[];
    for (final span in spans) {
      if (merged.isEmpty) {
        merged.add(span);
      } else {
        final last = merged.last;
        if (span.start <= last.end) {
          if (span.end > last.end) {
            merged[merged.length - 1] = _HighlightSpan(start: last.start, end: span.end);
          }
        } else {
          merged.add(span);
        }
      }
    }

    final textSpans = <TextSpan>[];
    int currentIndex = 0;

    for (final span in merged) {
      if (span.start > currentIndex) {
        textSpans.add(TextSpan(
          text: text.substring(currentIndex, span.start),
          style: const TextStyle(
            fontSize: 13.5,
            color: Color(0xFF0F172A),
            fontWeight: FontWeight.normal,
            height: 1.5,
          ),
        ));
      }

      textSpans.add(TextSpan(
        text: text.substring(span.start, span.end),
        style: const TextStyle(
          fontSize: 13.5,
          fontWeight: FontWeight.w900,
          color: Color(0xFF000000),
          backgroundColor: Color(0xFFFFD600),
          height: 1.5,
        ),
      ));

      currentIndex = span.end;
    }

    if (currentIndex < text.length) {
      textSpans.add(TextSpan(
        text: text.substring(currentIndex),
        style: const TextStyle(
          fontSize: 13.5,
          color: Color(0xFF0F172A),
          fontWeight: FontWeight.normal,
          height: 1.5,
        ),
      ));
    }

    return Text.rich(
      TextSpan(
        style: const TextStyle(fontSize: 13.5, color: Color(0xFF0F172A), height: 1.5),
        children: textSpans,
      ),
    );
  }

  Widget _buildResultCard(BuildContext context, SearchResult result) {
    final hasScore = result.similarityScore != null;
    final isMultimodal = result.searchType == 'multimodal';
    final isVisual = result.searchType == 'visual';
    final isSemantic = result.searchType == 'semantic' || (hasScore && !isMultimodal && !isVisual);
    final displaySnippet = result.previewSnippet.isNotEmpty
        ? result.previewSnippet
        : result.matchedText;
    final isExpanded = _expandedRawTextIds.contains(result.id);

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 16),
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Document Title + Match Type Badge
            Row(
              children: [
                Expanded(
                  child: Text(
                    result.imageName,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: Color(0xFF0F172A),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (isMultimodal)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF818CF8), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF4F46E5)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Multi-modal: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Multi-modal match',
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF4F46E5),
                          ),
                        ),
                      ],
                    ),
                  )
                else if (isVisual)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFAF5FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFD8B4FE), width: 1.2),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.qr_code_scanner, size: 14, color: Color(0xFF7E22CE)),
                        SizedBox(width: 4),
                        Text(
                          'Visual match',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF7E22CE),
                          ),
                        ),
                      ],
                    ),
                  )
                else if (isSemantic)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF93C5FD), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.psychology, size: 14, color: Color(0xFF1D4ED8)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Semantic match: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Semantic match',
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1D4ED8),
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0FDF4),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF86EFAC), width: 1.2),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.text_fields, size: 14, color: Color(0xFF15803D)),
                        SizedBox(width: 4),
                        Text(
                          'Keyword match',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF15803D),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),

            // Clickable Image Preview with Bounding Box Overlay & "Tap to zoom" hint
            Center(
              child: InkWell(
                onTap: () => _openImageZoom(context, result.imageUrl, result.imageName, result.visualObjects, result.id),
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  height: 220,
                  width: 165, // 3:4 aspect ratio (900x1200 document)
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFCBD5E1), width: 1),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Stack(
                    alignment: Alignment.bottomRight,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(7),
                        child: Image.network(
                          result.imageUrl,
                          height: 220,
                          width: 165,
                          cacheWidth: 330,
                          fit: BoxFit.fill,
                          errorBuilder: (context, error, stackTrace) => Container(
                            height: 220,
                            width: 165,
                            color: Colors.grey.shade200,
                            alignment: Alignment.center,
                            child: const Icon(Icons.broken_image, color: Colors.grey),
                          ),
                        ),
                      ),
                      if (result.hasVisualObjects && result.visualObjects.isNotEmpty)
                        Positioned.fill(
                          child: CustomPaint(
                            painter: BoundingBoxOverlayPainter(visualObjects: result.visualObjects),
                          ),
                        ),
                      Container(
                        margin: const EdgeInsets.all(4),
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color.fromRGBO(0, 0, 0, 0.75),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.zoom_in, color: Colors.white, size: 13),
                            SizedBox(width: 3),
                            Text(
                              'Zoom',
                              style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Phase 3 Visual Objects Badge Panel
            if (result.hasVisualObjects && result.visualObjects.isNotEmpty) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0F9FF),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFBAE6FD), width: 1.2),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.qr_code_scanner, size: 16, color: Color(0xFF0284C7)),
                        const SizedBox(width: 6),
                        Text(
                          '👁️ Visual Objects Detected (${result.visualObjects.length})',
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF0369A1),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: result.visualObjects.map((obj) => GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => _showObjectDetailsDialog(context, obj, result),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFF38BDF8)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.crop_free, size: 13, color: Color(0xFF0284C7)),
                              const SizedBox(width: 4),
                              Flexible(
                                child: Text(
                                  '${obj.label}: ${obj.locationDesc} (${obj.width}x${obj.height} px)',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF0C4A6E),
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                      )).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
            ],

            // Smart Relevant Text Preview Box with Vibrant Yellow Highlighter (shown when real text evidence exists)
            if (displaySnippet.trim().isNotEmpty && 
                displaySnippet.trim() != '(no text detected)' && 
                !displaySnippet.trim().startsWith('(no text')) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFFCD34D), width: 1.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isSemantic ? Icons.psychology : Icons.search,
                          size: 16,
                          color: const Color(0xFFB45309),
                        ),
                        const SizedBox(width: 6),
                        const Text(
                          'Relevant Text Preview',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 12.5,
                            color: Color(0xFF92400E),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    _buildHighlightedText(displaySnippet, result.highlightTerms),
                    if (result.matchedConcepts.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 5,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          const Text(
                            '💡 Matched concepts: ',
                            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Color(0xFF4338CA)),
                          ),
                          ...result.matchedConcepts.map(
                            (c) => Container(
                              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEEF2FF),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: const Color(0xFFC7D2FE), width: 1),
                              ),
                              child: Text(
                                c,
                                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Color(0xFF3730A3)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],

            // Optional Raw OCR View Expander (shown when genuine OCR text exists)
            if (result.matchedText.trim().isNotEmpty && 
                result.matchedText.trim() != '(no text detected)' && 
                !result.matchedText.trim().startsWith('(no text')) ...[
              InkWell(
                onTap: () {
                  setState(() {
                    if (isExpanded) {
                      _expandedRawTextIds.remove(result.id);
                    } else {
                      _expandedRawTextIds.add(result.id);
                    }
                  });
                },
                child: Padding(
                  padding: const EdgeInsets.only(top: 8, bottom: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        isExpanded ? 'Hide full OCR text' : 'View full OCR text (raw)',
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade600, decoration: TextDecoration.underline),
                      ),
                      Icon(
                        isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                        size: 14,
                        color: Colors.grey.shade600,
                      ),
                    ],
                  ),
                ),
              ),
              if (isExpanded) ...[
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(top: 4),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    result.matchedText,
                    style: const TextStyle(fontSize: 11, color: Colors.black87),
                  ),
                ),
              ],
            ],
            const SizedBox(height: 10),
            _buildRelatedDocumentsCardSection(context, result),
          ],
        ),
      ),
    );
  }

  Widget _buildRelatedDocumentsCardSection(BuildContext context, SearchResult result) {
    final imageId = result.id;
    final isExpanded = _expandedRelIds.contains(imageId);
    final isLoading = _loadingRelIds.contains(imageId);
    final error = _relErrors[imageId];
    final rels = _cachedRelationships[imageId];
    final canonicalId = _cachedCanonicalIds[imageId];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () => _toggleRelatedDocuments(imageId),
          borderRadius: BorderRadius.circular(6),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF86EFAC), width: 1.1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.hub_outlined, size: 14, color: Color(0xFF15803D)),
                const SizedBox(width: 6),
                Text(
                  isExpanded ? 'Hide Related Documents' : '🔗 Related Documents',
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF15803D),
                  ),
                ),
                if (isLoading) ...[
                  const SizedBox(width: 8),
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF15803D)),
                  ),
                ] else ...[
                  const SizedBox(width: 4),
                  Icon(
                    isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    size: 16,
                    color: const Color(0xFF15803D),
                  ),
                ],
              ],
            ),
          ),
        ),
        if (isExpanded) ...[
          if (isLoading && rels == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF15803D)),
                ),
              ),
            )
          else if (error != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, size: 15, color: Color(0xFFDC2626)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Failed to load relationships: $error',
                      style: const TextStyle(fontSize: 11.5, color: Color(0xFFB91C1C)),
                    ),
                  ),
                  TextButton(
                    onPressed: () => _fetchRelationships(imageId),
                    child: const Text('Retry', style: TextStyle(fontSize: 11.5)),
                  ),
                ],
              ),
            )
          else if (rels != null && rels.isEmpty)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.link_off, size: 15, color: Color(0xFF64748B)),
                  SizedBox(width: 6),
                  Text(
                    'No related documents found.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            )
          else if (rels != null && rels.isNotEmpty) ...[
            if (canonicalId != null)
              Padding(
                padding: const EdgeInsets.only(top: 6, bottom: 2),
                child: Text(
                  'Variant of canonical document #$canonicalId',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                ),
              ),
            ...rels.map((rel) => Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFBBF7D0)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  InkWell(
                    onTap: () => _openImageZoom(context, rel.imageUrl, rel.imageName, const [], rel.imageId),
                    borderRadius: BorderRadius.circular(6),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: Image.network(
                        rel.imageUrl,
                        width: 50,
                        height: 66,
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) => Container(
                          width: 50,
                          height: 66,
                          color: Colors.grey.shade200,
                          alignment: Alignment.center,
                          child: const Icon(Icons.broken_image, size: 20, color: Colors.grey),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          rel.imageName,
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 3),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFDCFCE7),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0xFF86EFAC)),
                          ),
                          child: Text(
                            rel.readableType,
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF15803D)),
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          'Evidence: ${rel.evidence}',
                          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
                        ),
                        if (rel.reason.isNotEmpty)
                          Text(
                            rel.reason,
                            style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.zoom_in, size: 20, color: Color(0xFF15803D)),
                    tooltip: 'Zoom related image',
                    onPressed: () => _openImageZoom(context, rel.imageUrl, rel.imageName, const [], rel.imageId),
                  ),
                ],
              ),
            )),
          ],
        ],
      ],
    );
  }
}

class BoundingBoxOverlayPainter extends CustomPainter {
  final List<VisualObject> visualObjects;

  BoundingBoxOverlayPainter({required this.visualObjects});

  @override
  void paint(Canvas canvas, Size size) {
    if (visualObjects.isEmpty) return;

    final boxPaint = Paint()
      ..color = const Color(0xFF00E5FF) // Vibrant Cyan
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final fillPaint = Paint()
      ..color = const Color(0x2A00E5FF) // Subtle transparent Cyan fill
      ..style = PaintingStyle.fill;

    final cornerPaint = Paint()
      ..color = const Color(0xFFFFD600) // Vibrant Yellow Corner Markers
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.square;

    for (final obj in visualObjects) {
      final rect = Rect.fromLTWH(
        obj.normX * size.width,
        obj.normY * size.height,
        obj.normW * size.width,
        obj.normH * size.height,
      );

      // Draw bounding box rectangle & fill
      canvas.drawRect(rect, fillPaint);
      canvas.drawRect(rect, boxPaint);

      // Draw corner brackets
      final cornerLen = (rect.width * 0.25).clamp(4.0, 14.0);

      // Top-Left
      canvas.drawLine(rect.topLeft, rect.topLeft + Offset(cornerLen, 0), cornerPaint);
      canvas.drawLine(rect.topLeft, rect.topLeft + Offset(0, cornerLen), cornerPaint);

      // Top-Right
      canvas.drawLine(rect.topRight, rect.topRight + Offset(-cornerLen, 0), cornerPaint);
      canvas.drawLine(rect.topRight, rect.topRight + Offset(0, cornerLen), cornerPaint);

      // Bottom-Left
      canvas.drawLine(rect.bottomLeft, rect.bottomLeft + Offset(cornerLen, 0), cornerPaint);
      canvas.drawLine(rect.bottomLeft, rect.bottomLeft + Offset(0, -cornerLen), cornerPaint);

      // Bottom-Right
      canvas.drawLine(rect.bottomRight, rect.bottomRight + Offset(-cornerLen, 0), cornerPaint);
      canvas.drawLine(rect.bottomRight, rect.bottomRight + Offset(0, -cornerLen), cornerPaint);
    }
  }

  @override
  bool shouldRepaint(covariant BoundingBoxOverlayPainter oldDelegate) {
    return oldDelegate.visualObjects != visualObjects;
  }
}

class _HighlightSpan {
  final int start;
  final int end;
  _HighlightSpan({required this.start, required this.end});
}
