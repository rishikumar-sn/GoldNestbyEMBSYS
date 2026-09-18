import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';

import 'api_service.dart';
import 'secure_store.dart';
import 'server_settings.dart';

class AppController extends ChangeNotifier {
  AppController({SecureStore? store}) : _store = store ?? SecureStore();

  final SecureStore _store;
  ServerSettings server = const ServerSettings(host: '', port: 8443);
  bool loading = true;
  bool busy = false;
  String? username;
  String? deviceId;
  String? error;

  bool get signedIn => username != null;

  Future<void> initialize() async {
    try {
      server = await _store.loadServer();
      if (server.isConfigured && await _store.refreshToken != null) {
        await _refresh();
        final device = await authorizedGet('/api/v1/devices/me');
        username = device['username'] as String?;
        deviceId = device['device_id'] as String?;
      }
    } on ApiException catch (exception) {
      error = exception.message;
      if (exception.statusCode == 401 || exception.statusCode == 403) {
        await _store.clearTokens();
      }
    } catch (_) {
      error = 'Could not load saved settings. Please reopen the app.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> saveServer(ServerSettings value) async {
    final changed = server.host != value.host || server.port != value.port;
    await _store.saveServer(value);
    server = value;
    if (changed) {
      await _store.clearTokens();
      username = null;
      deviceId = null;
    }
    error = null;
    notifyListeners();
  }

  Future<Map<String, dynamic>> testConnection(ServerSettings value) async {
    final api = ApiService(value);
    try {
      final health = await api.get('/api/v1/health');
      final ready = await api.get('/api/v1/ready');
      return {'health': health['status'], 'readiness': ready['status']};
    } finally {
      api.close();
    }
  }

  Future<void> login(String user, String password) async {
    busy = true;
    error = null;
    notifyListeners();
    try {
      final api = ApiService(server);
      try {
        final package = await PackageInfo.fromPlatform();
        final response = await api.post('/api/v1/auth/login', {
          'username': user.trim(),
          'password': password,
          'installation_id': await _store.installationId(),
          'platform': 'android',
          'app_version': package.version,
        });
        await _store.saveTokens(
          accessToken: response['access_token'] as String,
          refreshToken: response['refresh_token'] as String,
        );
        final device = await api.get(
          '/api/v1/devices/me',
          accessToken: response['access_token'] as String,
        );
        username = device['username'] as String?;
        deviceId = device['device_id'] as String?;
      } finally {
        api.close();
      }
    } on ApiException catch (exception) {
      error = exception.message;
    } catch (_) {
      error = 'Sign in failed. Please try again.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> _refresh() async {
    final token = await _store.refreshToken;
    if (token == null) {
      throw const ApiException('Please sign in again.', statusCode: 401);
    }
    final api = ApiService(server);
    try {
      final response = await api.post('/api/v1/auth/refresh', {
        'refresh_token': token,
      });
      await _store.saveTokens(
        accessToken: response['access_token'] as String,
        refreshToken: response['refresh_token'] as String,
      );
      deviceId = response['device_id'] as String?;
    } finally {
      api.close();
    }
  }

  Future<Map<String, dynamic>> authorizedGet(String path) async {
    return _authorized((api, token) => api.get(path, accessToken: token));
  }

  Future<Map<String, dynamic>> authorizedPost(
    String path,
    Map<String, dynamic> body,
  ) => _authorized((api, token) => api.post(path, body, accessToken: token));

  Future<List<dynamic>> authorizedList(String path) =>
      _authorized((api, token) => api.getList(path, accessToken: token));

  Future<List<int>> authorizedBytes(String path) =>
      _authorized((api, token) => api.getBytes(path, accessToken: token));

  Future<Map<String, dynamic>> authorizedUpload(
    String path,
    List<int> bytes,
    String filename,
  ) => _authorized(
    (api, token) =>
        api.uploadImage(path, bytes, filename: filename, accessToken: token),
  );

  Future<T> _authorized<T>(
    Future<T> Function(ApiService api, String token) action,
  ) async {
    var token = await _store.accessToken;
    if (token == null) {
      throw const ApiException('Please sign in again.', statusCode: 401);
    }
    for (var attempt = 0; attempt < 2; attempt++) {
      final api = ApiService(server);
      try {
        return await action(api, token!);
      } on ApiException catch (exception) {
        if (exception.statusCode != 401 || attempt > 0) rethrow;
      } finally {
        api.close();
      }
      await _refresh();
      token = await _store.accessToken;
    }
    throw const ApiException('Please sign in again.', statusCode: 401);
  }

  Future<void> logout() async {
    final refresh = await _store.refreshToken;
    final access = await _store.accessToken;
    if (refresh != null && access != null) {
      try {
        final api = ApiService(server);
        try {
          await api.post('/api/v1/auth/logout', {
            'refresh_token': refresh,
          }, accessToken: access);
        } finally {
          api.close();
        }
      } on ApiException {
        // Clear local credentials even if the server is offline.
      }
    }
    await _store.clearTokens();
    username = null;
    deviceId = null;
    notifyListeners();
  }
}
