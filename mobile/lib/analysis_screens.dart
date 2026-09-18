import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'core/app_controller.dart';

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({
    super.key,
    required this.controller,
    required this.mode,
  });
  final AppController controller;
  final String mode;

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  XFile? image;
  Uint8List? preview;
  bool busy = false;
  String? message;
  String? jobId;

  Future<void> pick(ImageSource source) async {
    try {
      final chosen = await ImagePicker().pickImage(source: source);
      if (chosen == null || !mounted) return;
      if (!RegExp(
        r'\.(png|jpe?g)$',
        caseSensitive: false,
      ).hasMatch(chosen.name)) {
        setState(() => message = 'Choose a JPEG or PNG image.');
        return;
      }
      final data = await chosen.readAsBytes();
      if (data.length > 20 * 1024 * 1024) {
        setState(() => message = 'Choose an image smaller than 20 MB.');
        return;
      }
      setState(() {
        image = chosen;
        preview = data;
        message = null;
      });
    } catch (error) {
      if (mounted) setState(() => message = 'Could not open the image: $error');
    }
  }

  Future<void> analyze() async {
    if (image == null || preview == null || busy) return;
    setState(() {
      busy = true;
      message = 'Creating analysis…';
    });
    try {
      final created = await widget.controller.authorizedPost('/api/v1/jobs', {
        'mode': widget.mode,
        'captured_at': DateTime.now().toUtc().toIso8601String(),
      });
      jobId = created['job_id'] as String;
      if (mounted) setState(() => message = 'Uploading image…');
      await widget.controller.authorizedUpload(
        '/api/v1/jobs/$jobId/images',
        preview!,
        image!.name,
      );
      await widget.controller.authorizedPost('/api/v1/jobs/$jobId/submit', {});
      if (mounted) {
        setState(() => message = 'Detecting and classifying jewellery…');
      }
      for (var attempt = 0; attempt < 180; attempt++) {
        if (!mounted) return;
        await Future<void>.delayed(const Duration(seconds: 2));
        final current = await widget.controller.authorizedGet(
          '/api/v1/jobs/$jobId',
        );
        if (current['status'] == 'completed') {
          if (!mounted) return;
          await Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => ResultReviewScreen(
                controller: widget.controller,
                jobId: jobId!,
              ),
            ),
          );
          return;
        }
        if (current['status'] == 'failed') {
          throw StateError(
            current['error_message']?.toString() ?? 'Analysis failed.',
          );
        }
      }
      throw StateError(
        'Analysis is still running. Find it in Previous results.',
      );
    } catch (error) {
      if (mounted) setState(() => message = error.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(
        widget.mode == 'single' ? 'Analyze one piece' : 'Analyze a group',
      ),
    ),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Use a clear photo on a plain, light background. Keep each piece visible.',
          ),
          const SizedBox(height: 20),
          if (preview != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.memory(preview!, height: 280, fit: BoxFit.contain),
            ),
            const SizedBox(height: 20),
          ],
          OutlinedButton.icon(
            onPressed: busy ? null : () => pick(ImageSource.camera),
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Take photo'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: busy ? null : () => pick(ImageSource.gallery),
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Choose photo'),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: busy || image == null ? null : analyze,
            child: const Text('Analyze jewellery'),
          ),
          if (busy) ...[
            const SizedBox(height: 16),
            const Center(child: CircularProgressIndicator()),
          ],
          if (message != null) ...[const SizedBox(height: 16), Text(message!)],
        ],
      ),
    ),
  );
}

class JobHistoryScreen extends StatefulWidget {
  const JobHistoryScreen({super.key, required this.controller});
  final AppController controller;

  @override
  State<JobHistoryScreen> createState() => _JobHistoryScreenState();
}

class _JobHistoryScreenState extends State<JobHistoryScreen> {
  List<Map<String, dynamic>> jobs = [];
  String? error;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    setState(() => loading = true);
    try {
      final response = await widget.controller.authorizedList('/api/v1/jobs');
      if (mounted) {
        setState(() {
          jobs = response.cast<Map<String, dynamic>>();
          error = null;
        });
      }
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Previous results'),
      actions: [
        IconButton(
          onPressed: refresh,
          icon: const Icon(Icons.refresh),
          tooltip: 'Refresh',
        ),
      ],
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? Center(child: Text(error!))
        : jobs.isEmpty
        ? const Center(child: Text('No analyses yet.'))
        : ListView.builder(
            itemCount: jobs.length,
            itemBuilder: (context, index) {
              final job = jobs[index];
              final completed = job['status'] == 'completed';
              final date = DateTime.tryParse(
                job['captured_at']?.toString() ?? '',
              )?.toLocal();
              return Card(
                child: ListTile(
                  title: Text(
                    '${job['mode'] == 'group' ? 'Group' : 'Single piece'} · ${job['physical_jewel_count'] ?? '…'} pieces',
                  ),
                  subtitle: Text(
                    '${date?.toString().substring(0, 16) ?? ''} · ${job['status']}',
                  ),
                  trailing: completed ? const Icon(Icons.chevron_right) : null,
                  onTap: completed
                      ? () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => ResultReviewScreen(
                              controller: widget.controller,
                              jobId: job['job_id'] as String,
                            ),
                          ),
                        )
                      : null,
                ),
              );
            },
          ),
  );
}

class ResultReviewScreen extends StatefulWidget {
  const ResultReviewScreen({
    super.key,
    required this.controller,
    required this.jobId,
  });
  final AppController controller;
  final String jobId;

  @override
  State<ResultReviewScreen> createState() => _ResultReviewScreenState();
}

