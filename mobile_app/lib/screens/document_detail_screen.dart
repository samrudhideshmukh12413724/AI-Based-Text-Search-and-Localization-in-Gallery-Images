import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/search_result.dart';
import '../theme/app_theme.dart';
import '../widgets/bounding_box_painter.dart';

class DocumentDetailScreen extends StatefulWidget {
  final String title;
  final String imageUrl;
  final String extractedText;
  final List<VisualObject> visualObjects;
  final Map<String, dynamic>? entities;
  final String? fileType;
  final String? fileSize;
  final String? date;

  const DocumentDetailScreen({
    super.key,
    required this.title,
    required this.imageUrl,
    required this.extractedText,
    this.visualObjects = const [],
    this.entities,
    this.fileType,
    this.fileSize,
    this.date,
  });

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  bool _showBoxes = true;

  void _copyText() {
    Clipboard.setData(ClipboardData(text: widget.extractedText));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('📋 Document text copied to clipboard!'),
        backgroundColor: AppTheme.success,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _openFullscreenViewer() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            foregroundColor: Colors.white,
            title: Text(widget.title, style: const TextStyle(fontSize: 16)),
            actions: [
              IconButton(
                icon: const Icon(Icons.copy),
                tooltip: 'Copy all text',
                onPressed: _copyText,
              ),
            ],
          ),
          body: Center(
            child: InteractiveViewer(
              panEnabled: true,
              boundaryMargin: const EdgeInsets.all(40),
              minScale: 0.5,
              maxScale: 6.0,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Image.network(
                    widget.imageUrl,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => const Icon(Icons.broken_image, size: 64, color: Colors.white54),
                  ),
                  if (_showBoxes && widget.visualObjects.isNotEmpty)
                    Positioned.fill(
                      child: CustomPaint(
                        painter: BoundingBoxOverlayPainter(visualObjects: widget.visualObjects),
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

  @override
  Widget build(BuildContext context) {
    final cleanExtracted = widget.extractedText.trim();
    final entitiesList = <MapEntry<String, String>>[];
    if (widget.entities != null) {
      widget.entities!.forEach((k, v) {
        if (v != null && v.toString().isNotEmpty) {
          entitiesList.add(MapEntry(k, v.toString()));
        }
      });
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(
          widget.title.toUpperCase(),
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: Icon(
              _showBoxes ? Icons.highlight_rounded : Icons.highlight_off_rounded,
              color: _showBoxes ? AppTheme.primary : AppTheme.textMuted,
            ),
            tooltip: 'Toggle OCR Highlights',
            onPressed: () => setState(() => _showBoxes = !_showBoxes),
          ),
          IconButton(
            icon: const Icon(Icons.copy_rounded),
            tooltip: 'Copy text',
            onPressed: _copyText,
          ),
        ],
      ),
      body: Column(
        children: [
          // Document Preview Area
          Expanded(
            flex: 5,
            child: Container(
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: GestureDetector(
                  onTap: _openFullscreenViewer,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      InteractiveViewer(
                        minScale: 0.8,
                        maxScale: 4.0,
                        child: Center(
                          child: Image.network(
                            widget.imageUrl,
                            fit: BoxFit.contain,
                            loadingBuilder: (_, child, progress) {
                              if (progress == null) return child;
                              return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
                            },
                            errorBuilder: (_, __, ___) => const Center(
                              child: Icon(Icons.insert_drive_file_outlined, size: 64, color: AppTheme.primary),
                            ),
                          ),
                        ),
                      ),
                      if (_showBoxes && widget.visualObjects.isNotEmpty)
                        Positioned.fill(
                          child: IgnorePointer(
                            child: CustomPaint(
                              painter: BoundingBoxOverlayPainter(visualObjects: widget.visualObjects),
                            ),
                          ),
                        ),
                      Positioned(
                        bottom: 12,
                        right: 12,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.65),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.zoom_in, color: Colors.white, size: 14),
                              SizedBox(width: 4),
                              Text('Tap to expand', style: TextStyle(color: Colors.white, fontSize: 11)),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Metadata & Detected Text Sheet
          Expanded(
            flex: 4,
            child: Container(
              width: double.infinity,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                boxShadow: [
                  BoxShadow(
                    color: Color(0x0C000000),
                    blurRadius: 16,
                    offset: Offset(0, -4),
                  ),
                ],
              ),
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title & Meta info
                  Text(
                    widget.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${widget.fileType ?? 'JPG'} • ${widget.fileSize ?? '2.1 MB'} • ${widget.date ?? 'Recent'}',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 12),

                  // Detected Text Pill Header
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFEF08A),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.auto_awesome, size: 12, color: Color(0xFF854D0E)),
                            SizedBox(width: 4),
                            Text(
                              'Detected Text',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF854D0E),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: _copyText,
                        icon: const Icon(Icons.copy, size: 14),
                        label: const Text('Copy', style: TextStyle(fontSize: 12)),
                        style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),

                  // Extracted text content box
                  Expanded(
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: SingleChildScrollView(
                        child: cleanExtracted.isNotEmpty
                            ? Text(
                                cleanExtracted,
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: AppTheme.textPrimary,
                                  height: 1.4,
                                ),
                              )
                            : const Text(
                                'No OCR text extracted from this document.',
                                style: TextStyle(fontSize: 12.5, color: AppTheme.textMuted, fontStyle: FontStyle.italic),
                              ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Open In Viewer Button
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: _openFullscreenViewer,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: const Text(
                        'Open in Viewer',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
