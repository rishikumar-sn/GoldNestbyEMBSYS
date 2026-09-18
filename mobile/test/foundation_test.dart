import 'package:flutter_test/flutter_test.dart';
import 'package:goldnest_mobile/core/api_service.dart';
import 'package:goldnest_mobile/core/server_settings.dart';

void main() {
  test('server settings only accept a host and a valid port', () {
    final settings = ServerSettings.parse('192.168.29.121', '8443');
    expect(settings.baseUri.toString(), 'https://192.168.29.121:8443');
    expect(
      () => ServerSettings.parse('https://example.com', '8443'),
      throwsFormatException,
    );
    expect(
      () => ServerSettings.parse('example.com/path', '8443'),
      throwsFormatException,
    );
    expect(
      () => ServerSettings.parse('example.com', '0'),
      throwsFormatException,
    );
  });

  test('pin matching requires the exact certificate digest', () {
    const bytes = [1, 2, 3, 4];
    const digest =
        '9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a';
    expect(matchesPinnedCertificate(bytes, digest), isTrue);
    expect(matchesPinnedCertificate([1, 2, 3, 5], digest), isFalse);
    expect(matchesPinnedCertificate(bytes, '0' * 64), isFalse);
  });

  test('secure client requires a configured certificate pin', () {
    expect(
      connectionConfigurationError(
        const ServerSettings(host: '192.168.29.121', port: 8443),
      ),
      contains('pinned server certificate'),
    );
  });
}
