import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goldnest_mobile/analysis_screens.dart';
import 'package:goldnest_mobile/core/app_controller.dart';

class ReviewController extends AppController {
  Map<String, dynamic>? confirmation;

  final result = <String, dynamic>{
    'job_id': 'job-1',
    'captured_at': '2026-09-18T08:00:00+00:00',
    'physical_jewel_count': 1,
    'type_counts': <String, dynamic>{'Bangle': 1},
    'artifacts': <String, dynamic>{'annotated': 'annotated.jpg'},
    'instances': <Map<String, dynamic>>[
      {
        'instance_number': 1,
        'artifacts': <String, dynamic>{'crop': 'crop_1.png'},
        'classification': <String, dynamic>{'label': 'Bangle'},
      },
    ],
  };

  @override
  Future<Map<String, dynamic>> authorizedGet(String path) async =>
      path.endsWith('/labels')
      ? <String, dynamic>{
          'labels': <String>['Bangle', 'Mattal'],
        }
      : result;

  @override
  Future<List<int>> authorizedBytes(String path) async => base64Decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lGQAAAAASUVORK5CYII=',
  );

  @override
  Future<Map<String, dynamic>> authorizedPost(
    String path,
    Map<String, dynamic> body,
  ) async {
    confirmation = body;
    return result;
  }
}

void main() {
  testWidgets('reviewer can replace a predicted type and confirm the piece', (
    tester,
  ) async {
    final controller = ReviewController();
    await tester.pumpWidget(
      MaterialApp(
        home: ResultReviewScreen(controller: controller, jobId: 'job-1'),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Model prediction: Bangle'), 200);
    expect(find.text('Model prediction: Bangle'), findsOneWidget);
    await tester.ensureVisible(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mattal').last);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Confirm all predictions'), 180);
    await tester.tap(find.text('Confirm all predictions'));
    await tester.pumpAndSettle();
    expect(controller.confirmation, {
      'items': [
        {'instance_number': 1, 'label': 'Mattal'},
      ],
    });
  });
}
