import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:campaign_app/l10n/app_localizations.dart';
import '../../../core/theme/app_theme.dart';
import '../../campaigns/providers/campaign_provider.dart';

class DraftReviewScreen extends ConsumerStatefulWidget {
  final String campaignId;

  const DraftReviewScreen({super.key, required this.campaignId});

  @override
  ConsumerState<DraftReviewScreen> createState() => _DraftReviewScreenState();
}

class _DraftReviewScreenState extends ConsumerState<DraftReviewScreen> {
  List<Draft> _drafts = [];
  bool _isLoading = true;
  String? _error;
  int _selectedIndex = 0;
  final TextEditingController _editController = TextEditingController();
  bool _isEditing = false;
  bool _isScheduling = false;
  int? _regeneratingIndex;

  @override
  void initState() {
    super.initState();
    _loadDrafts();
  }

  @override
  void dispose() {
    _editController.dispose();
    super.dispose();
  }

  Future<void> _loadDrafts() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final drafts = await ref
          .read(campaignsProvider.notifier)
          .getDrafts(widget.campaignId);
      
      setState(() {
        _drafts = drafts;
        _isLoading = false;
        if (drafts.isNotEmpty) {
          _editController.text = drafts[_selectedIndex].text;
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _selectVariant(int index) {
    setState(() {
      _selectedIndex = index;
      _editController.text = _drafts[index].text;
      _isEditing = false;
    });
  }

  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard'),
        duration: Duration(seconds: 1),
      ),
    );
  }

