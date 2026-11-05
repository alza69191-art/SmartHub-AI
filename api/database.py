import logging
import os

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger('smarthub.database')

def get_database_url():
    url = os.getenv('DATABASE_URL', '').strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'): ]
    return url or None

def initialize_database():
    url = get_database_url()
    if not url:
        logger.warning('DATABASE_URL is not configured; database setup skipped.')
        return False
    statements = [
        '''CREATE TABLE IF NOT EXISTS profiles (
            id UUID PRIMARY KEY,
            auth_subject TEXT UNIQUE NOT NULL,
            email TEXT,
            display_name TEXT,
            role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS support_tickets (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            subject VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'answered', 'closed')),
            priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS image_assets (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            file_name VARCHAR(160) NOT NULL,
            content_type VARCHAR(40) NOT NULL CHECK (content_type IN ('image/png','image/jpeg','image/webp')),
            data BYTEA NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL
        )''',
        'CREATE INDEX IF NOT EXISTS idx_image_assets_user_id ON image_assets(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_image_assets_expires_at ON image_assets(expires_at)',
        '''CREATE TABLE IF NOT EXISTS support_replies (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ticket_id BIGINT NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
            sender_user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
            sender_role TEXT NOT NULL CHECK (sender_role IN ('user', 'admin')),
            message TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )''',
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_email_lower_unique ON profiles (LOWER(email)) WHERE email IS NOT NULL',
        'CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)',
        'CREATE INDEX IF NOT EXISTS idx_support_replies_ticket_id ON support_replies(ticket_id)',
    ]
    statements.append('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS password_hash TEXT')
    with psycopg.connect(url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    logger.info('PostgreSQL connected; SmartHub tables are ready.')
    return True

def database_is_ready():
    url = get_database_url()
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                return cursor.fetchone()[0] == 1
    except Exception:
        logger.exception('PostgreSQL health check failed.')
        return False
