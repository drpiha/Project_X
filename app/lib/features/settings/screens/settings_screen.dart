import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:campaign_app/l10n/app_localizations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../providers/providers.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final userState = ref.watch(userProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.settings),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/campaigns'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(userProvider.notifier).fetchSettings(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Language settings
          _SectionTitle(title: l10n.languageSettings),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                _LanguageOption(
                  title: l10n.autoLanguage,
                  value: null,
                  groupValue: userState.locale,
                  onChanged: (value) => _updateLanguage(value),
                ),
                const Divider(height: 1),
                _LanguageOption(
                  title: l10n.turkish,
                  subtitle: 'Türkçe',
                  value: 'tr',
                  groupValue: userState.locale,
                  onChanged: (value) => _updateLanguage(value),
                ),
                const Divider(height: 1),
                _LanguageOption(
                  title: l10n.english,
                  subtitle: 'English',
                  value: 'en',
                  groupValue: userState.locale,
                  onChanged: (value) => _updateLanguage(value),
                ),
                const Divider(height: 1),
                _LanguageOption(
                  title: l10n.german,
                  subtitle: 'Deutsch',
                  value: 'de',
                  groupValue: userState.locale,
                  onChanged: (value) => _updateLanguage(value),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Auto post settings
          _SectionTitle(title: l10n.autoPost),
          const SizedBox(height: 8),
          Card(
            child: SwitchListTile(
              title: Text(l10n.autoPost),
              subtitle: Text(
                l10n.autoPostDescription,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              value: userState.autoPostEnabled,
              onChanged: _isLoading ? null : (value) => _updateAutoPost(value),
              activeColor: AppTheme.primaryColor,
            ),
          ),
          const SizedBox(height: 24),

          // Daily limit
          _SectionTitle(title: l10n.dailyLimit),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.dailyLimitDescription,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: Slider(
                          value: userState.dailyLimit.toDouble(),
                          min: 1,
                          max: 50,
                          divisions: 49,
                          label: userState.dailyLimit.toString(),
                          activeColor: AppTheme.primaryColor,
                          onChanged: _isLoading
                              ? null
                              : (value) {
                                  ref.read(userProvider.notifier).updateSettings(
                                        dailyLimit: value.toInt(),
                                      );
                                },
                        ),
                      ),
                      Container(
                        width: 50,
                        alignment: Alignment.center,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${userState.dailyLimit}',
                          style: const TextStyle(
                            color: AppTheme.primaryColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // X Connection status
          _SectionTitle(title: 'X Connection'),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: userState.isConnectedToX
                      ? AppTheme.successColor.withOpacity(0.1)
                      : AppTheme.warningColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  userState.isConnectedToX
                      ? Icons.check_circle
                      : Icons.warning,
                  color: userState.isConnectedToX
                      ? AppTheme.successColor
                      : AppTheme.warningColor,
                ),
              ),
              title: Text(
                userState.isConnectedToX
                    ? 'Connected as @${userState.xUsername ?? 'Unknown'}'
                    : 'Not connected',
              ),
              subtitle: Text(
                userState.isConnectedToX
                    ? 'Your X account is linked for posting'
                    : 'Connect to post directly to X',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              trailing: userState.isConnectedToX
                  ? null
                  : TextButton(
                      onPressed: _isLoading 
                          ? null 
                          : () async {
                              setState(() => _isLoading = true);
                              try {
                                await ref.read(userProvider.notifier).connectX();
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
                                  setState(() => _isLoading = false);
                                }
                              }
                            },
                      child: _isLoading 
                          ? const SizedBox(
                              width: 20, 
                              height: 20, 
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Connect'),
                    ),
            ),
          ),
          const SizedBox(height: 32),

          // App info
          Center(
            child: Column(
              children: [
                Text(
                  'Campaign Manager',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                Text(
                  'Version 1.0.0',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppTheme.textMuted,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _updateLanguage(String? locale) async {
    setState(() => _isLoading = true);
    try {
      await ref.read(userProvider.notifier).updateSettings(locale: locale ?? '');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _updateAutoPost(bool value) async {
    setState(() => _isLoading = true);
    try {
      await ref.read(userProvider.notifier).updateSettings(autoPostEnabled: value);
    } finally {
      setState(() => _isLoading = false);
    }
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: AppTheme.textSecondary,
              fontWeight: FontWeight.w600,
            ),
      ),
    );
  }
}

class _LanguageOption extends StatelessWidget {
  final String title;
  final String? subtitle;
  final String? value;
  final String? groupValue;
  final ValueChanged<String?> onChanged;

  const _LanguageOption({
    required this.title,
    this.subtitle,
    required this.value,
    required this.groupValue,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return RadioListTile<String?>(
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle!) : null,
      value: value,
      groupValue: groupValue,
      onChanged: onChanged,
      activeColor: AppTheme.primaryColor,
    );
  }
}
