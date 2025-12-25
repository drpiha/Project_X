import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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

  Future<void> _scheduleDraft(Draft draft) async {
    final TimeOfDay? time = await showTimePicker(
      context: context, 
      initialTime: TimeOfDay.now()
    );
    
    if (time == null) return;

    final timeStr = '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
    final DateTime now = DateTime.now();
    // If time is past, schedule for tomorrow? Or today if user picked it?
    // Let's assume today for now, backend handles date/start_date.
    
    setState(() => _isScheduling = true);
    
    try {
       await ref.read(campaignsProvider.notifier).scheduleCampaign(
        campaignId: widget.campaignId,
        timezone: 'Europe/Istanbul', 
        times: [timeStr],
        recurrence: 'once',
        startDate: now,
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
    setState(() => _isScheduling = true);

    try {
      await ref.read(campaignsProvider.notifier).scheduleCampaign(
        campaignId: widget.campaignId,
        timezone: 'Europe/Istanbul',
        times: ['09:00', '18:00'],
        startDate: DateTime.now(),
        autoPost: false,
        selectedVariantIndex: _selectedIndex,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Campaign scheduled successfully!'),
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
  final AppLocalizations l10n;

  const _DraftCard({
    required this.draft,
    required this.isSelected,
    required this.onTap,
    required this.onCopy,
    required this.onSchedule,
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
