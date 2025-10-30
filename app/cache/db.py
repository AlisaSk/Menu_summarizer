import sqlite3
import json
import os
from datetime import datetime, date
from typing import Optional
from app.core.config import settings

DATABASE_PATH = settings.DATABASE_PATH

def init_db():
    """Initialize SQLite database with cache table"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                menu_url TEXT NOT NULL,
                date TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(menu_url, date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_url_date ON cache(menu_url, date)")
        conn.commit()

def get(url: str, date_str: str) -> Optional[str]:
    """Get cached menu data for URL and date"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(
            "SELECT payload FROM cache WHERE menu_url = ? AND date = ?",
            (url, date_str)
        )
        result = cursor.fetchone()
        return result[0] if result else None

def set(url: str, date_str: str, payload: str):
    """Cache menu data for URL and date"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache (menu_url, date, payload) VALUES (?, ?, ?)",
            (url, date_str, payload)
        )
        conn.commit()

def purge_old(today_str: str):
    """Remove cache entries older than today"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("DELETE FROM cache WHERE date < ?", (today_str,))
        conn.commit()

def clear_all():
    """Clear all cache entries (for testing)"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("DELETE FROM cache")
        conn.commit()

def get_stats() -> dict:
    """Get cache statistics"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM cache")
        total_entries = cursor.fetchone()[0]
        
        from app.fetch.utils import today_prague_str
        today = today_prague_str()
        cursor = conn.execute("SELECT COUNT(*) FROM cache WHERE date = ?", (today,))
        today_entries = cursor.fetchone()[0]
        
        return {
            "total_entries": total_entries,
            "today_entries": today_entries,
            "database_path": DATABASE_PATH
        }
