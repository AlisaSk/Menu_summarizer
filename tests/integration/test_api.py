import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.cache import db as cache_db

# Test client
client = TestClient(app)

class TestIntegrationSummarize:
    """Integration tests for the /summarize endpoint"""
    
    def setup_method(self):
        """Clear cache before each test"""
        pass
    
    @patch('app.fetch.scraper.fetch_html_with_js_fallback')
    @patch('app.llm.client.summarize_menu')
    def test_summarize_endpoint_success(self, mock_llm, mock_fetch):
        """Test successful menu summarization"""
        # Mock HTML content
        mock_fetch.return_value = """
        <h1>Restaurace Test</h1>
        <div class="menu">
            <h2>Denní menu - středa</h2>
            <p>Polévka: Hovězí vývar 45,-</p>
            <p>Hlavní chod: Řízek s bramborami 185,- (1,3)</p>
        </div>
        """
        
        # Mock LLM response - need to handle new async signature
        async def mock_llm_async(*args, **kwargs):
            return {
                "restaurant_name": "Restaurace Test",
                "date": "2025-10-27",
                "day_of_week": "neděle",
                "menu_items": [
                    {
                        "category": "polévka",
                        "name": "Hovězí vývar",
                        "price": 45,
                        "allergens": [],
                        "weight": "300ml"
                    },
                    {
                        "category": "hlavní chod",
                        "name": "Řízek s bramborami", 
                        "price": 185,
                        "allergens": ["1", "3"],
                        "weight": "200g"
                    }
                ],
                "daily_menu": True,
                "source_url": "https://test-restaurant.cz"
            }
        
        mock_llm.side_effect = mock_llm_async
        
        # Make request
        response = client.post(
            "/summarize",
            json={"url": "https://test-restaurant.cz"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "cached" in data
        assert "data" in data
        assert data["cached"] is False
        
        menu_data = data["data"]
        assert menu_data["restaurant_name"] == "Restaurace Test"
        assert menu_data["date"] == "2025-10-27"
        assert len(menu_data["menu_items"]) == 2
        assert menu_data["daily_menu"] is True
    
    def test_summarize_invalid_url(self):
        """Test endpoint with invalid URL"""
        response = client.post(
            "/summarize",
            json={"url": "not-a-url"}
        )
        
        assert response.status_code == 400
        assert "must start with http" in response.json()["detail"]
    
    def test_summarize_missing_url(self):
        """Test endpoint with missing URL"""
        response = client.post("/summarize", json={})
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.fetch.scraper.fetch_html_with_js_fallback')
    def test_summarize_fetch_error(self, mock_fetch):
        """Test handling of fetch errors"""
        mock_fetch.side_effect = Exception("Network error")
        
        response = client.post(
            "/summarize",
            json={"url": "https://unreachable-site.com"}
        )
        
        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

class TestCacheIntegration:
    """Integration tests for caching functionality"""
    
    def setup_method(self):
        """Clear cache before each test"""
        pass
    
    @patch('app.fetch.scraper.fetch_html_with_js_fallback')
    @patch('app.llm.client.summarize_menu')
    def test_cache_hit_second_request(self, mock_llm, mock_fetch):
        """Test that second request with same URL uses cache"""
        # Mock responses
        mock_fetch.return_value = "<h1>Test Menu</h1>"
        
        async def mock_llm_async(*args, **kwargs):
            return {
                "restaurant_name": "Test Restaurant",
                "date": "2025-10-27",
                "day_of_week": "neděle",
                "menu_items": [
                    {
                        "category": "polévka",
                        "name": "Test Soup",
                        "price": 50,
                        "allergens": [],
                        "weight": None
                    }
                ],
                "daily_menu": True,
                "source_url": "https://test.com"
            }
        
        mock_llm.side_effect = mock_llm_async
        
        # First request
        response1 = client.post(
            "/summarize",
            json={"url": "https://test.com"}
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Verify LLM was called once
        assert mock_llm.call_count == 1
        
        # Second request with same URL
        response2 = client.post(
            "/summarize",
            json={"url": "https://test.com"}
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Verify LLM was not called again
        assert mock_llm.call_count == 1
        
        # Verify same data returned
        assert data1["data"] == data2["data"]

class TestHealthEndpoints:
    """Test health and utility endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data
    
    def test_cache_stats_endpoint(self):
        """Test cache statistics endpoint"""
        response = client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
