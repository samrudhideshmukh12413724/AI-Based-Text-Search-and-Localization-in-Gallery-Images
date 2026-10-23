import 'dart:async';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:photo_manager/photo_manager.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class SyncFolderScreen extends StatefulWidget {
  const SyncFolderScreen({super.key});

  @override
  State<SyncFolderScreen> createState() => _SyncFolderScreenState();
}

class _SyncFolderScreenState extends State<SyncFolderScreen> {
  final ApiService _api = ApiService();

  bool _loadingAlbums = true;
  String? _permissionError;
  List<AssetPathEntity> _albums = [];
  final Map<String, int> _albumCounts = {};
  final Map<String, Uint8List?> _albumThumbnails = {};

  bool _syncing = false;
  int _totalFiles = 0;
  int _syncedFiles = 0;
  int _alreadySyncedCount = 0;
  String? _syncStatus;
  String? _currentAlbumName;
  Timer? _pollerTimer;

  @override
  void initState() {
    super.initState();
    _loadAlbums();
  }

  @override
  void dispose() {
    _pollerTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadAlbums() async {
    setState(() {
      _loadingAlbums = true;
      _permissionError = null;
    });

    if (kIsWeb) {
      setState(() {
        _loadingAlbums = false;
        _permissionError = 'Album browsing is optimized for mobile devices.';
      });
      return;
    }

    try {
      final PermissionState ps = await PhotoManager.requestPermissionExtend();
      if (!ps.isAuth && !ps.hasAccess) {
        setState(() {
          _loadingAlbums = false;
          _permissionError = 'Storage/Gallery permission was not granted. Tap "Grant Permission" below or use the Storage Directory Picker.';
        });
        return;
      }

      final List<AssetPathEntity> list = await PhotoManager.getAssetPathList(
        type: RequestType.image,
        hasAll: true,
      );

      // Sort albums so that popular document folders appear at the top
      list.sort((a, b) {
        final nameA = a.name.toLowerCase();
        final nameB = b.name.toLowerCase();
        int score(String n) {
          if (n.contains('screenshot')) return 1;
          if (n.contains('whatsapp')) return 2;
          if (n.contains('download')) return 3;
          if (n.contains('document') || n.contains('scan')) return 4;
          if (n.contains('camera') || n.contains('dcim')) return 5;
          if (n.contains('recent') || n.contains('all')) return 6;
          return 10;
        }
        return score(nameA).compareTo(score(nameB));
      });

      setState(() {
        _albums = list;
        _loadingAlbums = false;
      });

      // Load counts and thumbnail previews asynchronously
      for (final album in list) {
        final count = await album.assetCountAsync;
        _albumCounts[album.id] = count;
        if (count > 0) {
          try {
            final assets = await album.getAssetListRange(start: 0, end: 1);
            if (assets.isNotEmpty) {
              final thumb = await assets.first.thumbnailDataWithSize(
                const ThumbnailSize(120, 120),
                quality: 80,
              );
              if (mounted) {
                setState(() {
                  _albumThumbnails[album.id] = thumb;
                });
              }
            }
          } catch (_) {}
        }
        if (mounted) setState(() {});
      }
    } catch (e) {
      setState(() {
        _loadingAlbums = false;
        _permissionError = 'Could not load device albums: $e';
      });
    }
  }

  int _documentPriorityScore(String name) {
    final lower = name.toLowerCase();
    if (lower.contains('pan') || lower.contains('aadhaar') || lower.contains('aadhar')) return 0;
    if (lower.contains('passport') || lower.contains('voter') || lower.contains('license') || lower.contains('licence')) return 1;
    if (lower.contains('receipt') || lower.contains('invoice') || lower.contains('bill') || lower.contains('statement')) return 2;
    if (lower.contains('salary') || lower.contains('tax') || lower.contains('form') || lower.contains('certificate')) return 3;
    if (lower.contains('scan') || lower.contains('doc') || lower.contains('pdf')) return 4;
    return 10;
  }

  Future<void> _syncEntireAlbum(AssetPathEntity album) async {
    final int totalCount = await album.assetCountAsync;
    if (totalCount == 0) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Folder "${album.name}" has no photos or documents.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    int scanLimit = totalCount;
    if (totalCount > 100) {
      if (!mounted) return;
      final choice = await showDialog<int>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.folder_zip_rounded, color: Color(0xFF2563EB)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Sync "${album.name}"',
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'This folder contains $totalCount documents. Choose how many to index:',
                style: const TextStyle(fontSize: 13.5, color: Color(0xFF475569)),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.bolt, color: Color(0xFFD97706), size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Already-synced files are skipped automatically via fast hash check.',
                        style: TextStyle(fontSize: 11.5, color: Color(0xFF334155)),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, 100),
              child: const Text('Latest 100'),
            ),
            if (totalCount > 300)
              TextButton(
                onPressed: () => Navigator.pop(ctx, 300),
                child: const Text('Latest 300'),
              ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, totalCount),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              child: Text('All ($totalCount)', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      );
      if (choice != null) {
        scanLimit = choice;
      } else {
        return;
      }
    }

