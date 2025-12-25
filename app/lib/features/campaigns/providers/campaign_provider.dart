import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'package:campaign_app/core/api/api_client.dart';
import 'package:campaign_app/core/config/app_config.dart';
import 'dart:io';

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
    return Campaign(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      language: json['language'] as String? ?? 'tr',
      hashtags: (json['hashtags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ?? [],
      tone: json['tone'] as String?,
      callToAction: json['call_to_action'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      mediaAssets: (json['media_assets'] as List<dynamic>?)
              ?.map((e) => MediaAsset.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
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
              .toList() ?? [],
      status: json['status'] as String,
      lastError: json['last_error'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      postedAt: json['posted_at'] != null
          ? DateTime.parse(json['posted_at'] as String)
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
              .toList() ?? [],
      safetyNotes: (json['safety_notes'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ?? [],
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
      final data = response.data as Map<String, dynamic>;
      final campaignsList = (data['campaigns'] as List<dynamic>)
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
    XFile? video,
  }) async {
    try {
      final map = {
        'title': title,
        'language': language,
        'hashtags': hashtags.join(','),
      };

      if (description != null && description.isNotEmpty) {
        map['description'] = description;
      }
      
      if (tone != null && tone.isNotEmpty) {
        map['tone'] = tone;
      }
      
      if (callToAction != null && callToAction.isNotEmpty) {
        map['call_to_action'] = callToAction;
      }

      final formData = FormData.fromMap(map);

      if (images != null) {
        for (final image in images) {
          final file = kIsWeb
              ? MultipartFile.fromBytes(await image.readAsBytes(), filename: image.name)
              : await MultipartFile.fromFile(image.path);
          
          formData.files.add(MapEntry('images', file));
        }
      }

      if (video != null) {
        final file = kIsWeb
            ? MultipartFile.fromBytes(await video.readAsBytes(), filename: video.name)
            : await MultipartFile.fromFile(video.path);

        formData.files.add(MapEntry('video', file));
      }

      final response = await _apiClient.postMultipart(
        AppConfig.campaigns,
        formData: formData,
      );

      final campaign = Campaign.fromJson(response.data as Map<String, dynamic>);
      
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
    required List<String> times,
    required DateTime startDate,
    DateTime? endDate,
    bool autoPost = false,
    String recurrence = 'daily',
    int dailyLimit = 10,
    int selectedVariantIndex = 0,
  }) async {
    try {
      await _apiClient.post(
        AppConfig.campaignSchedule(campaignId),
        data: {
          'timezone': timezone,
          'recurrence': recurrence,
          'times': times,
          'start_date': startDate.toIso8601String().split('T')[0],
          'end_date': endDate?.toIso8601String().split('T')[0],
          'auto_post': autoPost,
          'daily_limit': dailyLimit,
          'selected_variant_index': selectedVariantIndex,
        },
      );
    } catch (e) {
      rethrow;
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
