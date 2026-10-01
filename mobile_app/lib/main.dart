import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() {
  runApp(const AiImageSearchApp());
}

class AiImageSearchApp extends StatelessWidget {
  const AiImageSearchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Image Search',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
