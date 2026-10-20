import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/search_result.dart';

class ApiService {
  // Primary active URL for physical phone (LAN) and web/USB reverse
  static String _activeBaseUrl = kIsWeb ? 'http://127.0.0.1:8000' : 'http://192.168.1.3:8000';
  static String? customIp;

  // Multi-User Tenant Authentication State
  static String? authToken;
  static Map<String, dynamic>? currentUser;

  static bool get isLoggedIn => authToken != null && authToken!.isNotEmpty;
  static String get currentUsername => currentUser?['username'] as String? ?? 'Guest (Public)';
  static int get currentUserId => currentUser?['id'] as int? ?? 1;
  static bool get isCurrentUserAdmin => currentUser?['is_admin'] as bool? ?? false;

  static Map<String, String> get authHeaders {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (authToken != null && authToken!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $authToken';
    }
    return headers;
  }

  static List<String> get candidateUrls {
    final list = <String>[];
    if (customIp != null && customIp!.isNotEmpty) {
      list.add(_activeBaseUrl);
    }
    if (kIsWeb) {
      list.add('http://127.0.0.1:8000');
      list.add('http://localhost:8000');
    } else {
      list.add('http://192.168.1.3:8000'); // Primary Wi-Fi LAN IP (Laptop)
      list.add('http://127.0.0.1:8000');   // ADB reverse loopback
      list.add('http://10.0.2.2:8000');    // Android Emulator loopback
      list.add('http://192.168.1.2:8000'); // Alternate Wi-Fi LAN IP
      list.add('http://192.168.1.4:8000'); // Alternate Wi-Fi LAN IP
      list.add('http://192.168.1.7:8000'); // Alternate Wi-Fi LAN IP
    }
    return list;
  }

  static String get baseUrl => _activeBaseUrl;

  static void setCustomIp(String ip) {
    customIp = ip.trim();
    if (customIp!.isNotEmpty) {
      // Clean up accidental .8000 typo or trailing slashes
      String clean = customIp!.replaceAll('.8000', '');
      if (clean.endsWith('/')) {
        clean = clean.substring(0, clean.length - 1);
      }
      if (clean.startsWith('http://') || clean.startsWith('https://')) {
        _activeBaseUrl = clean;
      } else if (clean.contains('trycloudflare.com') ||
                 clean.contains('ngrok') ||
                 clean.contains('hf.space') ||
                 clean.contains('.com') ||
                 clean.contains('.app')) {
        _activeBaseUrl = 'https://$clean';
      } else {
        if (!clean.startsWith('http://')) {
          clean = 'http://$clean';
        }
        // If no port specified, append :8000
        final uri = Uri.tryParse(clean);
        if (uri != null && uri.hasPort) {
          _activeBaseUrl = clean;
        } else {
          _activeBaseUrl = clean.endsWith(':8000') ? clean : '$clean:8000';
        }
      }
    }
  }

  /// Automatically probe candidate URLs to find an active server connection.
  Future<String> findWorkingBaseUrl() async {
    for (final url in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$url/health')).timeout(const Duration(milliseconds: 5000));
        if (res.statusCode == 200) {
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
      return '⚠️ Backend Server Unreachable ($baseUrl).\nPlease check internet connection or verify the backend server is running.';
    }
    if (error is TimeoutException) {
      return '⌛ Request Timed Out. Inference or upload took longer than expected. Please retry.';
    }
    return errStr.replaceAll('Exception: ', '');
  }

  /// Sign In with username and password, receiving JWT bearer token.
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final res = await http.post(
        Uri.parse('$_activeBaseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username.trim(), 'password': password}),
      ).timeout(const Duration(seconds: 15));

      final body = jsonDecode(res.body);
      if (res.statusCode >= 400) {
        throw Exception(body['detail'] ?? 'Login failed');
      }

      authToken = body['access_token'] as String?;
      currentUser = {
        'id': body['user_id'],
        'username': body['username'],
        'is_admin': body['is_admin'] ?? false,
      };
      return currentUser!;
    } catch (e) {
      throw Exception(_formatErrorMessage(e, 'Login failed'));
    }
  }

