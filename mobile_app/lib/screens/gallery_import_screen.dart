import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class GalleryImportScreen extends StatefulWidget {
  const GalleryImportScreen({super.key});

  @override
  State<GalleryImportScreen> createState() => _GalleryImportScreenState();
}

class _GalleryImportScreenState extends State<GalleryImportScreen> {
  final ApiService _api = ApiService();
  int _activeSegment = 0; // 0: Recent, 1: Albums
  List<PlatformFile> _pickedFiles = [];
  final Set<int> _selectedIndices = {};
  bool _importing = false;
  String? _statusText;

  @override
  void initState() {
    super.initState();
    // Auto-open file picker initially so user can choose gallery items
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadFromDevice();
    });
  }

  Future<void> _loadFromDevice() async {
    try {
      final res = await FilePicker.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png', 'webp', 'pdf'],
        withData: true,
      );
      if (res != null && res.files.isNotEmpty) {
        setState(() {
          _pickedFiles = res.files;
          _selectedIndices.clear();
          // Select all by default or first two
          for (int i = 0; i < _pickedFiles.length; i++) {
            _selectedIndices.add(i);
          }
        });
      }
    } catch (_) {}
  }

  Future<void> _importSelected() async {
    if (_selectedIndices.isEmpty) return;

    final selectedFiles = _selectedIndices.map((i) => _pickedFiles[i]).toList();

    setState(() {
      _importing = true;
      _statusText = 'Importing ${selectedFiles.length} documents...';
    });

    int count = 0;
    for (int i = 0; i < selectedFiles.length; i++) {
      final file = selectedFiles[i];
      if (file.bytes == null) continue;
      setState(() => _statusText = 'Indexing ${i + 1} of ${selectedFiles.length} (${file.name})...');
      try {
        await _api.uploadImageBytes(file.bytes!, file.name, asyncProcessing: true);
        count++;
      } catch (_) {}
    }

    if (mounted) {
      setState(() => _importing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Imported $count documents to Vault!'),
          backgroundColor: AppTheme.success,
          behavior: SnackBarBehavior.floating,
        ),
      );
      Navigator.of(context).pop();
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
        title: const Text('Import from Gallery', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_photo_alternate_outlined),
            tooltip: 'Pick more images',
            onPressed: _loadFromDevice,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Segmented Tab (Recent / Albums)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _activeSegment = 0),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: _activeSegment == 0 ? AppTheme.primary : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          'Recent',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: _activeSegment == 0 ? Colors.white : AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _activeSegment = 1),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: _activeSegment == 1 ? AppTheme.primary : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          'Albums',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: _activeSegment == 1 ? Colors.white : AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Image Grid with Checkmark Selectors
            Expanded(
              child: _pickedFiles.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.photo_library_outlined, size: 54, color: AppTheme.textMuted.withValues(alpha: 0.7)),
                          const SizedBox(height: 14),
                          const Text(
                            'No documents selected yet',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppTheme.textSecondary),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Tap the button below to pick images or documents',
                            style: TextStyle(fontSize: 12.5, color: AppTheme.textMuted),
                          ),
                          const SizedBox(height: 18),
                          ElevatedButton.icon(
                            onPressed: _loadFromDevice,
                            icon: const Icon(Icons.add_photo_alternate, size: 18),
                            label: const Text('Select Photos'),
                          ),
                        ],
                      ),
                    )
                  : GridView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 3,
                        crossAxisSpacing: 8,
                        mainAxisSpacing: 8,
                        childAspectRatio: 0.95,
                      ),
                      itemCount: _pickedFiles.length,
                      itemBuilder: (context, index) {
                        final file = _pickedFiles[index];
                        final isSelected = _selectedIndices.contains(index);
                        final isPdf = file.name.toLowerCase().endsWith('.pdf');

                        return GestureDetector(
                          onTap: () {
                            setState(() {
                              if (isSelected) {
                                _selectedIndices.remove(index);
                              } else {
                                _selectedIndices.add(index);
                              }
                            });
                          },
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              // Image thumbnail preview
                              ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF1F5F9),
                                    border: Border.all(
                                      color: isSelected ? AppTheme.primary : AppTheme.border,
                                      width: isSelected ? 2.5 : 1,
                                    ),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: file.bytes != null && !isPdf
                                      ? Image.memory(
                                          file.bytes!,
                                          fit: BoxFit.cover,
                                        )
                                      : Center(
                                          child: Icon(
                                            isPdf ? Icons.picture_as_pdf_outlined : Icons.insert_drive_file_outlined,
                                            size: 32,
                                            color: isPdf ? const Color(0xFFDC2626) : AppTheme.primary,
                                          ),
                                        ),
                                ),
                              ),
                              // Circular selection badge on top-right
                              Positioned(
                                top: 6,
                                right: 6,
                                child: Container(
                                  width: 24,
                                  height: 24,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: isSelected ? AppTheme.primary : Colors.black.withValues(alpha: 0.35),
                                    border: Border.all(color: Colors.white, width: 2),
                                  ),
                                  child: isSelected
                                      ? const Icon(Icons.check, size: 14, color: Colors.white)
                                      : null,
                                ),
                              ),
                              // File name badge at bottom
                              Positioned(
                                bottom: 0,
                                left: 0,
                                right: 0,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.55),
                                    borderRadius: const BorderRadius.vertical(bottom: Radius.circular(11)),
                                  ),
                                  child: Text(
                                    file.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.w500),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),

            // Bottom Action Bar: "X selected" and [Import] button
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: Colors.white,
                border: const Border(top: BorderSide(color: AppTheme.border)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, -3),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _importing && _statusText != null
                          ? _statusText!
                          : '${_selectedIndices.length} selected',
                      style: const TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const Spacer(),
                  ElevatedButton(
                    onPressed: (_selectedIndices.isNotEmpty && !_importing) ? _importSelected : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _importing
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Text(
                            'Import',
                            style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
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
}