    setState(() {
      _syncing = true;
      _currentAlbumName = album.name;
      _totalFiles = scanLimit;
      _syncedFiles = 0;
      _alreadySyncedCount = 0;
      _syncStatus = 'Reading $scanLimit items from "${album.name}"...';
    });

    try {
      final List<AssetEntity> assets = await album.getAssetListRange(
        start: 0,
        end: scanLimit,
      );

      // Pre-check incremental sync
      setState(() {
        _syncStatus = 'Checking ${assets.length} items for duplicate or existing records...';
      });

      final checkList = assets.map((a) => {'filename': a.title ?? 'doc.jpg'}).toList();
      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missing = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySynced = (syncStatus['already_synced_count'] as int?) ?? (assets.length - missing.length);

      final toUpload = assets.where((a) => missing.contains(a.title)).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _syncing = false;
          _alreadySyncedCount = alreadySynced;
          _syncStatus = 'All ${assets.length} items in "${album.name}" are already up to date! ✅';
        });
        return;
      }

      // Sort by document priority then newest
      toUpload.sort((a, b) {
        final scoreA = _documentPriorityScore(a.title ?? '');
        final scoreB = _documentPriorityScore(b.title ?? '');
        if (scoreA != scoreB) return scoreA.compareTo(scoreB);
        final dateA = a.createDateTime;
        final dateB = b.createDateTime;
        return dateB.compareTo(dateA);
      });

      setState(() {
        _totalFiles = toUpload.length;
        _syncedFiles = 0;
        _syncStatus = 'Syncing ${toUpload.length} new items from "${album.name}" ($alreadySynced already cached)...';
      });

      int successCount = 0;
      const int concurrency = 3;

      for (int i = 0; i < toUpload.length; i += concurrency) {
        if (!_syncing) break;

        final end = (i + concurrency < toUpload.length) ? i + concurrency : toUpload.length;
        final chunk = toUpload.sublist(i, end);

        final futures = chunk.map((asset) async {
          final title = asset.title ?? 'document_${asset.id}.jpg';
          try {
            final file = await asset.file;
            Uint8List? bytes;
            if (file != null && await file.exists()) {
              bytes = await file.readAsBytes();
            } else {
              bytes = await asset.originBytes;
            }

            if (bytes != null && bytes.isNotEmpty) {
              await _api.uploadImageBytes(bytes, title, asyncProcessing: true);
              return true;
            }
          } catch (e) {
            debugPrint('Failed to sync $title: $e');
          }
          return false;
        }).toList();

        final results = await Future.wait(futures);
        for (final res in results) {
          if (res) {
            successCount++;
          }
        }

        if (mounted) {
          setState(() {
            _syncedFiles = end;
            _syncStatus = 'Uploading: $end/${toUpload.length} ($successCount sent, $alreadySynced skipped)...';
          });
        }
      }

      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'Finished syncing "${album.name}": $successCount new documents added to AI Vault! ($alreadySynced skipped)';
        });
        _startBackgroundPoller(successCount);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'Error syncing folder: $e';
        });
      }
    }
  }

  Future<void> _pickDirectoryFromStorage() async {
    try {
      final String? selectedDir = await FilePicker.getDirectoryPath();
      if (selectedDir == null || selectedDir.isEmpty) return;

      final dir = Directory(selectedDir);
      if (!await dir.exists()) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Cannot access this system path directly due to Android Scoped Storage. Please tap an album above!'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }

      setState(() {
        _syncing = true;
        _currentAlbumName = dir.path.split(Platform.pathSeparator).last;
        _syncStatus = 'Scanning directory: $_currentAlbumName...';
      });

      final List<File> files = [];
      await for (final entity in dir.list(recursive: true, followLinks: false)) {
        if (entity is File) {
          final p = entity.path.toLowerCase();
          if (p.endsWith('.jpg') || p.endsWith('.jpeg') || p.endsWith('.png') || p.endsWith('.webp') || p.endsWith('.pdf')) {
            files.add(entity);
          }
        }
      }

      if (files.isEmpty) {
        setState(() {
          _syncing = false;
          _syncStatus = 'No supported documents found in "$_currentAlbumName".';
        });
        return;
      }

      // Pre-check incremental sync
      final checkList = files.map((f) => {
        'filename': f.path.split(Platform.pathSeparator).last,
        'size': f.lengthSync(),
      }).toList();

      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missing = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySynced = (syncStatus['already_synced_count'] as int?) ?? (files.length - missing.length);

      final toUpload = files.where((f) {
        final name = f.path.split(Platform.pathSeparator).last;
        return missing.contains(name);
      }).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _syncing = false;
          _syncStatus = 'All ${files.length} documents in this directory are already synced! ✅';
        });
        return;
      }

      setState(() {
        _totalFiles = toUpload.length;
        _syncedFiles = 0;
        _alreadySyncedCount = alreadySynced;
        _syncStatus = 'Syncing ${toUpload.length} new documents ($alreadySynced skipped)...';
      });

      int successCount = 0;
      for (int i = 0; i < toUpload.length; i++) {
        if (!_syncing) break;
        final f = toUpload[i];
        final name = f.path.split(Platform.pathSeparator).last;

        setState(() {
          _syncedFiles = i + 1;
          _syncStatus = 'Uploading ${i + 1}/${toUpload.length}: $name...';
        });

        try {
          final bytes = await f.readAsBytes();
          await _api.uploadImageBytes(bytes, name, asyncProcessing: true);
          successCount++;
        } catch (_) {}
      }

      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'Successfully synced $successCount documents from directory! ($alreadySynced was already cached)';
        });
        _startBackgroundPoller(successCount);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'Storage directory scan error: $e';
        });
      }
    }
  }

  Future<void> _pickFilesWithSelectAllGuide() async {
    // Show quick guidance dialog so user knows how to Select All in Android file manager
    final shouldProceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Row(
          children: [
            Icon(Icons.tips_and_updates, color: Color(0xFFF59E0B)),
            SizedBox(width: 10),
            Text('Quick Tip', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ],
        ),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'How to select an ENTIRE folder in Android File Picker:',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5),
            ),
            SizedBox(height: 10),
            Text('1. Open any folder (e.g. WhatsApp, Downloads).', style: TextStyle(fontSize: 12.5)),
            SizedBox(height: 4),
            Text('2. Press and HOLD any photo until a checkmark appears.', style: TextStyle(fontSize: 12.5)),
            SizedBox(height: 4),
            Text('3. Tap the 3 dots (⋮) in the top-right corner.', style: TextStyle(fontSize: 12.5)),
            SizedBox(height: 4),
            Text('4. Tap "Select All" ➔ Tap "Select" to sync everything!', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: AppTheme.primary)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
            child: const Text('Open File Picker', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (shouldProceed != true) return;

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
        _syncStatus = 'Checking ${files.length} selected files...';
      });

      final checkList = files.map((f) => {'filename': f.name, 'size': f.size}).toList();
      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missing = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySynced = (syncStatus['already_synced_count'] as int?) ?? (files.length - missing.length);

      final toUpload = files.where((f) => missing.contains(f.name)).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _syncing = false;
          _syncStatus = 'All ${files.length} files are already synced! ✅';
        });
        return;
      }

      setState(() {
        _totalFiles = toUpload.length;
        _syncedFiles = 0;
        _alreadySyncedCount = alreadySynced;
        _syncStatus = 'Syncing ${toUpload.length} files ($alreadySynced skipped)...';
      });

      int successCount = 0;
      for (int i = 0; i < toUpload.length; i++) {
        if (!_syncing) break;
        final f = toUpload[i];
        if (f.bytes == null) continue;

        setState(() {
          _syncedFiles = i + 1;
          _syncStatus = 'Uploading ${i + 1}/${toUpload.length}: ${f.name}...';
        });

        try {
          await _api.uploadImageBytes(f.bytes!, f.name, asyncProcessing: true);
          successCount++;
        } catch (_) {}
      }

      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'Uploaded $successCount new files successfully! ($alreadySynced skipped)';
        });
        _startBackgroundPoller(successCount);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _syncing = false;
          _syncStatus = 'File picker sync error: $e';
        });
      }
    }
  }

  void _startBackgroundPoller(int count) {
    if (count <= 0) return;
    _pollerTimer?.cancel();
    int ticks = 0;
    _pollerTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      ticks++;
      try {
        final status = await _api.getSyncStatus();
        final queued = (status['queued'] as int?) ?? 0;
        final active = (status['active'] as int?) ?? 0;
        final bool isActive = (status['is_active'] as bool?) ?? false;

        if (mounted) {
          if (!isActive && queued == 0 && active == 0) {
            timer.cancel();
            setState(() {
              _syncStatus = 'AI Vault Indexing Complete! All synced documents are now searchable.';
            });
          } else if (ticks > 25) {
            timer.cancel();
          } else {
            setState(() {
              _syncStatus = 'AI Model is indexing text & embeddings ($active active, $queued in queue)...';
            });
          }
        }
      } catch (_) {
        if (ticks > 20) timer.cancel();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Sync Phone Folders', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text('Ingest whole albums with 1 tap into AI Vault', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Reload Folders',
            onPressed: _loadingAlbums ? null : _loadAlbums,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Active Sync Status Banner (if syncing or completed)
            if (_syncStatus != null) ...[
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _syncing ? const Color(0xFFEFF6FF) : const Color(0xFFF0FDF4),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: _syncing ? const Color(0xFF93C5FD) : const Color(0xFF86EFAC),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (_syncing)
                          const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2.5, color: Color(0xFF2563EB)),
                          )
                        else
                          const Icon(Icons.check_circle_rounded, size: 22, color: Color(0xFF16A34A)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _syncing
                                ? 'Syncing ${_currentAlbumName != null ? "\"$_currentAlbumName\"" : "Folder"}...'
                                : 'Sync Complete',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: _syncing ? const Color(0xFF1E40AF) : const Color(0xFF166534),
                            ),
                          ),
                        ),
                        if (_syncing)
                          TextButton(
                            onPressed: () => setState(() => _syncing = false),
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text('STOP', style: TextStyle(color: Color(0xFFDC2626), fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _syncStatus!,
                      style: TextStyle(
                        fontSize: 12.5,
                        color: _syncing ? const Color(0xFF334155) : const Color(0xFF15803D),
                        height: 1.3,
                      ),
                    ),
                    if (_syncing && _totalFiles > 0) ...[
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: _syncedFiles / _totalFiles,
                          minHeight: 6,
                          backgroundColor: Colors.white,
                          color: const Color(0xFF2563EB),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '$_syncedFiles of $_totalFiles uploaded${_alreadySyncedCount > 0 ? " • $_alreadySyncedCount already cached" : ""}',
                            style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                          ),
                          Text(
                            '${((_syncedFiles / _totalFiles) * 100).toInt()}%',
                            style: const TextStyle(fontSize: 11, color: Color(0xFF2563EB), fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],

            // Action Bar for Alternative Pickers
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _syncing ? null : _pickDirectoryFromStorage,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                        backgroundColor: Colors.white,
                        side: const BorderSide(color: Color(0xFFCBD5E1)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.drive_folder_upload, size: 18, color: Color(0xFF0F172A)),
                      label: const Text(
                        'Storage Folder (SAF)',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _syncing ? null : _pickFilesWithSelectAllGuide,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                        backgroundColor: Colors.white,
                        side: const BorderSide(color: Color(0xFFCBD5E1)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.checklist_rtl_rounded, size: 18, color: Color(0xFF0F172A)),
                      label: const Text(
                        'Multi-File Picker',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 6),

            // Header for Album List
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              child: Row(
                children: [
                  const Icon(Icons.photo_library_rounded, size: 16, color: Color(0xFF64748B)),
                  const SizedBox(width: 8),
                  const Text(
                    'CHOOSE A PHONE FOLDER TO SYNC ENTIRELY:',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF64748B),
                      letterSpacing: 0.5,
                    ),
                  ),
                  const Spacer(),
                  if (_albums.isNotEmpty)
                    Text(
                      '${_albums.length} folders',
                      style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8), fontWeight: FontWeight.w600),
                    ),
                ],
              ),
            ),

            // Main Content: Album Cards
            Expanded(
              child: _loadingAlbums
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircularProgressIndicator(strokeWidth: 3, color: AppTheme.primary),
                          SizedBox(height: 14),
                          Text('Discovering phone folders and albums...', style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
                        ],
                      ),
                    )
                  : _permissionError != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.lock_open_rounded, size: 54, color: Color(0xFFE11D48)),
                                const SizedBox(height: 14),
                                const Text(
                                  'Gallery Permission Required',
                                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  _permissionError!,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
                                ),
                                const SizedBox(height: 20),
                                ElevatedButton.icon(
                                  onPressed: () async {
                                    await PhotoManager.openSetting();
                                  },
                                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
                                  icon: const Icon(Icons.settings, size: 18, color: Colors.white),
                                  label: const Text('Open App Settings', style: TextStyle(color: Colors.white)),
                                ),
                                const SizedBox(height: 10),
                                TextButton(
                                  onPressed: _loadAlbums,
                                  child: const Text('Try Again'),
                                ),
                              ],
                            ),
                          ),
                        )
                      : _albums.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.folder_off_outlined, size: 48, color: Color(0xFF94A3B8)),
                                  const SizedBox(height: 12),
                                  const Text('No photo folders found on device', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                                  const SizedBox(height: 6),
                                  const Text('Use the "Storage Folder (SAF)" button above to select any custom folder.', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                  const SizedBox(height: 16),
                                  ElevatedButton(
                                    onPressed: _pickDirectoryFromStorage,
                                    child: const Text('Select Storage Folder'),
                                  ),
                                ],
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              itemCount: _albums.length,
                              separatorBuilder: (_, __) => const SizedBox(height: 8),
                              itemBuilder: (ctx, idx) {
                                final album = _albums[idx];
                                final count = _albumCounts[album.id] ?? 0;
                                final thumb = _albumThumbnails[album.id];
                                final isCurrentlySyncing = _syncing && _currentAlbumName == album.name;

                                return Container(
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                      color: isCurrentlySyncing ? const Color(0xFF3B82F6) : const Color(0xFFE2E8F0),
                                      width: isCurrentlySyncing ? 2 : 1,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withValues(alpha: 0.02),
                                        blurRadius: 6,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                  ),
                                  child: ListTile(
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                    leading: ClipRRect(
                                      borderRadius: BorderRadius.circular(10),
                                      child: Container(
                                        width: 50,
                                        height: 50,
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFEFF6FF),
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        child: thumb != null
                                            ? Image.memory(thumb, fit: BoxFit.cover)
                                            : const Icon(Icons.folder, color: Color(0xFF2563EB), size: 28),
                                      ),
                                    ),
                                    title: Text(
                                      album.name,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 14.5,
                                        color: Color(0xFF0F172A),
                                      ),
                                    ),
                                    subtitle: Text(
                                      '$count items in this folder',
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF64748B),
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    trailing: SizedBox(
                                      height: 38,
                                      child: ElevatedButton(
                                        onPressed: (_syncing || count == 0) ? null : () => _syncEntireAlbum(album),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(0xFF2563EB),
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(horizontal: 14),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                          elevation: 0,
                                        ),
                                        child: isCurrentlySyncing
                                            ? const SizedBox(
                                                width: 16,
                                                height: 16,
                                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                              )
                                            : const Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(Icons.sync, size: 16, color: Colors.white),
                                                  SizedBox(width: 6),
                                                  Text('SYNC ALL', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
                                                ],
                                              ),
                                      ),
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
}
