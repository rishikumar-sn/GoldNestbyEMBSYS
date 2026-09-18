import 'package:flutter_test/flutter_test.dart';
import 'package:goldnest_mobile/core/api_service.dart';
import 'package:goldnest_mobile/core/server_settings.dart';
import 'package:uuid/uuid.dart';

const liveHost = String.fromEnvironment('LIVE_SERVER_HOST');
const livePort = int.fromEnvironment('LIVE_SERVER_PORT', defaultValue: 8443);
const liveUsername = String.fromEnvironment('LIVE_TEST_USERNAME');
const livePassword = String.fromEnvironment('LIVE_TEST_PASSWORD');
const expectPinFailure = bool.fromEnvironment('LIVE_EXPECT_PIN_FAILURE');

void main() {
  test(
    'pinned LAN API supports connection, login, device and token rotation',
    () async {
      final api = ApiService(ServerSettings(host: liveHost, port: livePort));
      try {
        expect((await api.get('/api/v1/health'))['status'], 'ok');
        expect((await api.get('/api/v1/ready'))['database'], 'ok');
        final login = await api.post('/api/v1/auth/login', {
          'username': liveUsername,
          'password': livePassword,
          'installation_id': const Uuid().v4(),
          'platform': 'android',
          'app_version': '1.0.0',
        });
        final device = await api.get(
          '/api/v1/devices/me',
          accessToken: login['access_token'] as String,
        );
        expect(device['username'], liveUsername);
        expect(device['device_id'], login['device_id']);
        final refreshed = await api.post('/api/v1/auth/refresh', {
          'refresh_token': login['refresh_token'],
        });
        expect(refreshed['device_id'], login['device_id']);
        await expectLater(
          api.post('/api/v1/auth/refresh', {
            'refresh_token': login['refresh_token'],
          }),
          throwsA(isA<ApiException>()),
        );
        final logout = await api.post('/api/v1/auth/logout', {
          'refresh_token': refreshed['refresh_token'],
        }, accessToken: refreshed['access_token'] as String);
        expect(logout['status'], 'ok');
      } finally {
        api.close();
      }
    },
    skip:
        expectPinFailure ||
        liveHost.isEmpty ||
        liveUsername.isEmpty ||
        livePassword.isEmpty,
  );

  test('a wrong certificate pin rejects the LAN server', () async {
    final api = ApiService(ServerSettings(host: liveHost, port: livePort));
    try {
      await expectLater(
        api.get('/api/v1/health'),
        throwsA(isA<ApiException>()),
      );
    } finally {
      api.close();
    }
  }, skip: !expectPinFailure || liveHost.isEmpty);
}
