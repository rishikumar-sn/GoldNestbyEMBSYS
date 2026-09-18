import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import 'server_settings.dart';

class SecureStore {
  SecureStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<ServerSettings> loadServer() async {
    final host = await _storage.read(key: 'server_host') ?? '';
    final port = await _storage.read(key: 'server_port') ?? '8443';
    return ServerSettings(host: host, port: int.tryParse(port) ?? 8443);
  }

  Future<void> saveServer(ServerSettings settings) async {
    await _storage.write(key: 'server_host', value: settings.host);
    await _storage.write(key: 'server_port', value: settings.port.toString());
  }

  Future<String> installationId() async {
    final existing = await _storage.read(key: 'installation_id');
    if (existing != null && existing.isNotEmpty) return existing;
    final id = const Uuid().v4();
    await _storage.write(key: 'installation_id', value: id);
    return id;
  }

  Future<String?> get refreshToken => _storage.read(key: 'refresh_token');
  Future<String?> get accessToken => _storage.read(key: 'access_token');

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }
}
