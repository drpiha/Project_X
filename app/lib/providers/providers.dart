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

  const UserState({
    this.userId,
    this.locale,
    this.autoPostEnabled = false,
    this.dailyLimit = 10,
    this.isConnectedToX = false,
    this.xUsername,
  });

  UserState copyWith({
    String? userId,
    String? locale,
    bool? autoPostEnabled,
    int? dailyLimit,
    bool? isConnectedToX,
    String? xUsername,
  }) {
    return UserState(
      userId: userId ?? this.userId,
      locale: locale ?? this.locale,
      autoPostEnabled: autoPostEnabled ?? this.autoPostEnabled,
      dailyLimit: dailyLimit ?? this.dailyLimit,
      isConnectedToX: isConnectedToX ?? this.isConnectedToX,
      xUsername: xUsername ?? this.xUsername,
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
      final userId = data['id'] as String;
      
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
      );
    } catch (e) {
      // Ignore errors
    }
  }

  Future<void> updateSettings({
    String? locale,
    bool? autoPostEnabled,
    int? dailyLimit,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (locale != null) {
        data['ui_language_override'] = locale.isEmpty ? null : locale;
      }
      if (autoPostEnabled != null) data['auto_post_enabled'] = autoPostEnabled;
      if (dailyLimit != null) data['daily_post_limit'] = dailyLimit;
      
      final response = await _apiClient.put(AppConfig.settings, data: data);
      final responseData = response.data as Map<String, dynamic>;
      
      state = state.copyWith(
        locale: locale ?? state.locale,
        autoPostEnabled: autoPostEnabled ?? state.autoPostEnabled,
        dailyLimit: dailyLimit ?? state.dailyLimit,
        isConnectedToX: responseData['is_x_connected'] as bool? ?? state.isConnectedToX,
        xUsername: responseData['x_username'] as String? ?? state.xUsername,
      );
      
      // Save locale preference locally
      if (locale != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('locale_override', locale);
      }
    } catch (e) {
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
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        throw 'Could not launch $url';
      }
    } catch (e, stack) {
      debugPrint('Error launching X OAuth: $e');
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
