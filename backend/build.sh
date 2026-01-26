#!/bin/bash
# Render Build Script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
python -c "
import asyncio
from app.db.session import engine
from app.db.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database tables created/updated successfully')

asyncio.run(init_db())
"

# Add missing columns (safe - uses IF NOT EXISTS)
echo "Ensuring schema is up to date..."
python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def migrate():
    async with engine.begin() as conn:
        # Get existing columns
        result = await conn.execute(text(
            \"SELECT column_name FROM information_schema.columns WHERE table_name = 'x_accounts'\"
        ))
        existing = {row[0] for row in result}
        print(f'Existing x_accounts columns: {existing}')

        if 'oauth_code_verifier' not in existing:
            await conn.execute(text('ALTER TABLE x_accounts ADD COLUMN oauth_code_verifier TEXT'))
            print('Added oauth_code_verifier')

        if 'oauth_state_expires_at' not in existing:
            await conn.execute(text('ALTER TABLE x_accounts ADD COLUMN oauth_state_expires_at TIMESTAMP'))
            print('Added oauth_state_expires_at')

        if 'oauth_state_used' not in existing:
            await conn.execute(text('ALTER TABLE x_accounts ADD COLUMN oauth_state_used BOOLEAN DEFAULT FALSE'))
            print('Added oauth_state_used')

        # Check draft_media_assets table
        result2 = await conn.execute(text(
            \"SELECT table_name FROM information_schema.tables WHERE table_name = 'draft_media_assets'\"
        ))
        if not result2.fetchone():
            print('draft_media_assets table will be created by create_all')

    print('Schema migration complete')

asyncio.run(migrate())
" || echo "Migration warning (non-fatal)"

echo "Build complete!"
