import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'main_shell.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final ApiService _api = ApiService();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _isRegisterMode = false;
  bool _obscurePassword = true;
  bool _loading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _navigateToMainShell() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainShell()),
    );
  }

  Future<void> _submitAuth() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    if (username.isEmpty || password.isEmpty) {
      setState(() => _errorMessage = 'Please enter both username/email and password.');
      return;
    }

    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      if (_isRegisterMode) {
        await _api.register(username, password);
      }
      await _api.login(username, password);
      if (mounted) {
        _navigateToMainShell();
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

  void _continueAsGuest() {
    _api.logout(); // Reset to guest state
    _navigateToMainShell();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Logo & Header
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryContainer,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.document_scanner,
                      size: 28,
                      color: AppTheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'DocuLens AI',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Intelligent Document Search',
                  style: TextStyle(
                    fontSize: 12.5,
                    color: AppTheme.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 28),

                // Illustration Widget
                _buildHeroIllustration(),
                const SizedBox(height: 28),

                // Tagline
                const Text(
                  'Your Documents.\nOne Intelligent Search.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                    height: 1.25,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Scan documents, search extracted text,\nand discover visual information in your files.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: AppTheme.textSecondary,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 28),

                // Error Banner
                if (_errorMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF2F2),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFFECACA)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, size: 18, color: AppTheme.error),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(fontSize: 12, color: AppTheme.error),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Input Fields
                TextField(
                  controller: _usernameController,
                  keyboardType: TextInputType.emailAddress,
                  style: const TextStyle(fontSize: 14.5, color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    hintText: 'Email or username',
                    prefixIcon: const Icon(Icons.mail_outline_rounded, size: 20, color: AppTheme.textMuted),
                    fillColor: const Color(0xFFF8FAFC),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  style: const TextStyle(fontSize: 14.5, color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    hintText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20, color: AppTheme.textMuted),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                        size: 20,
                        color: AppTheme.textMuted,
                      ),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                    ),
                    fillColor: const Color(0xFFF8FAFC),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Sign In Button
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _loading ? null : _submitAuth,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: _loading
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.2),
                          )
                        : Text(
                            _isRegisterMode ? 'Create Account' : 'Sign In',
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                  ),
                ),
                const SizedBox(height: 12),

                // Continue as Guest Button
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: OutlinedButton(
                    onPressed: _continueAsGuest,
                    style: OutlinedButton.styleFrom(
                      backgroundColor: Colors.white,
                      side: const BorderSide(color: AppTheme.border, width: 1.2),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: const Text(
                      'Continue as Guest',
                      style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                    ),
                  ),
                ),
                const SizedBox(height: 22),

                // Toggle Register / Login
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _isRegisterMode ? 'Already have an account? ' : "Don't have an account? ",
                      style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                    ),
                    GestureDetector(
                      onTap: () {
                        setState(() {
                          _isRegisterMode = !_isRegisterMode;
                          _errorMessage = null;
                        });
                      },
                      child: Text(
                        _isRegisterMode ? 'Sign In' : 'Create Account',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeroIllustration() {
    return Container(
      width: 170,
      height: 130,
      decoration: BoxDecoration(
        color: const Color(0xFFF5F3FF), // Soft violet tint
        borderRadius: BorderRadius.circular(24),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Document sheet
          Container(
            width: 90,
            height: 100,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFDDD6FE), width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: 0.08),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEEF2FF),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(Icons.badge_outlined, size: 14, color: AppTheme.primary),
                ),
                const SizedBox(height: 10),
                Container(width: 50, height: 4, decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(2))),
                const SizedBox(height: 6),
                Container(width: 60, height: 4, decoration: BoxDecoration(color: const Color(0xFFE2E8F0), borderRadius: BorderRadius.circular(2))),
                const SizedBox(height: 6),
                Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE2E8F0), borderRadius: BorderRadius.circular(2))),
              ],
            ),
          ),
          // Magnifying glass lens overlay
          Positioned(
            right: 28,
            bottom: 14,
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppTheme.primary,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primary.withValues(alpha: 0.35),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: const Icon(Icons.search, size: 24, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}
