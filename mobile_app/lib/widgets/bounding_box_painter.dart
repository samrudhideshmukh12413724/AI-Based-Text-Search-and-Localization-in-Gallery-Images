import 'package:flutter/material.dart';
import '../models/search_result.dart';

class BoundingBoxOverlayPainter extends CustomPainter {
  final List<VisualObject> visualObjects;

  BoundingBoxOverlayPainter({required this.visualObjects});

  @override
  void paint(Canvas canvas, Size size) {
    if (visualObjects.isEmpty) return;

    final cyanBoxPaint = Paint()
      ..color = const Color(0xFF00E5FF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final cyanFillPaint = Paint()
      ..color = const Color(0x2A00E5FF)
      ..style = PaintingStyle.fill;

    final yellowBoxPaint = Paint()
      ..color = const Color(0xFFFFB300)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final yellowFillPaint = Paint()
      ..color = const Color(0x60FFE600)
      ..style = PaintingStyle.fill;

    final yellowGlowPaint = Paint()
      ..color = const Color(0x35FFEA00)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.5;

    final cornerPaint = Paint()
      ..color = const Color(0xFFFFEA00)
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

      if (isTextHighlight) {
        canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), yellowGlowPaint);
      }
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), currentFill);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(2)), currentBox);

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
