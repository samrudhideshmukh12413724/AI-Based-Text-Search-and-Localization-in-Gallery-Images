import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'document_detail_screen.dart';

class CameraScanScreen extends StatefulWidget {
  const CameraScanScreen({super.key});

  @override
  State<CameraScanScreen> createState() => _CameraScanScreenState();
}

class _CameraScanScreenState extends State<CameraScanScreen> {
  final ImagePicker _picker = ImagePicker();
  final ApiService _api = ApiService();
  bool _flashOn = false;
  bool _processing = false;
  String? _statusText;

  Future<void> _captureFromCamera() async {
    try {
      setState(() {
        _processing = true;
        _statusText = 'Opening camera...';
      });
      final file = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1800,
        maxHeight: 1800,
        imageQuality: 90,
      );
      if (file == null) {
        setState(() => _processing = false);
        return;
      }

      setState(() => _statusText = 'Enhancing & Running OCR...');
      final bytes = await file.readAsBytes();
      final res = await _api.uploadImageBytes(bytes, file.name.isNotEmpty ? file.name : 'scan_${DateTime.now().millisecondsSinceEpoch}.jpg');

      if (!mounted) return;

      final doc = res['document'] as Map<String, dynamic>? ?? {};
      final fullText = (doc['extracted_text'] as String?) ?? (res['extracted_text'] as String?) ?? '';
      final imageName = (doc['image_name'] as String?) ?? file.name;
      final rawUrl = (doc['image_url'] as String?) ?? '';
      final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${ApiService.baseUrl}$rawUrl';

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => DocumentDetailScreen(
            title: imageName,
            imageUrl: fullUrl,
            extractedText: fullText,
            fileType: 'CAMERA SCAN',
            fileSize: '${(bytes.length / 1024).toStringAsFixed(0)} KB',
            date: 'Just now',
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _processing = false;
          _statusText = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Scan failed: $e'),
            backgroundColor: AppTheme.error,
          ),
        );
      }
    }
  }

  Future<void> _pickFromGallery() async {
    try {
      final file = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1800,
        maxHeight: 1800,
        imageQuality: 90,
      );
      if (file == null) return;

      setState(() {
        _processing = true;
        _statusText = 'Analyzing document...';
      });

      final bytes = await file.readAsBytes();
      final res = await _api.uploadImageBytes(bytes, file.name);

      if (!mounted) return;

      final doc = res['document'] as Map<String, dynamic>? ?? {};
      final fullText = (doc['extracted_text'] as String?) ?? (res['extracted_text'] as String?) ?? '';
      final imageName = (doc['image_name'] as String?) ?? file.name;
      final rawUrl = (doc['image_url'] as String?) ?? '';
      final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${ApiService.baseUrl}$rawUrl';

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => DocumentDetailScreen(
            title: imageName,
            imageUrl: fullUrl,
            extractedText: fullText,
            fileType: 'GALLERY',
            fileSize: '${(bytes.length / 1024).toStringAsFixed(0)} KB',
            date: 'Just now',
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _processing = false;
          _statusText = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed: $e'),
            backgroundColor: AppTheme.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark slate viewfinder background
      body: SafeArea(
        child: Stack(
          children: [
            // Viewfinder Document Target Area
            Center(
              child: Container(
                width: MediaQuery.of(context).size.width * 0.85,
                height: MediaQuery.of(context).size.height * 0.60,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.04),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.2), width: 1.5),
                ),
                child: Stack(
                  children: [
                    // Corner targeting brackets
                    _buildCorner(Alignment.topLeft),
                    _buildCorner(Alignment.topRight),
                    _buildCorner(Alignment.bottomLeft),
                    _buildCorner(Alignment.bottomRight),

                    // Center scan guide text
                    Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.document_scanner_outlined,
                            size: 48,
                            color: Colors.white.withValues(alpha: 0.6),
                          ),
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                            decoration: BoxDecoration(
                              color: Colors.black.withValues(alpha: 0.5),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Text(
                              'Position document within frame',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Top Bar Controls (Close & Flash)
            Positioned(
              top: 16,
              left: 20,
              right: 20,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 28, color: Colors.white),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                  IconButton(
                    icon: Icon(
                      _flashOn ? Icons.flash_on_rounded : Icons.flash_off_rounded,
                      size: 26,
                      color: _flashOn ? const Color(0xFFFACC15) : Colors.white,
                    ),
                    onPressed: () => setState(() => _flashOn = !_flashOn),
                  ),
                ],
              ),
            ),

            // Processing Indicator
            if (_processing)
              Container(
                color: Colors.black.withValues(alpha: 0.75),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(color: AppTheme.primary, strokeWidth: 3),
                      const SizedBox(height: 18),
                      Text(
                        _statusText ?? 'Processing document...',
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),

            // Bottom Shutter Controls
            Positioned(
              bottom: 30,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  // Gallery icon shortcut
                  IconButton(
                    icon: const Icon(Icons.photo_library_outlined, size: 28, color: Colors.white),
                    tooltip: 'Gallery',
                    onPressed: _processing ? null : _pickFromGallery,
                  ),

                  // Center circular shutter button
                  GestureDetector(
                    onTap: _processing ? null : _captureFromCamera,
                    child: Container(
                      width: 76,
                      height: 76,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 4),
                      ),
                      padding: const EdgeInsets.all(5),
                      child: Container(
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ),

                  // Enhancement / mode icon
                  IconButton(
                    icon: const Icon(Icons.auto_fix_high_rounded, size: 28, color: Colors.white),
                    tooltip: 'Auto Enhance',
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('✨ Magic Color & 4-Point Dewarping enabled by default'),
                          duration: Duration(seconds: 2),
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCorner(Alignment alignment) {
    const size = 28.0;
    const thickness = 3.5;
    const color = Color(0xFF38BDF8); // Electric Sky Blue

    final isTop = alignment == Alignment.topLeft || alignment == Alignment.topRight;
    final isLeft = alignment == Alignment.topLeft || alignment == Alignment.bottomLeft;

    return Align(
      alignment: alignment,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          border: Border(
            top: isTop ? const BorderSide(color: color, width: thickness) : BorderSide.none,
            bottom: !isTop ? const BorderSide(color: color, width: thickness) : BorderSide.none,
            left: isLeft ? const BorderSide(color: color, width: thickness) : BorderSide.none,
            right: !isLeft ? const BorderSide(color: color, width: thickness) : BorderSide.none,
          ),
        ),
      ),
    );
  }
}
