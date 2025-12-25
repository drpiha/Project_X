# Project_X: Social Media Campaign Manager

Project_X is a full-stack application designed to manage, generate, and schedule social media campaigns for X (Twitter). It uses AI to generate tweet variants and provides a robust scheduling system.

## Project Structure

- **/backend**: FastAPI application with SQLAlchemy (PostgreSQL/SQLite).
- **/app**: Flutter mobile/web application.
- **/docs**: Project documentation.

## Features

- **AI Generation**: Powered by OpenRouter (DeepSeek/Gemini).
- **Campaign Management**: Organize tweets with media and hashtags.
- **X Integration**: OAuth2 flow for posting directly to X.
- **Multilingual**: Supports Turkish, English, and German.

## Getting Started

### Docker Setup (Recommended)
Run the entire stack with:
```bash
docker-compose up -d
```

This starts:
- Backend API on port 8000
- PostgreSQL database on port 5432
- Scheduler worker for auto-posting

### Manual Setup

#### Backend
1. `cd backend`
2. Create `venv`: `python -m venv venv`
3. Activate: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
4. Install dependencies: `pip install -r requirements.txt`
5. Setup `.env` (use `.env.example` as reference)
6. Run: `uvicorn app.main:app --reload --host 0.0.0.0`

#### Flutter App
1. `cd app`
2. Install dependencies: `flutter pub get`
3. Run web: `flutter run -d chrome`
4. Run mobile: `flutter run`

## X (Twitter) OAuth Setup

For real X integration (not mock mode):

1. Create a project at [X Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Enable OAuth 2.0 with PKCE
3. Set redirect URI to your callback URL (e.g., `https://yourdomain.com/v1/x/oauth/callback`)
4. Update `.env`:
   ```env
   X_CLIENT_ID=your_client_id
   X_CLIENT_SECRET=your_client_secret
   X_REDIRECT_URI=https://yourdomain.com/v1/x/oauth/callback
   FEATURE_X_POSTING=true
   ```

## Deployment

### Environment Variables
Required for production:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Random secret for encryption
- `X_CLIENT_ID`, `X_CLIENT_SECRET`: X OAuth credentials
- `OPENROUTER_API_KEY`: For AI tweet generation

### Docker Compose Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## API Documentation

When running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

