import 'dart:async';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:photo_manager/photo_manager.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/search_result.dart';
import '../services/api_service.dart';
import 'sync_folder_screen.dart';

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
  bool _showFullExtractedText = false;
  final Set<int> _expandedRawTextIds = <int>{};
  final Map<int, List<RelatedImage>> _cachedRelationships = {};
  final Map<int, int?> _cachedCanonicalIds = {};
  final Set<int> _loadingRelIds = <int>{};
  final Set<int> _expandedRelIds = <int>{};
  final Map<int, String> _relErrors = {};

  int _batchTotal = 0;
  int _batchCurrent = 0;
  String? _batchStatus;
  Timer? _syncPollerTimer;
  int _searchRequestId = 0;

  int _documentPriorityScore(String filename) {
    final lower = filename.toLowerCase();
    const highKeywords = [
      'pan', 'aadhaar', 'aadhar', 'receipt', 'invoice', 'bill', 'cert',
      'marksheet', 'id', 'card', 'college', 'exam', 'admit', 'admission',
      'fees', 'fee', 'salary', 'form', 'pass', 'bonafide', 'hallticket',
      'transcript', 'degree', 'diploma', 'voter', 'license', 'passport',
      'challan', 'bank', 'statement', 'tuition', 'screenshot', 'screen', 'scan', 'cam'
    ];
    for (final kw in highKeywords) {
      if (lower.contains(kw)) return 0; // High priority document (indexes first)
    }
    return 1; // Standard photo
  }

  void _startBackgroundSyncPoller(int successCount, int alreadySyncedCount) {
    _syncPollerTimer?.cancel();
    int pollerCycles = 0;
    _syncPollerTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      pollerCycles++;
      if (!mounted || pollerCycles > 60) {
        timer.cancel();
        return;
      }
      try {
        final status = await _api.getSyncStatus();
        final queued = (status['queued'] as int?) ?? 0;
        final active = (status['active'] as int?) ?? 0;
        final bool isActive = (status['is_active'] as bool?) ?? false;

        if (mounted) {
          if (isActive && (queued > 0 || active > 0)) {
            setState(() {
              _batchStatus = 'AI Indexing in progress ($active active, $queued queued)';
            });
          } else {
            setState(() {
              _batchStatus = 'Synced $successCount new documents ($alreadySyncedCount up to date). Indexing complete.';
            });
            timer.cancel();
            // If user has an active query, refresh search results safely
            if (_hasSearched && _searchController.text.trim().isNotEmpty) {
              _search();
            }
          }
        }
      } catch (_) {
        timer.cancel();
      }
    });
  }

  Future<void> _pickImage() async {
    setState(() {
      _error = null;
      _extractedText = '';
      _batchStatus = null;
    });
    try {
      final file = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1600,
        maxHeight: 1600,
        imageQuality: 88,
      );
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

  Future<void> _syncDirectoryFromStorage() async {
    try {
      final String? selectedDir = await FilePicker.getDirectoryPath();
      if (selectedDir == null || selectedDir.isEmpty) return;

      final dir = Directory(selectedDir);
      if (!await dir.exists()) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Storage path is restricted by Android Scoped Storage. Please tap any phone album to sync!'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        return;
      }

      final dirName = dir.path.split(Platform.pathSeparator).last;
      setState(() {
        _loading = true;
        _batchStatus = 'Scanning folder "$dirName" for documents...';
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
          _loading = false;
          _batchStatus = 'No supported documents found in "$dirName".';
        });
        return;
      }

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
          _loading = false;
          _batchStatus = 'All ${files.length} documents in "$dirName" are already synced! (0 new files)';
        });
        return;
      }

      setState(() {
        _batchTotal = toUpload.length;
        _batchCurrent = 0;
        _batchStatus = 'Syncing ${toUpload.length} documents from "$dirName" ($alreadySynced already cached)...';
      });

      int successCount = 0;
      int failedCount = 0;
      const int concurrency = 3;

      for (int i = 0; i < toUpload.length; i += concurrency) {
        if (!_loading) break;
        final end = (i + concurrency < toUpload.length) ? i + concurrency : toUpload.length;
        final chunk = toUpload.sublist(i, end);

        final futures = chunk.map((f) async {
          final name = f.path.split(Platform.pathSeparator).last;
          try {
            final bytes = await f.readAsBytes();
            if (bytes.isNotEmpty) {
              await _api.uploadImageBytes(bytes, name, asyncProcessing: true);
              return true;
            }
          } catch (e) {
            debugPrint('Error uploading $name: $e');
          }
          return false;
        }).toList();

        final results = await Future.wait(futures);
        for (final res in results) {
          if (res) {
            successCount++;
          } else {
            failedCount++;
          }
        }

        if (mounted) {
          setState(() {
            _batchCurrent = end;
            _batchStatus = 'Uploading: $end/${toUpload.length} ($successCount sent, $alreadySynced skipped)...';
          });
        }
      }

      if (mounted) {
        setState(() {
          _loading = false;
          _batchStatus = failedCount > 0
              ? 'Finished syncing "$dirName": $successCount new documents indexed ($failedCount errors, $alreadySynced skipped)'
              : 'Finished syncing "$dirName": $successCount new documents indexed! ($alreadySynced skipped)';
        });
        if (_hasSearched && _searchController.text.trim().isNotEmpty) {
          _search();
        }
        if (successCount > 0) {
          _startBackgroundSyncPoller(successCount, alreadySynced);
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Storage directory sync error: $e';
        });
      }
    }
  }

  Future<void> _syncMobileFolderWithFilePicker() async {
    if (mounted) {
      final shouldProceed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: const Row(
            children: [
              Icon(Icons.tips_and_updates, color: Color(0xFFF59E0B)),
              SizedBox(width: 10),
              Text('How to Select All', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          content: const Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'To select an entire folder of photos:',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5),
              ),
              SizedBox(height: 10),
              Text('1. Tap and HOLD any photo in the folder.', style: TextStyle(fontSize: 12.5)),
              SizedBox(height: 4),
              Text('2. Tap the 3 dots (⋮) in the top-right corner.', style: TextStyle(fontSize: 12.5)),
              SizedBox(height: 4),
              Text('3. Tap "Select All" ➔ Tap "Select" to sync everything!', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Color(0xFF2563EB))),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2563EB)),
              child: const Text('Open File Picker', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
      if (shouldProceed != true) return;
    }

    try {
      final result = await FilePicker.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png', 'webp'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final files = result.files;
      setState(() {
        _loading = true;
        _batchTotal = files.length;
        _batchCurrent = 0;
        _batchStatus = 'Checking ${files.length} documents for incremental sync...';
      });

      // Step 1: Pre-check with backend to skip already-indexed documents
      final checkList = files.map((f) => {'filename': f.name, 'size': f.size}).toList();
      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missingNames = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySyncedCount = (syncStatus['already_synced_count'] as int?) ?? (files.length - missingNames.length);

      final toUpload = files.where((f) => missingNames.contains(f.name)).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _batchStatus = 'All ${files.length} documents are already synced (0 new files).';
        });
        return;
      }

      // Priority sort: important documents (PAN, Aadhaar, receipts, forms) first!
      toUpload.sort((a, b) {
        final scoreA = _documentPriorityScore(a.name);
        final scoreB = _documentPriorityScore(b.name);
        return scoreA.compareTo(scoreB);
      });

      setState(() {
        _batchTotal = toUpload.length;
        _batchCurrent = 0;
        _batchStatus = 'Syncing ${toUpload.length} new documents ($alreadySyncedCount already up to date)...';
      });

      int successCount = 0;
      int failedCount = 0;
      const int concurrency = 3;

      for (int i = 0; i < toUpload.length; i += concurrency) {
        if (!_loading) {
          debugPrint('Sync canceled by user');
          break;
        }

        final end = (i + concurrency < toUpload.length) ? i + concurrency : toUpload.length;
        final chunk = toUpload.sublist(i, end);

        final futures = chunk.map((f) async {
          final name = f.name;
          Uint8List? bytes = f.bytes;
          if (bytes == null && f.path != null) {
            try {
              bytes = await File(f.path!).readAsBytes();
            } catch (e) {
              debugPrint('Error reading file $name: $e');
            }
          }
          if (bytes != null && bytes.isNotEmpty) {
            try {
              await _api.uploadImageBytes(bytes, name, asyncProcessing: true);
              return true;
            } catch (e) {
              debugPrint('Error uploading $name: $e');
              return false;
            }
          }
          return false;
        }).toList();

        final results = await Future.wait(futures);
        for (final res in results) {
          if (res) {
            successCount++;
          } else {
            failedCount++;
          }
        }

        if (mounted) {
          setState(() {
            _batchCurrent = end;
            _batchStatus = 'Uploading: $end/${toUpload.length} ($successCount sent, $alreadySyncedCount skipped)...';
          });
        }
      }

      if (mounted) {
        setState(() {
          _loading = false;
          _batchStatus = failedCount > 0
              ? 'Uploaded $successCount documents ($failedCount skipped). AI background indexing active.'
              : 'Uploaded $successCount documents. AI background indexing active.';
        });
        if (_hasSearched && _searchController.text.trim().isNotEmpty) {
          _search();
        }
        if (successCount > 0) {
          _startBackgroundSyncPoller(successCount, alreadySyncedCount);
        }
      }
    } catch (e) {
      setState(() => _error = 'Folder sync error: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _syncFolder() async {
    setState(() {
      _error = null;
      _batchStatus = null;
    });

    if (kIsWeb) {
      await _syncMobileFolderWithFilePicker();
      return;
    }

    try {
      final PermissionState ps = await PhotoManager.requestPermissionExtend();
      if (!ps.isAuth && !ps.hasAccess) {
        await _syncMobileFolderWithFilePicker();
        return;
      }

      final List<AssetPathEntity> rawAlbums = await PhotoManager.getAssetPathList(
        type: RequestType.image,
      );

      if (!mounted) return;

      if (rawAlbums.isEmpty) {
        await _syncMobileFolderWithFilePicker();
        return;
      }

      // Filter and separate specific folders (Camera, WhatsApp, Downloads, etc.)
      final List<AssetPathEntity> albums = rawAlbums;

      final selectedAlbum = await showModalBottomSheet<dynamic>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (ctx) {
          return SafeArea(
            child: Container(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(ctx).size.height * 0.75,
              ),
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEFF6FF),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(Icons.folder_copy, color: Color(0xFF2563EB), size: 24),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Sync a Mobile Folder',
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Tap any 1 folder below to sync all documents inside it',
                                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Action Cards for Full Hub & Storage Directory
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () => Navigator.of(ctx).pop('sync_hub'),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEFF6FF),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFF93C5FD)),
                              ),
                              child: const Column(
                                children: [
                                  Icon(Icons.folder_shared_rounded, color: Color(0xFF2563EB), size: 24),
                                  SizedBox(height: 6),
                                  Text(
                                    'Folder Sync Hub',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Color(0xFF1E40AF)),
                                  ),
                                  SizedBox(height: 2),
                                  Text(
                                    'Visual Album Browser',
                                    style: TextStyle(fontSize: 10, color: Color(0xFF3B82F6)),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: InkWell(
                            onTap: () => Navigator.of(ctx).pop('storage_dir'),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF0FDF4),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFF86EFAC)),
                              ),
                              child: const Column(
                                children: [
                                  Icon(Icons.drive_folder_upload, color: Color(0xFF16A34A), size: 24),
                                  SizedBox(height: 6),
                                  Text(
                                    'Storage Folder',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Color(0xFF166534)),
                                  ),
                                  SizedBox(height: 2),
                                  Text(
                                    'Internal Storage SAF',
                                    style: TextStyle(fontSize: 10, color: Color(0xFF15803D)),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: InkWell(
                            onTap: () => Navigator.of(ctx).pop('file_picker'),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFFCBD5E1)),
                              ),
                              child: const Column(
                                children: [
                                  Icon(Icons.checklist_rtl_rounded, color: Color(0xFF475569), size: 24),
                                  SizedBox(height: 6),
                                  Text(
                                    'Multi-Files',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Color(0xFF334155)),
                                  ),
                                  SizedBox(height: 2),
                                  Text(
                                    'With Select All tip',
                                    style: TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                    child: Text(
                      'OR CHOOSE A PHONE FOLDER BELOW (1-TAP SYNC ENTIRE FOLDER):',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 0.5),
                    ),
                  ),
                  const Divider(height: 1, color: Color(0xFFE2E8F0)),
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: albums.length,
                      separatorBuilder: (_, __) => const Divider(height: 1, indent: 64, color: Color(0xFFF1F5F9)),
                      itemBuilder: (ctx, idx) {
                        final album = albums[idx];
                        return FutureBuilder<int>(
                          future: album.assetCountAsync,
                          builder: (ctx, snap) {
                            final count = snap.data ?? 0;
                            return ListTile(
                              leading: Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: const Color(0xFFEFF6FF),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: const Color(0xFFBFDBFE)),
                                ),
                                child: const Icon(Icons.folder, color: Color(0xFF2563EB), size: 24),
                              ),
                              title: Text(
                                album.name,
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF0F172A)),
                              ),
                              subtitle: Text(
                                '$count photos • Tap to sync WHOLE folder',
                                style: const TextStyle(fontSize: 11.5, color: Color(0xFF2563EB), fontWeight: FontWeight.w500),
                              ),
                              trailing: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF15803D),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Text(
                                  'SYNC ALL',
                                  style: TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.bold),
                                ),
                              ),
                              onTap: () => Navigator.of(ctx).pop(album),
                            );
                          },
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );

      if (selectedAlbum == null || !mounted) return;

      if (selectedAlbum == 'sync_hub') {
        await Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const SyncFolderScreen()),
        );
        return;
      }

      if (selectedAlbum == 'storage_dir') {
        await _syncDirectoryFromStorage();
        return;
      }

      if (selectedAlbum == 'file_picker') {
        await _syncMobileFolderWithFilePicker();
        return;
      }

      final AssetPathEntity album = selectedAlbum as AssetPathEntity;
      final int totalCount = await album.assetCountAsync;
      if (totalCount == 0) {
        setState(() => _error = 'Selected folder "${album.name}" is empty.');
        return;
      }

      int scanLimit = totalCount;
      if (totalCount > 100) {
        if (!mounted) return;
        final choice = await showDialog<int>(
          context: context,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                const Icon(Icons.flash_on, color: Color(0xFFF59E0B)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Sync "${album.name}"',
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            content: Text(
              'This folder has $totalCount items. How would you like to sync?\n\n'
              'Quick Scan (Latest 100): Scans your recent documents (PAN card, Aadhaar, receipts) in seconds.\n\n'
              '📦 Extended (Latest 500): Scans the latest 500 photos.\n\n'
              'Full Sync (All $totalCount): Indexes the complete album.',
              style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, 100),
                child: const Text('Quick (100)'),
              ),
              if (totalCount > 500)
                TextButton(
                  onPressed: () => Navigator.pop(ctx, 500),
                  child: const Text('📦 Latest 500'),
                ),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, totalCount),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2563EB)),
                child: Text('All ($totalCount)'),
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
        _loading = true;
        _batchTotal = scanLimit;
        _batchCurrent = 0;
        _batchStatus = 'Reading folder "${album.name}" ($scanLimit photos)...';
      });

      final List<AssetEntity> assets = await album.getAssetListRange(
        start: 0,
        end: scanLimit,
      );

      // Pre-check for incremental sync: skip already-indexed files
      setState(() {
        _batchStatus = 'Checking ${assets.length} items in "${album.name}" for updates...';
      });
      final checkList = assets.map((a) => {'filename': a.title ?? 'doc.jpg'}).toList();
      final syncStatus = await _api.checkImagesForSync(checkList);
      final List<String> missing = (syncStatus['missing'] as List<dynamic>?)?.cast<String>() ?? [];
      final int alreadySyncedCount = (syncStatus['already_synced_count'] as int?) ?? (assets.length - missing.length);

      final toUpload = assets.where((a) => missing.contains(a.title)).toList();

      if (toUpload.isEmpty) {
        setState(() {
          _batchStatus = 'All ${assets.length} items in "${album.name}" are already synced (0 new).';
        });
        return;
      }

      // Priority sort: documents (PAN, Aadhaar, receipts, forms) first, followed by newest photos!
      toUpload.sort((a, b) {
        final scoreA = _documentPriorityScore(a.title ?? '');
        final scoreB = _documentPriorityScore(b.title ?? '');
        if (scoreA != scoreB) return scoreA.compareTo(scoreB);
        final dateA = a.createDateTime;
        final dateB = b.createDateTime;
        return dateB.compareTo(dateA); // Newest first
      });

      setState(() {
        _batchTotal = toUpload.length;
        _batchCurrent = 0;
        _batchStatus = 'Syncing ${toUpload.length} new items from "${album.name}" ($alreadySyncedCount already up to date)...';
      });

      int successCount = 0;
      int failedCount = 0;
      const int concurrency = 3;

      for (int i = 0; i < toUpload.length; i += concurrency) {
        if (!_loading) {
          debugPrint('Folder sync canceled by user at $i/${toUpload.length}');
          break;
        }

        final end = (i + concurrency < toUpload.length) ? i + concurrency : toUpload.length;
        final chunk = toUpload.sublist(i, end);

        final futures = chunk.map((asset) async {
          final name = asset.title ?? 'doc_${asset.id}.jpg';
          try {
            Uint8List? bytes;
            try {
              bytes = await asset.thumbnailDataWithSize(const ThumbnailSize(1600, 1600), quality: 85);
            } catch (_) {}
            if (bytes == null || bytes.isEmpty) {
              final file = await asset.file;
              if (file != null) {
                bytes = await file.readAsBytes();
              }
            }
            if (bytes != null && bytes.isNotEmpty) {
              await _api.uploadImageBytes(bytes, name, asyncProcessing: true);
              return true;
            }
            return false;
          } catch (e) {
            debugPrint('Error uploading $name: $e');
            return false;
          }
        }).toList();

        final results = await Future.wait(futures);
        for (final res in results) {
          if (res) {
            successCount++;
          } else {
            failedCount++;
          }
        }

        if (mounted) {
          setState(() {
            _batchCurrent = end;
            _batchStatus = 'Transferred: $end/${toUpload.length} ($successCount sent, $alreadySyncedCount skipped)...';
          });
        }
      }

      if (mounted) {
        setState(() {
          _loading = false;
          _batchStatus = failedCount > 0
              ? 'Uploaded $successCount photos ($failedCount skipped). AI background indexing active.'
              : 'Uploaded $successCount photos. AI background indexing active.';
        });
        if (_hasSearched && _searchController.text.trim().isNotEmpty) {
          _search();
        }
        if (successCount > 0) {
          _startBackgroundSyncPoller(successCount, alreadySyncedCount);
        }
      }
    } catch (e) {
      debugPrint('Error in folder sync: $e');
      await _syncMobileFolderWithFilePicker();
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _pickAndSyncGallery() async {
    await _syncFolder();
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
          _extractedText += '\n\nVisual Objects Detected: $visSum';
        }
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _results = [];
    _hasSearched = false;
  }

  void _clearSearch() {
    _searchRequestId++;
    _searchController.clear();
    if (mounted) {
      setState(() {
        _results = [];
        _hasSearched = false;
        _searchType = null;
        _searchMessage = null;
        _error = null;
        _loading = false;
      });
    }
  }

  Future<void> _search([String? queryOverride]) async {
    final q = queryOverride ?? _searchController.text.trim();
    if (q.isEmpty) {
      _clearSearch();
      return;
    }
    final reqId = ++_searchRequestId;
    setState(() {
      _loading = true;
      _error = null;
      _hasSearched = true;
    });
    try {
      final response = await _api.search(q);
      if (!mounted || reqId != _searchRequestId) return;
      if (_searchController.text.trim().isEmpty) {
        _clearSearch();
        return;
      }
      setState(() {
        _results = response.results;
        _searchType = response.searchType;
        _searchMessage = response.message;
      });
    } catch (e) {
      if (!mounted || reqId != _searchRequestId) return;
      setState(() {
        _error = e.toString();
        _results = [];
      });
    } finally {
      if (mounted && reqId == _searchRequestId) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _scanViaCamera() async {
    setState(() {
      _error = null;
      _extractedText = '';
      _batchStatus = null;
    });
    try {
      final file = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1600,
        maxHeight: 1600,
        imageQuality: 88,
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() {
        _selectedImageBytes = bytes;
        _selectedImageName = file.name;
      });
      await _extractText();
    } catch (e) {
      setState(() => _error = 'Camera capture failed: $e');
    }
  }

  void _copyToClipboard(String text, {String? successMessage}) {
    if (text.trim().isEmpty) return;
    Clipboard.setData(ClipboardData(text: text.trim()));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                successMessage ?? 'Copied to clipboard!',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF15803D),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }

  Future<void> _launchActionUrl(String urlString) async {
    try {
      final uri = Uri.parse(urlString);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        _copyToClipboard(urlString, successMessage: 'Copied $urlString');
      }
    } catch (_) {
      _copyToClipboard(urlString, successMessage: 'Copied $urlString');
    }
  }

  Future<void> _launchUpiOrCopy(BuildContext context, String upiId) async {
    try {
      final uri = Uri.parse('upi://pay?pa=$upiId&pn=Payee&cu=INR');
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      } else {
        _copyToClipboard(upiId, successMessage: 'UPI ID "$upiId" copied! Open GPay/PhonePe to pay.');
      }
    } catch (_) {
      _copyToClipboard(upiId, successMessage: 'UPI ID "$upiId" copied! Open GPay/PhonePe to pay.');
    }
  }

  void _showSelectableTextSheet(BuildContext context, String title, String fullText) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.75,
        minChildSize: 0.4,
        maxChildSize: 0.95,
        expand: false,
        builder: (ctx, scrollController) => Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.copy_all, color: Color(0xFF2563EB)),
                    tooltip: 'Copy all text',
                    onPressed: () {
                      _copyToClipboard(fullText, successMessage: 'All document text copied!');
                      Navigator.of(ctx).pop();
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(ctx).pop(),
                  ),
                ],
              ),
              const Text(
                'Drag touch cursor across words to select, highlight, and copy specific sections:',
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
              ),
              const Divider(height: 16),
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: SelectableText(
                      fullText.trim().isEmpty ? '(no text extracted from this document)' : fullText,
                      style: const TextStyle(fontSize: 14, height: 1.6, color: Color(0xFF0F172A)),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _exportPdf(String pdfUrl, String docName) async {
    try {
      final uri = Uri.parse(pdfUrl);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        _copyToClipboard(pdfUrl, successMessage: 'PDF Link: $pdfUrl');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('PDF Export: $e')),
      );
    }
  }

  Future<void> _exportAllAsMultiPdf() async {
    if (_results.isEmpty) return;
    final ids = _results.take(15).map((r) => r.id).toList();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
            const SizedBox(width: 10),
            Text('Compiling ${ids.length} documents into searchable PDF...'),
          ],
        ),
        duration: const Duration(seconds: 4),
      ),
    );
    try {
      final pdfBytes = await _api.exportMultiPdf(ids);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Multi-page PDF generated successfully (${(pdfBytes.length / 1024).toStringAsFixed(1)} KB)!'),
          backgroundColor: const Color(0xFF15803D),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Multi-page export failed: $e')),
      );
    }
  }

  void _openImageZoom(
    BuildContext context,
    String imageUrl,
    String imageName, [
    List<VisualObject> visualObjects = const [],
    int? imageId,
    String? fullText,
    String? pdfUrl,
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
              if (fullText != null && fullText.trim().isNotEmpty) ...[
                IconButton(
                  icon: const Icon(Icons.copy),
                  tooltip: 'Copy text',
                  onPressed: () => _copyToClipboard(fullText, successMessage: 'Document text copied!'),
                ),
                IconButton(
                  icon: const Icon(Icons.text_fields),
                  tooltip: 'Live text (drag to select)',
                  onPressed: () => _showSelectableTextSheet(context, imageName, fullText),
                ),
              ],
              if (pdfUrl != null && pdfUrl.isNotEmpty)
                IconButton(
                  icon: const Icon(Icons.picture_as_pdf),
                  tooltip: 'Export searchable PDF',
                  onPressed: () => _exportPdf(pdfUrl, imageName),
                ),
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
              maxScale: 5.0,
              child: Center(
                child: FittedBox(
                  fit: BoxFit.contain,
                  child: Stack(
                    children: [
                      Image.network(
                        imageUrl,
                        headers: ApiService.authHeaders,
                        cacheWidth: 1600,
                        loadingBuilder: (context, child, progress) {
                          if (progress == null) return child;
                          return const SizedBox(
                            width: 320,
                            height: 320,
                            child: Center(child: CircularProgressIndicator(color: Colors.white)),
                          );
                        },
                        errorBuilder: (context, error, stackTrace) => const SizedBox(
                          width: 320,
                          height: 320,
                          child: Center(
                            child: Icon(Icons.broken_image, color: Colors.white54, size: 64),
                          ),
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
                      headers: ApiService.authHeaders,
                      width: 56,
                      height: 72,
                      cacheWidth: 120,
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

  void _showServerSettingsDialog(BuildContext context) {
    final controller = TextEditingController(
      text: ApiService.baseUrl,
    );
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.cloud_sync, color: Color(0xFF4F46E5)),
            SizedBox(width: 8),
            Text('Server Connection', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Active Backend Server:\n${ApiService.baseUrl}',
                style: const TextStyle(fontSize: 12, color: Color(0xFF475569), fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: const InputDecoration(
                  labelText: 'Server URL or LAN IP',
                  hintText: 'https://golf-kitchen-tri-pst.trycloudflare.com',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Quick Switch:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  ActionChip(
                    avatar: const Icon(Icons.cloud_done, size: 14, color: Color(0xFF4F46E5)),
                    label: const Text('Live Cloud (Friends)', style: TextStyle(fontSize: 11)),
                    onPressed: () {
                      controller.text = 'https://golf-kitchen-tri-pst.trycloudflare.com';
                    },
                  ),
                  ActionChip(
                    avatar: const Icon(Icons.wifi, size: 14, color: Color(0xFF0284C7)),
                    label: const Text('Local Wi-Fi (192.168.1.3)', style: TextStyle(fontSize: 11)),
                    onPressed: () {
                      controller.text = 'http://192.168.1.3:8000';
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                ApiService.setCustomIp(controller.text);
                setState(() => _error = null);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Connected to: ${ApiService.baseUrl}'),
                    duration: const Duration(seconds: 2),
                    backgroundColor: const Color(0xFF10B981),
                  ),
                );
              }
              Navigator.of(ctx).pop();
            },
            child: const Text('CONNECT'),
          ),
        ],
      ),
    );
  }

  void _showUserAccountDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _UserAccountSheet(
        api: _api,
        onUserChanged: () {
          _clearSearch();
          setState(() {
            _error = null;
          });
          if (_searchController.text.trim().isNotEmpty) {
            _search();
          }
        },
      ),
    );
  }

  @override
  void dispose() {
    _syncPollerTimer?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Widget _buildFilterChip(String label, String queryTerm) {
    final currentQ = _searchController.text.trim().toLowerCase();
    final isSelected = queryTerm.isNotEmpty && currentQ == queryTerm.toLowerCase();
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
            color: isSelected ? Colors.white : const Color(0xFF1E293B),
          ),
        ),
        selected: isSelected,
        selectedColor: const Color(0xFF4F46E5),
        backgroundColor: const Color(0xFFF1F5F9),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: isSelected ? const Color(0xFF4F46E5) : const Color(0xFFCBD5E1),
            width: 1.2,
          ),
        ),
        showCheckmark: false,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        onSelected: (_) {
          if (isSelected) {
            _clearSearch();
          } else {
            _searchController.text = queryTerm;
            _search(queryTerm);
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF4F46E5), Color(0xFF7C3AED)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(10),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF4F46E5).withValues(alpha: 0.28),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(Icons.document_scanner, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'DocuLens AI',
                          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: Color(0xFF0F172A), letterSpacing: -0.3),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEEF2FF),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0xFFC7D2FE)),
                          ),
                          child: const Text(
                            'PRO',
                            style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: Color(0xFF4F46E5)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Text(
                    'Multi-Modal Scanner',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10.5, color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          // --- Multi-User Tenant Profile Chip ---
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: InkWell(
              onTap: () => _showUserAccountDialog(context),
              borderRadius: BorderRadius.circular(20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: ApiService.isLoggedIn
                        ? (ApiService.isCurrentUserAdmin
                            ? [const Color(0xFF059669), const Color(0xFF10B981)]
                            : [const Color(0xFF4F46E5), const Color(0xFF6366F1)])
                        : [const Color(0xFFF1F5F9), const Color(0xFFE2E8F0)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: ApiService.isLoggedIn
                      ? [
                          BoxShadow(
                            color: (ApiService.isCurrentUserAdmin
                                    ? const Color(0xFF10B981)
                                    : const Color(0xFF4F46E5))
                                .withValues(alpha: 0.25),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      ApiService.isLoggedIn
                          ? (ApiService.isCurrentUserAdmin ? Icons.admin_panel_settings : Icons.lock_person)
                          : Icons.account_circle_outlined,
                      size: 13,
                      color: ApiService.isLoggedIn ? Colors.white : const Color(0xFF475569),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      ApiService.isLoggedIn
                          ? '${ApiService.currentUsername} (#${ApiService.currentUserId})'
                          : 'Guest Vault',
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.bold,
                        color: ApiService.isLoggedIn ? Colors.white : const Color(0xFF334155),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: InkWell(
              onTap: () => _showServerSettingsDialog(context),
              borderRadius: BorderRadius.circular(20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: const BoxDecoration(
                        color: Color(0xFF10B981),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    const Text(
                      'Online',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF334155)),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // --- Document Ingestion Card ---
                  Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                      side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFEFF6FF),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Icon(Icons.auto_awesome, color: Color(0xFF2563EB), size: 18),
                              ),
                              const SizedBox(width: 8),
                              const Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Scan & Ingest Documents',
                                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                  ),
                                  Text(
                                    '4-Point Dewarping + Magic Color shadow removal',
                                    style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          Row(
                            children: [
                              Expanded(
                                flex: 4,
                                child: ElevatedButton.icon(
                                  onPressed: _loading ? null : _scanViaCamera,
                                  icon: const Icon(Icons.camera_alt, size: 17),
                                  label: const Text('CAM SCAN', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF4F46E5),
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                flex: 4,
                                child: OutlinedButton.icon(
                                  onPressed: _loading ? null : _pickImage,
                                  icon: const Icon(Icons.photo_library_outlined, size: 17, color: Color(0xFF334155)),
                                  label: const Text('GALLERY', style: TextStyle(fontSize: 12, color: Color(0xFF334155))),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                flex: 4,
                                child: ElevatedButton.icon(
                                  onPressed: (_loading && _batchTotal > 0)
                                      ? () {
                                          setState(() {
                                            _loading = false;
                                            _batchStatus = '⚠️ Sync stopped by user.';
                                          });
                                        }
                                      : (_loading ? null : _syncFolder),
                                  icon: Icon(
                                    (_loading && _batchTotal > 0) ? Icons.stop_circle_outlined : Icons.folder_open,
                                    size: 17,
                                  ),
                                  label: Text(
                                    (_loading && _batchTotal > 0) ? 'STOP' : 'SYNC FOLDER',
                                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: (_loading && _batchTotal > 0)
                                        ? const Color(0xFFDC2626)
                                        : const Color(0xFF15803D),
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          if (_batchStatus != null) ...[
                            const SizedBox(height: 10),
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: _batchStatus!.startsWith('') ? const Color(0xFFF0FDF4) : const Color(0xFFEFF6FF),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: _batchStatus!.startsWith('') ? const Color(0xFF86EFAC) : const Color(0xFF93C5FD)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _batchStatus!,
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: _batchStatus!.startsWith('') ? const Color(0xFF15803D) : const Color(0xFF1E40AF),
                                    ),
                                  ),
                                  if (_batchTotal > 0 && _batchCurrent <= _batchTotal && _loading) ...[
                                    const SizedBox(height: 6),
                                    LinearProgressIndicator(
                                      value: _batchCurrent / _batchTotal,
                                      backgroundColor: const Color(0xFFDBEAFE),
                                      color: const Color(0xFF2563EB),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                          if (_selectedImageBytes != null) ...[
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFFE2E8F0)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: Image.memory(
                                      _selectedImageBytes!,
                                      height: 160,
                                      fit: BoxFit.contain,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFEEF2FF),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: const Color(0xFFC7D2FE)),
                                        ),
                                        child: const Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(Icons.auto_fix_high, size: 12, color: Color(0xFF4F46E5)),
                                            SizedBox(width: 4),
                                            Text(
                                              '4-Point Dewarping & Magic Color Ready',
                                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF4F46E5)),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  ElevatedButton.icon(
                                    onPressed: _loading ? null : _extractText,
                                    icon: _loading
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                          )
                                        : const Icon(Icons.document_scanner),
                                    label: Text(_loading ? 'ENHANCING & EXTRACTING OCR...' : 'EXTRACT TEXT & INDEX WITH AI'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF4F46E5),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 13),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          if (_extractedText.isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFFE2E8F0)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      const Row(
                                        children: [
                                          Icon(Icons.check_circle, color: Color(0xFF10B981), size: 16),
                                          SizedBox(width: 6),
                                          Text(
                                            'Scanned & Indexed to Gallery',
                                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                          ),
                                        ],
                                      ),
                                      InkWell(
                                        onTap: () {
                                          _copyToClipboard(_extractedText, successMessage: 'OCR Text Copied!');
                                        },
                                        child: const Text('Copy Text', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF4F46E5))),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    _extractedText.length > 140 && !_showFullExtractedText
                                        ? '${_extractedText.substring(0, 140)}...'
                                        : _extractedText,
                                    style: const TextStyle(fontSize: 12, color: Color(0xFF475569), height: 1.4),
                                  ),
                                  if (_extractedText.length > 140)
                                    GestureDetector(
                                      onTap: () => setState(() => _showFullExtractedText = !_showFullExtractedText),
                                      child: Padding(
                                        padding: const EdgeInsets.only(top: 6),
                                        child: Text(
                                          _showFullExtractedText ? '▲ Show less' : '▼ Show full text (${_extractedText.split('\n').length} lines)',
                                          style: const TextStyle(fontSize: 11, color: Color(0xFF4F46E5), fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 14),

                  // --- Modern Search Box Card ---
                  Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                      side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.search, size: 18, color: Color(0xFF4F46E5)),
                              SizedBox(width: 6),
                              Text(
                                'Multi-Modal Search Engine',
                                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _searchController,
                                  style: const TextStyle(fontSize: 16, color: Color(0xFF0F172A), fontWeight: FontWeight.w500),
                                  decoration: InputDecoration(
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
                                    hintText: 'Search text, names, numbers, or QR...',
                                    hintStyle: const TextStyle(fontSize: 14.5, color: Color(0xFF94A3B8)),
                                    prefixIcon: const Icon(Icons.search, size: 24, color: Color(0xFF4F46E5)),
                                    suffixIcon: IconButton(
                                      icon: const Icon(Icons.clear, size: 20),
                                      tooltip: 'Clear search',
                                      onPressed: _clearSearch,
                                    ),
                                  ),
                                  onSubmitted: (_) => _search(),
                                ),
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton.icon(
                                onPressed: () => _search(),
                                icon: const Icon(Icons.search, size: 19, color: Colors.white),
                                label: const Text('Search', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF4F46E5),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  elevation: 0,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: [
                                _buildFilterChip('Receipts & Bills', 'receipt'),
                                _buildFilterChip('Identity Cards', 'id'),
                                _buildFilterChip('QR & Barcode', 'qr'),
                                _buildFilterChip('Academic & Exams', 'exam'),
                                _buildFilterChip('Notes & Text', 'notes'),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 14),

                  // --- Initial Empty Prompt (when user hasn't searched yet) ---
                  if (!_hasSearched && _results.isEmpty && _error == null) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 28),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: const Column(
                        children: [
                          Icon(Icons.search, size: 44, color: Color(0xFF6366F1)),
                          SizedBox(height: 12),
                          Text(
                            'Search Your Documents',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                          ),
                          SizedBox(height: 6),
                          Text(
                            'Type text, numbers, names, or categories to find documents in your vault.',
                            style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ],

                  // --- Results Section (only displayed on search) ---
                  if (_hasSearched && _results.isNotEmpty) ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            '${_results.length} Matches Found',
                            style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (_results.length >= 2) ...[
                          ElevatedButton.icon(
                            onPressed: _exportAllAsMultiPdf,
                            icon: const Icon(Icons.picture_as_pdf, size: 14),
                            label: const Text('ALL PDF', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFDC2626),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                          ),
                          const SizedBox(width: 8),
                        ],
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
                          Text(
                            'No documents found matching "${_searchController.text.trim()}".',
                            style: const TextStyle(fontSize: 13, color: Color(0xFF78350F)),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 14),
                          ElevatedButton.icon(
                            onPressed: _pickAndSyncGallery,
                            icon: const Icon(Icons.add_photo_alternate_outlined, size: 16),
                            label: const Text('SYNC MORE GALLERY PHOTOS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFD97706),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                              elevation: 0,
                            ),
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
          if (_loading)
            Container(
              color: Colors.black.withValues(alpha: 0.45),
              child: Center(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 28),
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.2),
                        blurRadius: 24,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(color: Color(0xFF4F46E5)),
                      const SizedBox(height: 18),
                      Text(
                        _batchStatus ?? 'Processing with AI...',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF0F172A)),
                      ),
                      if (_batchTotal > 0) ...[
                        const SizedBox(height: 14),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: LinearProgressIndicator(
                            value: _batchTotal > 0 ? (_batchCurrent / _batchTotal) : null,
                            backgroundColor: const Color(0xFFE2E8F0),
                            color: const Color(0xFF15803D),
                            minHeight: 8,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '$_batchCurrent of $_batchTotal photos (${((_batchCurrent / _batchTotal) * 100).toInt()}%)',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () {
                            setState(() {
                              _loading = false;
                              _batchStatus = '⚠️ Sync stopped by user.';
                            });
                          },
                          icon: const Icon(Icons.stop_circle, color: Colors.white, size: 18),
                          label: const Text('STOP SYNC', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFDC2626),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSmartActionChips(BuildContext context, SearchResult result) {
    final chips = <Widget>[];

    // 1. Phone numbers (Indian 10-digit mobile or standard formats)
    final phoneRegex = RegExp(r'\b(?:(?:\+|0{0,2})91[\s.-]?)?([6-9]\d{9})\b');
    final phoneMatches = phoneRegex.allMatches('${result.matchedText} ${result.previewSnippet}');
    final phones = <String>{};
    for (final m in phoneMatches) {
      final p = m.group(1);
      if (p != null && p.length == 10) phones.add(p);
    }
    for (final p in phones.take(2)) {
      chips.add(
        ActionChip(
          avatar: const Icon(Icons.phone, size: 14, color: Color(0xFF15803D)),
          label: Text('Call $p', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF15803D))),
          backgroundColor: const Color(0xFFDCFCE7),
          side: const BorderSide(color: Color(0xFF86EFAC)),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          onPressed: () => _launchActionUrl('tel:$p'),
        ),
      );
    }

    // 2. Email addresses
    final emailRegex = RegExp(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b');
    final emailMatches = emailRegex.allMatches('${result.matchedText} ${result.previewSnippet}');
    final emails = <String>{};
    for (final m in emailMatches) {
      emails.add(m.group(0)!.toLowerCase());
    }
    for (final e in emails.take(2)) {
      chips.add(
        ActionChip(
          avatar: const Icon(Icons.email_outlined, size: 14, color: Color(0xFF1D4ED8)),
          label: Text('Email $e', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF1D4ED8))),
          backgroundColor: const Color(0xFFEFF6FF),
          side: const BorderSide(color: Color(0xFF93C5FD)),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          onPressed: () => _launchActionUrl('mailto:$e'),
        ),
      );
    }

    // 3. UPI IDs (OCR Text, QR Payloads, & Extracted Entities)
    final upiRegex = RegExp(r'\b([a-zA-Z0-9.\-_]{2,32}@(okhdfcbank|okaxis|oksbi|okicici|paytm|ybl|ibl|upi|axl|apl|sbi|hdfcbank))\b', caseSensitive: false);
    final upiMatches = upiRegex.allMatches('${result.matchedText} ${result.previewSnippet} ${result.qrPayload}');
    final upis = <String>{};
    if (result.entities != null && result.entities!['qr_metadata'] is List) {
      for (final qm in (result.entities!['qr_metadata'] as List)) {
        if (qm is Map && qm['vpa'] != null && qm['vpa'].toString().trim().isNotEmpty) {
          upis.add(qm['vpa'].toString().trim());
        }
      }
    }
    for (final m in upiMatches) {
      upis.add(m.group(0)!);
    }
    for (final u in upis.take(2)) {
      chips.add(
        ActionChip(
          avatar: const Icon(Icons.payments_outlined, size: 14, color: Color(0xFF7E22CE)),
          label: Text('Pay UPI: $u', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF7E22CE))),
          backgroundColor: const Color(0xFFFAF5FF),
          side: const BorderSide(color: Color(0xFFD8B4FE)),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          onPressed: () => _launchUpiOrCopy(context, u),
        ),
      );
    }

    // 4. Web URLs (OCR Text, QR Payloads, & Extracted Entities)
    final urls = <String>{};
    if (result.entities != null && result.entities!['urls'] is List) {
      for (final u in (result.entities!['urls'] as List)) {
        if (u != null && u.toString().trim().isNotEmpty) {
          urls.add(u.toString().trim());
        }
      }
    }
    final urlRegex = RegExp(
      r'\b(?:https?://|www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s,;<>]*)?|\b(?:[a-zA-Z0-9-]+\.)+(?:com|in|org|net|edu|gov\.in|ac\.in|nic\.in|io|ai|co|app|gle|me|tech|xyz)(?:/[^\s,;<>]*)?\b',
      caseSensitive: false,
    );
    final urlMatches = urlRegex.allMatches('${result.matchedText} ${result.previewSnippet} ${result.qrPayload}');
    for (final m in urlMatches) {
      var rawU = m.group(0)!.trim();
      while (rawU.isNotEmpty && (rawU.endsWith('.') || rawU.endsWith(',') || rawU.endsWith(';') || rawU.endsWith(')') || rawU.endsWith('"') || rawU.endsWith("'"))) {
        rawU = rawU.substring(0, rawU.length - 1);
      }
      if (!rawU.toLowerCase().startsWith('http://') && !rawU.toLowerCase().startsWith('https://')) {
        rawU = 'https://${rawU.toLowerCase().startsWith("www.") ? rawU.substring(4) : rawU}';
      }
      urls.add(rawU);
    }

    for (final u in urls.take(3)) {
      String displayHost = u.replaceFirst(RegExp(r'^https?://(www\.)?'), '');
      if (displayHost.length > 22) {
        displayHost = '${displayHost.substring(0, 20)}...';
      }
      chips.add(
        ActionChip(
          avatar: const Icon(Icons.language, size: 14, color: Color(0xFF0369A1)),
          label: Text('Open $displayHost', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0369A1))),
          backgroundColor: const Color(0xFFE0F2FE),
          side: const BorderSide(color: Color(0xFF7DD3FC)),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          onPressed: () => _launchActionUrl(u),
        ),
      );
    }

    if (chips.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 2),
      child: Wrap(
        spacing: 6,
        runSpacing: 4,
        children: chips,
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
    final isKeyword = result.searchType == 'keyword' || (!hasScore ? false : result.similarityScore! >= 0.99);
    final isMultimodal = result.searchType == 'multimodal';
    final isVisual = result.searchType == 'visual';
    final isSemantic = result.searchType == 'semantic' || (!isKeyword && !isMultimodal && !isVisual);
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
                if (isKeyword)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0FDF4),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF86EFAC), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle_outline, size: 15, color: Color(0xFF15803D)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Exact match: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Exact match: 1.00',
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF15803D),
                          ),
                        ),
                      ],
                    ),
                  )
                else if (isMultimodal)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF818CF8), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.auto_awesome, size: 15, color: Color(0xFF4F46E5)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Multi-modal: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Multi-modal match',
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF4F46E5),
                          ),
                        ),
                      ],
                    ),
                  )
                else if (isVisual)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFAF5FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFD8B4FE), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.qr_code_scanner, size: 15, color: Color(0xFF7E22CE)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Visual match: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Visual match',
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF7E22CE),
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF93C5FD), width: 1.2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.psychology, size: 15, color: Color(0xFF1D4ED8)),
                        const SizedBox(width: 4),
                        Text(
                          hasScore
                              ? 'Semantic match: ${result.similarityScore!.toStringAsFixed(2)}'
                              : 'Semantic match',
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1D4ED8),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            if (result.matchReason != null && result.matchReason!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFCBD5E1), width: 1.0),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      result.matchReason!.toLowerCase().contains('qr')
                          ? Icons.qr_code_2
                          : Icons.lightbulb_outline,
                      size: 14,
                      color: const Color(0xFF475569),
                    ),
                    const SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        result.matchReason!,
                        style: const TextStyle(
                          fontSize: 12.0,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF334155),
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (result.indexingStatus == 'indexing') ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFF59E0B), width: 1.2),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFD97706)),
                    ),
                    SizedBox(width: 6),
                    Text(
                      'AI Deep Indexing in progress (OCR / CLIP / NER)...',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFB45309),
                      ),
                    ),
                  ],
                ),
              ),
            ] else if (result.indexingStatus == 'queued') ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFCBD5E1), width: 1.2),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.hourglass_top_rounded, size: 13, color: Color(0xFF64748B)),
                    SizedBox(width: 6),
                    Text(
                      'Queued for AI Deep Processing',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 12),

            // Clickable Image Preview with Bounding Box Overlay & "Tap to zoom" hint
            Center(
              child: InkWell(
                onTap: () => _openImageZoom(
                  context,
                  result.imageUrl,
                  result.imageName,
                  result.visualObjects,
                  result.id,
                  result.matchedText,
                  result.pdfUrl,
                ),
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  height: 250,
                  width: 190, // 3:4 aspect ratio
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFCBD5E1), width: 1.2),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 6,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Stack(
                    alignment: Alignment.bottomRight,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(9),
                        child: Image.network(
                          result.imageUrl,
                          headers: ApiService.authHeaders,
                          height: 250,
                          width: 190,
                          cacheWidth: 380,
                          fit: BoxFit.fill,
                          errorBuilder: (context, error, stackTrace) => Container(
                            height: 250,
                            width: 190,
                            color: Colors.grey.shade200,
                            alignment: Alignment.center,
                            child: const Icon(Icons.broken_image, color: Colors.grey),
                          ),
                        ),
                      ),
                      if (result.visualObjects.isNotEmpty)
                        Positioned.fill(
                          child: CustomPaint(
                            painter: BoundingBoxOverlayPainter(visualObjects: result.visualObjects),
                          ),
                        ),
                      Container(
                        margin: const EdgeInsets.all(6),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color.fromRGBO(0, 0, 0, 0.75),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.zoom_in, color: Colors.white, size: 14),
                            SizedBox(width: 4),
                            Text(
                              'Tap to Zoom',
                              style: TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),

            // Smart One-Tap Action Chips (Call, Email, Pay UPI, Open Link)
            _buildSmartActionChips(context, result),
            const SizedBox(height: 8),

            // Quick Action Toolbar: COPY TEXT, DRAG TO COPY, EXPORT PDF
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _copyToClipboard(
                      result.matchedText.isNotEmpty ? result.matchedText : displaySnippet,
                      successMessage: 'Document text copied!',
                    ),
                    icon: const Icon(Icons.copy, size: 16),
                    label: const Text('COPY TEXT', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                      minimumSize: Size.zero,
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: () => _showSelectableTextSheet(
                      context,
                      result.imageName,
                      result.matchedText.isNotEmpty ? result.matchedText : displaySnippet,
                    ),
                    icon: const Icon(Icons.text_fields, size: 16),
                    label: const Text('DRAG TO COPY', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                      minimumSize: Size.zero,
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (result.pdfUrl != null && result.pdfUrl!.isNotEmpty)
                    ElevatedButton.icon(
                      onPressed: () => _exportPdf(result.pdfUrl!, result.imageName),
                      icon: const Icon(Icons.picture_as_pdf, size: 16),
                      label: const Text('EXPORT PDF', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFDC2626),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                        minimumSize: Size.zero,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),

            // Phase 3 Visual Objects Badge Panel
            if (result.visualObjects.isNotEmpty) ...[
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
                          'Visual Objects Detected (${result.visualObjects.length})',
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
                        headers: ApiService.authHeaders,
                        width: 50,
                        height: 66,
                        cacheWidth: 100,
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

    final cyanBoxPaint = Paint()
      ..color = const Color(0xFF00E5FF) // Vibrant Cyan
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final cyanFillPaint = Paint()
      ..color = const Color(0x2A00E5FF) // Subtle transparent Cyan fill
      ..style = PaintingStyle.fill;

    // High-visibility luminous yellow highlighter for text matches in crowded documents
    final yellowBoxPaint = Paint()
      ..color = const Color(0xFFFFB300) // Deep Amber Yellow contour border
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final yellowFillPaint = Paint()
      ..color = const Color(0x60FFE600) // Radiant Fluorescent Yellow highlight fill
      ..style = PaintingStyle.fill;

    final yellowGlowPaint = Paint()
      ..color = const Color(0x35FFEA00) // Soft outer ambient glow for crowded documents
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.5;

    final cornerPaint = Paint()
      ..color = const Color(0xFFFFEA00) // Bright Yellow Corner Markers
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.square;

    for (final obj in visualObjects) {
      final isTextHighlight = obj.type == 'text_highlight';
      var rect = Rect.fromLTWH(
        obj.normX * size.width,
        obj.normY * size.height,
        obj.normW * size.width,
        obj.normH * size.height,
      );

      // In crowded documents with dense text lines, ensure minimum visibility
      if (isTextHighlight) {
        if (rect.height < 10.0 || rect.width < 14.0) {
          rect = Rect.fromCenter(
            center: rect.center,
            width: rect.width < 14.0 ? 14.0 : rect.width + 2.0,
            height: rect.height < 10.0 ? 10.0 : rect.height + 2.0,
          );
        }
      }

      final currentFill = isTextHighlight ? yellowFillPaint : cyanFillPaint;
      final currentBox = isTextHighlight ? yellowBoxPaint : cyanBoxPaint;

      // Draw bounding box glow, fill & contour rectangle
      if (isTextHighlight) {
        canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), yellowGlowPaint);
      }
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), currentFill);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), currentBox);

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

