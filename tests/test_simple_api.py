# ================================
# SIMPLE API TESTS (test_simple_api.py)
# ================================

import pytest
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test Configuration from .env
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@cl-solutions.com")


@pytest.fixture(scope="session")
def auth_headers():
    """Get authentication headers for all tests."""
    password = os.getenv("TEST_ADMIN_PASSWORD")
    if not password:
        pytest.skip("Set TEST_ADMIN_PASSWORD environment variable to run API tests")
    
    login_data = {"email": ADMIN_EMAIL, "password": password}
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    
    if response.status_code != 200:
        pytest.fail(f"Login failed: {response.status_code}")
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
def check_server():
    """Check if development server is running."""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            pytest.exit("Development server is not responding")
    except requests.exceptions.RequestException:
        pytest.exit("Development server is not running. Start with: uvicorn app.main:app --reload")


class TestPropertyAPI:
    """Test property-related API endpoints."""
    
    def test_properties_list(self, auth_headers):
        """Test GET /api/v1/properties/ returns proper structure."""
        response = requests.get(f"{BASE_URL}/api/v1/properties/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["total"], int)
        
        # If properties exist, check structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "city" in item
            assert "property_type" in item
            # Should be lightweight - no heavy fields
            assert "investagon_data" not in item
    
    def test_properties_list_performance(self, auth_headers):
        """Test that properties list responds quickly."""
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/v1/properties/", headers=auth_headers)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Too slow: {response_time:.2f}s"
    
    def test_property_detail(self, auth_headers):
        """Test GET /api/v1/properties/{id} returns detailed info."""
        # First get a property ID
        list_response = requests.get(f"{BASE_URL}/api/v1/properties/", headers=auth_headers)
        assert list_response.status_code == 200
        
        items = list_response.json()["items"]
        if not items:
            pytest.skip("No properties available for detail test")
        
        property_id = items[0]["id"]
        
        # Test detail endpoint
        response = requests.get(f"{BASE_URL}/api/v1/properties/{property_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "images" in data  # Should have detailed fields
        assert "city_id" in data
    
    def test_property_filtering(self, auth_headers):
        """Test property filtering works."""
        response = requests.get(
            f"{BASE_URL}/api/v1/properties/",
            headers=auth_headers,
            params={"property_type": "apartment"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned items should be apartments (if any)
        for item in data["items"]:
            if item.get("property_type"):
                assert item["property_type"] == "apartment"
    
    def test_property_pagination(self, auth_headers):
        """Test property pagination works."""
        response = requests.get(
            f"{BASE_URL}/api/v1/properties/",
            headers=auth_headers,
            params={"page": 1, "page_size": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 3
        assert len(data["items"]) <= 3


class TestInvestagonAPI:
    """Test Investagon-related API endpoints."""
    
    def test_can_sync_endpoint(self, auth_headers):
        """Test Investagon sync status endpoint."""
        response = requests.get(f"{BASE_URL}/api/v1/investagon/can-sync", headers=auth_headers)
        
        # Should work regardless of configuration
        assert response.status_code in [200, 503]
        data = response.json()
        assert "can_sync" in data
    
    def test_sync_history_endpoint(self, auth_headers):
        """Test Investagon sync history endpoint."""
        response = requests.get(f"{BASE_URL}/api/v1/investagon/sync-history", headers=auth_headers)
        
        # Should work even if no history exists
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPropertyStats:
    """Test property statistics endpoints."""
    
    def test_property_stats(self, auth_headers):
        """Test property statistics endpoint."""
        response = requests.get(f"{BASE_URL}/api/v1/properties/stats/overview", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected stats fields
        expected_fields = ["total_properties", "available_properties", "sold_properties"]
        for field in expected_fields:
            assert field in data
            assert isinstance(data[field], int)


class TestErrorHandling:
    """Test API error handling."""
    
    def test_invalid_property_id(self, auth_headers):
        """Test accessing non-existent property."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/v1/properties/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_invalid_endpoint(self, auth_headers):
        """Test accessing non-existent endpoint."""
        response = requests.get(f"{BASE_URL}/api/v1/nonexistent", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoint without auth."""
        response = requests.get(f"{BASE_URL}/api/v1/properties/")
        
        assert response.status_code == 401