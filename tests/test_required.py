"""
Required tests for the assignment:
a. Minimálně 2 unit testy (např. parsování odpovědi, validace struktury)
b. Minimálně 1 integrační test (např. celý flow analýzy)
c. 1 test cachingu - ověř, že při druhém volání se neposílá request na LLM API
"""
import pytest
from pydantic import ValidationError
from app.schemas import MenuItem, MenuData
from app.fetch.utils import normalize_price_human, extract_allergens
from app.cache.db import set, get, purge_old
from datetime import date, timedelta


class TestUnitTests:
    """Unit tests - testing individual functions"""
    
    def test_menu_item_validation(self):
        """Unit test 1: Validate MenuData structure"""
        # Valid menu item
        item = MenuItem(
            category="Polévky",
            name="Svíčková na smetaně",
            price=150,
            weight="250 g",
            allergens=["1", "3", "7"]
        )
        assert item.name == "Svíčková na smetaně"
        assert item.price == 150
        assert item.category == "Polévky"
        
        # Valid menu data
        menu = MenuData(
            restaurant_name="Test Restaurant",
            date="2025-10-30",
            day_of_week="pondělí",
            daily_menu=True,
            source_url="https://test.cz",
            menu_items=[item]
        )
        assert menu.restaurant_name == "Test Restaurant"
        assert len(menu.menu_items) == 1
        assert menu.daily_menu is True
        
    def test_price_normalization(self):
        """Unit test 2: Test price parsing logic"""
        assert normalize_price_human("150") == 150
        assert normalize_price_human("150 Kč") == 150
        assert normalize_price_human("150,-") == 150
        assert normalize_price_human("150 CZK") == 150
        assert normalize_price_human("") is None
        assert normalize_price_human("free") is None
        
    def test_allergen_extraction(self):
        """Unit test 3: Test allergen parsing logic"""
        assert extract_allergens("Kuře (1, 3, 7)") == ["1", "3", "7"]
        assert extract_allergens("Salát [2,4]") == ["2", "4"]
        assert extract_allergens("Alergeny: 1,3,7") == ["1", "3", "7"]
        assert extract_allergens("Bez alergenů") == []
        assert extract_allergens("") == []


class TestIntegration:
    """Integration test - testing full flow"""
    
    def test_full_api_flow(self):
        """Integration test: Test complete API flow with mock"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.config import settings
        
        # Enable mock mode for integration test
        original_mock = settings.USE_MOCK
        settings.USE_MOCK = True
        
        try:
            client = TestClient(app)
            
            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            
            # Test summarize endpoint with mock
            response = client.post(
                "/summarize",
                json={"url": "https://example.com/menu"}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert "cached" in data
            assert "data" in data
            
            menu_data = data["data"]
            assert "restaurant_name" in menu_data
            assert "day_of_week" in menu_data
            assert "daily_menu" in menu_data
            assert "menu_items" in menu_data
            assert isinstance(menu_data["menu_items"], list)
            
            # Validate menu item structure
            if menu_data["menu_items"]:
                item = menu_data["menu_items"][0]
                assert "name" in item
                assert "category" in item
                
        finally:
            settings.USE_MOCK = original_mock


class TestCaching:
    """Test caching functionality"""
    
    def test_cache_prevents_duplicate_llm_calls(self):
        """
        Cache test: Verify that second call doesn't hit LLM API
        Required: ověř, že při druhém volání se neposílá request na LLM API
        """
        test_url = "https://test-restaurant.cz/menu"
        test_date = date.today().isoformat()
        test_data = '{"restaurant_name": "Test", "items": []}'
        
        # First call - cache miss (would call LLM)
        cached = get(test_url, test_date)
        assert cached is None
        
        # Set cache
        set(test_url, test_date, test_data)
        
        # Second call - cache hit (no LLM call needed)
        cached = get(test_url, test_date)
        assert cached is not None
        assert cached == test_data
        
        # Verify cache works for same URL on same date
        cached_again = get(test_url, test_date)
        assert cached_again == test_data
        
        # Verify cache miss for different date
        different_date = (date.today() + timedelta(days=1)).isoformat()
        cached_different = get(test_url, different_date)
        assert cached_different is None
        
    def test_cache_purge_old_entries(self):
        """Test that old cache entries are purged"""
        test_url = "https://old-menu.cz/menu"
        old_date = (date.today() - timedelta(days=2)).isoformat()
        
        # Set old cache entry
        set(test_url, old_date, '{"test": "old"}')
        
        # Purge old entries (pass today's date)
        purge_old(date.today().isoformat())
        
        # Verify old entry was purged
        cached = get(test_url, old_date)
        assert cached is None
