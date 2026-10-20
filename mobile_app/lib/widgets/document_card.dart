import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class DocumentCard extends StatelessWidget {
  final String filename;
  final String? imageUrl;
  final String? subtitle;
  final VoidCallback onTap;

  const DocumentCard({
    super.key,
    required this.filename,
    this.imageUrl,
    this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isPdf = filename.toLowerCase().endsWith('.pdf');

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 120,
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Thumbnail preview
            Expanded(
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
                child: Container(
                  color: const Color(0xFFF1F5F9),
                  width: double.infinity,
                  child: imageUrl != null && imageUrl!.isNotEmpty
                      ? Image.network(
                          imageUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => _buildPlaceholder(isPdf),
                        )
                      : _buildPlaceholder(isPdf),
                ),
              ),
            ),
            // Info
            Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    filename,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle ?? 'Document',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder(bool isPdf) {
    return Center(
      child: Icon(
        isPdf ? Icons.picture_as_pdf_outlined : Icons.description_outlined,
        color: isPdf ? const Color(0xFFDC2626) : AppTheme.primary,
        size: 32,
      ),
    );
  }
}
