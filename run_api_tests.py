#!/usr/bin/env python3
# ================================
# SIMPLE API TEST RUNNER
# ================================

import requests
import json
import time
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@cl-solutions.com")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "")

def get_auth_headers():
    """Get authentication headers."""
    password = ADMIN_PASSWORD
    if not password:
        print("❌ Please set ADMIN_PASSWORD or TEST_ADMIN_PASSWORD environment variable")
        sys.exit(1)
    
    login_data = {"email": ADMIN_EMAIL, "password": password}
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_server_running():
    """Test if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        assert response.status_code == 200
        print("✅ Server is running")
        return True
    except:
        print("❌ Server is not running. Start with: uvicorn app.main:app --reload")
        return False

def test_properties_list(headers):
    """Test properties list endpoint."""
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/v1/properties/", headers=headers)
    end_time = time.time()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Properties list: {data['total']} properties in {end_time-start_time:.3f}s")
        return data
    else:
        print(f"❌ Properties list failed: {response.status_code}")
        return None

def test_property_detail(headers, property_id):
    """Test property detail endpoint."""
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/v1/properties/{property_id}", headers=headers)
    end_time = time.time()
    
    if response.status_code == 200:
        print(f"✅ Property detail: loaded in {end_time-start_time:.3f}s")
        return True
    else:
        print(f"❌ Property detail failed: {response.status_code}")
        return False

def test_property_filtering(headers):
    """Test property filtering."""
    response = requests.get(
        f"{BASE_URL}/api/v1/properties/", 
        headers=headers,
        params={"property_type": "apartment", "page_size": 5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Property filtering: {data['total']} apartments found")
        return True
    else:
        print(f"❌ Property filtering failed: {response.status_code}")
        return False

def test_investagon_status(headers):
    """Test Investagon sync status."""
    response = requests.get(f"{BASE_URL}/api/v1/investagon/can-sync", headers=headers)
    
    if response.status_code in [200, 503]:
        data = response.json()
        status = "available" if data.get("can_sync") else "not configured"
        print(f"✅ Investagon sync: {status}")
        return True
    else:
        print(f"❌ Investagon status failed: {response.status_code}")
        return False

def test_property_stats(headers):
    """Test property statistics."""
    response = requests.get(f"{BASE_URL}/api/v1/properties/stats/overview", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Property stats: {data.get('total_properties', 0)} total properties")
        return True
    else:
        print(f"❌ Property stats failed: {response.status_code}")
        return False

def main():
    """Run all API tests."""
    print("🔄 Starting API Tests...")
    print(f"Target: {BASE_URL}")
    print("-" * 50)
    
    # Test server
    if not test_server_running():
        return
    
    # Get authentication
    try:
        headers = get_auth_headers()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Run tests
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Properties list
    tests_total += 1
    properties_data = test_properties_list(headers)
    if properties_data:
        tests_passed += 1
    
    # Test 2: Property detail (if properties exist)
    if properties_data and properties_data["items"]:
        tests_total += 1
        property_id = properties_data["items"][0]["id"]
        if test_property_detail(headers, property_id):
            tests_passed += 1
    
    # Test 3: Property filtering
    tests_total += 1
    if test_property_filtering(headers):
        tests_passed += 1
    
    # Test 4: Investagon status
    tests_total += 1
    if test_investagon_status(headers):
        tests_passed += 1
    
    # Test 5: Property stats
    tests_total += 1
    if test_property_stats(headers):
        tests_passed += 1
    
    # Summary
    print("-" * 50)
    print(f"📊 Test Results: {tests_passed}/{tests_total} passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()