// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for German (`de`).
class AppLocalizationsDe extends AppLocalizations {
  AppLocalizationsDe([String locale = 'de']) : super(locale);

  @override
  String get appTitle => 'Kampagnen-Manager';

  @override
  String get welcome => 'Willkommen';

  @override
  String get welcomeSubtitle =>
      'Verwalten Sie Ihre Social-Media-Kampagnen einfach';

  @override
  String get connectWithX => 'Mit X verbinden';

  @override
  String get skipAndContinue => 'Überspringen und fortfahren';

  @override
  String get campaigns => 'Kampagnen';

  @override
  String get createCampaign => 'Kampagne erstellen';

  @override
  String get noCampaigns => 'Noch keine Kampagnen';

  @override
  String get createFirstCampaign => 'Erstellen Sie Ihre erste Kampagne';

  @override
  String get campaignTitle => 'Kampagnentitel';

  @override
  String get campaignDescription => 'Beschreibung';

  @override
  String get campaignDescriptionHint => 'Beschreiben Sie Ihre Kampagne kurz...';

  @override
  String get language => 'Sprache';

  @override
  String get hashtags => 'Hashtags';

  @override
  String get addHashtag => 'Hashtag hinzufügen';

  @override
  String get hashtagHint => '#hashtag';

  @override
  String get tone => 'Ton';

  @override
  String get toneInformative => 'Informativ';

  @override
  String get toneEmotional => 'Emotional';

  @override
  String get toneFormal => 'Formell';

  @override
  String get toneHopeful => 'Hoffnungsvoll';

  @override
  String get toneCallToAction => 'Handlungsaufforderung';

  @override
  String get callToAction => 'Handlungsaufforderungstext';

  @override
  String get callToActionHint => 'Z.B.: Handeln Sie jetzt!';

  @override
  String get images => 'Bilder';

  @override
  String get addImages => 'Bilder hinzufügen';

  @override
  String get maxImages => 'Max. 10 Bilder';

  @override
  String get video => 'Video';

  @override
  String get addVideo => 'Video hinzufügen';

  @override
  String get optionalVideo => 'Optional (max. 1)';

  @override
  String get schedule => 'Zeitplan';

  @override
  String get addTime => 'Zeit hinzufügen';

  @override
  String get generateDrafts => 'Entwürfe erstellen';

  @override
  String get drafts => 'Entwürfe';

  @override
  String get draftReview => 'Entwurfsprüfung';

  @override
  String get selectVariant => 'Wählen Sie eine Variante';

  @override
  String get characters => 'Zeichen';

  @override
  String get copy => 'Kopieren';

  @override
  String get edit => 'Bearbeiten';

  @override
  String get scheduleCampaign => 'Planen';

  @override
  String get settings => 'Einstellungen';

  @override
  String get languageSettings => 'Spracheinstellungen';

  @override
  String get autoLanguage => 'Automatisch (Gerätesprache)';

  @override
  String get turkish => 'Türkçe';

  @override
  String get english => 'English';

  @override
  String get german => 'Deutsch';

  @override
  String get autoPost => 'Automatisch posten';

  @override
  String get autoPostDescription => 'Automatisch zu geplanten Zeiten posten';

  @override
  String get dailyLimit => 'Tageslimit';

  @override
  String get dailyLimitDescription => 'Maximale Posts pro Tag';

  @override
  String get logs => 'Verlauf';

  @override
  String get noLogs => 'Noch keine Einträge';

  @override
  String get logGenerated => 'Erstellt';

  @override
  String get logScheduled => 'Geplant';

  @override
  String get logPosted => 'Gepostet';

  @override
  String get logFailed => 'Fehlgeschlagen';

  @override
  String get logSkipped => 'Übersprungen';

  @override
  String get save => 'Speichern';

  @override
  String get cancel => 'Abbrechen';

  @override
  String get delete => 'Löschen';

  @override
  String get confirm => 'Bestätigen';

  @override
  String get error => 'Fehler';

  @override
  String get success => 'Erfolg';

  @override
  String get loading => 'Lädt...';

  @override
  String get retry => 'Erneut versuchen';

  @override
  String get required => 'Dieses Feld ist erforderlich';

  @override
  String get invalidHashtag => 'Hashtag muss mit # beginnen';

  @override
  String maxCharacters(int count) {
    return 'Max. $count Zeichen';
  }

  @override
  String scheduledFor(String date) {
    return 'Geplant: $date';
  }

  @override
  String variantCount(int count) {
    return '$count Varianten';
  }
}
