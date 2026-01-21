import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'package:campaign_app/core/api/api_client.dart';
import 'package:campaign_app/core/config/app_config.dart';

/// Parse UTC datetime string from backend and convert to local time.
/// Backend sends naive UTC datetimes without timezone info.
DateTime parseUtcToLocal(String dateTimeStr) {
  final parsed = DateTime.parse(dateTimeStr);
  // Backend sends naive UTC datetime, so treat it as UTC and convert to local
  return DateTime.utc(
    parsed.year, parsed.month, parsed.day,
    parsed.hour, parsed.minute, parsed.second, parsed.millisecond,
  ).toLocal();
}

// Campaign model
class Campaign {
  final String id;
  final String userId;
  final String title;
  final String? description;
  final String language;
  final List<String> hashtags;
  final String? tone;
  final String? callToAction;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<MediaAsset> mediaAssets;

  Campaign({
    required this.id,
    required this.userId,
    required this.title,
    this.description,
    required this.language,
    required this.hashtags,
    this.tone,
    this.callToAction,
    required this.createdAt,
    required this.updatedAt,
    this.mediaAssets = const [],
  });

  factory Campaign.fromJson(Map<String, dynamic> json) {
    // Parse hashtags - handle both array and JSON string formats
    List<String> parseHashtags(dynamic hashtagsData) {
      if (hashtagsData == null) return [];
      if (hashtagsData is List) {
        return hashtagsData.map((e) => e.toString()).toList();
      }
      if (hashtagsData is String) {
        if (hashtagsData.isEmpty || hashtagsData == '[]') return [];
        try {
          final parsed = List<dynamic>.from(
            hashtagsData.startsWith('[')
                ? (hashtagsData as String).substring(1, hashtagsData.length - 1).split(',').map((s) => s.trim().replaceAll('"', ''))
                : hashtagsData.split(',').map((s) => s.trim())
          );
          return parsed.where((e) => e.toString().isNotEmpty).map((e) => e.toString()).toList();
        } catch (e) {
          return [];
        }
      }
      return [];
    }

    return Campaign(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      language: json['language'] as String? ?? 'tr',
      hashtags: parseHashtags(json['hashtags']),
      tone: json['tone'] as String?,
      callToAction: json['call_to_action'] as String?,
      createdAt: parseUtcToLocal(json['created_at'] as String),
      updatedAt: parseUtcToLocal(json['updated_at'] as String? ?? json['created_at'] as String),
      mediaAssets: (json['media_assets'] as List<dynamic>?)
              ?.map((e) => MediaAsset.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class MediaAsset {
  final String id;
  final String type;
  final String path;
  final String originalName;
  final String? altText;

  MediaAsset({
    required this.id,
    required this.type,
    required this.path,
    required this.originalName,
    this.altText,
  });

  factory MediaAsset.fromJson(Map<String, dynamic> json) {
    return MediaAsset(
      id: json['id'] as String,
      type: json['type'] as String,
      path: json['path'] as String,
      originalName: json['original_name'] as String,
      altText: json['alt_text'] as String?,
    );
  }
}

// Draft model
class Draft {
  final String id;
  final String campaignId;
  final int variantIndex;
  final String text;
  final int charCount;
  final List<String> hashtagsUsed;
  final String status;
  final String? lastError;
  final DateTime createdAt;
  final DateTime? postedAt;

  Draft({
    required this.id,
    required this.campaignId,
    required this.variantIndex,
    required this.text,
    required this.charCount,
    required this.hashtagsUsed,
    required this.status,
    this.lastError,
    required this.createdAt,
    this.postedAt,
  });

  factory Draft.fromJson(Map<String, dynamic> json) {
    return Draft(
      id: json['id'] as String,
      campaignId: json['campaign_id'] as String,
      variantIndex: json['variant_index'] as int,
      text: json['text'] as String,
      charCount: json['char_count'] as int,
      hashtagsUsed: (json['hashtags_used'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      status: json['status'] as String,
      lastError: json['last_error'] as String?,
      createdAt: parseUtcToLocal(json['created_at'] as String),
      postedAt: json['posted_at'] != null
          ? parseUtcToLocal(json['posted_at'] as String)
          : null,
    );
  }
}

// Generate response
class GenerateResponse {
  final String campaignId;
  final String language;
  final List<Variant> variants;
  final int bestVariantIndex;
  final String recommendedAltText;
  final String generator;

  GenerateResponse({
    required this.campaignId,
    required this.language,
    required this.variants,
    required this.bestVariantIndex,
    required this.recommendedAltText,
    required this.generator,
  });

  factory GenerateResponse.fromJson(Map<String, dynamic> json) {
    return GenerateResponse(
      campaignId: json['campaign_id'] as String,
      language: json['language'] as String,
      variants: (json['variants'] as List<dynamic>)
          .map((e) => Variant.fromJson(e as Map<String, dynamic>))
          .toList(),
      bestVariantIndex: json['best_variant_index'] as int,
      recommendedAltText: json['recommended_alt_text'] as String,
      generator: json['generator'] as String,
    );
  }
}

class Variant {
  final int variantIndex;
  final String text;
  final int charCount;
  final List<String> hashtagsUsed;
  final List<String> safetyNotes;

  Variant({
    required this.variantIndex,
    required this.text,
    required this.charCount,
    required this.hashtagsUsed,
    required this.safetyNotes,
  });

  factory Variant.fromJson(Map<String, dynamic> json) {
    return Variant(
      variantIndex: json['variant_index'] as int,
      text: json['text'] as String,
      charCount: json['char_count'] as int,
      hashtagsUsed: (json['hashtags_used'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      safetyNotes: (json['safety_notes'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
    );
  }
}

// Campaign state
class CampaignsState {
  final List<Campaign> campaigns;
  final bool isLoading;
  final String? error;

  const CampaignsState({
    this.campaigns = const [],
    this.isLoading = false,
    this.error,
  });

  CampaignsState copyWith({
    List<Campaign>? campaigns,
    bool? isLoading,
    String? error,
  }) {
    return CampaignsState(
      campaigns: campaigns ?? this.campaigns,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class CampaignsNotifier extends StateNotifier<CampaignsState> {
  final ApiClient _apiClient;

  CampaignsNotifier(this._apiClient) : super(const CampaignsState());

  Future<void> fetchCampaigns() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.get(AppConfig.campaigns);
      // Backend returns {"campaigns": [...], "total": N}
      final responseData = response.data;
      final List<dynamic> data;
      if (responseData is List) {
        data = responseData;
      } else if (responseData is Map && responseData.containsKey('campaigns')) {
        data = responseData['campaigns'] as List<dynamic>;
      } else {
        data = [];
      }
      final campaignsList = data
          .map((e) => Campaign.fromJson(e as Map<String, dynamic>))
          .toList();

      state = state.copyWith(
        campaigns: campaignsList,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<Campaign?> createCampaign({
    required String title,
    String? description,
    required String language,
    required List<String> hashtags,
    String? tone,
    String? callToAction,
    List<XFile>? images,
    List<XFile>? videos,
  }) async {
    try {
      // Backend expects Form data (multipart/form-data), not JSON
      final formData = FormData.fromMap({
        'title': title,
        'language': language,
      });

      // Add hashtags as separate form fields (backend expects this format)
      for (final tag in hashtags) {
        formData.fields.add(MapEntry('hashtags', tag));
      }

      if (description != null && description.isNotEmpty) {
        formData.fields.add(MapEntry('description', description));
      }

      if (tone != null && tone.isNotEmpty) {
        formData.fields.add(MapEntry('tone', tone));
      }

      if (callToAction != null && callToAction.isNotEmpty) {
        formData.fields.add(MapEntry('call_to_action', callToAction));
      }

      // Send as Form data POST request
      final response = await _apiClient.post(
        AppConfig.campaigns,
        data: formData,
      );

      final campaign = Campaign.fromJson(response.data as Map<String, dynamic>);

      // Upload images if provided
      if (images != null && images.isNotEmpty) {
        for (final image in images) {
          await uploadMedia(campaign.id, image);
        }
      }

      // Upload videos if provided
      if (videos != null && videos.isNotEmpty) {
        for (final video in videos) {
          await uploadMedia(campaign.id, video);
        }
      }

      state = state.copyWith(
        campaigns: [campaign, ...state.campaigns],
      );

      return campaign;
    } catch (e) {
      rethrow;
    }
  }

  Future<GenerateResponse?> generateDrafts({
    required String campaignId,
    required String language,
    required String topicSummary,
    required List<String> hashtags,
    String tone = 'informative',
    String? callToAction,
    int imageCount = 0,
    int variantCount = 6,
  }) async {
    try {
      final response = await _apiClient.post(
        AppConfig.campaignGenerate(campaignId),
        data: {
          'campaign_id': campaignId,
          'language': language,
          'topic_summary': topicSummary,
          'hashtags': hashtags,
          'tone': tone,
          'call_to_action': callToAction ?? '',
          'constraints': {
            'max_chars': 280,
            'target_chars': 268,
            'include_emojis': true,
            'emoji_density': 'low',
          },
          'assets': {
            'image_count': imageCount,
            'video_present': false,
          },
          'output': {
            'variants': variantCount,
          },
        },
      );

      return GenerateResponse.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      rethrow;
    }
  }

  Future<List<Draft>> getDrafts(String campaignId) async {
    try {
      final response = await _apiClient.get(
        AppConfig.campaignDrafts(campaignId),
      );

      return (response.data as List<dynamic>)
          .map((e) => Draft.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> scheduleCampaign({
    required String campaignId,
    required String timezone,
    List<String>? times,
    List<String>? scheduledTimes, // Full ISO datetime strings (preferred)
    required DateTime startDate,
    DateTime? endDate,
    bool autoPost = false,
    String recurrence = 'daily',
    int dailyLimit = 10,
    int selectedVariantIndex = 0,
    int imagesPerTweet = 1,
    int postIntervalMin = 120, // 2 minutes default
    int postIntervalMax = 300, // 5 minutes default
  }) async {
    try {
      await _apiClient.post(
        AppConfig.campaignSchedule(campaignId),
        data: {
          'timezone': timezone,
          'recurrence': recurrence,
          'times': times ?? [],
          'scheduled_times': scheduledTimes ?? [], // Full ISO datetime strings
          'start_date': startDate.toIso8601String().split('T')[0],
          'end_date': endDate?.toIso8601String().split('T')[0],
          'auto_post': autoPost,
          'daily_limit': dailyLimit,
          'selected_variant_index': selectedVariantIndex,
          'images_per_tweet': imagesPerTweet,
          'post_interval_min': postIntervalMin,
          'post_interval_max': postIntervalMax,
        },
      );
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getCampaignDetail(String campaignId) async {
    try {
      final response = await _apiClient.get(
        '${AppConfig.campaignDetail(campaignId)}/detail',
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }

  /// Get a single campaign by ID
  Future<Campaign?> getCampaign(String campaignId) async {
    try {
      final response = await _apiClient.get(
        AppConfig.campaignDetail(campaignId),
      );
      return Campaign.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      rethrow;
    }
  }

  /// Update a campaign
  Future<Campaign?> updateCampaign({
    required String campaignId,
    String? title,
    String? description,
    String? language,
    List<String>? hashtags,
    String? tone,
    String? callToAction,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (title != null) data['title'] = title;
      if (description != null) data['description'] = description;
      if (language != null) data['language'] = language;
      if (hashtags != null) data['hashtags'] = hashtags;
      if (tone != null) data['tone'] = tone;
      if (callToAction != null) data['call_to_action'] = callToAction;

      final response = await _apiClient.put(
        AppConfig.campaignDetail(campaignId),
        data: data,
      );

      final updated = Campaign.fromJson(response.data as Map<String, dynamic>);

      // Update in local state
      state = state.copyWith(
        campaigns: state.campaigns.map((c) => c.id == campaignId ? updated : c).toList(),
      );

      return updated;
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> regenerateDraft(String draftId) async {
    try {
      final response = await _apiClient.post(
        '/v1/drafts/$draftId/regenerate',
        data: {},
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }

  /// Update draft text and/or schedule
  Future<Map<String, dynamic>> updateDraft({
    required String draftId,
    String? text,
    DateTime? scheduledFor,
    String? status,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (text != null) data['text'] = text;
      if (scheduledFor != null) data['scheduled_for'] = scheduledFor.toIso8601String();
      if (status != null) data['status'] = status;

      final response = await _apiClient.put(
        '/v1/drafts/$draftId',
        data: data,
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }

  /// Delete a draft
  Future<void> deleteDraft(String draftId) async {
    try {
      await _apiClient.delete('/v1/drafts/$draftId');
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> uploadMedia(String campaignId, XFile file) async {
    try {
      final bytes = await file.readAsBytes();
      final fileName = file.name;

      // Determine content type
      String contentType = 'application/octet-stream';
      if (fileName.toLowerCase().endsWith('.jpg') || fileName.toLowerCase().endsWith('.jpeg')) {
        contentType = 'image/jpeg';
      } else if (fileName.toLowerCase().endsWith('.png')) {
        contentType = 'image/png';
      } else if (fileName.toLowerCase().endsWith('.gif')) {
        contentType = 'image/gif';
      } else if (fileName.toLowerCase().endsWith('.mp4')) {
        contentType = 'video/mp4';
      } else if (fileName.toLowerCase().endsWith('.mov')) {
        contentType = 'video/quicktime';
      }

      final formData = FormData.fromMap({
        'campaign_id': campaignId,
        'file': MultipartFile.fromBytes(
          bytes,
          filename: fileName,
          contentType: DioMediaType.parse(contentType),
        ),
        'alt_text': '',
      });

      final response = await _apiClient.post(
        AppConfig.mediaUpload,
        data: formData,
      );

      return response.data as Map<String, dynamic>;
    } catch (e) {
      debugPrint('Media upload failed: $e');
      return null;
    }
  }
}

final campaignsProvider =
    StateNotifierProvider<CampaignsNotifier, CampaignsState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CampaignsNotifier(apiClient);
});

// Selected campaign for draft review
final selectedCampaignProvider = StateProvider<Campaign?>((ref) => null);
final selectedVariantProvider = StateProvider<int>((ref) => 0);
