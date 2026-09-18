import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goldnest_mobile/core/app_controller.dart';
import 'package:goldnest_mobile/main.dart';

void main() {
  testWidgets('login uses the blue theme and company logo asset', (
    tester,
  ) async {
    final controller = AppController()..loading = false;
    await tester.pumpWidget(GoldNestApp(controller: controller));
    await tester.pumpAndSettle();
    expect(find.text('GOLDNEST'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Image &&
            widget.image is AssetImage &&
            (widget.image as AssetImage).assetName ==
                'assets/branding/embsys_logo.png',
      ),
      findsOneWidget,
    );
    expect(
      Theme.of(tester.element(find.byType(LoginScreen))).colorScheme.primary,
      const Color(0xFF0868B8),
    );
    expect(tester.takeException(), isNull);
    controller.dispose();
  });
}
