import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import 'package:url_launcher/url_launcher.dart';

// User state
class UserState {
  final String? userId;
  final String? locale;
  final bool autoPostEnabled;
  final int dailyLimit;
  final bool isConnectedToX;
  final String? xUsername;
  final String? defaultTone;
  final String? defaultTweetLanguage;
  final int? defaultImagesPerTweet;

  const UserState({
    this.userId,
    this.locale,
    this.autoPostEnabled = false,
    this.dailyLimit = 10,
    this.isConnectedToX = false,
    this.xUsername,
    this.defaultTone,
    this.defaultTweetLanguage,
    this.defaultImagesPerTweet,
  });

  UserState copyWith({
    String? userId,
    String? locale,
    bool? autoPostEnabled,
    int? dailyLimit,
    bool? isConnectedToX,
    String? xUsername,
    String? defaultTone,
    String? defaultTweetLanguage,
    int? defaultImagesPerTweet,
  }) {
    return UserState(
      userId: userId ?? this.userId,
      locale: locale ?? this.locale,
      autoPostEnabled: autoPostEnabled ?? this.autoPostEnabled,
      dailyLimit: dailyLimit ?? this.dailyLimit,
      isConnectedToX: isConnectedToX ?? this.isConnectedToX,
      xUsername: xUsername ?? this.xUsername,
      defaultTone: defaultTone ?? this.defaultTone,
      defaultTweetLanguage: defaultTweetLanguage ?? this.defaultTweetLanguage,
      defaultImagesPerTweet: defaultImagesPerTweet ?? this.defaultImagesPerTweet,
    );
  }
}

class UserNotifier extends StateNotifier<UserState> {
  final ApiClient _apiClient;

  UserNotifier(this._apiClient) : super(const UserState());

  Future<void> createAnonymousUser(String? deviceLocale) async {
    try {
      final response = await _apiClient.post(
        AppConfig.authAnonymous,
        data: {'device_locale': deviceLocale ?? 'tr'},
      );
      
      final data = response.data as Map<String, dynamic>;
      // Backend returns 'id' not 'user_id'
      final userId = (data['id'] ?? data['user_id']) as String;

      _apiClient.setUserId(userId);
      
      state = state.copyWith(
        userId: userId,
        locale: data['ui_language_override'] as String?,
        autoPostEnabled: data['auto_post_enabled'] as bool? ?? false,
        dailyLimit: data['daily_post_limit'] as int? ?? 10,
        isConnectedToX: data['is_x_connected'] as bool? ?? false,
        xUsername: data['x_username'] as String?,
      );
      
      // Save to preferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('user_id', userId);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> loadSavedUser() async {
    final prefs = await SharedPreferences.getInstance();
    final savedUserId = prefs.getString('user_id');
    final savedLocale = prefs.getString('locale_override');
    
    if (savedUserId != null) {
      _apiClient.setUserId(savedUserId);
      state = state.copyWith(
        userId: savedUserId,
        locale: savedLocale,
      );
      
      // Refresh from server
      await fetchSettings();
    }
  }

  Future<void> fetchSettings() async {
    if (state.userId == null) return;

    try {
      final response = await _apiClient.get(AppConfig.settings);
      final data = response.data as Map<String, dynamic>;

      state = state.copyWith(
        locale: data['ui_language_override'] as String?,
        autoPostEnabled: data['auto_post_enabled'] as bool? ?? false,
        dailyLimit: data['daily_post_limit'] as int? ?? 10,
        isConnectedToX: data['is_x_connected'] as bool? ?? false,
        xUsername: data['x_username'] as String?,
        defaultTone: data['default_tone'] as String? ?? 'informative',
        defaultTweetLanguage: data['default_tweet_language'] as String? ?? 'tr',
        defaultImagesPerTweet: data['default_images_per_tweet'] as int? ?? 1,
      );
    } catch (e) {
      // Ignore errors
    }
  }

  Future<void> updateSettings({
    String? locale,
    bool? autoPostEnabled,
    int? dailyLimit,
    String? defaultTone,
    String? defaultTweetLanguage,
    int? defaultImagesPerTweet,
  }) async {
    // Update local state immediately for responsive UI
    final newLocale = locale ?? state.locale;
    state = state.copyWith(
      locale: newLocale,
      autoPostEnabled: autoPostEnabled ?? state.autoPostEnabled,
      dailyLimit: dailyLimit ?? state.dailyLimit,
      defaultTone: defaultTone ?? state.defaultTone,
      defaultTweetLanguage: defaultTweetLanguage ?? state.defaultTweetLanguage,
      defaultImagesPerTweet: defaultImagesPerTweet ?? state.defaultImagesPerTweet,
    );

    // Save locale preference locally (even if backend fails)
    if (locale != null) {
      final prefs = await SharedPreferences.getInstance();
      if (locale.isEmpty) {
        await prefs.remove('locale_override');
      } else {
        await prefs.setString('locale_override', locale);
      }
    }

    // Try to update backend (ignore errors for locale changes)
    try {
      final data = <String, dynamic>{};
      if (locale != null) {
        data['ui_language_override'] = locale.isEmpty ? null : locale;
      }
      if (autoPostEnabled != null) data['auto_post_enabled'] = autoPostEnabled;
      if (dailyLimit != null) data['daily_post_limit'] = dailyLimit;
      if (defaultTone != null) data['default_tone'] = defaultTone;
      if (defaultTweetLanguage != null) data['default_tweet_language'] = defaultTweetLanguage;
      if (defaultImagesPerTweet != null) data['default_images_per_tweet'] = defaultImagesPerTweet;

      final response = await _apiClient.put(AppConfig.settings, data: data);
      final responseData = response.data as Map<String, dynamic>;

      // Update state from response
      state = state.copyWith(
        isConnectedToX: responseData['is_x_connected'] as bool? ?? state.isConnectedToX,
        xUsername: responseData['x_username'] as String? ?? state.xUsername,
        defaultTone: responseData['default_tone'] as String? ?? state.defaultTone,
        defaultTweetLanguage: responseData['default_tweet_language'] as String? ?? state.defaultTweetLanguage,
        defaultImagesPerTweet: responseData['default_images_per_tweet'] as int? ?? state.defaultImagesPerTweet,
      );
    } catch (e) {
      // If only locale change, don't rethrow - local change is enough
      if (locale != null && autoPostEnabled == null && dailyLimit == null &&
          defaultTone == null && defaultTweetLanguage == null && defaultImagesPerTweet == null) {
        debugPrint('Backend settings update failed, but locale change saved locally: $e');
        return;
      }
      rethrow;
    }
  }

  void setConnectedToX(bool connected) {
    state = state.copyWith(isConnectedToX: connected);
  }

  Future<void> connectX() async {
    try {
      final response = await _apiClient.post(AppConfig.xOAuthStart);
      final data = response.data as Map<String, dynamic>;
      final url = data['authorize_url'] as String;

      final uri = Uri.parse(url);

      // For web platform, use a different approach
      if (kIsWeb) {
        // Web: open in popup window and listen for postMessage
        await _openOAuthPopup(url);
      } else {
        // Mobile: use external browser
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        } else {
          throw 'Could not launch $url';
        }
      }
    } catch (e, stack) {
      debugPrint('Error launching X OAuth: $e');
      debugPrint('Stack: $stack');
      rethrow;
    }
  }

