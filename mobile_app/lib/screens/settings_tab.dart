import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'auth_screen.dart';

class SettingsTab extends StatefulWidget {
  const SettingsTab({super.key});

  @override
  State<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<SettingsTab> {
  final ApiService _api = ApiService();
  final TextEditingController _ipController = TextEditingController();
  bool _testingConnection = false;
  String? _connectionStatus;

  @override
  void initState() {
    super.initState();
    _ipController.text = ApiService.customIp ?? ApiService.baseUrl;
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() {
      _testingConnection = true;
      _connectionStatus = null;
    });
    try {
      ApiService.setCustomIp(_ipController.text.trim());
      final url = await _api.findWorkingBaseUrl();
      setState(() {
        _connectionStatus = 'Connected successfully to: $url ✅';
      });
    } catch (e) {
      setState(() {
        _connectionStatus = 'Connection failed: $e ❌';
      });
    } finally {
      setState(() => _testingConnection = false);
    }
  }

  void _signOut() {
    _api.logout();
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Settings', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          children: [
            // User Profile Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
              ),
              child: Row(
                children: [
                  const CircleAvatar(
                    radius: 26,
                    backgroundColor: AppTheme.primaryContainer,
                    child: Icon(Icons.person, color: AppTheme.primary, size: 28),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ApiService.currentUsername,
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          ApiService.isLoggedIn
                              ? (ApiService.isCurrentUserAdmin ? 'Administrator (All Vaults)' : 'Tenant User #${ApiService.currentUserId}')
                              : 'Guest Mode (Public Vault)',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  OutlinedButton(
                    onPressed: _signOut,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      side: const BorderSide(color: Color(0xFFFECACA)),
                    ),
                    child: Text(
                      ApiService.isLoggedIn ? 'Sign Out' : 'Sign In',
                      style: const TextStyle(fontSize: 12, color: AppTheme.error, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Server & Network Configuration Card
            const Text(
              'Backend Server Connection',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Server URL / IP',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _ipController,
                    decoration: const InputDecoration(
                      hintText: 'https://xxx.trycloudflare.com or 192.168.1.3:8000',
                      prefixIcon: Icon(Icons.dns_rounded, size: 20, color: AppTheme.primary),
                      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _testingConnection ? null : _testConnection,
                      icon: _testingConnection
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Icon(Icons.electrical_services_rounded, size: 18),
                      label: const Text('Test Connection & Save'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                  if (_connectionStatus != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      _connectionStatus!,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _connectionStatus!.contains('✅') ? AppTheme.success : AppTheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Engine & Security Info Card
            const Text(
              'Multi-Modal Engine',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
              ),
              child: const Column(
                children: [
                  ListTile(
                    leading: Icon(Icons.auto_awesome, color: AppTheme.primary),
                    title: Text('OCR Engine', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                    subtitle: Text('PaddleOCR + Tesseract Dual Fallback', style: TextStyle(fontSize: 11.5)),
                  ),
                  Divider(height: 1, color: AppTheme.border),
                  ListTile(
                    leading: Icon(Icons.qr_code_scanner, color: AppTheme.primary),
                    title: Text('Visual Object & QR Detector', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                    subtitle: Text('OpenCV + PyZbar Computer Vision', style: TextStyle(fontSize: 11.5)),
                  ),
                  Divider(height: 1, color: AppTheme.border),
                  ListTile(
                    leading: Icon(Icons.verified_user_outlined, color: AppTheme.primary),
                    title: Text('Steganographic Security Verification', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                    subtitle: Text('Hidden Payload Integrity Check active', style: TextStyle(fontSize: 11.5)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // App Version Footer
            const Center(
              child: Column(
                children: [
                  Text(
                    'DocuLens AI v2.0 Pro',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Intelligent Multi-Modal Document Search Engine',
                    style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
