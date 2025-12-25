// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Turkish (`tr`).
class AppLocalizationsTr extends AppLocalizations {
  AppLocalizationsTr([String locale = 'tr']) : super(locale);

  @override
  String get appTitle => 'Kampanya Yöneticisi';

  @override
  String get welcome => 'Hoş Geldiniz';

  @override
  String get welcomeSubtitle => 'Sosyal medya kampanyalarınızı kolayca yönetin';

  @override
  String get connectWithX => 'X ile Bağlan';

  @override
  String get skipAndContinue => 'Atla ve Devam Et';

  @override
  String get campaigns => 'Kampanyalar';

  @override
  String get createCampaign => 'Kampanya Oluştur';

  @override
  String get noCampaigns => 'Henüz kampanya yok';

  @override
  String get createFirstCampaign => 'İlk kampanyanızı oluşturun';

  @override
  String get campaignTitle => 'Kampanya Başlığı';

  @override
  String get campaignDescription => 'Açıklama';

  @override
  String get campaignDescriptionHint => 'Kampanyanızı kısaca açıklayın...';

  @override
  String get language => 'Dil';

  @override
  String get hashtags => 'Hashtagler';

  @override
  String get addHashtag => 'Hashtag Ekle';

  @override
  String get hashtagHint => '#hashtag';

  @override
  String get tone => 'Ton';

  @override
  String get toneInformative => 'Bilgilendirici';

  @override
  String get toneEmotional => 'Duygusal';

  @override
  String get toneFormal => 'Resmi';

  @override
  String get toneHopeful => 'Umut Verici';

  @override
  String get toneCallToAction => 'Eylem Çağrısı';

  @override
  String get callToAction => 'Eylem Çağrısı Metni';

  @override
  String get callToActionHint => 'Örn: Bugün harekete geç!';

  @override
  String get images => 'Görseller';

  @override
  String get addImages => 'Görsel Ekle';

  @override
  String get maxImages => 'En fazla 10 görsel';

  @override
  String get video => 'Video';

  @override
  String get addVideo => 'Video Ekle';

  @override
  String get optionalVideo => 'İsteğe bağlı (maks. 1)';

  @override
  String get schedule => 'Zamanlama';

  @override
  String get addTime => 'Saat Ekle';

  @override
  String get generateDrafts => 'Taslakları Oluştur';

  @override
  String get drafts => 'Taslaklar';

  @override
  String get draftReview => 'Taslak İnceleme';

  @override
  String get selectVariant => 'Bir varyant seçin';

  @override
  String get characters => 'karakter';

  @override
  String get copy => 'Kopyala';

  @override
  String get edit => 'Düzenle';

  @override
  String get scheduleCampaign => 'Planla';

  @override
  String get settings => 'Ayarlar';

  @override
  String get languageSettings => 'Dil Ayarları';

  @override
  String get autoLanguage => 'Otomatik (Cihaz Dili)';

  @override
  String get turkish => 'Türkçe';

  @override
  String get english => 'English';

  @override
  String get german => 'Deutsch';

  @override
  String get autoPost => 'Otomatik Paylaşım';

  @override
  String get autoPostDescription =>
      'Planlanan saatlerde otomatik olarak paylaş';

  @override
  String get dailyLimit => 'Günlük Limit';

  @override
  String get dailyLimitDescription => 'Günde en fazla paylaşım sayısı';

  @override
  String get logs => 'Geçmiş';

  @override
  String get noLogs => 'Henüz kayıt yok';

  @override
  String get logGenerated => 'Oluşturuldu';

  @override
  String get logScheduled => 'Planlandı';

  @override
  String get logPosted => 'Paylaşıldı';

  @override
  String get logFailed => 'Başarısız';

  @override
  String get logSkipped => 'Atlandı';

  @override
  String get save => 'Kaydet';

  @override
  String get cancel => 'İptal';

  @override
  String get delete => 'Sil';

  @override
  String get confirm => 'Onayla';

  @override
  String get error => 'Hata';

  @override
  String get success => 'Başarılı';

  @override
  String get loading => 'Yükleniyor...';

  @override
  String get retry => 'Tekrar Dene';

  @override
  String get required => 'Bu alan zorunludur';

  @override
  String get invalidHashtag => 'Hashtag # ile başlamalı';

  @override
  String maxCharacters(int count) {
    return 'En fazla $count karakter';
  }

  @override
  String scheduledFor(String date) {
    return 'Planlandı: $date';
  }

  @override
  String variantCount(int count) {
    return '$count varyant';
  }
}
