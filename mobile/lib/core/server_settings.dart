import 'package:flutter/foundation.dart';

const configuredCertificateFingerprint = String.fromEnvironment(
  'GOLDNEST_CERT_SHA256',
);
const allowInsecureHttp = bool.fromEnvironment('ALLOW_INSECURE_HTTP');

class ServerSettings {
  const ServerSettings({required this.host, required this.port});

  final String host;
  final int port;

  bool get isConfigured => host.isNotEmpty;
  Uri get baseUri =>
      Uri(scheme: allowInsecureHttp ? 'http' : 'https', host: host, port: port);

  static ServerSettings parse(String hostInput, String portInput) {
    final host = hostInput.trim();
    final port = int.tryParse(portInput.trim());
    if (host.isEmpty ||
        host.contains(RegExp(r'[\s/:?#@]')) ||
        !RegExp(r'^[a-zA-Z0-9.-]+$').hasMatch(host)) {
      throw const FormatException('Enter a server IP address or hostname.');
    }
    if (port == null || port < 1 || port > 65535) {
      throw const FormatException('Enter a port between 1 and 65535.');
    }
    return ServerSettings(host: host, port: port);
  }
}

String? connectionConfigurationError(ServerSettings settings) {
  if (!settings.isConfigured) return 'Set the server address first.';
  if (!allowInsecureHttp &&
      !RegExp(r'^[a-fA-F0-9]{64}$')
          .hasMatch(configuredCertificateFingerprint)) {
    return 'This app build has no valid pinned server certificate fingerprint.';
  }
  if (kReleaseMode && allowInsecureHttp) {
    return 'HTTP is unavailable in release builds.';
  }
  return null;
}
