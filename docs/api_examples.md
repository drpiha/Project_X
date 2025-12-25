# API Examples - cURL Commands

## 1. Create Anonymous User
```bash
curl -X POST http://localhost:8000/v1/auth/anonymous \
  -H "Content-Type: application/json" \
  -d '{"device_locale": "tr"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-24T12:00:00",
  "device_locale": "tr",
  "ui_language_override": "tr",
  "auto_post_enabled": false,
  "daily_post_limit": 10
}
```

## 2. Get Settings
```bash
curl -X GET http://localhost:8000/v1/settings \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

## 3. Update Settings
```bash
curl -X PUT http://localhost:8000/v1/settings \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "ui_language_override": "en",
    "auto_post_enabled": true,
    "daily_post_limit": 5
  }'
```

## 4. Create Campaign (with images)
```bash
curl -X POST http://localhost:8000/v1/campaigns \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -F "title=Çevre Kampanyası" \
  -F "description=Çevre bilinci oluşturma kampanyası" \
  -F "language=tr" \
  -F "hashtags=#ÇevreBilinci,#DoğayıKoru" \
  -F "tone=hopeful" \
  -F "call_to_action=Bugün harekete geç!" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg"
```

## 5. List Campaigns
```bash
curl -X GET "http://localhost:8000/v1/campaigns?limit=10&offset=0" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

## 6. Get Campaign
```bash
curl -X GET http://localhost:8000/v1/campaigns/CAMPAIGN_ID \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

## 7. Generate Tweet Variants
```bash
curl -X POST http://localhost:8000/v1/campaigns/CAMPAIGN_ID/generate \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "campaign_id": "CAMPAIGN_ID",
    "language": "tr",
    "topic_summary": "Çevre koruma ve sürdürülebilirlik",
    "hashtags": ["#ÇevreBilinci", "#DoğayıKoru"],
    "tone": "hopeful",
    "call_to_action": "Bugün harekete geç!",
    "constraints": {
      "max_chars": 280,
      "target_chars": 268,
      "include_emojis": true,
      "emoji_density": "low"
    },
    "output": {
      "variants": 6
    }
  }'
```

## 8. Schedule Campaign
```bash
curl -X POST http://localhost:8000/v1/campaigns/CAMPAIGN_ID/schedule \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "timezone": "Europe/Istanbul",
    "recurrence": "daily",
    "times": ["09:00", "12:00", "18:00"],
    "start_date": "2025-12-24",
    "auto_post": false,
    "daily_limit": 3,
    "selected_variant_index": 0
  }'
```

## 9. Get Drafts
```bash
curl -X GET http://localhost:8000/v1/campaigns/CAMPAIGN_ID/drafts \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

## 10. Get Logs
```bash
curl -X GET "http://localhost:8000/v1/logs?campaign_id=CAMPAIGN_ID&limit=50" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

## 11. Start X OAuth
```bash
curl -X POST http://localhost:8000/v1/x/oauth/start \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000"
```

Response:
```json
{
  "authorize_url": "http://localhost:8000/v1/x/oauth/mock?state=...",
  "state": "random_state_string"
}
```

## 12. Complete X OAuth (Mock)
```bash
curl -X POST http://localhost:8000/v1/x/oauth/callback \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "code": "mock_code_...",
    "state": "state_from_start"
  }'
```

## 13. Post to X (Mock)
```bash
curl -X POST http://localhost:8000/v1/x/post \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "draft_id": "DRAFT_ID"
  }'
```

## Health Check
```bash
curl http://localhost:8000/health
```

## OpenAPI Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
