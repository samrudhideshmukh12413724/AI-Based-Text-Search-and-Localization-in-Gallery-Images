import 'package:flutter/material.dart';
import '../models/search_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class SearchResultCard extends StatelessWidget {
  final SearchResult result;
  final String searchQuery;
  final VoidCallback onTap;

  const SearchResultCard({
    super.key,
    required this.result,
    required this.searchQuery,
    required this.onTap,
  });

  TextSpan _buildHighlightedText(String text, List<String> terms) {
    if (terms.isEmpty || text.isEmpty) {
      return TextSpan(
        text: text,
        style: const TextStyle(fontSize: 12.5, color: AppTheme.textSecondary, height: 1.35),
      );
    }

    final lowerText = text.toLowerCase();
    final spans = <TextSpan>[];
    int currentIndex = 0;

    // Collect all match ranges
    final matches = <_MatchRange>[];
    for (final term in terms) {
      final cleanTerm = term.trim().toLowerCase();
      if (cleanTerm.isEmpty) continue;
      int start = 0;
      while ((start = lowerText.indexOf(cleanTerm, start)) != -1) {
        matches.add(_MatchRange(start, start + cleanTerm.length));
        start += cleanTerm.length;
      }
    }

    if (matches.isEmpty) {
      return TextSpan(
        text: text,
        style: const TextStyle(fontSize: 12.5, color: AppTheme.textSecondary, height: 1.35),
      );
    }

    // Sort and merge overlapping match ranges
    matches.sort((a, b) => a.start.compareTo(b.start));
    final merged = <_MatchRange>[];
    var current = matches.first;
    for (int i = 1; i < matches.length; i++) {
      final next = matches[i];
      if (next.start <= current.end) {
        current = _MatchRange(current.start, next.end > current.end ? next.end : current.end);
      } else {
        merged.add(current);
        current = next;
      }
    }
    merged.add(current);

    for (final m in merged) {
      if (m.start > currentIndex) {
        spans.add(TextSpan(
          text: text.substring(currentIndex, m.start),
          style: const TextStyle(fontSize: 12.5, color: AppTheme.textSecondary, height: 1.35),
        ));
      }
      spans.add(TextSpan(
        text: text.substring(m.start, m.end),
        style: const TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.bold,
          backgroundColor: AppTheme.highlightYellow,
          color: AppTheme.highlightYellowText,
        ),
      ));
      currentIndex = m.end;
    }

    if (currentIndex < text.length) {
      spans.add(TextSpan(
        text: text.substring(currentIndex),
        style: const TextStyle(fontSize: 12.5, color: AppTheme.textSecondary, height: 1.35),
      ));
    }

    return TextSpan(children: spans);
  }

  @override
  Widget build(BuildContext context) {
    final isPdf = result.imageName.toLowerCase().endsWith('.pdf');
    final queryTerms = [
      if (searchQuery.isNotEmpty) searchQuery,
      ...result.highlightTerms,
    ];

    // Format display snippet
    String snippet = result.previewSnippet.isNotEmpty
        ? result.previewSnippet
        : result.matchedText.replaceAll('\n', ' ').trim();
    if (snippet.length > 120) {
      snippet = '${snippet.substring(0, 117)}...';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Thumbnail on left
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    width: 58,
                    height: 58,
                    color: const Color(0xFFF1F5F9),
                    child: result.imageUrl.isNotEmpty
                        ? Image.network(
                            result.imageUrl,
                            headers: ApiService.authHeaders,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => _buildThumbPlaceholder(isPdf),
                          )
                        : _buildThumbPlaceholder(isPdf),
                  ),
                ),
                const SizedBox(width: 12),
                // Title, metadata, snippet
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        result.imageName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Text(
                            isPdf ? 'PDF' : 'JPG',
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                          const Text(' • ', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
                          Text(
                            result.searchType?.toUpperCase() ?? 'DOCUMENT',
                            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                          ),
                        ],
                      ),
                      if (snippet.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        RichText(
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          text: _buildHighlightedText(snippet, queryTerms),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                const Padding(
                  padding: EdgeInsets.only(top: 14),
                  child: Icon(
                    Icons.chevron_right,
                    size: 20,
                    color: AppTheme.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildThumbPlaceholder(bool isPdf) {
    return Center(
      child: Icon(
        isPdf ? Icons.picture_as_pdf_outlined : Icons.insert_drive_file_outlined,
        color: isPdf ? const Color(0xFFDC2626) : AppTheme.primary,
        size: 26,
      ),
    );
  }
}

class _MatchRange {
  final int start;
  final int end;
  _MatchRange(this.start, this.end);
}
