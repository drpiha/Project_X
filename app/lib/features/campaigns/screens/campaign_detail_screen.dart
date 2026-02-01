import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:campaign_app/l10n/app_localizations.dart';
import '../providers/campaign_provider.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/api/api_client.dart';

class CampaignDetailScreen extends ConsumerStatefulWidget {
  final String campaignId;

  const CampaignDetailScreen({
    required this.campaignId,
    super.key,
  });

  @override
  ConsumerState<CampaignDetailScreen> createState() => _CampaignDetailScreenState();
}

class _CampaignDetailScreenState extends ConsumerState<CampaignDetailScreen> {
  Timer? _refreshTimer;
  Map<String, dynamic>? _campaignDetail;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCampaignDetail();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  int _consecutiveFailures = 0;

  void _startAutoRefresh() {
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      // Stop auto-refresh after 3 consecutive failures (backend likely sleeping)
      if (_consecutiveFailures < 3) {
        _loadCampaignDetail(silent: true);
      }
    });
  }

  Future<void> _loadCampaignDetail({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final detail = await ref.read(campaignsProvider.notifier).getCampaignDetail(widget.campaignId);
      if (mounted) {
        _consecutiveFailures = 0;
        setState(() {
          _campaignDetail = detail;
          _isLoading = false;
        });
      }
    } catch (e) {
      _consecutiveFailures++;
      if (mounted) {
        // On silent refresh, don't overwrite existing data with error
        if (!silent || _campaignDetail == null) {
          setState(() {
            _error = e.toString();
            _isLoading = false;
          });
        }
      }
    }
  }

  Future<void> _deleteCampaign() async {
    final l10n = AppLocalizations.of(context)!;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.deleteCampaign),
        content: Text(l10n.deleteCampaignConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.errorColor),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.delete('/v1/campaigns/${widget.campaignId}');

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(l10n.campaignDeleted),
            backgroundColor: AppTheme.successColor,
          ),
        );
        // Refresh campaigns list and go back
        ref.read(campaignsProvider.notifier).fetchCampaigns();
        context.go('/campaigns');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${l10n.error}: $e'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  /// Parse UTC datetime string from backend and convert to local time
  DateTime _parseUtcToLocal(String dateTimeStr) {
    final parsed = DateTime.parse(dateTimeStr);
    // Backend sends naive UTC datetime, so we need to treat it as UTC and convert to local
    return DateTime.utc(
      parsed.year, parsed.month, parsed.day,
      parsed.hour, parsed.minute, parsed.second, parsed.millisecond,
    ).toLocal();
  }

  String _getTimeDisplay(Map<String, dynamic> draft) {
    final status = draft['status'] as String;

    if (status == 'posted' && draft['posted_at'] != null) {
      final postedAt = _parseUtcToLocal(draft['posted_at'] as String);
      return "${postedAt.hour.toString().padLeft(2, '0')}:${postedAt.minute.toString().padLeft(2, '0')}'da gönderildi";
    }

    if (draft['scheduled_for'] != null) {
      final scheduledFor = _parseUtcToLocal(draft['scheduled_for'] as String);
      final now = DateTime.now();
      final diff = scheduledFor.difference(now);

      if (diff.isNegative) return "Zamanı geçti";

      if (diff.inMinutes < 60) {
        return "${diff.inMinutes} dk sonra";
      } else if (diff.inHours < 24) {
        return "${diff.inHours} saat sonra";
      } else {
        return "${scheduledFor.day}/${scheduledFor.month} ${scheduledFor.hour}:${scheduledFor.minute.toString().padLeft(2, '0')}";
      }
    }

    return "Zamanlanmadı";
  }

  IconData _getStatusIcon(String status) {
    switch (status) {
      case 'posted':
        return Icons.check_circle;
      case 'pending':
        return Icons.schedule;
      case 'failed':
        return Icons.error;
      default:
        return Icons.help;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'posted':
        return AppTheme.successColor;
      case 'pending':
        return Colors.orange;
      case 'failed':
        return AppTheme.errorColor;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.campaignDetail)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.campaignDetail)),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('${l10n.error}: $_error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadCampaignDetail,
                child: Text(l10n.retry),
              ),
            ],
          ),
        ),
      );
    }

    if (_campaignDetail == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.campaignDetail)),
        body: Center(child: Text(l10n.campaignNotFound)),
      );
    }

    final campaign = _campaignDetail!['campaign'] as Map<String, dynamic>;
    final drafts = (_campaignDetail!['drafts'] as List<dynamic>).cast<Map<String, dynamic>>();
    final stats = _campaignDetail!['stats'] as Map<String, dynamic>;

    return Scaffold(
      appBar: AppBar(
        title: Text(campaign['title'] as String),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadCampaignDetail,
            tooltip: l10n.retry,
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'edit') {
                context.go('/campaigns/${widget.campaignId}/edit');
              } else if (value == 'delete') {
                _deleteCampaign();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'edit',
                child: Row(
                  children: [
                    const Icon(Icons.edit_outlined, color: AppTheme.primaryColor),
                    const SizedBox(width: 8),
                    Text(l10n.editCampaign, style: const TextStyle(color: AppTheme.primaryColor)),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    const Icon(Icons.delete_outline, color: AppTheme.errorColor),
                    const SizedBox(width: 8),
                    Text(l10n.deleteCampaign, style: const TextStyle(color: AppTheme.errorColor)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // Stats Card
          Container(
            padding: const EdgeInsets.all(16),
            color: AppTheme.cardColor,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _StatItem(
                  label: l10n.total,
                  value: stats['total'].toString(),
                  color: Colors.blue,
                ),
                _StatItem(
                  label: l10n.sent,
                  value: stats['posted'].toString(),
                  color: AppTheme.successColor,
                ),
                _StatItem(
                  label: l10n.pending,
                  value: stats['pending'].toString(),
                  color: Colors.orange,
                ),
                _StatItem(
                  label: l10n.failed,
                  value: stats['failed'].toString(),
                  color: AppTheme.errorColor,
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Drafts List
          Expanded(
            child: drafts.isEmpty
                ? Center(child: Text(l10n.noTweetsYet))
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: drafts.length,
                    itemBuilder: (context, index) {
                      final draft = drafts[index];
                      return _DraftCard(
                        draft: draft,
                        statusIcon: _getStatusIcon(draft['status'] as String),
                        statusColor: _getStatusColor(draft['status'] as String),
                        timeDisplay: _getTimeDisplay(draft),
                        onRefresh: _loadCampaignDetail,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatItem({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: AppTheme.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _DraftCard extends ConsumerWidget {
  final Map<String, dynamic> draft;
  final IconData statusIcon;
  final Color statusColor;
  final String timeDisplay;
  final VoidCallback onRefresh;

  const _DraftCard({
    required this.draft,
    required this.statusIcon,
    required this.statusColor,
    required this.timeDisplay,
    required this.onRefresh,
  });

  Future<void> _openXLink(String url) async {
    // Try to open in X app via deep link first
    final tweetIdMatch = RegExp(r'/status/(\d+)').firstMatch(url);
    if (tweetIdMatch != null) {
      final tweetId = tweetIdMatch.group(1)!;
      final xAppUri = Uri.parse('twitter://status?id=$tweetId');
      try {
        if (await canLaunchUrl(xAppUri)) {
          await launchUrl(xAppUri);
          return;
        }
      } catch (_) {
        // X app not installed, fall through to browser
      }
    }

    // Fallback to web URL
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _copyToClipboard(BuildContext context, String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(AppLocalizations.of(context)!.copied), duration: const Duration(seconds: 1)),
    );
  }

  Future<void> _editDraft(BuildContext context, WidgetRef ref) async {
    final draftId = draft['id'] as String;
    final currentText = draft['text'] as String;
    final status = draft['status'] as String;

    // Don't allow editing posted drafts
    if (status == 'posted') {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.postedTweetsCannotBeEdited)),
      );
      return;
    }

    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _EditDraftSheet(
        currentText: currentText,
        scheduledFor: draft['scheduled_for'] as String?,
      ),
    );

    if (result != null) {
      try {
        await ref.read(campaignsProvider.notifier).updateDraft(
          draftId: draftId,
          text: result['text'] as String?,
          scheduledFor: result['scheduled_for'] as DateTime?,
          status: result['status'] as String?,
        );
        onRefresh();
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context)!.tweetUpdated),
              backgroundColor: AppTheme.successColor,
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          final l10n = AppLocalizations.of(context)!;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${l10n.error}: $e'), backgroundColor: AppTheme.errorColor),
          );
        }
      }
    }
  }

  Future<void> _scheduleDraft(BuildContext context, WidgetRef ref) async {
    final draftId = draft['id'] as String;
    final status = draft['status'] as String;
    final l10n = AppLocalizations.of(context)!;

    if (status == 'posted') return;

    final TimeOfDay? time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );

    if (time == null || !context.mounted) return;

    final now = DateTime.now();
    final scheduledFor = DateTime(now.year, now.month, now.day, time.hour, time.minute);

    try {
      await ref.read(campaignsProvider.notifier).updateDraft(
        draftId: draftId,
        scheduledFor: scheduledFor,
        status: 'pending',
      );
      onRefresh();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(l10n.tweetScheduled),
            backgroundColor: AppTheme.successColor,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${l10n.error}: $e'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
  }

  Future<void> _deleteDraft(BuildContext context, WidgetRef ref) async {
    final draftId = draft['id'] as String;
    final l10n = AppLocalizations.of(context)!;

    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.deleteDraft),
        content: Text(l10n.deleteDraftConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.errorColor),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );

    if (confirmed != true || !context.mounted) return;

    try {
      await ref.read(campaignsProvider.notifier).deleteDraft(draftId);
      onRefresh();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(l10n.draftDeleted),
            backgroundColor: AppTheme.successColor,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${l10n.error}: $e'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final xPostUrl = draft['x_post_url'] as String?;
    final mediaAssets = (draft['media_assets'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    final status = draft['status'] as String;
    final isPosted = status == 'posted';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: isPosted ? null : () => _editDraft(context, ref),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status and Time
              Row(
                children: [
                  Icon(statusIcon, color: statusColor, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      timeDisplay,
                      style: TextStyle(
                        fontSize: 12,
                        color: statusColor,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  // Action buttons
                  IconButton(
                    icon: const Icon(Icons.copy, size: 18),
                    onPressed: () => _copyToClipboard(context, draft['text'] as String),
                    tooltip: AppLocalizations.of(context)!.copy,
                    color: AppTheme.textMuted,
                  ),
                  if (!isPosted)
                    IconButton(
                      icon: const Icon(Icons.schedule, size: 18),
                      onPressed: () => _scheduleDraft(context, ref),
                      tooltip: AppLocalizations.of(context)!.schedule,
                      color: AppTheme.primaryColor,
                    ),
                  if (!isPosted)
                    IconButton(
                      icon: const Icon(Icons.edit, size: 18),
                      onPressed: () => _editDraft(context, ref),
                      tooltip: AppLocalizations.of(context)!.edit,
                      color: AppTheme.accentColor,
                    ),
                  if (!isPosted)
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18),
                      onPressed: () => _deleteDraft(context, ref),
                      tooltip: AppLocalizations.of(context)!.delete,
                      color: AppTheme.errorColor,
                    ),
                  if (xPostUrl != null)
                    IconButton(
                      icon: const Icon(Icons.open_in_new, size: 18),
                      onPressed: () => _openXLink(xPostUrl),
                      tooltip: "X",
                      color: AppTheme.successColor,
                    ),
                ],
              ),
              const SizedBox(height: 8),

              // Tweet Text
              Text(
                draft['text'] as String,
                style: const TextStyle(fontSize: 14),
              ),

              // Character count
              const SizedBox(height: 8),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${(draft['text'] as String).length}/280',
                      style: const TextStyle(fontSize: 11, color: AppTheme.primaryColor),
                    ),
                  ),
                ],
              ),

              // Media Thumbnails
              if (mediaAssets.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 4,
                  children: mediaAssets.map((media) {
                    return Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Icon(Icons.image, size: 20),
                    );
                  }).toList(),
                ),
              ],

              // Error Message
              if (draft['last_error'] != null) ...[
                const SizedBox(height: 8),
                Text(
                  'Hata: ${draft['last_error']}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.errorColor,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Bottom sheet for editing a draft
class _EditDraftSheet extends StatefulWidget {
  final String currentText;
  final String? scheduledFor;

  const _EditDraftSheet({
    required this.currentText,
    this.scheduledFor,
  });

  @override
  State<_EditDraftSheet> createState() => _EditDraftSheetState();
}

class _EditDraftSheetState extends State<_EditDraftSheet> {
  late TextEditingController _textController;
  DateTime? _scheduledFor;

  /// Parse UTC datetime string from backend and convert to local time
  DateTime? _parseUtcToLocal(String? dateTimeStr) {
    if (dateTimeStr == null) return null;
    final parsed = DateTime.tryParse(dateTimeStr);
    if (parsed == null) return null;
    // Backend sends naive UTC datetime, so we need to treat it as UTC and convert to local
    return DateTime.utc(
      parsed.year, parsed.month, parsed.day,
      parsed.hour, parsed.minute, parsed.second, parsed.millisecond,
    ).toLocal();
  }

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController(text: widget.currentText);
    if (widget.scheduledFor != null) {
      _scheduledFor = _parseUtcToLocal(widget.scheduledFor);
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _pickDateTime() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _scheduledFor ?? DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );

    if (date == null || !mounted) return;

    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_scheduledFor ?? DateTime.now()),
    );

    if (time == null || !mounted) return;

    setState(() {
      _scheduledFor = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.textMuted.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Title
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    l10n.editTweet,
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: _textController.text.length > 280
                          ? AppTheme.errorColor.withOpacity(0.1)
                          : AppTheme.successColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '${_textController.text.length}/280',
                      style: TextStyle(
                        color: _textController.text.length > 280
                            ? AppTheme.errorColor
                            : AppTheme.successColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Text field
              TextField(
                controller: _textController,
                maxLines: 5,
                maxLength: 280,
                decoration: InputDecoration(
                  hintText: l10n.tweetContent,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 16),

              // Schedule picker
              InkWell(
                onTap: _pickDateTime,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.schedule, color: AppTheme.primaryColor),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _scheduledFor != null
                              ? '${_scheduledFor!.day}/${_scheduledFor!.month}/${_scheduledFor!.year} ${_scheduledFor!.hour.toString().padLeft(2, '0')}:${_scheduledFor!.minute.toString().padLeft(2, '0')}'
                              : l10n.selectSchedule,
                          style: TextStyle(
                            color: _scheduledFor != null ? null : AppTheme.textMuted,
                          ),
                        ),
                      ),
                      if (_scheduledFor != null)
                        IconButton(
                          icon: const Icon(Icons.clear, size: 20),
                          onPressed: () => setState(() => _scheduledFor = null),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: Text(l10n.cancel),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    flex: 2,
                    child: ElevatedButton(
                      onPressed: _textController.text.length > 280
                          ? null
                          : () {
                              Navigator.pop(context, {
                                'text': _textController.text,
                                'scheduled_for': _scheduledFor,
                                'status': _scheduledFor != null ? 'pending' : 'draft',
                              });
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryColor,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: Text(
                        l10n.save,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
