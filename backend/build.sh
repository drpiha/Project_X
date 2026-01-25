#!/bin/bash
# Render Build Script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
# First create all tables (for new deployments)
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

# Then add any missing columns for existing deployments
echo "Ensuring all columns exist..."
python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def ensure_columns():
    async with engine.begin() as conn:
        # Check and add oauth_code_verifier column if missing
        try:
            await conn.execute(text('''
                ALTER TABLE x_accounts ADD COLUMN IF NOT EXISTS oauth_code_verifier TEXT
            '''))
            print('oauth_code_verifier column ensured')
        except Exception as e:
            print(f'Column already exists or error: {e}')

        # Check and add oauth_state_expires_at column if missing
        try:
            await conn.execute(text('''
                ALTER TABLE x_accounts ADD COLUMN IF NOT EXISTS oauth_state_expires_at TIMESTAMP
            '''))
            print('oauth_state_expires_at column ensured')
        except Exception as e:
            print(f'Column already exists or error: {e}')

        # Check and add oauth_state_used column if missing
        try:
            await conn.execute(text('''
                ALTER TABLE x_accounts ADD COLUMN IF NOT EXISTS oauth_state_used BOOLEAN DEFAULT FALSE
            '''))
            print('oauth_state_used column ensured')
        except Exception as e:
            print(f'Column already exists or error: {e}')

asyncio.run(ensure_columns())
"

echo "Build complete!"
