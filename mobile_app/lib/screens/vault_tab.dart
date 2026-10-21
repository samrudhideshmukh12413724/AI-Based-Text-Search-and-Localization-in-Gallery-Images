import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'camera_scan_screen.dart';
import 'document_detail_screen.dart';
import 'gallery_import_screen.dart';

class VaultTab extends StatefulWidget {
  const VaultTab({super.key});

  @override
  State<VaultTab> createState() => _VaultTabState();
}

class _VaultTabState extends State<VaultTab> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _documents = [];
  bool _loading = true;
  String _activeCategory = 'All';
  final TextEditingController _filterController = TextEditingController();

  final List<String> _categories = [
    'All',
    'Receipts & Bills',
    'Identity Cards',
    'Academic',
    'Notes',
  ];

  @override
  void initState() {
    super.initState();
    _loadVault();
  }

  @override
  void dispose() {
    _filterController.dispose();
    super.dispose();
  }

  Future<void> _loadVault() async {
    setState(() => _loading = true);
    try {
      final list = await _api.fetchTenantDocuments();
      if (mounted) {
        setState(() {
          _documents = list;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> get _filteredDocuments {
    final query = _filterController.text.trim().toLowerCase();
    return _documents.where((doc) {
      final name = (doc['image_name'] as String? ?? '').toLowerCase();
      final text = (doc['extracted_text'] as String? ?? '').toLowerCase();

      // Search text match
      if (query.isNotEmpty && !name.contains(query) && !text.contains(query)) {
        return false;
      }

      // Category filter
      if (_activeCategory == 'Receipts & Bills') {
        return name.contains('receipt') || name.contains('bill') || name.contains('invoice') || text.contains('total') || text.contains('amount');
      } else if (_activeCategory == 'Identity Cards') {
        return name.contains('pan') || name.contains('aadhaar') || name.contains('id') || name.contains('card') || name.contains('pass');
      } else if (_activeCategory == 'Academic') {
        return name.contains('cert') || name.contains('marksheet') || name.contains('college') || name.contains('exam') || name.contains('admission');
      } else if (_activeCategory == 'Notes') {
        return name.contains('note') || name.contains('doc') || text.isNotEmpty;
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Document Vault', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh vault',
            onPressed: _loadVault,
          ),
          IconButton(
            icon: const Icon(Icons.camera_alt_outlined),
            tooltip: 'Scan document',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const CameraScanScreen()),
              ).then((_) => _loadVault());
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Search Vault Filter Field
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              child: TextField(
                controller: _filterController,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'Filter files in vault...',
                  prefixIcon: const Icon(Icons.filter_list_rounded, size: 20, color: AppTheme.textMuted),
                  suffixIcon: _filterController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            _filterController.clear();
                            setState(() {});
                          },
                        )
                      : null,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                ),
              ),
            ),

            // Category Chips Row
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Row(
                children: _categories.map((cat) {
                  final isSelected = _activeCategory == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: GestureDetector(
                      onTap: () => setState(() => _activeCategory = cat),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.primary : Colors.white,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: isSelected ? AppTheme.primary : AppTheme.border),
                        ),
                        child: Text(
                          cat,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                            color: isSelected ? Colors.white : AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 6),

            // Document Count Badge
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
              child: Row(
                children: [
                  Text(
                    '${_filteredDocuments.length} Documents',
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                  ),
                  const Spacer(),
                  Text(
                    ApiService.isLoggedIn ? 'Vault #${ApiService.currentUserId}' : 'Public Vault',
                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),

            // Grid of Documents
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                  : _filteredDocuments.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.folder_open_rounded, size: 52, color: AppTheme.textMuted),
                              const SizedBox(height: 12),
                              const Text('No documents found in vault', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                              const SizedBox(height: 6),
                              ElevatedButton.icon(
                                onPressed: () {
                                  Navigator.of(context).push(
                                    MaterialPageRoute(builder: (_) => const GalleryImportScreen()),
                                  ).then((_) => _loadVault());
                                },
                                icon: const Icon(Icons.upload_file_rounded, size: 18),
                                label: const Text('Import Documents'),
                              ),
                            ],
                          ),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 6, 16, 24),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 12,
                            mainAxisSpacing: 12,
                            childAspectRatio: 0.88,
                          ),
                          itemCount: _filteredDocuments.length,
                          itemBuilder: (context, index) {
                            final doc = _filteredDocuments[index];
                            final name = doc['image_name'] as String? ?? 'document_${index + 1}.jpg';
                            final rawUrl = doc['image_url'] as String? ?? '';
                            final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${ApiService.baseUrl}$rawUrl';
                            final text = doc['extracted_text'] as String? ?? '';
                            final isPdf = name.toLowerCase().endsWith('.pdf');

                            return InkWell(
                              onTap: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) => DocumentDetailScreen(
                                      title: name,
                                      imageUrl: fullUrl,
                                      extractedText: text,
                                      fileType: isPdf ? 'PDF' : 'IMAGE',
                                      date: 'Indexed',
                                    ),
                                  ),
                                );
                              },
                              borderRadius: BorderRadius.circular(16),
                              child: Container(
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
                                          child: fullUrl.isNotEmpty && !isPdf
                                              ? Image.network(
                                                  fullUrl,
                                                  headers: ApiService.authHeaders,
                                                  fit: BoxFit.cover,
                                                  errorBuilder: (_, __, ___) => _buildPlaceholder(isPdf),
                                                )
                                              : _buildPlaceholder(isPdf),
                                        ),
                                      ),
                                    ),
                                    // Info
                                    Padding(
                                      padding: const EdgeInsets.all(10),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            name,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w700,
                                              fontSize: 13,
                                              color: AppTheme.textPrimary,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            isPdf ? 'PDF Document' : 'Scanned Image',
                                            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
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
        isPdf ? Icons.picture_as_pdf_outlined : Icons.insert_drive_file_outlined,
        color: isPdf ? const Color(0xFFDC2626) : AppTheme.primary,
        size: 34,
      ),
    );
  }
}
