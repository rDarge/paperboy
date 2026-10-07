import sqlite3
import os
import logging
from datetime import datetime

DB_FILE = "guild_configs.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database table for multi-guild configuration."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_configs (
                guild_id TEXT PRIMARY KEY,
                guild_name TEXT,
                channel_id TEXT,
                role_id TEXT,
                schedule_time TEXT DEFAULT '12:00',
                enabled INTEGER DEFAULT 1,
                last_posted_date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logging.info("Database initialized successfully.")


def get_guild_config(guild_id: str):
    """Retrieve configuration for a specific guild."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM guild_configs WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def set_guild_config(guild_id: str, guild_name: str = None, channel_id: str = None, 
                     role_id: str = None, schedule_time: str = None, enabled: int = None):
    """
    Create or update configuration for a guild.
    Only updates provided fields.
    """
    existing = get_guild_config(guild_id)
    
    new_guild_name = guild_name if guild_name is not None else (existing["guild_name"] if existing else "Unknown Guild")
    new_channel_id = str(channel_id) if channel_id is not None else (existing["channel_id"] if existing else None)
    new_role_id = str(role_id) if role_id is not None else (existing["role_id"] if existing else "CROSSWORD")
    new_schedule_time = schedule_time if schedule_time is not None else (existing["schedule_time"] if existing else "12:00")
    new_enabled = enabled if enabled is not None else (existing["enabled"] if existing else 1)
    new_last_posted = existing["last_posted_date"] if existing else None

    with get_db() as conn:
        conn.execute("""
            INSERT INTO guild_configs (guild_id, guild_name, channel_id, role_id, schedule_time, enabled, last_posted_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id) DO UPDATE SET
                guild_name = excluded.guild_name,
                channel_id = excluded.channel_id,
                role_id = excluded.role_id,
                schedule_time = excluded.schedule_time,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (str(guild_id), new_guild_name, new_channel_id, new_role_id, new_schedule_time, new_enabled, new_last_posted))
        conn.commit()
    
    return get_guild_config(guild_id)


def update_last_posted_date(guild_id: str, date_str: str):
    """Update last posted date for a guild to prevent duplicate posts."""
    with get_db() as conn:
        conn.execute("""
            UPDATE guild_configs SET last_posted_date = ? WHERE guild_id = ?
        """, (date_str, str(guild_id)))
        conn.commit()


def get_guilds_to_notify(current_time_hhmm: str, current_date_str: str):
    """
    Fetch all active guilds configured for the given schedule time (HH:MM)
    that haven't received today's puzzle post yet.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM guild_configs
            WHERE enabled = 1
              AND schedule_time = ?
              AND (last_posted_date IS NULL OR last_posted_date != ?)
              AND channel_id IS NOT NULL
        """, (current_time_hhmm, current_date_str))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
