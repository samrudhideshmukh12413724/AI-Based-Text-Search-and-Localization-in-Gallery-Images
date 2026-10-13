import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/search_result.dart';

class ApiService {
  static String _activeBaseUrl = 'http://192.168.1.7:8000';
  static String? customIp;

  static List<String> get candidateUrls {
    final list = <String>[];
    if (customIp != null && customIp!.isNotEmpty) {
      final formatted = customIp!.startsWith('http') ? customIp! : 'http://$customIp';
      list.add(formatted.endsWith(':8000') ? formatted : '$formatted:8000');
    }
    if (kIsWeb) {
      list.add('http://127.0.0.1:8000');
    } else {
      list.add('http://127.0.0.1:8000'); // ADB reverse USB
      list.add('http://192.168.1.7:8000'); // Wi-Fi LAN
      list.add('http://10.0.2.2:8000'); // Emulator
    }
    return list;
  }

  static String get baseUrl => _activeBaseUrl;

  static void setCustomIp(String ip) {
    customIp = ip.trim();
    if (customIp!.isNotEmpty) {
      final formatted = customIp!.startsWith('http') ? customIp! : 'http://$customIp';
      _activeBaseUrl = formatted.endsWith(':8000') ? formatted : '$formatted:8000';
    }
  }

  /// Automatically probe candidate URLs to find an active server connection.
  Future<String> findWorkingBaseUrl() async {
    for (final url in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$url/auth/me')).timeout(const Duration(milliseconds: 4000));
        if (res.statusCode < 500) {
          _activeBaseUrl = url;
          return url;
        }
      } catch (_) {
        // Try next candidate
      }
    }
    return _activeBaseUrl;
  }

  String _formatErrorMessage(Object error, String defaultMsg) {
    final errStr = error.toString();
    if (error is SocketException || errStr.contains('SocketException') || errStr.contains('Connection refused') || errStr.contains('ClientException')) {
      return '⚠️ Backend Server Unreachable ($baseUrl).\nEnsure backend is running and phone is connected to Wi-Fi/USB.';
    }
    if (error is TimeoutException) {
      return '⌛ Request Timed Out. Backend model inference took longer than expected.';
    }
    return errStr.replaceAll('Exception: ', '');
  }

  Future<Map<String, dynamic>> uploadImageBytes(List<int> bytes, String filename) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_activeBaseUrl/upload'),
      );
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );

      final streamed = await request.send().timeout(const Duration(seconds: 60));
      final response = await http.Response.fromStream(streamed);
      final body = jsonDecode(response.body);

      if (response.statusCode >= 400) {
        throw Exception(body['detail'] ?? 'Upload failed');
      }

      return body as Map<String, dynamic>;
    } catch (e) {
      await findWorkingBaseUrl();
      throw Exception(_formatErrorMessage(e, 'Upload failed'));
    }
  }

  Future<SearchResponse> search(String query) async {
    try {
      final response = await http.post(
        Uri.parse('$_activeBaseUrl/search'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': query}),
      ).timeout(const Duration(seconds: 45));

      final body = jsonDecode(response.body);
      if (response.statusCode >= 400) {
        throw Exception(body['detail'] ?? 'Search failed');
      }

      return SearchResponse.fromJson(body as Map<String, dynamic>, _activeBaseUrl);
    } catch (e) {
      await findWorkingBaseUrl();
      throw Exception(_formatErrorMessage(e, 'Search failed'));
    }
  }

  Future<RelationshipResponse> getRelationships(int imageId) async {
    try {
      final response = await http.get(
        Uri.parse('$_activeBaseUrl/images/$imageId/relationships'),
      ).timeout(const Duration(seconds: 15));

      final body = jsonDecode(response.body);
      if (response.statusCode >= 400) {
        throw Exception(body['detail'] ?? 'Failed to fetch relationships');
      }

      return RelationshipResponse.fromJson(body as Map<String, dynamic>, _activeBaseUrl);
    } catch (e) {
      throw Exception(_formatErrorMessage(e, 'Failed to fetch relationships'));
    }
  }
}
