class AppConfig {
  // API Configuration - Use environment variables for flexibility
  // Build with: flutter build apk --dart-define=API_BASE_URL=https://your-api.com
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: _defaultApiUrl,
  );

  // Default API URL based on build mode
  static const String _defaultApiUrl = bool.fromEnvironment('dart.vm.product')
      ? 'https://campaign-backend.campaignapp.workers.dev'  // Production
      : 'http://localhost:8000';  // Development

  // API timeout settings
  static const int apiTimeoutSeconds = 30;
  static const int uploadTimeoutSeconds = 120;

  // Supported languages
  static const List<String> supportedLocales = ['tr', 'en', 'de'];
  static const String defaultLocale = 'tr';

  // Media limits (should match backend)
  static const int maxImagesPerCampaign = 15;
  static const int maxVideosPerCampaign = 10; // No hard limit, but reasonable
  static const int maxFileSizeMB = 50;
  static const List<String> allowedImageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
  static const List<String> allowedVideoExtensions = ['.mp4', '.mov', '.avi', '.webm'];

  // Tweet limits
  static const int maxTweetChars = 280;
  static const int targetTweetChars = 268;

  // Security settings
  static const int maxRetryAttempts = 3;
  static const int retryDelayMs = 1000;

  // API endpoints
  static const String authAnonymous = '/v1/auth/anonymous';
  static const String settings = '/v1/settings';
  static const String campaigns = '/v1/campaigns';
  static const String logs = '/v1/logs';
  static const String xOAuthStart = '/v1/x/oauth/start';
  static const String xOAuthCallback = '/v1/x/oauth/callback';
  static const String xPost = '/v1/x/post';

  static String campaignDetail(String id) => '/v1/campaigns/$id';
  static String campaignGenerate(String id) => '/v1/campaigns/$id/generate';
  static String campaignSchedule(String id) => '/v1/campaigns/$id/schedule';
  static String campaignDrafts(String id) => '/v1/campaigns/$id/drafts';
  static String campaignDetailView(String id) => '/v1/campaigns/$id/detail';
  static String mediaDistribute(String id) => '/v1/campaigns/$id/media/distribute';
  static String scheduleAuto(String id) => '/v1/campaigns/$id/schedule/auto';
  static String scheduleCalculate(String id) => '/v1/campaigns/$id/schedule/calculate';
  static const String mediaUpload = '/v1/media/upload';

  // Validate file extension
  static bool isValidImageExtension(String filename) {
    final ext = filename.toLowerCase();
    return allowedImageExtensions.any((e) => ext.endsWith(e));
  }

  static bool isValidVideoExtension(String filename) {
    final ext = filename.toLowerCase();
    return allowedVideoExtensions.any((e) => ext.endsWith(e));
  }
}
