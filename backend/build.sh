#!/bin/bash
# Render Build Script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database setup..."
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

echo "Running schema migrations..."
python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine

MIGRATIONS = {
    'x_accounts': [
        ('oauth_code_verifier', 'TEXT'),
        ('oauth_state_expires_at', 'TIMESTAMP'),
        ('oauth_state_used', 'BOOLEAN DEFAULT FALSE'),
    ],
    'schedules': [
        ('auto_post', 'BOOLEAN DEFAULT FALSE'),
        ('daily_limit', 'INTEGER DEFAULT 10'),
        ('selected_variant_index', 'INTEGER DEFAULT 0'),
        ('post_interval_min', 'INTEGER DEFAULT 120'),
        ('post_interval_max', 'INTEGER DEFAULT 300'),
    ],
    'drafts': [
        ('last_error', 'TEXT'),
        ('schedule_id', 'VARCHAR(36)'),
        ('variant_index', 'INTEGER DEFAULT 0'),
    ],
    'media_assets': [
        ('x_media_id', 'VARCHAR(255)'),
        ('file_data', 'BYTEA'),
    ],
}

async def migrate():
    async with engine.begin() as conn:
        for table, columns in MIGRATIONS.items():
            # Get existing columns
            result = await conn.execute(text(
                f\"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'\"
            ))
            existing = {row[0] for row in result}
            print(f'{table}: {len(existing)} existing columns')

            for col_name, col_type in columns:
                if col_name not in existing:
                    try:
                        await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
                        print(f'  + Added {table}.{col_name} ({col_type})')
                    except Exception as e:
                        print(f'  ! Error adding {table}.{col_name}: {e}')
                else:
                    print(f'  = {table}.{col_name} already exists')

    print('Schema migration complete')

asyncio.run(migrate())
" || echo "Migration completed with warnings"

echo "Build complete!"
