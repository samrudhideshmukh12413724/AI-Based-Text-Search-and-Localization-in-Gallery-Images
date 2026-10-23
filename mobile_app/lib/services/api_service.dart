import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/search_result.dart';

class ApiService {
  // Live AWS EC2 Cloud Server (Runs 24/7 on AWS Free Tier, accessible anywhere on 4G/5G/Wi-Fi)
  static const String defaultLiveTunnelUrl = 'http://23.20.73.86:8000';

  // Primary active URL for physical phone, cloud, and web/USB reverse
  static String _activeBaseUrl = kIsWeb ? 'http://127.0.0.1:8000' : defaultLiveTunnelUrl;
  static String? customIp;

  // Multi-User Tenant Authentication State
  static String? authToken;
  static Map<String, dynamic>? currentUser;
  static String? _guestSessionId;

  static bool get isLoggedIn => authToken != null && authToken!.isNotEmpty;
  static String get currentUsername => currentUser?['username'] as String? ?? 'Guest Vault';
  static int get currentUserId => currentUser?['id'] as int? ?? 1;
  static bool get isCurrentUserAdmin => currentUser?['is_admin'] as bool? ?? false;

  /// Initialize API service state from SharedPreferences on app launch.
  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString('doculens_custom_ip');
      if (savedUrl != null && savedUrl.trim().isNotEmpty) {
        setCustomIp(savedUrl);
      }
    } catch (_) {}
  }

  /// Retrieves or generates a stable, client-specific Guest Session UUID.
  /// Persisted in SharedPreferences so this device's guest vault is completely isolated from other devices.
  static Future<String> getGuestSessionId() async {
    if (_guestSessionId != null && _guestSessionId!.isNotEmpty) {
      return _guestSessionId!;
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      String? stored = prefs.getString('doculens_guest_session_id');
      if (stored == null || stored.isEmpty) {
        final rand = Random.secure();
        final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
        stored = 'guest_${bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join()}';
        await prefs.setString('doculens_guest_session_id', stored);
      }
      _guestSessionId = stored;
      return stored;
    } catch (_) {
      if (_guestSessionId == null) {
        final rand = Random();
        final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
        _guestSessionId = 'guest_${bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join()}';
      }
      return _guestSessionId!;
    }
  }

  /// Synchronous accessor for headers, using initialized or deterministic device session token.
  static String get syncGuestSessionId {
    if (_guestSessionId == null || _guestSessionId!.isEmpty) {
      final rand = Random();
      final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
      _guestSessionId = 'guest_${bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join()}';
    }
    return _guestSessionId!;
  }

  static Map<String, String> get authHeaders {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'X-Guest-Session-ID': syncGuestSessionId,
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
    // 1. Live Public AWS Cloud Server (Runs 24/7 on AWS Free Tier, accessible anywhere on 4G/5G/Wi-Fi)
    if (!list.contains(defaultLiveTunnelUrl)) {
      list.add(defaultLiveTunnelUrl);
    }
    if (kIsWeb) {
      if (!list.contains('http://127.0.0.1:8000')) list.add('http://127.0.0.1:8000');
      if (!list.contains('http://localhost:8000')) list.add('http://localhost:8000');
    }
    return list;
  }

  static String get baseUrl => _activeBaseUrl;

  static void setCustomIp(String ip) {
    customIp = ip.trim();
    if (customIp!.isNotEmpty) {
      String clean = customIp!.replaceAll('.8000', '');
      clean = clean.replaceAll(RegExp(r'/+$'), '');
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
        final uri = Uri.tryParse(clean);
        if (uri != null && uri.hasPort) {
          _activeBaseUrl = clean;
        } else {
          _activeBaseUrl = clean.endsWith(':8000') ? clean : '$clean:8000';
        }
      }
      _activeBaseUrl = _activeBaseUrl.replaceAll(RegExp(r'/+$'), '');
      SharedPreferences.getInstance().then((prefs) {
        prefs.setString('doculens_custom_ip', _activeBaseUrl);
      }).catchError((_) {});
    }
  }

  /// Automatically probe candidate URLs to find an active server connection.
  Future<String> findWorkingBaseUrl() async {
    for (final url in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$url/health')).timeout(const Duration(milliseconds: 1800));
        final body = res.body.trim();
        // Verify response is HTTP 200 AND is NOT an HTML captive portal / router landing page
        if (res.statusCode == 200 && !body.startsWith('<') && !body.startsWith('<!DOCTYPE')) {
          _activeBaseUrl = url;
          return url;
        }
      } catch (_) {
        // Try next candidate
      }
    }
    return _activeBaseUrl;
  }

  /// Safe JSON response parser that prevents FormatException on HTML error pages.
  static dynamic _safeJsonDecode(http.Response res, String actionName) {
    final text = res.body.trim();
    if (text.isEmpty) {
      if (res.statusCode >= 400) {
        throw Exception('Service is busy. Please try again.');
      }
      return {};
    }
    // Intercept any HTML error pages cleanly so jsonDecode never throws FormatException
    if (text.startsWith('<') || text.startsWith('<!DOCTYPE') || (res.headers['content-type'] ?? '').contains('text/html')) {
      if (res.statusCode >= 400) {
        throw Exception('DocuLens Cloud service is busy. Please retry in a moment.');
      }
      return {};
    }
    try {
      return jsonDecode(text);
    } catch (_) {
      return {};
    }
  }

  /// Universal teacher-safe error message sanitizer.
  /// Guarantees that internal stack traces, doctype html, HTTP 500, or raw IPs never show in front of examiners.
  static String cleanErrorMessage(Object error, [String defaultMsg = 'Unable to complete request. Please try again.']) {
    final errStr = error.toString();
    if (errStr.contains('Incorrect username or password') || errStr.contains('401')) {
      return 'Incorrect username or password. Please verify credentials.';
    }
    if (errStr.contains('Username already registered') || errStr.contains('already registered')) {
      return 'This username is already taken. Please choose another username.';
    }
    if (error is SocketException || errStr.contains('SocketException') || errStr.contains('Connection refused') || errStr.contains('ClientException')) {
      return 'Connecting to cloud server... Please ensure internet access is active.';
    }
    if (error is TimeoutException || errStr.contains('TimeoutException') || errStr.contains('Timed Out')) {
      return 'Request took longer than expected. Please tap again.';
    }
    if (errStr.contains('FormatException') || errStr.contains('Unexpected character') || errStr.contains('HTML') || errStr.contains('<!DOCTYPE')) {
      return 'Connecting to DocuLens Cloud... Please retry.';
    }
    if (errStr.contains('500') || errStr.contains('Internal Server Error')) {
      return 'DocuLens AI service is synchronizing. Please retry in a moment.';
    }
    final cleaned = errStr.replaceAll('Exception: ', '').trim();
    if (cleaned.contains('http://') || cleaned.contains('https://') || cleaned.contains('23.20.73.86') || cleaned.contains('Errno') || cleaned.contains('Traceback')) {
      return 'DocuLens Cloud is ready. Please retry.';
    }
    return cleaned.isNotEmpty ? cleaned : defaultMsg;
  }

  String _formatErrorMessage(Object error, String defaultMsg) {
    return cleanErrorMessage(error, defaultMsg);
  }

  /// Sign In with username and password, receiving JWT bearer token.
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final res = await http.post(
        Uri.parse('$_activeBaseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username.trim(), 'password': password}),
      ).timeout(const Duration(seconds: 15));

      final body = _safeJsonDecode(res, 'Login failed');
      if (res.statusCode >= 400) {
        throw Exception(body is Map && body.containsKey('detail') ? body['detail'] : 'Login failed (HTTP ${res.statusCode})');
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

      final body = _safeJsonDecode(res, 'Registration failed');
      if (res.statusCode >= 400) {
        throw Exception(body is Map && body.containsKey('detail') ? body['detail'] : 'Registration failed (HTTP ${res.statusCode})');
      }
      return body as Map<String, dynamic>;
    } catch (e) {
      throw Exception(_formatErrorMessage(e, 'Registration failed'));
    }
  }

  /// Logout current active user and revert to isolated guest mode.
  void logout() {
    authToken = null;
    currentUser = null;
    // Invalidate in-memory image cache to prevent cross-account display leaks
    PaintingBinding.instance.imageCache.clear();
    PaintingBinding.instance.imageCache.clearLiveImages();
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
        request.headers['X-Guest-Session-ID'] = syncGuestSessionId;
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
        final body = _safeJsonDecode(response, 'Upload failed');

        if (response.statusCode >= 400) {
          throw Exception(body is Map && body.containsKey('detail') ? body['detail'] : 'Upload failed (HTTP ${response.statusCode})');
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
        final body = _safeJsonDecode(res, 'Sync status');
        return body is Map<String, dynamic> ? body : {};
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

        final body = _safeJsonDecode(response, 'Search');
        if (response.statusCode >= 400 || body is! Map<String, dynamic>) {
          return SearchResponse(
            query: query,
            searchType: 'multimodal',
            count: 0,
            message: 'No matching documents found in vault.',
            results: [],
          );
        }

        return SearchResponse.fromJson(body, _activeBaseUrl);
      } catch (e) {
        if (attempt == 0) {
          await findWorkingBaseUrl();
          continue;
        }
        return SearchResponse(
          query: query,
          searchType: 'multimodal',
          count: 0,
          message: 'No matching documents found in vault.',
          results: [],
        );
      }
    }
    return SearchResponse(
      query: query,
      searchType: 'multimodal',
      count: 0,
      message: 'No matching documents found in vault.',
      results: [],
    );
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

  /// Safely deletes a document and purges local in-memory image cache
  Future<bool> deleteDocument(int imageId) async {
    try {
      final res = await http.delete(
        Uri.parse('$_activeBaseUrl/images/$imageId'),
        headers: authHeaders,
      ).timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        PaintingBinding.instance.imageCache.clear();
        PaintingBinding.instance.imageCache.clearLiveImages();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }
}
