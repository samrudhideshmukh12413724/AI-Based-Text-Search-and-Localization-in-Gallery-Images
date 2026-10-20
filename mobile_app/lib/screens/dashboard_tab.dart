import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/document_card.dart';
import 'camera_scan_screen.dart';
import 'document_detail_screen.dart';
import 'gallery_import_screen.dart';
import 'sync_folder_screen.dart';

class DashboardTab extends StatefulWidget {
  final Function(String query) onSearchRequested;
  final VoidCallback onViewAllDocuments;

  const DashboardTab({
    super.key,
    required this.onSearchRequested,
    required this.onViewAllDocuments,
  });

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  final ApiService _api = ApiService();
  final TextEditingController _searchController = TextEditingController();
  List<Map<String, dynamic>> _recentDocs = [];
  bool _loadingDocs = true;
  bool _isConnected = true;
  String _activeFilter = 'All Files';

  @override
  void initState() {
    super.initState();
    _checkServerAndLoadDocuments();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _checkServerAndLoadDocuments() async {
    setState(() => _loadingDocs = true);
    try {
      await _api.findWorkingBaseUrl();
      final docs = await _api.fetchTenantDocuments();
      if (mounted) {
        setState(() {
          _recentDocs = docs;
          _isConnected = true;
          _loadingDocs = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isConnected = false;
          _loadingDocs = false;
        });
      }
    }
  }

  void _triggerSearch() {
    final q = _searchController.text.trim();
    if (q.isNotEmpty) {
      widget.onSearchRequested(q);
    }
  }

  void _showUserAccountDialog() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const CircleAvatar(
                    radius: 24,
                    backgroundColor: AppTheme.primaryContainer,
                    child: Icon(Icons.person, color: AppTheme.primary, size: 28),
                  ),
                  const SizedBox(width: 14),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        ApiService.currentUsername,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      Text(
                        ApiService.isLoggedIn ? 'Vault #${ApiService.currentUserId}' : 'Guest Mode (Public Vault)',
                        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Divider(color: AppTheme.border),
              ListTile(
                leading: const Icon(Icons.dns_outlined, color: AppTheme.primary),
                title: const Text('Backend Server IP'),
                subtitle: Text(ApiService.baseUrl, style: const TextStyle(fontSize: 11)),
                onTap: () {
                  Navigator.pop(ctx);
                  _showServerConfigDialog();
                },
              ),
              ListTile(
                leading: const Icon(Icons.refresh_rounded, color: AppTheme.primary),
                title: const Text('Refresh Document Index'),
                onTap: () {
                  Navigator.pop(ctx);
                  _checkServerAndLoadDocuments();
                },
              ),
              ListTile(
                leading: const Icon(Icons.logout_rounded, color: AppTheme.error),
                title: const Text('Sign Out', style: TextStyle(color: AppTheme.error, fontWeight: FontWeight.bold)),
                onTap: () {
                  _api.logout();
                  Navigator.pop(ctx);
                  _checkServerAndLoadDocuments();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showServerConfigDialog() {
    final controller = TextEditingController(text: ApiService.customIp ?? ApiService.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Server Configuration', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Set Cloudflare public URL or LAN IP for testing on physical phone:',
              style: TextStyle(fontSize: 12.5, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(hintText: 'https://xxx.trycloudflare.com'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              ApiService.setCustomIp(controller.text.trim());
              Navigator.pop(ctx);
              _checkServerAndLoadDocuments();
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _checkServerAndLoadDocuments,
          color: AppTheme.primary,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            physics: const AlwaysScrollableScrollPhysics(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top App Header
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: AppTheme.primaryContainer,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Center(
                            child: Icon(Icons.document_scanner_rounded, color: AppTheme.primary, size: 22),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'DocuLens AI',
                              style: TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.textPrimary,
                                letterSpacing: -0.3,
                              ),
                            ),
                            Text(
                              'Intelligent Document Search',
                              style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        // Connected Pill
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: _isConnected ? AppTheme.successContainer : const Color(0xFFFEF2F2),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: _isConnected ? const Color(0xFFA7F3D0) : const Color(0xFFFECACA),
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(
                                  color: _isConnected ? AppTheme.success : AppTheme.error,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                _isConnected ? 'Connected' : 'Offline',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.bold,
                                  color: _isConnected ? const Color(0xFF065F46) : AppTheme.error,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Profile Avatar
                        InkWell(
                          onTap: _showUserAccountDialog,
                          borderRadius: BorderRadius.circular(20),
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: const Color(0xFFF1F5F9),
                              shape: BoxShape.circle,
                              border: Border.all(color: AppTheme.border),
                            ),
                            child: const Icon(Icons.person_outline_rounded, size: 20, color: AppTheme.textPrimary),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Hero Search Bar (Screen 2)
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.border),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.03),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(left: 14),
                        child: Icon(Icons.search_rounded, color: AppTheme.textMuted, size: 22),
                      ),
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          textInputAction: TextInputAction.search,
                          onSubmitted: (_) => _triggerSearch(),
                          style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w500, color: AppTheme.textPrimary),
                          decoration: const InputDecoration(
                            hintText: 'Search text, documents, or objects...',
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 15),
                            fillColor: Colors.transparent,
                          ),
                        ),
                      ),
                      if (_searchController.text.isNotEmpty)
                        IconButton(
                          icon: const Icon(Icons.close_rounded, size: 18, color: AppTheme.textMuted),
                          onPressed: () {
                            _searchController.clear();
                            setState(() {});
                          },
                        ),
                      // Suffix purple search button
                      Padding(
                        padding: const EdgeInsets.all(6),
                        child: InkWell(
                          onTap: _triggerSearch,
                          borderRadius: BorderRadius.circular(12),
                          child: Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(
                              color: AppTheme.primary,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Icon(Icons.search_rounded, color: Colors.white, size: 22),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Filter Pills
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
                const SizedBox(height: 24),

                // Quick Actions Header
                const Text(
                  'Quick Actions',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),

                // Quick Actions Cards Grid (Screen 2)
                Row(
                  children: [
                    Expanded(
                      child: _buildQuickActionCard(
                        icon: Icons.camera_alt_outlined,
                        title: 'Camera Scan',
                        subtitle: 'Scan new document',
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(builder: (_) => const CameraScanScreen()),
                          ).then((_) => _checkServerAndLoadDocuments());
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildQuickActionCard(
                        icon: Icons.photo_library_outlined,
                        title: 'Gallery Import',
                        subtitle: 'Select from gallery',
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(builder: (_) => const GalleryImportScreen()),
                          ).then((_) => _checkServerAndLoadDocuments());
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildQuickActionCard(
                  icon: Icons.sync_rounded,
                  title: 'Sync Folder',
                  subtitle: 'Sync from your folder',
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SyncFolderScreen()),
                    ).then((_) => _checkServerAndLoadDocuments());
                  },
                  isWide: true,
                ),
                const SizedBox(height: 24),

                // "Your Documents" Section (Screen 2)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Your Documents',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    GestureDetector(
                      onTap: widget.onViewAllDocuments,
                      child: const Text(
                        'View All',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Horizontal Carousel of Recent Documents
                SizedBox(
                  height: 154,
                  child: _loadingDocs
                      ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                      : _recentDocs.isNotEmpty
                          ? ListView.separated(
                              scrollDirection: Axis.horizontal,
                              itemCount: _recentDocs.length > 8 ? 8 : _recentDocs.length,
                              separatorBuilder: (_, __) => const SizedBox(width: 12),
                              itemBuilder: (context, index) {
                                final doc = _recentDocs[index];
                                final name = doc['image_name'] as String? ?? 'document_${index + 1}.jpg';
                                final rawUrl = doc['image_url'] as String? ?? '';
                                final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${ApiService.baseUrl}$rawUrl';
                                final text = doc['extracted_text'] as String? ?? '';

                                return DocumentCard(
                                  filename: name,
                                  imageUrl: fullUrl,
                                  subtitle: 'Recent • Indexed',
                                  onTap: () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => DocumentDetailScreen(
                                          title: name,
                                          imageUrl: fullUrl,
                                          extractedText: text,
                                          fileType: name.toLowerCase().endsWith('.pdf') ? 'PDF' : 'IMAGE',
                                          date: 'Recent',
                                        ),
                                      ),
                                    );
                                  },
                                );
                              },
                            )
                          : Container(
                              width: double.infinity,
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(color: AppTheme.border),
                              ),
                              child: Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.document_scanner_outlined, size: 36, color: AppTheme.textMuted),
                                    const SizedBox(height: 8),
                                    const Text('No documents scanned yet', style: TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                                    const SizedBox(height: 8),
                                    TextButton(
                                      onPressed: () {
                                        Navigator.of(context).push(
                                          MaterialPageRoute(builder: (_) => const CameraScanScreen()),
                                        ).then((_) => _checkServerAndLoadDocuments());
                                      },
                                      child: const Text('Scan your first document'),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFilterPill(String title) {
    final isSelected = _activeFilter == title;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: () {
          setState(() => _activeFilter = title);
          if (_searchController.text.isNotEmpty) {
            _triggerSearch();
          }
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primary : const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: isSelected ? AppTheme.primary : AppTheme.border),
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

  Widget _buildQuickActionCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    bool isWide = false,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
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
        child: isWide
            ? Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: AppTheme.primary, size: 22),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppTheme.textPrimary),
                        ),
                        Text(
                          subtitle,
                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: AppTheme.primary, size: 22),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppTheme.textPrimary),
                            ),
                            Text(
                              subtitle,
                              style: const TextStyle(fontSize: 11.5, color: AppTheme.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted, size: 18),
                    ],
                  ),
                ],
              ),
      ),
    );
  }
}
