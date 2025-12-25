"""
Seed Script

Creates sample data for development and testing.
Run with: python scripts/seed.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import uuid
import pytz

from app.db.session import async_session_maker
from app.db.models import User, Campaign, Draft, Schedule, PostLog


async def seed_database():
    """Seed the database with sample data."""
    print("Seeding database...")
    
    async with async_session_maker() as db:
        try:
            # Create sample user
            user = User(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                device_locale="tr",
                ui_language_override="tr",
                auto_post_enabled=False,
                daily_post_limit=10,
            )
            db.add(user)
            print(f"Created user: {user.id}")
            
            # Create sample campaigns
            campaigns_data = [
                {
                    "title": "Çevre Koruma Kampanyası",
                    "description": "Çevre bilinci oluşturma ve doğayı koruma çağrısı kampanyası",
                    "language": "tr",
                    "hashtags": ["#ÇevreBilinci", "#DoğayıKoru", "#YeşilGelecek"],
                    "tone": "hopeful",
                    "call_to_action": "Bugün harekete geç!",
                },
                {
                    "title": "Education for All",
                    "description": "Campaign to raise awareness about education accessibility",
                    "language": "en",
                    "hashtags": ["#EducationForAll", "#LearnTogether"],
                    "tone": "informative",
                    "call_to_action": "Support education today",
                },
                {
                    "title": "Umweltschutz Kampagne",
                    "description": "Kampagne für Umweltbewusstsein",
                    "language": "de",
                    "hashtags": ["#Umweltschutz", "#Nachhaltigkeit"],
                    "tone": "call_to_action",
                    "call_to_action": "Handeln Sie jetzt!",
                },
            ]
            
            for i, data in enumerate(campaigns_data):
                campaign = Campaign(
                    user_id=user.id,
                    **data
                )
                db.add(campaign)
                await db.flush()
                
                # Add sample drafts for Turkish campaign
                if data["language"] == "tr":
                    drafts = [
                        "🌟 Çevre koruma hakkında düşündükçe, insan hikayelerinin gücünü görüyoruz. Her birimiz değişim yaratabiliriz. Bugün harekete geç! #ÇevreBilinci #DoğayıKoru",
                        "📊 Çevre koruma konusunda bilmeniz gereken gerçekler var. Araştırmalar önemli sonuçlar ortaya koyuyor. Bugün harekete geç! #YeşilGelecek",
                        "💪 Çevre koruma için somut çözümler üretebiliriz. Birlikte değişim yaratabiliriz. Bugün harekete geç! #ÇevreBilinci #DoğayıKoru",
                        "🌍 Dünya genelinde çevre koruma konusu giderek daha fazla gündemde. Uluslararası arenada tartışılıyor. #YeşilGelecek",
                        "❤️ Çevre koruma konusunda dayanışma şart. Birlik ve beraberlikle ses çıkarıyoruz. Bugün harekete geç! #ÇevreBilinci",
                        "✨ Her birimizin çevre koruma konusunda bir hikayesi var. Gerçek deneyimler bize ilham veriyor. #DoğayıKoru #YeşilGelecek",
                    ]
                    
                    for j, text in enumerate(drafts):
                        draft = Draft(
                            campaign_id=campaign.id,
                            variant_index=j,
                            text=text,
                            char_count=len(text),
                            hashtags_used=[tag for tag in data["hashtags"] if tag in text],
                            status="pending",
                        )
                        db.add(draft)
                    
                    # Create a sample schedule
                    tz = pytz.timezone("Europe/Istanbul")
                    schedule = Schedule(
                        campaign_id=campaign.id,
                        timezone="Europe/Istanbul",
                        times=["09:00", "12:00", "18:00"],
                        recurrence="daily",
                        start_date=tz.localize(datetime.now()),
                        is_active=True,
                        auto_post=False,
                        daily_limit=3,
                        selected_variant_index=0,
                    )
                    db.add(schedule)
                
                print(f"Created campaign: {campaign.title}")
            
            # Create sample post log
            log = PostLog(
                campaign_id=campaign.id,
                action="generated",
                details={"message": "Seed data created", "variants": 6}
            )
            db.add(log)
            
            await db.commit()
            print("\nDatabase seeded successfully!")
            print(f"\nSample user ID for testing: {user.id}")
            print("Use this in the X-User-Id header for API requests.")
            
        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