  Future<void> _regenerateDraft(int index) async {
    final draft = _drafts[index];
    setState(() => _regeneratingIndex = index);

    try {
      final result = await ref
          .read(campaignsProvider.notifier)
          .regenerateDraft(draft.id);

      if (mounted) {
        // Update the draft in the list
        setState(() {
          _drafts[index] = Draft(
            id: draft.id,
            campaignId: draft.campaignId,
            variantIndex: draft.variantIndex,
            text: result['text'] as String,
            charCount: result['char_count'] as int,
            hashtagsUsed: draft.hashtagsUsed,
            status: 'draft',
            createdAt: draft.createdAt,
          );
          if (index == _selectedIndex) {
            _editController.text = result['text'] as String;
          }
          _regeneratingIndex = null;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Tweet regenerated!'),
            backgroundColor: AppTheme.successColor,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _regeneratingIndex = null);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Future<void> _scheduleDraft(Draft draft) async {
    final TimeOfDay? time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now()
    );

    if (time == null) return;

    final DateTime now = DateTime.now();

    // Create the full datetime for scheduling
    DateTime scheduledDateTime = DateTime(
      now.year, now.month, now.day,
      time.hour, time.minute,
    );

    // If time is past, schedule from NOW + 1 minute (not tomorrow)
    if (scheduledDateTime.isBefore(now)) {
      scheduledDateTime = now.add(const Duration(minutes: 1));
    }

    setState(() => _isScheduling = true);

    try {
      // Get device's timezone
      final String deviceTimezone = await FlutterTimezone.getLocalTimezone();

      // DEBUG: Print timezone info
      debugPrint('=== SCHEDULING DEBUG ===');
      debugPrint('User selected time: ${time.hour}:${time.minute}');
      debugPrint('Device timezone: $deviceTimezone');
      debugPrint('Scheduled DateTime (local): $scheduledDateTime');
      debugPrint('Scheduled DateTime ISO: ${scheduledDateTime.toIso8601String()}');
      debugPrint('Scheduled DateTime UTC: ${scheduledDateTime.toUtc()}');
      debugPrint('=======================');

      // FIX: Send as UTC with 'Z' suffix to avoid timezone confusion
      // This ensures the exact time the user selected is preserved
      final scheduledUtc = scheduledDateTime.toUtc();
      final scheduledIsoString = scheduledUtc.toIso8601String();

      await ref.read(campaignsProvider.notifier).scheduleCampaign(
        campaignId: widget.campaignId,
        timezone: deviceTimezone,
        scheduledTimes: [scheduledIsoString],
        recurrence: 'once',
        startDate: scheduledDateTime,
        autoPost: true, // User wants automation
        selectedVariantIndex: draft.variantIndex,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
           const SnackBar(content: Text('Tweet Scheduled!'), backgroundColor: AppTheme.successColor)
        );
      }
    } catch (e) {
      if (mounted) {
         ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    } finally {
      if (mounted) setState(() => _isScheduling = false);
    }
  }

  Future<void> _scheduleCampaign() async {
    // Show simplified scheduling dialog
    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _ScheduleBottomSheet(
        draftCount: _drafts.length,
      ),
    );

    if (result == null) return;

    setState(() => _isScheduling = true);

    try {
      // Get device's timezone
      final String deviceTimezone = await FlutterTimezone.getLocalTimezone();

      // Calculate times based on start date, time, and random intervals
      final DateTime startDate = result['startDate'] as DateTime;
      final TimeOfDay startTime = result['startTime'] as TimeOfDay;
      final int tweetCount = result['tweetCount'] as int;
      final int imagesPerTweet = result['imagesPerTweet'] as int;
      final int intervalMinSeconds = result['intervalMinSeconds'] as int? ?? 120;
      final int intervalMaxSeconds = result['intervalMaxSeconds'] as int? ?? 300;

      // Create DateTime for the first tweet using selected date and time
      DateTime scheduledDateTime = DateTime(
        startDate.year,
        startDate.month,
        startDate.day,
        startTime.hour,
        startTime.minute,
      );

      // Handle past times - if selected time has passed, start immediately (add 1 minute buffer)
      final now = DateTime.now();
      if (scheduledDateTime.isBefore(now)) {
        // If it's today and time passed, start from NOW + 1 minute (not tomorrow!)
        if (startDate.day == now.day && startDate.month == now.month && startDate.year == now.year) {
          scheduledDateTime = now.add(const Duration(minutes: 1));
          debugPrint('Time already passed, scheduling from NOW + 1 minute: $scheduledDateTime');
        }
      }

      // Generate scheduled_times list with random intervals (user-configurable)
      // Each time is a full ISO datetime string in LOCAL time
      List<String> scheduledTimes = [];
      DateTime currentDateTime = scheduledDateTime;
      final random = Random();
      int lastIntervalSeconds = 0;
      final intervalRange = intervalMaxSeconds - intervalMinSeconds;

      for (int i = 0; i < tweetCount; i++) {
        // IMPORTANT: Convert to UTC before sending to avoid timezone confusion
        // This ensures the exact time user selected is preserved regardless of device timezone
        final utcDateTime = currentDateTime.toUtc();
        scheduledTimes.add(utcDateTime.toIso8601String());

        // Generate random interval in seconds that's different from last one
        int intervalSeconds;
        if (intervalRange > 0) {
          do {
            intervalSeconds = intervalMinSeconds + random.nextInt(intervalRange + 1);
          } while (intervalSeconds == lastIntervalSeconds && tweetCount > 1 && intervalRange > 30);
        } else {
          intervalSeconds = intervalMinSeconds;
        }
        lastIntervalSeconds = intervalSeconds;

        currentDateTime = currentDateTime.add(Duration(seconds: intervalSeconds));
      }

      // Send the scheduled times as full ISO datetimes
      await ref.read(campaignsProvider.notifier).scheduleCampaign(
        campaignId: widget.campaignId,
        timezone: deviceTimezone,
        scheduledTimes: scheduledTimes,
        startDate: scheduledDateTime,
        autoPost: true,
        dailyLimit: tweetCount,
        selectedVariantIndex: _selectedIndex,
        imagesPerTweet: imagesPerTweet,
        postIntervalMin: intervalMinSeconds,
        postIntervalMax: intervalMaxSeconds,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$tweetCount tweet scheduled starting at ${startTime.format(context)}!'),
            backgroundColor: AppTheme.successColor,
          ),
        );
        context.go('/campaigns');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isScheduling = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.draftReview),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: _buildBody(context, l10n),
      bottomNavigationBar: _drafts.isNotEmpty
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Container(
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: AppTheme.primaryGradient,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryColor.withOpacity(0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: ElevatedButton(
                    onPressed: _isScheduling ? null : _scheduleCampaign,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    child: _isScheduling
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.schedule, size: 24),
                              const SizedBox(width: 8),
                              Text(
                                l10n.scheduleCampaign,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
              ),
            )
          : null,
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
              onPressed: _loadDrafts,
              child: Text(l10n.retry),
            ),
          ],
        ),
      );
    }

    if (_drafts.isEmpty) {
      return Center(
        child: Text(l10n.noCampaigns),
      );
    }

    return Column(
      children: [
        // Selection info
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          color: AppTheme.surfaceColor,
          child: Text(
            l10n.selectVariant,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: AppTheme.textSecondary,
                ),
          ),
        ),

        // Variants list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _drafts.length,
            itemBuilder: (context, index) {
              final draft = _drafts[index];
              final isSelected = index == _selectedIndex;

              return _DraftCard(
                draft: draft,
                isSelected: isSelected,
                onTap: () => _selectVariant(index),
                onCopy: () => _copyToClipboard(draft.text),
                onSchedule: () => _scheduleDraft(draft),
                onRegenerate: () => _regenerateDraft(index),
                isRegenerating: _regeneratingIndex == index,
                l10n: l10n,
              );
            },
          ),
        ),

        // Edit section (when selected)
        if (_isEditing || true) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceColor,
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${l10n.edit} #${_selectedIndex + 1}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    _CharCountBadge(
                      count: _editController.text.length,
                      maxCount: 280,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _editController,
                  maxLines: 3,
                  maxLength: 280,
                  decoration: InputDecoration(
                    hintText: 'Edit tweet text...',
                    counterText: '',
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.copy),
                      onPressed: () => _copyToClipboard(_editController.text),
                    ),
                  ),
                  onChanged: (value) {
                    setState(() {});
                  },
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _DraftCard extends StatelessWidget {
  final Draft draft;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback onCopy;
  final VoidCallback onSchedule;
  final VoidCallback onRegenerate;
  final bool isRegenerating;
  final AppLocalizations l10n;

  const _DraftCard({
    required this.draft,
    required this.isSelected,
    required this.onTap,
    required this.onCopy,
    required this.onSchedule,
    required this.onRegenerate,
    this.isRegenerating = false,
    required this.l10n,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: isSelected ? AppTheme.primaryColor : Colors.transparent,
          width: 2,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppTheme.primaryColor
                          : AppTheme.cardColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Text(
                        '${draft.variantIndex + 1}',
                        style: TextStyle(
                          color: isSelected
                              ? Colors.white
                              : AppTheme.textSecondary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const Spacer(),
                  _CharCountBadge(
                    count: draft.charCount,
                    maxCount: 280,
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.copy, size: 20),
                    onPressed: onCopy,
                    color: AppTheme.textMuted,
                    tooltip: l10n.copy,
                  ),
                  isRegenerating
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : IconButton(
                          icon: const Icon(Icons.refresh, size: 20),
                          onPressed: onRegenerate,
                          color: AppTheme.accentColor,
                          tooltip: 'Regenerate',
                        ),
                  IconButton(
                    icon: const Icon(Icons.calendar_today, size: 20),
                    onPressed: onSchedule,
                    color: AppTheme.primaryColor,
                    tooltip: 'Schedule This',
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                draft.text,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (draft.hashtagsUsed.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: draft.hashtagsUsed.map((tag) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.accentColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        tag,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppTheme.accentColor,
                            ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _CharCountBadge extends StatelessWidget {
  final int count;
  final int maxCount;

  const _CharCountBadge({
    required this.count,
    required this.maxCount,
  });

  @override
  Widget build(BuildContext context) {
    final isNearLimit = count > maxCount * 0.9;
    final isOverLimit = count > maxCount;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isOverLimit
            ? AppTheme.errorColor.withOpacity(0.1)
            : isNearLimit
                ? AppTheme.warningColor.withOpacity(0.1)
                : AppTheme.successColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        '$count/$maxCount',
        style: TextStyle(
          color: isOverLimit
              ? AppTheme.errorColor
              : isNearLimit
                  ? AppTheme.warningColor
                  : AppTheme.successColor,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }
}

/// Simplified scheduling bottom sheet
class _ScheduleBottomSheet extends StatefulWidget {
  final int draftCount;

  const _ScheduleBottomSheet({required this.draftCount});

  @override
  State<_ScheduleBottomSheet> createState() => _ScheduleBottomSheetState();
}

class _ScheduleBottomSheetState extends State<_ScheduleBottomSheet> {
  late DateTime _startDate;
  TimeOfDay _startTime = TimeOfDay.now();
  int _tweetCount = 5;
  int _imagesPerTweet = 1;

  // Random interval in seconds for natural posting (default 2-5 minutes)
  int _intervalMinSeconds = 120; // 2 minutes
  int _intervalMaxSeconds = 300; // 5 minutes
  bool _showAdvancedInterval = false;

  @override
  void initState() {
    super.initState();
    _startDate = DateTime.now();
    // Set initial time to current time (immediate scheduling)
    final now = DateTime.now();
    _startTime = TimeOfDay(hour: now.hour, minute: now.minute);
    // Default tweet count to available drafts or 5
    _tweetCount = widget.draftCount > 0 ? widget.draftCount.clamp(1, 10) : 5;
  }

  String _formatDate(DateTime date) {
    return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')}.${date.year}';
  }

  String _formatEstimatedEndTime() {
    // Use average interval for estimated end time
    double avgIntervalSeconds = (_intervalMinSeconds + _intervalMaxSeconds) / 2;
    int estimatedSeconds = (avgIntervalSeconds * (_tweetCount - 1)).round();
    int startMinutes = _startTime.hour * 60 + _startTime.minute;
    int endMinutes = startMinutes + (estimatedSeconds ~/ 60);
    int endHour = (endMinutes ~/ 60) % 24;
    int endMinute = endMinutes % 60;
    return '${endHour.toString().padLeft(2, '0')}:${endMinute.toString().padLeft(2, '0')}';
  }

  String _formatInterval(int seconds) {
    if (seconds >= 60) {
      int minutes = seconds ~/ 60;
      int remainingSeconds = seconds % 60;
      if (remainingSeconds == 0) {
        return '$minutes dk';
      }
      return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
    }
    return '$seconds sn';
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
              // Handle bar
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
              Text(
                l10n.scheduleCampaign,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 24),

              // Start Date
              _buildOptionRow(
                context,
                icon: Icons.calendar_today,
                label: l10n.startDate,
                child: InkWell(
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: _startDate,
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                    );
                    if (date != null) {
                      setState(() => _startDate = date);
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primaryColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      _formatDate(_startDate),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.primaryColor,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Start Time
              _buildOptionRow(
                context,
                icon: Icons.access_time,
                label: l10n.startTime,
                child: InkWell(
                  onTap: () async {
                    final time = await showTimePicker(
                      context: context,
                      initialTime: _startTime,
                    );
                    if (time != null) {
                      setState(() => _startTime = time);
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primaryColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      _startTime.format(context),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.primaryColor,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Interval Info (configurable)
              _buildOptionRow(
                context,
                icon: Icons.timer,
                label: l10n.interval,
                child: InkWell(
                  onTap: () => setState(() => _showAdvancedInterval = !_showAdvancedInterval),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: _showAdvancedInterval
                          ? AppTheme.primaryColor.withOpacity(0.1)
                          : AppTheme.surfaceColor,
                      borderRadius: BorderRadius.circular(12),
                      border: _showAdvancedInterval
                          ? Border.all(color: AppTheme.primaryColor.withOpacity(0.3))
                          : null,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${_formatInterval(_intervalMinSeconds)}-${_formatInterval(_intervalMaxSeconds)}',
                          style: TextStyle(
                            fontSize: 14,
                            color: _showAdvancedInterval
                                ? AppTheme.primaryColor
                                : AppTheme.textSecondary,
                            fontWeight: _showAdvancedInterval ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          _showAdvancedInterval ? Icons.expand_less : Icons.expand_more,
                          size: 16,
                          color: _showAdvancedInterval
                              ? AppTheme.primaryColor
                              : AppTheme.textMuted,
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              // Advanced interval settings (expandable)
              if (_showAdvancedInterval) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Min interval slider
                      Row(
                        children: [
                          SizedBox(
                            width: 80,
                            child: Text(
                              l10n.intervalMin,
                              style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                            ),
                          ),
                          Expanded(
                            child: Slider(
                              value: _intervalMinSeconds.toDouble(),
                              min: 30,
                              max: 600,
                              divisions: 19,
                              label: _formatInterval(_intervalMinSeconds),
                              onChanged: (value) {
                                setState(() {
                                  _intervalMinSeconds = value.round();
                                  // Ensure max is always >= min
                                  if (_intervalMaxSeconds < _intervalMinSeconds) {
                                    _intervalMaxSeconds = _intervalMinSeconds;
                                  }
                                });
                              },
                            ),
                          ),
                          SizedBox(
                            width: 50,
                            child: Text(
                              _formatInterval(_intervalMinSeconds),
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                              textAlign: TextAlign.right,
                            ),
                          ),
                        ],
                      ),
                      // Max interval slider
                      Row(
                        children: [
                          SizedBox(
                            width: 80,
                            child: Text(
                              l10n.intervalMax,
                              style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                            ),
                          ),
                          Expanded(
                            child: Slider(
                              value: _intervalMaxSeconds.toDouble(),
                              min: 60,
                              max: 900,
                              divisions: 28,
                              label: _formatInterval(_intervalMaxSeconds),
                              onChanged: (value) {
                                setState(() {
                                  _intervalMaxSeconds = value.round();
                                  // Ensure min is always <= max
                                  if (_intervalMinSeconds > _intervalMaxSeconds) {
                                    _intervalMinSeconds = _intervalMaxSeconds;
                                  }
                                });
                              },
                            ),
                          ),
                          SizedBox(
                            width: 50,
                            child: Text(
                              _formatInterval(_intervalMaxSeconds),
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                              textAlign: TextAlign.right,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),

              // Tweet Count
              _buildOptionRow(
                context,
                icon: Icons.format_list_numbered,
                label: l10n.tweetCount,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      onPressed: _tweetCount > 1
                          ? () => setState(() => _tweetCount--)
                          : null,
                      icon: const Icon(Icons.remove_circle_outline),
                      color: AppTheme.primaryColor,
                      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      padding: EdgeInsets.zero,
                    ),
                    Container(
                      width: 40,
                      alignment: Alignment.center,
                      child: Text(
                        '$_tweetCount',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: _tweetCount < 20
                          ? () => setState(() => _tweetCount++)
                          : null,
                      icon: const Icon(Icons.add_circle_outline),
                      color: AppTheme.primaryColor,
                      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      padding: EdgeInsets.zero,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Images per tweet
              _buildOptionRow(
                context,
                icon: Icons.image,
                label: l10n.imagesPerTweet,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (int i = 0; i <= 4; i++)
                      Padding(
                        padding: EdgeInsets.only(right: i < 4 ? 4 : 0),
                        child: ChoiceChip(
                          label: Text(i == 0 ? '-' : '$i'),
                          selected: _imagesPerTweet == i,
                          onSelected: (selected) {
                            if (selected) {
                              setState(() => _imagesPerTweet = i);
                            }
                          },
                          selectedColor: AppTheme.primaryColor,
                          labelStyle: TextStyle(
                            color: _imagesPerTweet == i ? Colors.white : null,
                          ),
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Summary
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: AppTheme.textMuted),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '$_tweetCount tweet, ${_startTime.format(context)} - ~${_formatEstimatedEndTime()}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: AppTheme.textSecondary,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Schedule Button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(context, {
                      'startDate': _startDate,
                      'startTime': _startTime,
                      'tweetCount': _tweetCount,
                      'imagesPerTweet': _imagesPerTweet,
                      'intervalMinSeconds': _intervalMinSeconds,
                      'intervalMaxSeconds': _intervalMaxSeconds,
                    });
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.schedule, color: Colors.white),
                      const SizedBox(width: 8),
                      Text(
                        l10n.schedule,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOptionRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Widget child,
  }) {
    return Row(
      children: [
        Icon(icon, color: AppTheme.textMuted, size: 24),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
        child,
      ],
    );
  }
}
