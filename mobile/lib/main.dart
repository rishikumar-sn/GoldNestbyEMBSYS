import 'package:flutter/material.dart';

import 'core/app_controller.dart';
import 'core/server_settings.dart';
import 'analysis_screens.dart';

const _companyLogo = 'assets/branding/embsys_logo.png';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = AppController();
  controller.initialize();
  runApp(GoldNestApp(controller: controller));
}

class GoldNestApp extends StatelessWidget {
  const GoldNestApp({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) => MaterialApp(
      title: 'GoldNest',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        fontFamily: 'GoldNestRoboto',
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0868B8),
          primary: const Color(0xFF0868B8),
          secondary: const Color(0xFF287CC1),
          surface: Colors.white,
        ),
        scaffoldBackgroundColor: Colors.white,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Color(0xFF075A9B),
          surfaceTintColor: Colors.white,
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 15,
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      ),
      home: controller.loading
          ? const Scaffold(
              body: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Image(image: AssetImage(_companyLogo), width: 190),
                    SizedBox(height: 24),
                    CircularProgressIndicator(),
                  ],
                ),
              ),
            )
          : controller.signedIn
          ? HomeScreen(controller: controller)
          : LoginScreen(controller: controller),
    ),
  );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.controller});
  final AppController controller;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final formKey = GlobalKey<FormState>();
  final username = TextEditingController();
  final password = TextEditingController();
  bool showPassword = false;

  @override
  void dispose() {
    username.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Image.asset(_companyLogo, width: 205, height: 72),
                  const SizedBox(height: 18),
                  Text(
                    'GOLDNEST',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      letterSpacing: 4,
                      color: scheme.secondary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 38),
                  Text(
                    'Welcome back',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF113B5D),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Sign in to your jewellery workspace.',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 28),
                  Card(
                    elevation: 0,
                    color: const Color(0xFFF2F7FC),
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Form(
                        key: formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            TextFormField(
                              controller: username,
                              textInputAction: TextInputAction.next,
                              autocorrect: false,
                              enableSuggestions: false,
                              decoration: const InputDecoration(
                                labelText: 'Username',
                                prefixIcon: Icon(Icons.person_outline),
                              ),
                              validator: (value) =>
                                  value == null || value.trim().isEmpty
                                  ? 'Enter your username.'
                                  : null,
                            ),
                            const SizedBox(height: 16),
                            TextFormField(
                              controller: password,
                              obscureText: !showPassword,
                              onFieldSubmitted: (_) => submit(),
                              decoration: InputDecoration(
                                labelText: 'Password',
                                prefixIcon: const Icon(Icons.lock_outline),
                                suffixIcon: IconButton(
                                  tooltip: showPassword
                                      ? 'Hide password'
                                      : 'Show password',
                                  icon: Icon(
                                    showPassword
                                        ? Icons.visibility_off_outlined
                                        : Icons.visibility_outlined,
                                  ),
                                  onPressed: () => setState(
                                    () => showPassword = !showPassword,
                                  ),
                                ),
                              ),
                              validator: (value) =>
                                  value == null || value.isEmpty
                                  ? 'Enter your password.'
                                  : null,
                            ),
                            if (widget.controller.error != null) ...[
                              const SizedBox(height: 14),
                              Text(
                                widget.controller.error!,
                                style: TextStyle(color: scheme.error),
                              ),
                            ],
                            const SizedBox(height: 22),
                            FilledButton(
                              onPressed: widget.controller.busy ? null : submit,
                              child: widget.controller.busy
                                  ? const SizedBox(
                                      height: 22,
                                      width: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text('Sign in'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) =>
                            ServerSettingsScreen(controller: widget.controller),
                      ),
                    ),
                    icon: const Icon(Icons.settings_ethernet),
                    label: Text(
                      widget.controller.server.isConfigured
                          ? '${widget.controller.server.host}:${widget.controller.server.port}'
                          : 'Set server address',
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> submit() async {
    if (!formKey.currentState!.validate()) return;
    await widget.controller.login(username.text, password.text);
  }
}

class ServerSettingsScreen extends StatefulWidget {
  const ServerSettingsScreen({super.key, required this.controller});
  final AppController controller;

  @override
  State<ServerSettingsScreen> createState() => _ServerSettingsScreenState();
}

class _ServerSettingsScreenState extends State<ServerSettingsScreen> {
  late final TextEditingController host;
  late final TextEditingController port;
  bool checking = false;
  String? message;

  @override
  void initState() {
    super.initState();
    host = TextEditingController(text: widget.controller.server.host);
    port = TextEditingController(
      text: widget.controller.server.port.toString(),
    );
  }

  @override
  void dispose() {
    host.dispose();
    port.dispose();
    super.dispose();
  }

  ServerSettings? parsed() {
    try {
      return ServerSettings.parse(host.text, port.text);
    } on FormatException catch (exception) {
      setState(() => message = exception.message);
      return null;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Server settings')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Text('Connect to GoldNest on your local network.'),
          const SizedBox(height: 24),
          TextField(
            controller: host,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Server IP or hostname',
              hintText: '192.168.1.25',
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: port,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'HTTPS port',
              hintText: '8443',
            ),
          ),
          const SizedBox(height: 18),
          Card(
            elevation: 0,
            child: ListTile(
              leading: const Icon(Icons.verified_user_outlined),
              title: const Text('Certificate pin'),
              subtitle: Text(
                configuredCertificateFingerprint.isEmpty
                    ? 'No certificate configured in this app build.'
                    : '${configuredCertificateFingerprint.substring(0, 16)}…',
              ),
            ),
          ),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(
              message!,
              style: TextStyle(color: Theme.of(context).colorScheme.primary),
            ),
          ],
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: checking ? null : checkConnection,
            icon: checking
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.wifi_tethering),
            label: const Text('Test connection'),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: checking ? null : save,
            child: const Text('Save server'),
          ),
        ],
      ),
    ),
  );

  Future<void> checkConnection() async {
    final settings = parsed();
    if (settings == null) return;
    setState(() {
      checking = true;
      message = null;
    });
    try {
      final result = await widget.controller.testConnection(settings);
      if (!mounted) return;
      setState(
        () => message = result['readiness'] == 'ready'
            ? 'Connected securely. Server and worker are ready.'
            : 'Connected securely. Server is online; the worker is not ready yet.',
      );
    } catch (exception) {
      if (!mounted) return;
      setState(() => message = exception.toString());
    } finally {
      if (mounted) setState(() => checking = false);
    }
  }

  Future<void> save() async {
    final settings = parsed();
    if (settings == null) return;
    try {
      await widget.controller.saveServer(settings);
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      if (mounted) setState(() => message = 'Could not save server settings.');
    }
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.controller});
  final AppController controller;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Row(
        children: [
          Image.asset(_companyLogo, width: 94, height: 36),
          const SizedBox(width: 12),
          const Text('GoldNest'),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'Server settings',
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => ServerSettingsScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.settings_outlined),
        ),
      ],
    ),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Welcome, ${controller.username}',
            style: Theme.of(context).textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text('Your jewellery workspace is connected.'),
          const SizedBox(height: 28),
          Card(
            elevation: 0,
            color: const Color(0xFFF2F7FC),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.verified_user_outlined, size: 34),
                  const SizedBox(height: 16),
                  Text(
                    'Signed-in device',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  SelectableText(
                    'Device ID: ${controller.deviceId ?? 'Unavailable'}',
                  ),
                  const SizedBox(height: 8),
                  SelectableText('Server: ${controller.server.baseUri}'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) =>
                    AnalysisScreen(controller: controller, mode: 'single'),
              ),
            ),
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Analyze one piece'),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) =>
                    AnalysisScreen(controller: controller, mode: 'group'),
              ),
            ),
            icon: const Icon(Icons.auto_awesome_mosaic_outlined),
            label: const Text('Analyze a group'),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => JobHistoryScreen(controller: controller),
              ),
            ),
            icon: const Icon(Icons.history),
            label: const Text('Previous results'),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: controller.logout,
            icon: const Icon(Icons.logout),
            label: const Text('Sign out'),
          ),
        ],
      ),
    ),
  );
}
