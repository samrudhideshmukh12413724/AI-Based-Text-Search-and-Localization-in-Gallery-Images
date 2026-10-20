import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class ConnectionErrorView extends StatelessWidget {
  final VoidCallback onRetry;
  final VoidCallback? onContinueOffline;
  final String? customMessage;

  const ConnectionErrorView({
    super.key,
    required this.onRetry,
    this.onContinueOffline,
    this.customMessage,
  });

  void _showConfigureServerDialog(BuildContext context) {
    final controller = TextEditingController(text: ApiService.customIp ?? ApiService.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Configure Backend URL', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter your local LAN IP (e.g. 192.168.1.3:8000) or Cloudflare tunnel URL:',
              style: TextStyle(fontSize: 12.5, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                hintText: 'https://xxx.trycloudflare.com',
                contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              ApiService.setCustomIp(controller.text.trim());
              Navigator.pop(ctx);
              onRetry();
            },
            child: const Text('Save & Reconnect'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 36),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Circular Wi-Fi disconnected illustration
            Container(
              width: 96,
              height: 96,
              decoration: const BoxDecoration(
                color: Color(0xFFF1F5F9),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Container(
                  width: 68,
                  height: 68,
                  decoration: const BoxDecoration(
                    color: Color(0xFFEDE9FE), // Soft Lavender
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.wifi_off_rounded,
                    size: 36,
                    color: AppTheme.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Connection issue',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              customMessage ?? 'Unable to connect to the AI server.\nCheck your connection and try again.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 13.5,
                color: AppTheme.textSecondary,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: onRetry,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text(
                  'Retry Connection',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ),
            ),
            const SizedBox(height: 10),
            if (onContinueOffline != null)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: onContinueOffline,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text(
                    'Continue Offline',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                  ),
                ),
              ),
            const SizedBox(height: 20),
            InkWell(
              onTap: () => _showConfigureServerDialog(context),
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: const BoxDecoration(
                        color: AppTheme.error,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Backend server unreachable (${ApiService.baseUrl})',
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: AppTheme.textSecondary,
                        decoration: TextDecoration.underline,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
