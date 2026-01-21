#!/bin/bash
# Render Build Script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine
from app.db.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database tables created successfully')

asyncio.run(init_db())
"

echo "Build complete!"