  Future<void> _openOAuthPopup(String url) async {
    // For web, we'll use url_launcher which will open in a new window
    // and we'll listen for postMessage events
    final uri = Uri.parse(url);

    // Open in a popup-style window
    if (await canLaunchUrl(uri)) {
      await launchUrl(
        uri,
        webOnlyWindowName: '_blank',
        mode: LaunchMode.platformDefault,
      );

      // The callback page will use postMessage to communicate back
      // We'll poll the server to check if auth completed
      await _pollForOAuthCompletion();
    } else {
      throw 'Could not launch $url';
    }
  }

  Future<void> _pollForOAuthCompletion() async {
    // Poll the settings endpoint to check if X connection is established
    const maxAttempts = 60; // 60 attempts * 2 seconds = 2 minutes timeout
    const pollInterval = Duration(seconds: 2);

    for (int i = 0; i < maxAttempts; i++) {
      await Future.delayed(pollInterval);

      try {
        await fetchSettings();

        if (state.isConnectedToX) {
          debugPrint('OAuth completed successfully!');
          return;
        }
      } catch (e) {
        // Continue polling even if there's an error
        debugPrint('Poll attempt $i failed: $e');
      }
    }

    throw 'OAuth timeout - please try again';
  }

  Future<void> handleOAuthCallback(Uri uri) async {
    try {
      final params = uri.queryParameters;

      if (params.containsKey('error')) {
        throw params['error'] ?? 'Unknown error';
      }

      if (params.containsKey('success') && params['success'] == 'true') {
        final username = params['username'];

        // Refresh settings from server
        await fetchSettings();

        debugPrint('OAuth success: Connected as @$username');
      }
    } catch (e, stack) {
      debugPrint('Error handling OAuth callback: $e');
      debugPrint('Stack: $stack');
      rethrow;
    }
  }
}

final userProvider = StateNotifierProvider<UserNotifier, UserState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserNotifier(apiClient);
});

// Locale provider
final localeProvider = StateProvider<Locale?>((ref) {
  final userState = ref.watch(userProvider);
  if (userState.locale != null && userState.locale!.isNotEmpty) {
    return Locale(userState.locale!);
  }
  return null; // Use system locale
});
