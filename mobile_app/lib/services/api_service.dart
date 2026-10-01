import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/search_result.dart';

class ApiService {
  // Web uses 127.0.0.1; Android emulator uses 10.0.2.2; Real phone uses PC IP
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  Future<Map<String, dynamic>> uploadImageBytes(List<int> bytes, String filename) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/upload'),
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: filename,
      ),
    );

    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    final body = jsonDecode(response.body);

    if (response.statusCode >= 400) {
      throw Exception(body['detail'] ?? 'Upload failed');
    }

    return body as Map<String, dynamic>;
  }

  Future<SearchResponse> search(String query) async {
    final response = await http.post(
      Uri.parse('$baseUrl/search'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'query': query}),
    );

    final body = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      throw Exception(body['detail'] ?? 'Search failed');
    }

    return SearchResponse.fromJson(body as Map<String, dynamic>, baseUrl);
  }

  Future<RelationshipResponse> getRelationships(int imageId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/images/$imageId/relationships'),
    );

    final body = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      throw Exception(body['detail'] ?? 'Failed to fetch relationships');
    }

    return RelationshipResponse.fromJson(body as Map<String, dynamic>, baseUrl);
  }
}
