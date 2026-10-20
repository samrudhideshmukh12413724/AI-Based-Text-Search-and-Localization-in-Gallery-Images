import 'package:flutter/material.dart';
import '../models/search_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/connection_error_view.dart';
import '../widgets/search_result_card.dart';
import 'document_detail_screen.dart';

class SearchTab extends StatefulWidget {
  final String? initialQuery;

  const SearchTab({super.key, this.initialQuery});

  @override
  State<SearchTab> createState() => _SearchTabState();
}

class _SearchTabState extends State<SearchTab> {
  final ApiService _api = ApiService();
  final TextEditingController _searchController = TextEditingController();

  List<SearchResult> _allResults = [];
  bool _loading = false;
  String? _errorMessage;
  bool _isConnectionError = false;
  String _activeFilter = 'All Files'; // 'All Files', 'Text', 'Images', 'QR & Barcode'

  @override
  void initState() {
    super.initState();
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      _searchController.text = widget.initialQuery!;
      _performSearch(widget.initialQuery!);
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void setQueryAndSearch(String query) {
    _searchController.text = query;
    _performSearch(query);
  }

  Future<void> _performSearch(String query) async {
    final cleanQuery = query.trim();
    if (cleanQuery.isEmpty) return;

    setState(() {
      _loading = true;
      _errorMessage = null;
      _isConnectionError = false;
    });

    try {
      final res = await _api.search(cleanQuery);
      if (mounted) {
        setState(() {
          _allResults = res.results;
          if (_allResults.isEmpty) {
            _errorMessage = res.message.isNotEmpty ? res.message : 'No matching documents found.';
          }
        });
      }
    } catch (e) {
      if (mounted) {
        final err = e.toString();
        setState(() {
          _isConnectionError = err.contains('Unreachable') || err.contains('SocketException') || err.contains('Connection');
          _errorMessage = err.replaceAll('Exception: ', '');
          _allResults = [];
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  List<SearchResult> get _filteredResults {
    if (_activeFilter == 'All Files') return _allResults;
    if (_activeFilter == 'Text') {
      return _allResults.where((r) => r.matchedText.isNotEmpty).toList();
    }
    if (_activeFilter == 'Images') {
      return _allResults.where((r) => !r.imageName.toLowerCase().endsWith('.pdf')).toList();
    }
    if (_activeFilter == 'QR & Barcode') {
      return _allResults.where((r) => r.qrPayload.isNotEmpty || r.visualObjects.any((v) => v.type == 'qr_code')).toList();
    }
    return _allResults;
  }

  void _openDetail(SearchResult result) {
    final isPdf = result.imageName.toLowerCase().endsWith('.pdf');
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DocumentDetailScreen(
          title: result.imageName,
          imageUrl: result.imageUrl,
          extractedText: result.matchedText,
          visualObjects: result.visualObjects,
          entities: result.entities,
          fileType: isPdf ? 'PDF DOCUMENT' : 'IMAGE',
          fileSize: '2.1 MB',
          date: 'Indexed',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Column(
          children: [
            // Top Search Bar
            Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
              color: Colors.white,
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                          textInputAction: TextInputAction.search,
                          onSubmitted: (q) => _performSearch(q),
                          decoration: InputDecoration(
                            hintText: 'Search text, documents, or QR...',
                            prefixIcon: const Icon(Icons.search_rounded, size: 22, color: AppTheme.primary),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.close_rounded, size: 18),
                                    onPressed: () {
                                      _searchController.clear();
                                      setState(() {
                                        _allResults = [];
                                        _errorMessage = null;
                                      });
                                    },
                                  )
                                : null,
                            fillColor: const Color(0xFFF8FAFC),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: AppTheme.border),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: AppTheme.border),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Search button icon
                      Container(
                        decoration: BoxDecoration(
                          color: AppTheme.primary,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: IconButton(
                          icon: const Icon(Icons.search_rounded, color: Colors.white, size: 22),
                          onPressed: () => _performSearch(_searchController.text),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Filter Pills Row (Screen 3)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildFilterPill('All Files'),
                        _buildFilterPill('Text'),
                        _buildFilterPill('Images'),
                        _buildFilterPill('QR & Barcode'),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Content / Results Body
            Expanded(
              child: _loading
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircularProgressIndicator(color: AppTheme.primary),
                          SizedBox(height: 14),
                          Text('Scanning multi-modal index...', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                        ],
                      ),
                    )
                  : _isConnectionError
                      ? ConnectionErrorView(
                          onRetry: () => _performSearch(_searchController.text),
                          onContinueOffline: () => setState(() => _isConnectionError = false),
                        )
                      : _filteredResults.isNotEmpty
                          ? ListView.builder(
                              padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                              itemCount: _filteredResults.length,
                              itemBuilder: (context, index) {
                                final item = _filteredResults[index];
                                return SearchResultCard(
                                  result: item,
                                  searchQuery: _searchController.text.trim(),
                                  onTap: () => _openDetail(item),
                                );
                              },
                            )
                          : Center(
                              child: Padding(
                                padding: const EdgeInsets.all(32),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.search_off_rounded,
                                      size: 56,
                                      color: AppTheme.textMuted.withValues(alpha: 0.6),
                                    ),
                                    const SizedBox(height: 16),
                                    Text(
                                      _errorMessage ?? 'Search your documents',
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w700,
                                        color: AppTheme.textPrimary,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    const Text(
                                      'Find receipts, invoices, identity cards, certificates, or text notes.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                                    ),
                                  ],
                                ),
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterPill(String title) {
    final isSelected = _activeFilter == title;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: () => setState(() => _activeFilter = title),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primary : const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isSelected ? AppTheme.primary : AppTheme.border,
            ),
          ),
          child: Text(
            title,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              color: isSelected ? Colors.white : AppTheme.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}
