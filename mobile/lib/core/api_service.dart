import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import 'server_settings.dart';

String certificateFingerprint(X509Certificate certificate) =>
    sha256.convert(certificate.der).toString();

bool matchesPinnedCertificate(
  List<int> certificateDer,
  String expectedFingerprint,
) =>
    sha256.convert(certificateDer).toString().toLowerCase() ==
    expectedFingerprint.replaceAll(':', '').toLowerCase();

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiService {
  ApiService(this.settings) {
    final error = connectionConfigurationError(settings);
    if (error != null) throw ApiException(error);
    _client =
        allowInsecureHttp
              ? HttpClient()
              : HttpClient(context: SecurityContext(withTrustedRoots: false))
          ..badCertificateCallback = (certificate, host, port) =>
              host.toLowerCase() == settings.host.toLowerCase() &&
              port == settings.port &&
              matchesPinnedCertificate(
                certificate.der,
                configuredCertificateFingerprint,
              );
    _client.connectionTimeout = const Duration(seconds: 8);
    _client.idleTimeout = const Duration(seconds: 8);
  }

  final ServerSettings settings;
  late final HttpClient _client;

  void close() => _client.close(force: true);

  Future<Map<String, dynamic>> get(String path, {String? accessToken}) =>
      request('GET', path, accessToken: accessToken);

  Future<Map<String, dynamic>> post(
    String path,
    Map<String, dynamic> body, {
    String? accessToken,
  }) => request('POST', path, body: body, accessToken: accessToken);

  Future<Map<String, dynamic>> request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    String? accessToken,
  }) async {
    final decoded = await requestAny(
      method,
      path,
      body: body,
      accessToken: accessToken,
    );
    if (decoded is! Map<String, dynamic>) {
      throw const ApiException('Invalid server response.');
    }
    return decoded;
  }

  Future<List<dynamic>> getList(String path, {String? accessToken}) async {
    final decoded = await requestAny('GET', path, accessToken: accessToken);
    if (decoded is! List<dynamic>) {
      throw const ApiException('Invalid server response.');
    }
    return decoded;
  }

  Future<dynamic> requestAny(
    String method,
    String path, {
    Map<String, dynamic>? body,
    String? accessToken,
  }) async {
    if (!path.startsWith('/api/v1/') || path.contains('..')) {
      throw const ApiException('Invalid API path.');
    }
    final uri = settings.baseUri.replace(path: path);
    try {
      final request = await _client
          .openUrl(method, uri)
          .timeout(const Duration(seconds: 12));
      request.followRedirects = false;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (accessToken != null) {
        request.headers.set(
          HttpHeaders.authorizationHeader,
          'Bearer $accessToken',
        );
      }
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }
      final response = await request.close().timeout(
        const Duration(seconds: 15),
      );
      final content = await utf8.decoder
          .bind(response)
          .join()
          .timeout(const Duration(seconds: 15));
      final decoded = content.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(content);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = decoded is Map ? decoded['detail'] : null;
        throw ApiException(
          detail is String ? detail : 'Server returned ${response.statusCode}.',
          statusCode: response.statusCode,
        );
      }
      return decoded;
    } on ApiException {
      rethrow;
    } on HandshakeException {
      throw const ApiException(
        'Secure connection failed. Check the server certificate and address.',
      );
    } on SocketException {
      throw const ApiException(
        'Cannot reach the server. Check Wi-Fi, address, and port.',
      );
    } on TimeoutException {
      throw const ApiException('The server did not respond in time.');
    } on FormatException {
      throw const ApiException('The server sent an invalid response.');
    }
  }

  Future<List<int>> getBytes(String path, {required String accessToken}) async {
    if (!path.startsWith('/api/v1/') || path.contains('..')) {
      throw const ApiException('Invalid API path.');
    }
    try {
      final request = await _client.getUrl(
        settings.baseUri.replace(path: path),
      );
      request.followRedirects = false;
      request.headers.set(
        HttpHeaders.authorizationHeader,
        'Bearer $accessToken',
      );
      final response = await request.close().timeout(
        const Duration(seconds: 30),
      );
      final bytes = await response
          .fold<List<int>>(<int>[], (data, chunk) {
            data.addAll(chunk);
            return data;
          })
          .timeout(const Duration(seconds: 30));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          'Image unavailable (${response.statusCode}).',
          statusCode: response.statusCode,
        );
      }
      return bytes;
    } on HandshakeException {
      throw const ApiException(
        'Secure connection failed. Check the server certificate and address.',
      );
    } on SocketException {
      throw const ApiException(
        'Cannot reach the server. Check Wi-Fi, address, and port.',
      );
    } on TimeoutException {
      throw const ApiException('The server did not respond in time.');
    }
  }

  Future<Map<String, dynamic>> uploadImage(
    String path,
    List<int> bytes, {
    required String filename,
    required String accessToken,
  }) async {
    if (!path.startsWith('/api/v1/') || path.contains('..')) {
      throw const ApiException('Invalid API path.');
    }
    final boundary = 'goldnest-${DateTime.now().microsecondsSinceEpoch}';
    final safeName = filename.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
    final isPng = safeName.toLowerCase().endsWith('.png');
    final prefix = utf8.encode(
      '--$boundary\r\nContent-Disposition: form-data; name="file"; filename="$safeName"\r\nContent-Type: image/${isPng ? 'png' : 'jpeg'}\r\n\r\n',
    );
    final suffix = utf8.encode('\r\n--$boundary--\r\n');
    try {
      final request = await _client.postUrl(
        settings.baseUri.replace(path: path),
      );
      request.followRedirects = false;
      request.headers.set(
        HttpHeaders.authorizationHeader,
        'Bearer $accessToken',
      );
      request.headers.set(
        HttpHeaders.contentTypeHeader,
        'multipart/form-data; boundary=$boundary',
      );
      request.contentLength = prefix.length + bytes.length + suffix.length;
      request.add(prefix);
      request.add(bytes);
      request.add(suffix);
      final response = await request.close().timeout(
        const Duration(seconds: 60),
      );
      final content = await utf8.decoder
          .bind(response)
          .join()
          .timeout(const Duration(seconds: 30));
      final decoded = jsonDecode(content);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = decoded is Map ? decoded['detail'] : null;
        throw ApiException(
          detail is String ? detail : 'Upload failed (${response.statusCode}).',
          statusCode: response.statusCode,
        );
      }
      if (decoded is! Map<String, dynamic>) {
        throw const ApiException('Invalid server response.');
      }
      return decoded;
    } on HandshakeException {
      throw const ApiException(
        'Secure connection failed. Check the server certificate and address.',
      );
    } on SocketException {
      throw const ApiException(
        'Cannot reach the server. Check Wi-Fi, address, and port.',
      );
    } on TimeoutException {
      throw const ApiException('The server did not respond in time.');
    }
  }
}
