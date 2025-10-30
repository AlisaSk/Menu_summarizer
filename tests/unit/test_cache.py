import pytest
import tempfile
import os
import sqlite3
import time
from app.cache import db as cache_db

class TestCache:
    """Unit tests for cache functionality"""
    
    def setup_method(self):
        """Initialize clean database for each test"""
        # Use temporary database for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Temporarily override DATABASE_PATH
        self.original_db_path = cache_db.DATABASE_PATH
        cache_db.DATABASE_PATH = self.temp_db_path
        
        cache_db.init_db()
        cache_db.clear_all()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Restore original DATABASE_PATH
        cache_db.DATABASE_PATH = self.original_db_path
        
        # Windows fix: close all SQLite connections before deleting
        try:
            # Force close any open SQLite connections
            conn = sqlite3.connect(self.temp_db_path)
            conn.close()
            
            # Small delay to allow file handle release
            time.sleep(0.1)
            
            # Remove temporary database
            if os.path.exists(self.temp_db_path):
                os.unlink(self.temp_db_path)
        except Exception:
            # If cleanup fails, it's not critical for tests
            pass
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        url = "https://test.com"
        date = "2025-10-27"
        payload = '{"test": "data"}'
        
        # Set cache
        cache_db.set(url, date, payload)
        
        # Get cache
        result = cache_db.get(url, date)
        assert result == payload
    
    def test_cache_get_nonexistent(self):
        """Test getting non-existent cache entry"""
        result = cache_db.get("https://nonexistent.com", "2025-10-27")
        assert result is None
    
    def test_cache_replace_existing(self):
        """Test replacing existing cache entry"""
        url = "https://test.com"
        date = "2025-10-27"
        payload1 = '{"version": 1}'
        payload2 = '{"version": 2}'
        
        # Set initial value
        cache_db.set(url, date, payload1)
        assert cache_db.get(url, date) == payload1
        
        # Replace with new value
        cache_db.set(url, date, payload2)
        assert cache_db.get(url, date) == payload2
    
    def test_cache_different_dates(self):
        """Test cache isolation between different dates"""
        url = "https://test.com"
        date1 = "2025-10-27"
        date2 = "2025-10-28"
        payload1 = '{"date": "27"}'
        payload2 = '{"date": "28"}'
        
        # Set different payloads for different dates
        cache_db.set(url, date1, payload1)
        cache_db.set(url, date2, payload2)
        
        # Verify both are stored correctly
        assert cache_db.get(url, date1) == payload1
        assert cache_db.get(url, date2) == payload2
    
    def test_cache_different_urls(self):
        """Test cache isolation between different URLs"""
        url1 = "https://restaurant1.com"
        url2 = "https://restaurant2.com"
        date = "2025-10-27"
        payload1 = '{"restaurant": 1}'
        payload2 = '{"restaurant": 2}'
        
        # Set different payloads for different URLs
        cache_db.set(url1, date, payload1)
        cache_db.set(url2, date, payload2)
        
        # Verify both are stored correctly
        assert cache_db.get(url1, date) == payload1
        assert cache_db.get(url2, date) == payload2
    
    def test_purge_old_entries(self):
        """Test purging old cache entries"""
        url = "https://test.com"
        old_date = "2025-10-25"
        current_date = "2025-10-27"
        future_date = "2025-10-29"
        
        payload = '{"test": "data"}'
        
        # Set entries for different dates
        cache_db.set(url, old_date, payload)
        cache_db.set(url, current_date, payload)
        cache_db.set(url, future_date, payload)
        
        # Verify all entries exist
        assert cache_db.get(url, old_date) == payload
        assert cache_db.get(url, current_date) == payload
        assert cache_db.get(url, future_date) == payload
        
        # Purge old entries (before current_date)
        cache_db.purge_old(current_date)
        
        # Verify old entry is removed, others remain
        assert cache_db.get(url, old_date) is None
        assert cache_db.get(url, current_date) == payload
        assert cache_db.get(url, future_date) == payload
    
    def test_clear_all_cache(self):
        """Test clearing all cache entries"""
        # Add multiple entries
        cache_db.set("https://test1.com", "2025-10-27", '{"test": 1}')
        cache_db.set("https://test2.com", "2025-10-27", '{"test": 2}')
        cache_db.set("https://test1.com", "2025-10-28", '{"test": 3}')
        
        # Verify entries exist
        assert cache_db.get("https://test1.com", "2025-10-27") is not None
        assert cache_db.get("https://test2.com", "2025-10-27") is not None
        assert cache_db.get("https://test1.com", "2025-10-28") is not None
        
        # Clear all
        cache_db.clear_all()
        
        # Verify all entries are removed
        assert cache_db.get("https://test1.com", "2025-10-27") is None
        assert cache_db.get("https://test2.com", "2025-10-27") is None
        assert cache_db.get("https://test1.com", "2025-10-28") is None
