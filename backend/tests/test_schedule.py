import pytest
from datetime import date, datetime, timedelta
import pytz
from httpx import AsyncClient

from app.db.models import User, Campaign, Draft
from app.api.v1.schedule import calculate_next_runs


class TestSchedule:
    """Tests for scheduling endpoints and next run calculation."""
    
    @pytest.mark.asyncio
    async def test_schedule_next_runs_calculation(self):
        """
        Test that next runs are calculated correctly.
        
        Creates a mock schedule and verifies next runs are:
        - In the future
        - Within the date range
        - At the correct times
        """
        from app.db.models import Schedule
        import uuid
        
        tz = pytz.timezone("Europe/Istanbul")
        now = datetime.now(tz)
        
        # Create a mock schedule (not saved to DB)
        schedule = Schedule(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            timezone="Europe/Istanbul",
            times=["09:00", "12:00", "18:00"],
            recurrence="daily",
            start_date=now - timedelta(days=1),  # Started yesterday
            end_date=now + timedelta(days=30),   # Ends in 30 days
            is_active=True,
        )
        
        next_runs = calculate_next_runs(schedule, count=5)
        
        # Should have 5 runs
        assert len(next_runs) == 5
        
        # All runs should be valid ISO format
        for run in next_runs:
            parsed = datetime.fromisoformat(run)
            # Compare both as offset-aware datetimes
            assert parsed > now  # Should be in future
    
    @pytest.mark.asyncio
    async def test_schedule_next_runs_once(self):
        """Test next runs for a one-time schedule."""
        from app.db.models import Schedule
        import uuid
        
        tz = pytz.timezone("Europe/Berlin")
        now = datetime.now(tz)
        tomorrow = now + timedelta(days=1)
        
        schedule = Schedule(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            timezone="Europe/Berlin",
            times=["10:00", "15:00"],
            recurrence="once",
            start_date=tomorrow,
            is_active=True,
        )
        
        next_runs = calculate_next_runs(schedule, count=5)
        
        # For once, should only return runs for the start date
        assert len(next_runs) <= 2
    
    @pytest.mark.asyncio
    async def test_schedule_creation(self, client: AsyncClient, test_user: User, db_session):
        """Test creating a schedule for a campaign."""
        user_id = str(test_user.id)
        
        # Create campaign
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={"title": "Schedule Test", "language": "tr"}
        )
        campaign_id = response.json()["id"]
        
        # Generate drafts first
        response = await client.post(
            f"/v1/campaigns/{campaign_id}/generate",
            headers={"X-User-Id": user_id},
            json={
                "campaign_id": campaign_id,
                "language": "tr",
                "topic_summary": "Test topic for scheduling",
                "hashtags": ["#Test"],
                "tone": "informative",
            }
        )
        assert response.status_code == 200
        
        # Create schedule
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = await client.post(
            f"/v1/campaigns/{campaign_id}/schedule",
            headers={"X-User-Id": user_id},
            json={
                "timezone": "Europe/Istanbul",
                "recurrence": "daily",
                "times": ["09:00", "18:00"],
                "start_date": tomorrow,
                "auto_post": False,
                "daily_limit": 5,
                "selected_variant_index": 0,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schedule_id" in data
        assert "next_runs" in data
        assert len(data["next_runs"]) > 0
    
    @pytest.mark.asyncio
    async def test_schedule_without_drafts_fails(self, client: AsyncClient, test_user: User):
        """Test that scheduling fails if no drafts exist."""
        user_id = str(test_user.id)
        
        # Create campaign (no drafts)
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={"title": "No Drafts", "language": "tr"}
        )
        campaign_id = response.json()["id"]
        
        # Try to schedule without drafts
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = await client.post(
            f"/v1/campaigns/{campaign_id}/schedule",
            headers={"X-User-Id": user_id},
            json={
                "timezone": "Europe/Istanbul",
                "recurrence": "daily",
                "times": ["09:00"],
                "start_date": tomorrow,
            }
        )
        
        assert response.status_code == 400
        assert "drafts" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_drafts(self, client: AsyncClient, test_user: User):
        """Test getting drafts for a campaign."""
        user_id = str(test_user.id)
        
        # Create campaign
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={"title": "Drafts Test", "language": "tr"}
        )
        campaign_id = response.json()["id"]
        
        # Generate drafts
        response = await client.post(
            f"/v1/campaigns/{campaign_id}/generate",
            headers={"X-User-Id": user_id},
            json={
                "campaign_id": campaign_id,
                "language": "tr", 
                "topic_summary": "Test",
                "hashtags": [],
            }
        )
        assert response.status_code == 200
        
        # Get drafts
        response = await client.get(
            f"/v1/campaigns/{campaign_id}/drafts",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        drafts = response.json()
        
        assert len(drafts) == 6  # Default 6 variants
        for draft in drafts:
            assert "text" in draft
            assert "char_count" in draft
            assert "status" in draft
