import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:campaign_app/l10n/app_localizations.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/campaign_provider.dart';

class CreateCampaignScreen extends ConsumerStatefulWidget {
  const CreateCampaignScreen({super.key});

  @override
  ConsumerState<CreateCampaignScreen> createState() => _CreateCampaignScreenState();
}

class _CreateCampaignScreenState extends ConsumerState<CreateCampaignScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _hashtagController = TextEditingController();
  final _ctaController = TextEditingController();

  String _selectedLanguage = 'tr';
  String _selectedTone = 'informative';
  final List<String> _hashtags = [];
  final List<XFile> _images = [];
  XFile? _video;

  final List<String> _scheduleTimes = ['09:00', '18:00'];
  int _variantCount = 3;

  bool _isLoading = false;
  bool _isGenerating = false;

  final ImagePicker _picker = ImagePicker();

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _hashtagController.dispose();
    _ctaController.dispose();
    super.dispose();
  }

  Future<void> _pickImages() async {
    if (_images.length >= 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Maximum 10 images allowed')),
      );
      return;
    }

    final List<XFile> picked = await _picker.pickMultiImage();
    if (picked.isNotEmpty) {
      setState(() {
        final remaining = 10 - _images.length;
        _images.addAll(
          picked.take(remaining),
        );
      });
    }
  }

  Future<void> _pickVideo() async {
    final XFile? picked = await _picker.pickVideo(source: ImageSource.gallery);
    if (picked != null) {
      setState(() {
        _video = picked;
      });
    }
  }

  void _addHashtag() {
    var tag = _hashtagController.text.trim();
    if (tag.isEmpty) return;

    // if (!tag.startsWith('#')) {
    //   tag = '#$tag';
    // }

    tag = tag.replaceAll(' ', '');

    if (!_hashtags.contains(tag)) {
      setState(() {
        _hashtags.add(tag);
        _hashtagController.clear();
      });
    }
  }

  void _removeHashtag(String tag) {
    setState(() {
      _hashtags.remove(tag);
    });
  }

  void _addScheduleTime() {
    showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    ).then((time) {
      if (time != null) {
        final timeStr =
            '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
        if (!_scheduleTimes.contains(timeStr)) {
          setState(() {
            _scheduleTimes.add(timeStr);
            _scheduleTimes.sort();
          });
        }
      }
    });
  }

  Future<void> _createAndGenerate() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      // Create campaign
      final campaign = await ref.read(campaignsProvider.notifier).createCampaign(
        title: _titleController.text,
        description: _descriptionController.text,
        language: _selectedLanguage,
        hashtags: _hashtags,
        tone: _selectedTone,
        callToAction: _ctaController.text,
        images: _images.isNotEmpty ? _images : null,
        video: _video,
      );

      if (campaign == null) {
        throw Exception('Failed to create campaign');
      }

      setState(() {
        _isLoading = false;
        _isGenerating = true;
      });

      // Generate drafts
      final response = await ref.read(campaignsProvider.notifier).generateDrafts(
        campaignId: campaign.id,
        language: _selectedLanguage,
        topicSummary: _descriptionController.text.isNotEmpty
            ? _descriptionController.text
            : _titleController.text,
        hashtags: _hashtags,
        tone: _selectedTone,
        callToAction: _ctaController.text,

        imageCount: _images.length,
        variantCount: _variantCount,
      );

      if (mounted) {
        context.go('/campaigns/${campaign.id}/drafts');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isGenerating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.createCampaign),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Title
            TextFormField(
              controller: _titleController,
              decoration: InputDecoration(
                labelText: l10n.campaignTitle,
                prefixIcon: const Icon(Icons.title),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return l10n.required;
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Description
            TextFormField(
              controller: _descriptionController,
              decoration: InputDecoration(
                labelText: l10n.campaignDescription,
                hintText: l10n.campaignDescriptionHint,
                prefixIcon: const Icon(Icons.description),
                alignLabelWithHint: true,
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),

            // Language selector
            DropdownButtonFormField<String>(
              value: _selectedLanguage,
              decoration: InputDecoration(
                labelText: l10n.language,
                prefixIcon: const Icon(Icons.language),
              ),
              items: const [
                DropdownMenuItem(value: 'tr', child: Text('Türkçe')),
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: 'de', child: Text('Deutsch')),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() => _selectedLanguage = value);
                }
              },
            ),
            const SizedBox(height: 16),

            // Tone selector
            DropdownButtonFormField<String>(
              value: _selectedTone,
              decoration: InputDecoration(
                labelText: l10n.tone,
                prefixIcon: const Icon(Icons.mood),
              ),
              items: [
                DropdownMenuItem(value: 'informative', child: Text(l10n.toneInformative)),
                DropdownMenuItem(value: 'emotional', child: Text(l10n.toneEmotional)),
                DropdownMenuItem(value: 'formal', child: Text(l10n.toneFormal)),
                DropdownMenuItem(value: 'hopeful', child: Text(l10n.toneHopeful)),
                DropdownMenuItem(value: 'call_to_action', child: Text(l10n.toneCallToAction)),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() => _selectedTone = value);
                }
              },
            ),
            const SizedBox(height: 24),

            // Hashtags section
            Text(
              l10n.hashtags,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _hashtagController,
                    decoration: InputDecoration(
                      hintText: l10n.hashtagHint,
                      prefixIcon: const Icon(Icons.tag),
                    ),
                    onFieldSubmitted: (_) => _addHashtag(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _addHashtag,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            if (_hashtags.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _hashtags.map((tag) {
                  return Chip(
                    label: Text(tag),
                    deleteIcon: const Icon(Icons.close, size: 18),
                    onDeleted: () => _removeHashtag(tag),
                    backgroundColor: AppTheme.primaryColor.withOpacity(0.1),
                    labelStyle: const TextStyle(color: AppTheme.primaryColor),
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: 24),

            // Call to action
            TextFormField(
              controller: _ctaController,
              decoration: InputDecoration(
                labelText: l10n.callToAction,
                hintText: l10n.callToActionHint,
                prefixIcon: const Icon(Icons.flash_on),
              ),
              maxLength: 80,
            ),
            const SizedBox(height: 24),

            // Images section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  l10n.images,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Text(
                  '${_images.length}/10',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_images.isEmpty)
              OutlinedButton.icon(
                onPressed: _pickImages,
                icon: const Icon(Icons.add_photo_alternate),
                label: Text(l10n.addImages),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                ),
              )
            else
              Column(
                children: [
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 8,
                    ),
                    itemCount: _images.length + (_images.length < 10 ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _images.length) {
                        return InkWell(
                          onTap: _pickImages,
                          child: Container(
                            decoration: BoxDecoration(
                              border: Border.all(color: AppTheme.cardColor),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Icon(
                              Icons.add,
                              color: AppTheme.textMuted,
                            ),
                          ),
                        );
                      }
                      return Stack(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: kIsWeb
                                ? Image.network(
                                    _images[index].path,
                                    fit: BoxFit.cover,
                                    width: double.infinity,
                                    height: double.infinity,
                                  )
                                : Image.file(
                                    File(_images[index].path),
                                    fit: BoxFit.cover,
                                    width: double.infinity,
                                    height: double.infinity,
                                  ),
                          ),
                          Positioned(
                            top: 4,
                            right: 4,
                            child: GestureDetector(
                              onTap: () {
                                setState(() {
                                  _images.removeAt(index);
                                });
                              },
                              child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: const BoxDecoration(
                                  color: Colors.black54,
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(
                                  Icons.close,
                                  size: 16,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ],
              ),
            const SizedBox(height: 24),

            // Video section
            Text(
              l10n.video,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (_video == null)
              OutlinedButton.icon(
                onPressed: _pickVideo,
                icon: const Icon(Icons.videocam),
                label: Text('${l10n.addVideo} (${l10n.optionalVideo})'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                ),
              )
            else
              ListTile(
                leading: const Icon(Icons.videocam),
                title: Text(_video!.path.split('/').last),
                trailing: IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () {
                    setState(() => _video = null);
                  },
                ),
                tileColor: AppTheme.surfaceColor,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            const SizedBox(height: 24),

            // Schedule times
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  l10n.schedule,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                TextButton.icon(
                  onPressed: _addScheduleTime,
                  icon: const Icon(Icons.add, size: 18),
                  label: Text(l10n.addTime),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _scheduleTimes.map((time) {
                return Chip(
                  avatar: const Icon(Icons.schedule, size: 18),
                  label: Text(time),
                  deleteIcon: const Icon(Icons.close, size: 18),
                  onDeleted: () {
                    setState(() {
                      _scheduleTimes.remove(time);
                    });
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Variant count
            Text(
              'Variant Count: $_variantCount',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Slider(
              value: _variantCount.toDouble(),
              min: 1,
              max: 6,
              divisions: 5,
              label: '$_variantCount',
              onChanged: (value) {
                setState(() {
                  _variantCount = value.toInt();
                });
              },
            ),
            const SizedBox(height: 16),
            const SizedBox(height: 40),

            // Generate button
            Container(
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
                onPressed: (_isLoading || _isGenerating) ? null : _createAndGenerate,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  shadowColor: Colors.transparent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: _isLoading || _isGenerating
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            _isGenerating ? 'Oluşturuluyor...' : l10n.loading,
                            style: const TextStyle(fontSize: 18),
                          ),
                        ],
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.auto_awesome, size: 24),
                          const SizedBox(width: 8),
                          Text(
                            l10n.generateDrafts,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
