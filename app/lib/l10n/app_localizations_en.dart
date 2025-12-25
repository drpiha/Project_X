// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Campaign Manager';

  @override
  String get welcome => 'Welcome';

  @override
  String get welcomeSubtitle => 'Easily manage your social media campaigns';

  @override
  String get connectWithX => 'Connect with X';

  @override
  String get skipAndContinue => 'Skip and Continue';

  @override
  String get campaigns => 'Campaigns';

  @override
  String get createCampaign => 'Create Campaign';

  @override
  String get noCampaigns => 'No campaigns yet';

  @override
  String get createFirstCampaign => 'Create your first campaign';

  @override
  String get campaignTitle => 'Campaign Title';

  @override
  String get campaignDescription => 'Description';

  @override
  String get campaignDescriptionHint => 'Briefly describe your campaign...';

  @override
  String get language => 'Language';

  @override
  String get hashtags => 'Hashtags';

  @override
  String get addHashtag => 'Add Hashtag';

  @override
  String get hashtagHint => '#hashtag';

  @override
  String get tone => 'Tone';

  @override
  String get toneInformative => 'Informative';

  @override
  String get toneEmotional => 'Emotional';

  @override
  String get toneFormal => 'Formal';

  @override
  String get toneHopeful => 'Hopeful';

  @override
  String get toneCallToAction => 'Call to Action';

  @override
  String get callToAction => 'Call to Action Text';

  @override
  String get callToActionHint => 'E.g.: Take action today!';

  @override
  String get images => 'Images';

  @override
  String get addImages => 'Add Images';

  @override
  String get maxImages => 'Max 10 images';

  @override
  String get video => 'Video';

  @override
  String get addVideo => 'Add Video';

  @override
  String get optionalVideo => 'Optional (max 1)';

  @override
  String get schedule => 'Schedule';

  @override
  String get addTime => 'Add Time';

  @override
  String get generateDrafts => 'Generate Drafts';

  @override
  String get drafts => 'Drafts';

  @override
  String get draftReview => 'Draft Review';

  @override
  String get selectVariant => 'Select a variant';

  @override
  String get characters => 'characters';

  @override
  String get copy => 'Copy';

  @override
  String get edit => 'Edit';

  @override
  String get scheduleCampaign => 'Schedule';

  @override
  String get settings => 'Settings';

  @override
  String get languageSettings => 'Language Settings';

  @override
  String get autoLanguage => 'Automatic (Device Language)';

  @override
  String get turkish => 'Türkçe';

  @override
  String get english => 'English';

  @override
  String get german => 'Deutsch';

  @override
  String get autoPost => 'Auto Post';

  @override
  String get autoPostDescription => 'Automatically post at scheduled times';

  @override
  String get dailyLimit => 'Daily Limit';

  @override
  String get dailyLimitDescription => 'Maximum posts per day';

  @override
  String get logs => 'History';

  @override
  String get noLogs => 'No logs yet';

  @override
  String get logGenerated => 'Generated';

  @override
  String get logScheduled => 'Scheduled';

  @override
  String get logPosted => 'Posted';

  @override
  String get logFailed => 'Failed';

  @override
  String get logSkipped => 'Skipped';

  @override
  String get save => 'Save';

  @override
  String get cancel => 'Cancel';

  @override
  String get delete => 'Delete';

  @override
  String get confirm => 'Confirm';

  @override
  String get error => 'Error';

  @override
  String get success => 'Success';

  @override
  String get loading => 'Loading...';

  @override
  String get retry => 'Retry';

  @override
  String get required => 'This field is required';

  @override
  String get invalidHashtag => 'Hashtag must start with #';

  @override
  String maxCharacters(int count) {
    return 'Max $count characters';
  }

  @override
  String scheduledFor(String date) {
    return 'Scheduled: $date';
  }

  @override
  String variantCount(int count) {
    return '$count variants';
  }
}
