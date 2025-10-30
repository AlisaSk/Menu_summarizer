import os
import tempfile
import pytest
import sqlite3
from app.cache import db as cache_db
from app.core import config

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment with mock settings"""
    # Store original values
    original_db_path = cache_db.DATABASE_PATH
    original_use_mock = config.settings.USE_MOCK
    
    # Create temporary database for tests
    temp_db = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    # Override settings for tests - disable USE_MOCK for integration tests
    cache_db.DATABASE_PATH = temp_db_path
    config.settings.USE_MOCK = False  # Allow mocking to work properly
    
    # Initialize test database
    cache_db.init_db()
    
    yield
    
    # Restore original values
    cache_db.DATABASE_PATH = original_db_path
    config.settings.USE_MOCK = original_use_mock
    
    # Cleanup temporary database - close all connections first (Windows fix)
    try:
        # Force close any open SQLite connections
        conn = sqlite3.connect(temp_db_path)
        conn.close()
        
        # Small delay to allow file handle release
        import time
        time.sleep(0.1)
        
        # Remove file
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
    except Exception:
        # If cleanup fails, it's not critical for tests
        pass
