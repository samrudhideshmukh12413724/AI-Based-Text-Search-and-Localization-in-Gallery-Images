import 'package:flutter/material.dart';
import 'screens/auth_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AiImageSearchApp());
}

class AiImageSearchApp extends StatelessWidget {
  const AiImageSearchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DocuLens AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const AuthScreen(),
    );
  }
}
