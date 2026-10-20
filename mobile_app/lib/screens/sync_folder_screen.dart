import 'dart:async';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class SyncFolderScreen extends StatefulWidget {
  const SyncFolderScreen({super.key});

  @override
  State<SyncFolderScreen> createState() => _SyncFolderScreenState();
}

class _SyncFolderScreenState extends State<SyncFolderScreen> {
  final ApiService _api = ApiService();
  final String _selectedPath = '/storage/emulated/0/Documents';
  bool _syncing = false;
  int _totalFiles = 0;
  int _syncedFiles = 0;
  String? _syncStatus;
  Timer? _pollerTimer;

  @override
  void dispose() {
    _pollerTimer?.cancel();
    super.dispose();
  }

  Future<void> _chooseAndSyncFiles() async {
    try {
      final result = await FilePicker.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png', 'webp', 'pdf'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final files = result.files;
      setState(() {
        _syncing = true;
        _totalFiles = files.length;
        _syncedFiles = 0;
        _syncStatus = 'Checking ${files.length} documents for incremental sync...';
      });

      // Incremental sync pre-check
      final checkList = files.map((f) => {'filename': f.name, 'size': f.size}).toList();
      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missingNames = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySyncedCount = (syncStatus['already_synced_count'] as int?) ?? (files.length - missingNames.length);

      final toUpload = files.where((f) => missingNames.contains(f.name)).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _syncing = false;
          _syncStatus = 'All $alreadySyncedCount documents are already up to date! ✅';
        });
        return;
      }

      setState(() {
        _syncStatus = 'Uploading ${toUpload.length} new documents ($alreadySyncedCount already indexed)...';
      });

      int successCount = 0;
      for (int i = 0; i < toUpload.length; i++) {
        if (!_syncing) break;
        final f = toUpload[i];
        if (f.bytes == null) continue;

        setState(() {
          _syncedFiles = i + 1;
          _syncStatus = 'Ingesting document ${i + 1} of ${toUpload.length} (${f.name})...';
        });

        try {
          await _api.uploadImageBytes(f.bytes!, f.name, asyncProcessing: true);
          successCount++;
        } catch (_) {}
      }

      setState(() {
        _syncing = false;
        _syncStatus = 'Synced $successCount new documents successfully! ($alreadySyncedCount was already cached)';
      });
    } catch (e) {
      setState(() {
        _syncing = false;
        _syncStatus = 'Sync error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text('Sync Folder', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            children: [
              const Spacer(flex: 1),

              // Folder Illustration
              Container(
                width: 120,
                height: 120,
                decoration: const BoxDecoration(
                  color: Color(0xFFF5F3FF), // Soft violet
                  shape: BoxShape.circle,
                ),
                child: Center(
                  child: Container(
                    width: 82,
                    height: 82,
                    decoration: BoxDecoration(
                      color: AppTheme.primaryContainer,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: const Stack(
                      alignment: Alignment.center,
                      children: [
                        Icon(Icons.folder_copy_rounded, size: 42, color: AppTheme.primary),
                        Positioned(
                          right: 14,
                          bottom: 14,
                          child: Icon(Icons.sync_rounded, size: 22, color: Color(0xFF4338CA)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 28),

              // Title & Subtitle
              const Text(
                'Sync Your Folder',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Keep your important documents\nsynced and searchable in real time.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 36),

              // Sync Progress Status (if active or finished)
              if (_syncStatus != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: _syncing ? const Color(0xFFEFF6FF) : const Color(0xFFECFDF5),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: _syncing ? const Color(0xFFBFDBFE) : const Color(0xFFA7F3D0)),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          if (_syncing)
                            const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                            )
                          else
                            const Icon(Icons.check_circle_rounded, size: 18, color: AppTheme.success),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              _syncStatus!,
                              style: TextStyle(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w600,
                                color: _syncing ? const Color(0xFF1E40AF) : const Color(0xFF065F46),
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (_syncing && _totalFiles > 0) ...[
                        const SizedBox(height: 10),
                        LinearProgressIndicator(
                          value: _syncedFiles / _totalFiles,
                          backgroundColor: Colors.white,
                          color: AppTheme.primary,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ],

              // Choose Folder Button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _syncing ? null : _chooseAndSyncFiles,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text(
                    'Choose Folder',
                    style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Sync Settings Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('⚙️ Incremental Sync & SHA-256 deduplication is active'),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  },
                  style: OutlinedButton.styleFrom(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    side: const BorderSide(color: AppTheme.border, width: 1.2),
                  ),
                  child: const Text(
                    'Sync Settings',
                    style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                  ),
                ),
              ),

              const Spacer(flex: 2),

              // Selected Folder Tile
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: const Icon(Icons.folder_outlined, color: AppTheme.primary, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Selected folder',
                            style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _selectedPath,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}
