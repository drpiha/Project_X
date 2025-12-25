# Project_X: Social Media Campaign Manager

Project_X is a full-stack application designed to manage, generate, and schedule social media campaigns for X (Twitter). It uses AI to generate tweet variants and provides a robust scheduling system.

## Project Structure

- **/backend**: FastAPI application with SQLAlchemy (PostgreSQL/SQLite).
- **/app**: Flutter mobile application.
- **/docs**: Project documentation.

## Features

- **AI Generation**: Powered by OpenRouter (DeepSeek/Gemini).
- **Campaign Management**: Organize tweets with media and hashtags.
- **X Integration**: OAuth2 flow for posting directly to X.
- **Multilingual**: Supports Turkish, English, and German.

## Getting Started

### Backend
1. `cd backend`
2. Create `venv`: `python -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Setup `.env` (use `.env.example` as reference).
5. Run: `uvicorn app.main:app --reload`

### App
1. `cd app`
2. Install dependencies: `flutter pub get`
3. Run: `flutter run`

## Docker Setup
Run the entire stack with:
```bash
docker-compose up -d
```
