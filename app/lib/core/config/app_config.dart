class AppConfig {
  // API Configuration
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.0.187:8000', // User's WiFi IP for phone testing
  );

  // Supported languages
  static const List<String> supportedLocales = ['tr', 'en', 'de'];
  static const String defaultLocale = 'tr';

  // Media limits
  static const int maxImagesPerCampaign = 10;
  static const int maxVideosPerCampaign = 1;
  static const int maxFileSizeMB = 50;

  // Tweet limits
  static const int maxTweetChars = 280;
  static const int targetTweetChars = 268;

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
}