class _UserAccountSheet extends StatefulWidget {
  final ApiService api;
  final VoidCallback onUserChanged;

  const _UserAccountSheet({
    required this.api,
    required this.onUserChanged,
  });

  @override
  State<_UserAccountSheet> createState() => _UserAccountSheetState();
}

class _UserAccountSheetState extends State<_UserAccountSheet> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _isAdminReg = false;
  bool _loading = false;
  String? _statusMessage;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin(String username, String password) async {
    setState(() {
      _loading = true;
      _errorMessage = null;
      _statusMessage = null;
    });
    try {
      await widget.api.login(username, password);
      widget.onUserChanged();
      if (mounted) {
        setState(() {
          _statusMessage = 'Signed in as $username (Vault #${ApiService.currentUserId})';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('🔐 Authenticated as $username (Vault #${ApiService.currentUserId})'),
            backgroundColor: const Color(0xFF10B981),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceAll('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _handleRegister() async {
    final u = _usernameController.text.trim();
    final p = _passwordController.text;
    if (u.isEmpty || p.isEmpty) {
      setState(() => _errorMessage = 'Please enter both username and password.');
      return;
    }
    setState(() {
      _loading = true;
      _errorMessage = null;
      _statusMessage = null;
    });
    try {
      await widget.api.register(u, p, isAdmin: _isAdminReg);
      // Automatically login after successful registration
      await widget.api.login(u, p);
      widget.onUserChanged();
      if (mounted) {
        setState(() {
          _statusMessage = '🎉 Registered & Signed in as $u (Vault #${ApiService.currentUserId})';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('🎉 Account created! Signed into Vault #${ApiService.currentUserId}'),
            backgroundColor: const Color(0xFF10B981),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceAll('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _handleLogout() {
    widget.api.logout();
    widget.onUserChanged();
    setState(() {
      _statusMessage = 'Reverted to Guest Public Vault';
      _errorMessage = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Signed out. Active in Public Guest Vault.'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isLogged = ApiService.isLoggedIn;
    final currentU = ApiService.currentUsername;
    final currentId = ApiService.currentUserId;
    final isAdmin = ApiService.isCurrentUserAdmin;

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              // Drag Handle
              Center(
                child: Container(
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 14),

              // Title Header
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEEF2FF),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.shield_outlined, color: Color(0xFF4F46E5), size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Tenant Vault & Privacy Security',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                          ),
                          Text(
                            isLogged
                                ? 'Active: $currentU (Vault #$currentId) · ${isAdmin ? 'Admin RBAC' : 'Tenant Isolated'}'
                                : 'Active: Public Guest Mode (Unauthenticated)',
                            style: TextStyle(
                              fontSize: 12,
                              color: isLogged ? (isAdmin ? const Color(0xFF059669) : const Color(0xFF4F46E5)) : const Color(0xFF64748B),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 8),

              // TabBar Navigation
              TabBar(
                controller: _tabController,
                labelColor: const Color(0xFF4F46E5),
                unselectedLabelColor: const Color(0xFF64748B),
                indicatorColor: const Color(0xFF4F46E5),
                indicatorWeight: 2.5,
                tabs: const [
                  Tab(icon: Icon(Icons.swap_horiz, size: 18), text: 'Switch Vault'),
                  Tab(icon: Icon(Icons.person_add_alt_1, size: 18), text: 'Sign In / Register'),
                  Tab(icon: Icon(Icons.lock_clock_outlined, size: 18), text: 'Cloud Privacy'),
                ],
              ),

              // Tab Content Area
              SizedBox(
                height: 340,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildSwitchTab(isLogged, currentU, currentId, isAdmin),
                    _buildAuthTab(),
                    _buildPrivacyTab(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSwitchTab(bool isLogged, String currentU, int currentId, bool isAdmin) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Active status badge
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isLogged ? const Color(0xFFF0FDF4) : const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: isLogged ? const Color(0xFFBBF7D0) : const Color(0xFFE2E8F0)),
            ),
            child: Row(
              children: [
                Icon(
                  isLogged ? Icons.verified_user : Icons.info_outline,
                  color: isLogged ? const Color(0xFF16A34A) : const Color(0xFF64748B),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isLogged
                            ? 'Logged In: $currentU (Vault #$currentId)'
                            : 'Guest Mode (Public Vault)',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A)),
                      ),
                      Text(
                        isLogged
                            ? 'Row-Level Security active. User B cannot see your documents.'
                            : 'All public demo images visible. Sign in to isolate your documents.',
                        style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B)),
                      ),
                    ],
                  ),
                ),
                if (isLogged)
                  TextButton(
                    onPressed: _handleLogout,
                    style: TextButton.styleFrom(
                      foregroundColor: const Color(0xFFDC2626),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                    child: const Text('LOGOUT', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
              ],
            ),
          ),

          const SizedBox(height: 16),
          const Text(
            'Quick-Switch Demo Tenants (Instant Testing):',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF475569)),
          ),
          const SizedBox(height: 8),

          // Preset 1: Alice (Admin)
          _buildPresetTile(
            title: 'Alice (Admin Tenant · Vault #1)',
            subtitle: 'Owns 367 demo library documents · Full administrative access',
            icon: Icons.admin_panel_settings,
            iconColor: const Color(0xFF059669),
            isSelected: isLogged && currentU == 'alice',
            onTap: () => _handleLogin('alice', 'password123'),
          ),

          const SizedBox(height: 8),

          // Preset 2: Bob (Isolated Tenant)
          _buildPresetTile(
            title: 'Bob (Isolated User · Private Vault)',
            subtitle: 'Clean tenant · Cannot see Alice\'s documents · Strict IDOR protection',
            icon: Icons.lock_person,
            iconColor: const Color(0xFF4F46E5),
            isSelected: isLogged && currentU.startsWith('isolated_bob') || currentU == 'bob',
            onTap: () => _handleLogin('bob', 'BobPassword123!'),
          ),

          const SizedBox(height: 8),

          // Preset 3: Guest Mode
          _buildPresetTile(
            title: 'Guest Mode (Public Shared Vault)',
            subtitle: 'Unauthenticated testing · Standard public read access',
            icon: Icons.public,
            iconColor: const Color(0xFF64748B),
            isSelected: !isLogged,
            onTap: _handleLogout,
          ),

          if (_statusMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              _statusMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFF10B981), fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ],
          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              _errorMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFFDC2626), fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPresetTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color iconColor,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: _loading ? null : onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? iconColor.withValues(alpha: 0.08) : const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? iconColor : const Color(0xFFE2E8F0),
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: iconColor, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.bold,
                      color: isSelected ? iconColor : const Color(0xFF0F172A),
                    ),
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 10.5, color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle, color: iconColor, size: 18),
          ],
        ),
      ),
    );
  }

  Widget _buildAuthTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _usernameController,
            decoration: const InputDecoration(
              labelText: 'Username',
              prefixIcon: Icon(Icons.person_outline, size: 18),
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _passwordController,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Password',
              prefixIcon: Icon(Icons.lock_outline, size: 18),
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Checkbox(
                value: _isAdminReg,
                onChanged: (val) => setState(() => _isAdminReg = val ?? false),
              ),
              const Expanded(
                child: Text(
                  'Register as Admin (Role-Based Access Control)',
                  style: TextStyle(fontSize: 11.5, color: Color(0xFF475569)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_loading)
            const Center(child: CircularProgressIndicator())
          else
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _handleLogin(_usernameController.text, _passwordController.text),
                    icon: const Icon(Icons.login, size: 16),
                    label: const Text('SIGN IN'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _handleRegister,
                    icon: const Icon(Icons.person_add, size: 16),
                    label: const Text('REGISTER'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4F46E5),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          if (_statusMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              _statusMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFF10B981), fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ],
          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              _errorMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFFDC2626), fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPrivacyTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Production Cloud Deployment Privacy Protections',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
          ),
          const SizedBox(height: 10),
          _buildPrivacyRow(
            icon: Icons.public_off,
            color: const Color(0xFF10B981),
            title: '1. Data Residency (100% On-Premise / Edge)',
            detail: 'Zero cloud API leakage. EasyOCR, sentence-transformers & MobileNet run entirely on your private cluster without sending images to Google/OpenAI.',
          ),
          const SizedBox(height: 10),
          _buildPrivacyRow(
            icon: Icons.shield,
            color: const Color(0xFF2563EB),
            title: '2. Multi-Tenant Vault Isolation',
            detail: 'JWT Bearer token verification. SQLite Row-Level Security scopes every query strictly to user_id. User A cannot view or search User B\'s documents.',
          ),
          const SizedBox(height: 10),
          _buildPrivacyRow(
            icon: Icons.enhanced_encryption,
            color: const Color(0xFF7C3AED),
            title: '3. Storage at Rest (AES-256 Envelope)',
            detail: 'Files in uploads/ are partitioned per tenant (uploads/user_{id}/) and encrypted at rest with AES-256-GCM. Physical disk theft yields unreadable ciphertext.',
          ),
          const SizedBox(height: 10),
          _buildPrivacyRow(
            icon: Icons.visibility_off,
            color: const Color(0xFFD97706),
            title: '4. Real-Time PII Masking & Redaction',
            detail: 'Aadhaar numbers (XXXX-XXXX-1234), PAN cards, and signatures are automatically detected and masked in viewer & export outputs unless authorized.',
          ),
        ],
      ),
    );
  }

  Widget _buildPrivacyRow({
    required IconData icon,
    required Color color,
    required String title,
    required String detail,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: color),
                ),
                const SizedBox(height: 2),
                Text(
                  detail,
                  style: const TextStyle(fontSize: 10.5, color: Color(0xFF475569)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

