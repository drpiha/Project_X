import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:campaign_app/l10n/app_localizations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/api/api_client.dart';
import '../../../core/config/app_config.dart';

class PostLog {
  final String id;
  final String campaignId;
  final String? draftId;
  final DateTime runAt;
  final String action;
  final Map<String, dynamic>? details;

  PostLog({
    required this.id,
    required this.campaignId,
    this.draftId,
    required this.runAt,
    required this.action,
    this.details,
  });

  factory PostLog.fromJson(Map<String, dynamic> json) {
    return PostLog(
      id: json['id'] as String,
      campaignId: json['campaign_id'] as String,
      draftId: json['draft_id'] as String?,
      runAt: DateTime.parse(json['run_at'] as String),
      action: json['action'] as String,
      details: json['details'] as Map<String, dynamic>?,
    );
  }
}

class LogsScreen extends ConsumerStatefulWidget {
  const LogsScreen({super.key});

  @override
  ConsumerState<LogsScreen> createState() => _LogsScreenState();
}

class _LogsScreenState extends ConsumerState<LogsScreen> {
  List<PostLog> _logs = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadLogs();
  }

  Future<void> _loadLogs() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get(AppConfig.logs);
      final data = response.data as Map<String, dynamic>;
      final logsList = (data['logs'] as List<dynamic>)
          .map((e) => PostLog.fromJson(e as Map<String, dynamic>))
          .toList();

      setState(() {
        _logs = logsList;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.logs),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/campaigns'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadLogs,
          ),
        ],
      ),
      body: _buildBody(context, l10n),
    );
  }

  Widget _buildBody(BuildContext context, AppLocalizations l10n) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: AppTheme.errorColor.withOpacity(0.5),
            ),
            const SizedBox(height: 16),
            Text(_error!, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _loadLogs,
              child: Text(l10n.retry),
            ),
          ],
        ),
      );
    }

    if (_logs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.surfaceColor,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(
                Icons.history,
                size: 80,
                color: AppTheme.primaryColor.withOpacity(0.5),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              l10n.noLogs,
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadLogs,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _logs.length,
        itemBuilder: (context, index) {
          final log = _logs[index];
          return _LogCard(log: log, l10n: l10n);
        },
      ),
    );
  }
}

class _LogCard extends StatelessWidget {
  final PostLog log;
  final AppLocalizations l10n;

  const _LogCard({required this.log, required this.l10n});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            _ActionIcon(action: log.action),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getActionText(log.action),
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _formatDateTime(log.runAt),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (log.details != null &&
                      log.details!['message'] != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      log.details!['message'] as String,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppTheme.textSecondary,
                          ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getActionText(String action) {
    switch (action) {
      case 'generated':
        return l10n.logGenerated;
      case 'scheduled':
        return l10n.logScheduled;
      case 'posted':
        return l10n.logPosted;
      case 'failed':
        return l10n.logFailed;
      case 'skipped':
        return l10n.logSkipped;
      default:
        return action;
    }
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

class _ActionIcon extends StatelessWidget {
  final String action;

  const _ActionIcon({required this.action});

  @override
  Widget build(BuildContext context) {
    IconData icon;
    Color color;

    switch (action) {
      case 'generated':
        icon = Icons.auto_awesome;
        color = AppTheme.accentColor;
        break;
      case 'scheduled':
        icon = Icons.schedule;
        color = AppTheme.infoColor;
        break;
      case 'posted':
        icon = Icons.check_circle;
        color = AppTheme.successColor;
        break;
      case 'failed':
        icon = Icons.error;
        color = AppTheme.errorColor;
        break;
      case 'skipped':
        icon = Icons.skip_next;
        color = AppTheme.warningColor;
        break;
      default:
        icon = Icons.info;
        color = AppTheme.textMuted;
    }

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: color, size: 24),
    );
  }
}
