import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_image_search/models/search_result.dart';

void main() {
  group('Related Documents Model & Parsing Tests', () {
    test('RelatedImage parses JSON correctly', () {
      final json = {
        'image_id': 18,
        'image_name': 'loan_education.jpg',
        'image_url': '/uploads/loan_education.jpg',
        'relationship_type': 'shared_application_id',
        'confidence_score': 1.0,
        'evidence': 'ALT-2026-APP-8841',
        'reason': "Shares Application Id: 'ALT-2026-APP-8841'",
      };

      final rel = RelatedImage.fromJson(json, 'http://127.0.0.1:8000');
      expect(rel.imageId, 18);
      expect(rel.imageName, 'loan_education.jpg');
      expect(rel.imageUrl, 'http://127.0.0.1:8000/uploads/loan_education.jpg');
      expect(rel.relationshipType, 'shared_application_id');
      expect(rel.readableType, 'Related by Application ID');
      expect(rel.confidenceScore, 1.0);
      expect(rel.evidence, 'ALT-2026-APP-8841');
      expect(rel.reason, contains('ALT-2026-APP-8841'));
    });

    test('RelationshipResponse parses canonical and empty relationships', () {
      final jsonEmpty = {
        'image_id': 2,
        'canonical_image_id': null,
        'relationships': [],
      };

      final respEmpty = RelationshipResponse.fromJson(jsonEmpty, 'http://127.0.0.1:8000');
      expect(respEmpty.imageId, 2);
      expect(respEmpty.canonicalImageId, isNull);
      expect(respEmpty.relationships, isEmpty);

      final jsonDupe = {
        'image_id': 15,
        'canonical_image_id': 1,
        'relationships': [
          {
            'image_id': 18,
            'image_name': 'loan_education.jpg',
            'image_url': '/uploads/loan_education.jpg',
            'relationship_type': 'shared_application_id',
            'confidence_score': 1.0,
            'evidence': 'ALT-2026-APP-8841',
            'reason': "Shares Application Id: 'ALT-2026-APP-8841'",
          }
        ],
      };

      final respDupe = RelationshipResponse.fromJson(jsonDupe, 'http://127.0.0.1:8000');
      expect(respDupe.imageId, 15);
      expect(respDupe.canonicalImageId, 1);
      expect(respDupe.relationships.length, 1);
      expect(respDupe.relationships.first.imageId, 18);
    });

    test('Readable relationship type mappings', () {
      final types = {
        'shared_application_id': 'Related by Application ID',
        'shared_enrollment_id': 'Related by Enrollment ID',
        'shared_aadhaar': 'Related by Aadhaar Number',
        'shared_phone': 'Related by Phone Number',
        'shared_email': 'Related by Email Address',
        'shared_pan': 'Related by PAN Number',
        'shared_transaction_id': 'Related by Transaction ID',
      };

      for (final entry in types.entries) {
        final rel = RelatedImage(
          imageId: 10,
          imageName: 'test.jpg',
          imageUrl: 'http://test.jpg',
          relationshipType: entry.key,
          confidenceScore: 1.0,
          evidence: '12345',
          reason: 'test',
        );
        expect(rel.readableType, entry.value);
      }
    });
  });

  group('Related Documents Empty State UI Test', () {
    testWidgets('Renders empty state message when no relationships exist', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.link_off, size: 48, color: Color(0xFF94A3B8)),
                  SizedBox(height: 12),
                  Text(
                    'No related documents found.',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('No related documents found.'), findsOneWidget);
      expect(find.byIcon(Icons.link_off), findsOneWidget);
    });
  });
}
