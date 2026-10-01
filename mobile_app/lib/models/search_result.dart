class VisualObject {
  final String label;
  final String type;
  final int x;
  final int y;
  final int width;
  final int height;
  final double normX;
  final double normY;
  final double normW;
  final double normH;
  final String data;
  final String locationDesc;
  final String confidence;

  VisualObject({
    required this.label,
    required this.type,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.normX,
    required this.normY,
    required this.normW,
    required this.normH,
    required this.data,
    required this.locationDesc,
    required this.confidence,
  });

  factory VisualObject.fromJson(Map<String, dynamic> json) {
    final bbox = (json['bbox'] as Map<String, dynamic>?) ?? {};
    final norm = (json['normalized_bbox'] as Map<String, dynamic>?) ?? {};

    return VisualObject(
      label: json['label']?.toString() ?? 'QR Code',
      type: json['type']?.toString() ?? 'qr_code',
      x: (bbox['x'] as num?)?.toInt() ?? 0,
      y: (bbox['y'] as num?)?.toInt() ?? 0,
      width: (bbox['width'] as num?)?.toInt() ?? 0,
      height: (bbox['height'] as num?)?.toInt() ?? 0,
      normX: (norm['x'] as num?)?.toDouble() ?? 0.0,
      normY: (norm['y'] as num?)?.toDouble() ?? 0.0,
      normW: (norm['width'] as num?)?.toDouble() ?? 0.0,
      normH: (norm['height'] as num?)?.toDouble() ?? 0.0,
      data: json['data']?.toString() ?? '',
      locationDesc: json['location_desc']?.toString() ?? 'Embedded',
      confidence: json['confidence']?.toString() ?? 'Detected',
    );
  }
}

class SearchResult {
  final int id;
  final String imageName;
  final String imageUrl;
  final String matchedText;
  final double? similarityScore;
  final String? searchType;
  final String previewSnippet;
  final List<String> highlightTerms;
  final List<String> matchedConcepts;
  final bool hasVisualObjects;
  final String visualSummary;
  final List<VisualObject> visualObjects;

  SearchResult({
    required this.id,
    required this.imageName,
    required this.imageUrl,
    required this.matchedText,
    this.similarityScore,
    this.searchType,
    this.previewSnippet = '',
    this.highlightTerms = const [],
    this.matchedConcepts = const [],
    this.hasVisualObjects = false,
    this.visualSummary = '',
    this.visualObjects = const [],
  });

  factory SearchResult.fromJson(
    Map<String, dynamic> json,
    String baseUrl, {
    String? defaultSearchType,
  }) {
    final url = (json['image_url'] as String?) ?? '';
    final score = json['similarity_score'];
    final rawHighlights = (json['highlight_terms'] as List<dynamic>?) ?? [];
    final rawConcepts = (json['matched_concepts'] as List<dynamic>?) ?? [];
    final rawVisualObjs = (json['visual_objects'] as List<dynamic>?) ?? [];

    return SearchResult(
      id: (json['id'] as num?)?.toInt() ?? 0,
      imageName: (json['image_name'] as String?) ?? '',
      imageUrl: url.startsWith('http') ? url : '$baseUrl$url',
      matchedText: (json['matched_text'] as String?) ?? '',
      similarityScore: score != null ? (score as num).toDouble() : null,
      searchType: (json['search_type'] as String?) ?? defaultSearchType,
      previewSnippet: (json['preview_snippet'] as String?) ?? (json['matched_text'] as String?) ?? '',
      highlightTerms: rawHighlights.map((e) => e.toString()).toList(),
      matchedConcepts: rawConcepts.map((e) => e.toString()).toList(),
      hasVisualObjects: (json['has_visual_objects'] as bool?) ?? (rawVisualObjs.isNotEmpty),
      visualSummary: (json['visual_summary'] as String?) ?? '',
      visualObjects: rawVisualObjs
          .whereType<Map<String, dynamic>>()
          .map((e) => VisualObject.fromJson(e))
          .toList(),
    );
  }
}

class SearchResponse {
  final String query;
  final String searchType;
  final int count;
  final String message;
  final List<SearchResult> results;

  SearchResponse({
    required this.query,
    required this.searchType,
    required this.count,
    required this.message,
    required this.results,
  });

  factory SearchResponse.fromJson(Map<String, dynamic> json, String baseUrl) {
    final searchType = (json['search_type'] as String?) ?? 'keyword';
    final rawResults = (json['results'] as List<dynamic>?) ??
        (json['matched_images'] as List<dynamic>?) ??
        [];

    return SearchResponse(
      query: (json['query'] as String?) ?? '',
      searchType: searchType,
      count: (json['count'] as num?)?.toInt() ??
          (json['total_matches'] as num?)?.toInt() ??
          rawResults.length,
      message: (json['message'] as String?) ?? '',
      results: rawResults
          .whereType<Map<String, dynamic>>()
          .map((e) => SearchResult.fromJson(e, baseUrl, defaultSearchType: searchType))
          .toList(),
    );
  }
}

class RelatedImage {
  final int imageId;
  final String imageName;
  final String imageUrl;
  final String relationshipType;
  final double confidenceScore;
  final String evidence;
  final String reason;

  RelatedImage({
    required this.imageId,
    required this.imageName,
    required this.imageUrl,
    required this.relationshipType,
    required this.confidenceScore,
    required this.evidence,
    required this.reason,
  });

  String get readableType {
    switch (relationshipType.toLowerCase()) {
      case 'shared_application_id':
        return 'Related by Application ID';
      case 'shared_enrollment_id':
        return 'Related by Enrollment ID';
      case 'shared_aadhaar':
        return 'Related by Aadhaar Number';
      case 'shared_phone':
        return 'Related by Phone Number';
      case 'shared_email':
        return 'Related by Email Address';
      case 'shared_pan':
        return 'Related by PAN Number';
      case 'shared_transaction_id':
        return 'Related by Transaction ID';
      case 'shared_person_name':
        return 'Related by Person Name';
      default:
        final clean = relationshipType
            .replaceAll('shared_', '')
            .replaceAll('_', ' ')
            .split(' ')
            .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
            .join(' ');
        return clean.isEmpty ? 'Related Document' : 'Related by $clean';
    }
  }

  factory RelatedImage.fromJson(Map<String, dynamic> json, String baseUrl) {
    final url = (json['image_url'] as String?) ?? '/uploads/${json['image_name'] ?? ''}';
    return RelatedImage(
      imageId: (json['image_id'] as num?)?.toInt() ?? 0,
      imageName: (json['image_name'] as String?) ?? '',
      imageUrl: url.startsWith('http') ? url : '$baseUrl$url',
      relationshipType: (json['relationship_type'] as String?) ?? '',
      confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 1.0,
      evidence: (json['evidence'] as String?) ?? '',
      reason: (json['reason'] as String?) ?? '',
    );
  }
}

class RelationshipResponse {
  final int imageId;
  final int? canonicalImageId;
  final List<RelatedImage> relationships;

  RelationshipResponse({
    required this.imageId,
    this.canonicalImageId,
    required this.relationships,
  });

  factory RelationshipResponse.fromJson(Map<String, dynamic> json, String baseUrl) {
    final rawRels = (json['relationships'] as List<dynamic>?) ?? [];
    return RelationshipResponse(
      imageId: (json['image_id'] as num?)?.toInt() ?? 0,
      canonicalImageId: (json['canonical_image_id'] as num?)?.toInt(),
      relationships: rawRels
          .whereType<Map<String, dynamic>>()
          .map((e) => RelatedImage.fromJson(e, baseUrl))
          .toList(),
    );
  }
}

