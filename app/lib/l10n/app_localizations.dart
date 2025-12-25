import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_de.dart';
import 'app_localizations_en.dart';
import 'app_localizations_tr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
    Locale('tr')
  ];

  /// The app title
  ///
  /// In tr, this message translates to:
  /// **'Kampanya Yöneticisi'**
  String get appTitle;

  /// No description provided for @welcome.
  ///
  /// In tr, this message translates to:
  /// **'Hoş Geldiniz'**
  String get welcome;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In tr, this message translates to:
  /// **'Sosyal medya kampanyalarınızı kolayca yönetin'**
  String get welcomeSubtitle;

  /// No description provided for @connectWithX.
  ///
  /// In tr, this message translates to:
  /// **'X ile Bağlan'**
  String get connectWithX;

  /// No description provided for @skipAndContinue.
  ///
  /// In tr, this message translates to:
  /// **'Atla ve Devam Et'**
  String get skipAndContinue;

  /// No description provided for @campaigns.
  ///
  /// In tr, this message translates to:
  /// **'Kampanyalar'**
  String get campaigns;

  /// No description provided for @createCampaign.
  ///
  /// In tr, this message translates to:
  /// **'Kampanya Oluştur'**
  String get createCampaign;

  /// No description provided for @noCampaigns.
  ///
  /// In tr, this message translates to:
  /// **'Henüz kampanya yok'**
  String get noCampaigns;

  /// No description provided for @createFirstCampaign.
  ///
  /// In tr, this message translates to:
  /// **'İlk kampanyanızı oluşturun'**
  String get createFirstCampaign;

  /// No description provided for @campaignTitle.
  ///
  /// In tr, this message translates to:
  /// **'Kampanya Başlığı'**
  String get campaignTitle;

  /// No description provided for @campaignDescription.
  ///
  /// In tr, this message translates to:
  /// **'Açıklama'**
  String get campaignDescription;

  /// No description provided for @campaignDescriptionHint.
  ///
  /// In tr, this message translates to:
  /// **'Kampanyanızı kısaca açıklayın...'**
  String get campaignDescriptionHint;

  /// No description provided for @language.
  ///
  /// In tr, this message translates to:
  /// **'Dil'**
  String get language;

  /// No description provided for @hashtags.
  ///
  /// In tr, this message translates to:
  /// **'Hashtagler'**
  String get hashtags;

  /// No description provided for @addHashtag.
  ///
  /// In tr, this message translates to:
  /// **'Hashtag Ekle'**
  String get addHashtag;

  /// No description provided for @hashtagHint.
  ///
  /// In tr, this message translates to:
  /// **'#hashtag'**
  String get hashtagHint;

  /// No description provided for @tone.
  ///
  /// In tr, this message translates to:
  /// **'Ton'**
  String get tone;

  /// No description provided for @toneInformative.
  ///
  /// In tr, this message translates to:
  /// **'Bilgilendirici'**
  String get toneInformative;

  /// No description provided for @toneEmotional.
  ///
  /// In tr, this message translates to:
  /// **'Duygusal'**
  String get toneEmotional;

  /// No description provided for @toneFormal.
  ///
  /// In tr, this message translates to:
  /// **'Resmi'**
  String get toneFormal;

  /// No description provided for @toneHopeful.
  ///
  /// In tr, this message translates to:
  /// **'Umut Verici'**
  String get toneHopeful;

  /// No description provided for @toneCallToAction.
  ///
  /// In tr, this message translates to:
  /// **'Eylem Çağrısı'**
  String get toneCallToAction;

  /// No description provided for @callToAction.
  ///
  /// In tr, this message translates to:
  /// **'Eylem Çağrısı Metni'**
  String get callToAction;

  /// No description provided for @callToActionHint.
  ///
  /// In tr, this message translates to:
  /// **'Örn: Bugün harekete geç!'**
  String get callToActionHint;

  /// No description provided for @images.
  ///
  /// In tr, this message translates to:
  /// **'Görseller'**
  String get images;

  /// No description provided for @addImages.
  ///
  /// In tr, this message translates to:
  /// **'Görsel Ekle'**
  String get addImages;

  /// No description provided for @maxImages.
  ///
  /// In tr, this message translates to:
  /// **'En fazla 10 görsel'**
  String get maxImages;

  /// No description provided for @video.
  ///
  /// In tr, this message translates to:
  /// **'Video'**
  String get video;

  /// No description provided for @addVideo.
  ///
  /// In tr, this message translates to:
  /// **'Video Ekle'**
  String get addVideo;

  /// No description provided for @optionalVideo.
  ///
  /// In tr, this message translates to:
  /// **'İsteğe bağlı (maks. 1)'**
  String get optionalVideo;

  /// No description provided for @schedule.
  ///
  /// In tr, this message translates to:
  /// **'Zamanlama'**
  String get schedule;

  /// No description provided for @addTime.
  ///
  /// In tr, this message translates to:
  /// **'Saat Ekle'**
  String get addTime;

  /// No description provided for @generateDrafts.
  ///
  /// In tr, this message translates to:
  /// **'Taslakları Oluştur'**
  String get generateDrafts;

  /// No description provided for @drafts.
  ///
  /// In tr, this message translates to:
  /// **'Taslaklar'**
  String get drafts;

  /// No description provided for @draftReview.
  ///
  /// In tr, this message translates to:
  /// **'Taslak İnceleme'**
  String get draftReview;

  /// No description provided for @selectVariant.
  ///
  /// In tr, this message translates to:
  /// **'Bir varyant seçin'**
  String get selectVariant;

  /// No description provided for @characters.
  ///
  /// In tr, this message translates to:
  /// **'karakter'**
  String get characters;

  /// No description provided for @copy.
  ///
  /// In tr, this message translates to:
  /// **'Kopyala'**
  String get copy;

  /// No description provided for @edit.
  ///
  /// In tr, this message translates to:
  /// **'Düzenle'**
  String get edit;

  /// No description provided for @scheduleCampaign.
  ///
  /// In tr, this message translates to:
  /// **'Planla'**
  String get scheduleCampaign;

  /// No description provided for @settings.
  ///
  /// In tr, this message translates to:
  /// **'Ayarlar'**
  String get settings;

  /// No description provided for @languageSettings.
  ///
  /// In tr, this message translates to:
  /// **'Dil Ayarları'**
  String get languageSettings;

  /// No description provided for @autoLanguage.
  ///
  /// In tr, this message translates to:
  /// **'Otomatik (Cihaz Dili)'**
  String get autoLanguage;

  /// No description provided for @turkish.
  ///
  /// In tr, this message translates to:
  /// **'Türkçe'**
  String get turkish;

  /// No description provided for @english.
  ///
  /// In tr, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @german.
  ///
  /// In tr, this message translates to:
  /// **'Deutsch'**
  String get german;

  /// No description provided for @autoPost.
  ///
  /// In tr, this message translates to:
  /// **'Otomatik Paylaşım'**
  String get autoPost;

  /// No description provided for @autoPostDescription.
  ///
  /// In tr, this message translates to:
  /// **'Planlanan saatlerde otomatik olarak paylaş'**
  String get autoPostDescription;

  /// No description provided for @dailyLimit.
  ///
  /// In tr, this message translates to:
  /// **'Günlük Limit'**
  String get dailyLimit;

  /// No description provided for @dailyLimitDescription.
  ///
  /// In tr, this message translates to:
  /// **'Günde en fazla paylaşım sayısı'**
  String get dailyLimitDescription;

  /// No description provided for @logs.
  ///
  /// In tr, this message translates to:
  /// **'Geçmiş'**
  String get logs;

  /// No description provided for @noLogs.
  ///
  /// In tr, this message translates to:
  /// **'Henüz kayıt yok'**
  String get noLogs;

  /// No description provided for @logGenerated.
  ///
  /// In tr, this message translates to:
  /// **'Oluşturuldu'**
  String get logGenerated;

  /// No description provided for @logScheduled.
  ///
  /// In tr, this message translates to:
  /// **'Planlandı'**
  String get logScheduled;

  /// No description provided for @logPosted.
  ///
  /// In tr, this message translates to:
  /// **'Paylaşıldı'**
  String get logPosted;

  /// No description provided for @logFailed.
  ///
  /// In tr, this message translates to:
  /// **'Başarısız'**
  String get logFailed;

  /// No description provided for @logSkipped.
  ///
  /// In tr, this message translates to:
  /// **'Atlandı'**
  String get logSkipped;

  /// No description provided for @save.
  ///
  /// In tr, this message translates to:
  /// **'Kaydet'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In tr, this message translates to:
  /// **'İptal'**
  String get cancel;

  /// No description provided for @delete.
  ///
  /// In tr, this message translates to:
  /// **'Sil'**
  String get delete;

  /// No description provided for @confirm.
  ///
  /// In tr, this message translates to:
  /// **'Onayla'**
  String get confirm;

  /// No description provided for @error.
  ///
  /// In tr, this message translates to:
  /// **'Hata'**
  String get error;

  /// No description provided for @success.
  ///
  /// In tr, this message translates to:
  /// **'Başarılı'**
  String get success;

  /// No description provided for @loading.
  ///
  /// In tr, this message translates to:
  /// **'Yükleniyor...'**
  String get loading;

  /// No description provided for @retry.
  ///
  /// In tr, this message translates to:
  /// **'Tekrar Dene'**
  String get retry;

  /// No description provided for @required.
  ///
  /// In tr, this message translates to:
  /// **'Bu alan zorunludur'**
  String get required;

  /// No description provided for @invalidHashtag.
  ///
  /// In tr, this message translates to:
  /// **'Hashtag # ile başlamalı'**
  String get invalidHashtag;

  /// No description provided for @maxCharacters.
  ///
  /// In tr, this message translates to:
  /// **'En fazla {count} karakter'**
  String maxCharacters(int count);

  /// No description provided for @scheduledFor.
  ///
  /// In tr, this message translates to:
  /// **'Planlandı: {date}'**
  String scheduledFor(String date);

  /// No description provided for @variantCount.
  ///
  /// In tr, this message translates to:
  /// **'{count} varyant'**
  String variantCount(int count);
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['de', 'en', 'tr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
    case 'tr':
      return AppLocalizationsTr();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