  /// Register a new tenant account with role attributes.
  Future<Map<String, dynamic>> register(String username, String password, {bool isAdmin = false}) async {
    try {
      final res = await http.post(
        Uri.parse('$_activeBaseUrl/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username.trim(),
          'password': password,
          'is_admin': isAdmin,
        }),
      ).timeout(const Duration(seconds: 15));

      final body = jsonDecode(res.body);
      if (res.statusCode >= 400) {
        throw Exception(body['detail'] ?? 'Registration failed');
      }
      return body as Map<String, dynamic>;
    } catch (e) {
      throw Exception(_formatErrorMessage(e, 'Registration failed'));
    }
  }

  /// Logout current active user and revert to public guest mode.
  void logout() {
    authToken = null;
    currentUser = null;
  }

  /// Fetch list of registered users for quick tenant profile switching.
  Future<List<Map<String, dynamic>>> fetchAvailableUsers() async {
    try {
      final res = await http.get(
        Uri.parse('$_activeBaseUrl/auth/users'),
        headers: authHeaders,
      ).timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.cast<Map<String, dynamic>>();
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  /// Retrieve documents scoped strictly to current tenant.
  Future<List<Map<String, dynamic>>> fetchTenantDocuments() async {
    try {
      final res = await http.get(
        Uri.parse('$_activeBaseUrl/images'),
        headers: authHeaders,
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.cast<Map<String, dynamic>>();
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  /// High-speed check for incremental synchronization: skips already indexed images.
  Future<Map<String, dynamic>> checkImagesForSync(List<Map<String, dynamic>> files) async {
    try {
      final res = await http.post(
        Uri.parse('$_activeBaseUrl/images/sync-check'),
        headers: authHeaders,
        body: jsonEncode({'files': files}),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
      return {
        'missing': files.map((f) => f['filename'] as String).toList(),
        'already_synced': <String>[],
      };
    } catch (_) {
      return {
        'missing': files.map((f) => f['filename'] as String).toList(),
        'already_synced': <String>[],
      };
    }
  }

  Future<Map<String, dynamic>> uploadImageBytes(
    List<int> bytes,
    String filename, {
    bool asyncProcessing = false,
  }) async {
    for (int attempt = 0; attempt < 2; attempt++) {
      try {
        final uri = Uri.parse('$_activeBaseUrl/upload${asyncProcessing ? '?async_processing=true' : ''}');
        final request = http.MultipartRequest('POST', uri);
        if (authToken != null && authToken!.isNotEmpty) {
          request.headers['Authorization'] = 'Bearer $authToken';
        }
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
        if (attempt == 0) {
          await findWorkingBaseUrl();
          continue;
        }
        throw Exception(_formatErrorMessage(e, 'Upload failed'));
      }
    }
    throw Exception('Upload failed after connection retry');
  }

  /// Retrieve real-time background sync queue metrics and worker status.
  Future<Map<String, dynamic>> getSyncStatus() async {
    try {
      final res = await http.get(
        Uri.parse('$_activeBaseUrl/sync/status'),
        headers: authHeaders,
      ).timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
      return {};
    } catch (_) {
      return {};
    }
  }

  Future<SearchResponse> search(String query) async {
    for (int attempt = 0; attempt < 2; attempt++) {
      try {
        final response = await http.post(
          Uri.parse('$_activeBaseUrl/search'),
          headers: authHeaders,
          body: jsonEncode({'query': query}),
        ).timeout(const Duration(seconds: 45));

        final body = jsonDecode(response.body);
        if (response.statusCode >= 400) {
          throw Exception(body['detail'] ?? 'Search failed');
        }

        return SearchResponse.fromJson(body as Map<String, dynamic>, _activeBaseUrl);
      } catch (e) {
        if (attempt == 0) {
          await findWorkingBaseUrl();
          continue;
        }
        throw Exception(_formatErrorMessage(e, 'Search failed'));
      }
    }
    throw Exception('Search failed after connection retry');
  }

  Future<RelationshipResponse> getRelationships(int imageId) async {
    try {
      final response = await http.get(
        Uri.parse('$_activeBaseUrl/images/$imageId/relationships'),
        headers: authHeaders,
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

  String getExportPdfUrl(int imageId) {
    return '$_activeBaseUrl/images/$imageId/export-pdf';
  }

  Future<List<int>> exportMultiPdf(List<int> imageIds) async {
    final response = await http.post(
      Uri.parse('$_activeBaseUrl/images/export-multi-pdf'),
      headers: authHeaders,
      body: jsonEncode({'image_ids': imageIds}),
    ).timeout(const Duration(seconds: 45));

    if (response.statusCode >= 400) {
      throw Exception('Multi-page PDF compilation failed');
    }
    return response.bodyBytes;
  }
}