class _ResultReviewScreenState extends State<ResultReviewScreen> {
  Map<String, dynamic>? result;
  Uint8List? annotated;
  Map<int, Uint8List> crops = {};
  List<String> labels = [];
  final Map<int, String> selected = {};
  bool busy = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() => busy = true);
    try {
      final loaded = await widget.controller.authorizedGet(
        '/api/v1/jobs/${widget.jobId}/result',
      );
      final taxonomy = await widget.controller.authorizedGet(
        '/api/v1/jobs/labels',
      );
      final artifact =
          (loaded['artifacts'] as Map<String, dynamic>)['annotated'] as String;
      final bytes = await widget.controller.authorizedBytes(
        '/api/v1/jobs/${widget.jobId}/artifacts/$artifact',
      );
      final cropBytes = <int, Uint8List>{};
      for (final rawItem in loaded['instances'] as List<dynamic>) {
        final item = rawItem as Map<String, dynamic>;
        final number = item['instance_number'] as int;
        final crop =
            (item['artifacts'] as Map<String, dynamic>)['crop'] as String;
        cropBytes[number] = Uint8List.fromList(
          await widget.controller.authorizedBytes(
            '/api/v1/jobs/${widget.jobId}/artifacts/$crop',
          ),
        );
      }
      if (!mounted) return;
      setState(() {
        result = loaded;
        labels = (taxonomy['labels'] as List<dynamic>).cast<String>();
        annotated = Uint8List.fromList(bytes);
        crops = cropBytes;
        selected.clear();
        for (final item in (loaded['instances'] as List<dynamic>)) {
          final piece = item as Map<String, dynamic>;
          selected[piece['instance_number'] as int] =
              (piece['classification'] as Map<String, dynamic>)['label']
                  as String;
        }
        error = null;
      });
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> confirm() async {
    if (result == null || busy) return;
    setState(() => busy = true);
    try {
      await widget.controller.authorizedPost(
        '/api/v1/jobs/${widget.jobId}/confirm',
        {
          'items': selected.entries
              .map(
                (entry) => {'instance_number': entry.key, 'label': entry.value},
              )
              .toList(),
        },
      );
      await load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Labels saved. Future predictions now use this confirmed example.',
            ),
          ),
        );
      }
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = result;
    final pieces = data == null
        ? <dynamic>[]
        : data['instances'] as List<dynamic>;
    final selectedCounts = <String, int>{};
    for (final label in selected.values) {
      selectedCounts[label] = (selectedCounts[label] ?? 0) + 1;
    }
    final captured = data == null
        ? null
        : DateTime.tryParse(data['captured_at'] as String)?.toLocal();
    return Scaffold(
      appBar: AppBar(title: const Text('Review predictions')),
      body: SafeArea(
        child: data == null
            ? Center(
                child: error != null
                    ? Text(error!)
                    : const CircularProgressIndicator(),
              )
            : ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  if (annotated != null)
                    Container(
                      height: 360,
                      decoration: BoxDecoration(
                        border: Border.all(color: const Color(0xFFD8E7F5)),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: InteractiveViewer(
                        minScale: .5,
                        maxScale: 5,
                        child: Image.memory(annotated!, fit: BoxFit.contain),
                      ),
                    ),
                  const SizedBox(height: 16),
                  Text(
                    '${data['physical_jewel_count']} ${data['physical_jewel_count'] == 1 ? 'piece' : 'pieces'}',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  if (captured != null)
                    Text('Captured ${captured.toString().substring(0, 16)}'),
                  const SizedBox(height: 10),
                  const Text('Type count'),
                  Wrap(
                    spacing: 8,
                    children: selectedCounts.entries
                        .map(
                          (entry) =>
                              Chip(label: Text('${entry.key}: ${entry.value}')),
                        )
                        .toList(),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Check and edit each type before confirming.',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  for (final item in pieces) ...[
                    Builder(
                      builder: (context) {
                        final piece = item as Map<String, dynamic>;
                        final number = piece['instance_number'] as int;
                        final classification =
                            piece['classification'] as Map<String, dynamic>;
                        final predicted =
                            classification['predicted_label'] ??
                            classification['label'];
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (crops[number] != null) ...[
                                  Center(
                                    child: Image.memory(
                                      crops[number]!,
                                      height: 125,
                                      fit: BoxFit.contain,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                ],
                                Text(
                                  'Piece $number',
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium,
                                ),
                                Text('Model prediction: $predicted'),
                                const SizedBox(height: 12),
                                DropdownButtonFormField<String>(
                                  key: ValueKey(
                                    '${widget.jobId}-$number-${classification['confirmed_at']}',
                                  ),
                                  initialValue: selected[number],
                                  decoration: const InputDecoration(
                                    labelText: 'Jewellery type',
                                  ),
                                  items: labels
                                      .map(
                                        (label) => DropdownMenuItem(
                                          value: label,
                                          child: Text(label),
                                        ),
                                      )
                                      .toList(),
                                  onChanged: busy
                                      ? null
                                      : (label) {
                                          if (label != null) {
                                            setState(
                                              () => selected[number] = label,
                                            );
                                          }
                                        },
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 8),
                  ],
                  if (pieces.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: busy ? null : confirm,
                      icon: const Icon(Icons.check_circle_outline),
                      label: Text(
                        data['confirmed_at'] == null
                            ? 'Confirm all predictions'
                            : 'Save corrected labels',
                      ),
                    ),
                  ],
                  if (busy)
                    const Padding(
                      padding: EdgeInsets.all(14),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}
