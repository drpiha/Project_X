import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Campaign


class TestCampaigns:
    """Tests for campaign CRUD endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, client: AsyncClient):
        """Test anonymous user creation."""
        response = await client.post(
            "/v1/auth/anonymous",
            json={"device_locale": "tr"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["device_locale"] == "tr"
        assert data["ui_language_override"] == "tr"
    
    @pytest.mark.asyncio
    async def test_campaign_create_and_list(self, client: AsyncClient, test_user: User):
        """
        Test campaign creation and listing.
        
        Creates a campaign and verifies it appears in the list.
        """
        user_id = str(test_user.id)
        
        # Create campaign
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={
                "title": "Test Kampanya",
                "description": "Test açıklaması",
                "language": "tr",
                "hashtags": "#Test,#Kampanya",
                "tone": "informative",
            }
        )
        
        assert response.status_code == 200
        campaign_data = response.json()
        
        assert campaign_data["title"] == "Test Kampanya"
        assert campaign_data["description"] == "Test açıklaması"
        assert campaign_data["language"] == "tr"
        assert "#Test" in campaign_data["hashtags"]
        
        campaign_id = campaign_data["id"]
        
        # List campaigns
        response = await client.get(
            "/v1/campaigns",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        list_data = response.json()
        
        assert list_data["total"] >= 1
        assert any(c["id"] == campaign_id for c in list_data["campaigns"])
    
    @pytest.mark.asyncio
    async def test_get_campaign(self, client: AsyncClient, test_user: User):
        """Test getting a specific campaign."""
        user_id = str(test_user.id)
        
        # Create campaign first
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={
                "title": "Get Test",
                "language": "en",
            }
        )
        campaign_id = response.json()["id"]
        
        # Get campaign
        response = await client.get(
            f"/v1/campaigns/{campaign_id}",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == campaign_id
        assert data["title"] == "Get Test"
    
    @pytest.mark.asyncio
    async def test_campaign_not_found(self, client: AsyncClient, test_user: User):
        """Test 404 for non-existent campaign."""
        response = await client.get(
            "/v1/campaigns/00000000-0000-0000-0000-000000000000",
            headers={"X-User-Id": str(test_user.id)}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_campaign(self, client: AsyncClient, test_user: User):
        """Test campaign update."""
        user_id = str(test_user.id)
        
        # Create campaign
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={"title": "Original Title", "language": "tr"}
        )
        campaign_id = response.json()["id"]
        
        # Update campaign
        response = await client.put(
            f"/v1/campaigns/{campaign_id}",
            headers={"X-User-Id": user_id},
            json={"title": "Updated Title", "description": "New description"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "New description"
    
    @pytest.mark.asyncio
    async def test_delete_campaign(self, client: AsyncClient, test_user: User):
        """Test campaign deletion."""
        user_id = str(test_user.id)
        
        # Create campaign
        response = await client.post(
            "/v1/campaigns",
            headers={"X-User-Id": user_id},
            data={"title": "To Delete", "language": "tr"}
        )
        campaign_id = response.json()["id"]
        
        # Delete campaign
        response = await client.delete(
            f"/v1/campaigns/{campaign_id}",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        response = await client.get(
            f"/v1/campaigns/{campaign_id}",
            headers={"X-User-Id": user_id}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_invalid_user_id(self, client: AsyncClient):
        """Test with invalid user ID format."""
        response = await client.get(
            "/v1/campaigns",
            headers={"X-User-Id": "invalid-uuid"}
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_missing_user_id(self, client: AsyncClient):
        """Test without user ID header."""
        response = await client.get("/v1/campaigns")
        
        assert response.status_code == 422  # Missing required header
