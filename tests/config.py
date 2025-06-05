# ================================
# TEST CONFIGURATION (tests/config.py)
# ================================

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test Configuration
TEST_CONFIG = {
    "base_url": os.getenv("TEST_BASE_URL", "http://localhost:8000"),
    "admin_email": os.getenv("TEST_ADMIN_EMAIL", "admin@cl-solutions.com"),
    "admin_password": os.getenv("TEST_ADMIN_PASSWORD", ""),  # Set in environment
    "timeout": int(os.getenv("TEST_TIMEOUT", "10")),
    "performance_thresholds": {
        "list_endpoint": float(os.getenv("TEST_PERF_LIST_ENDPOINT", "2.0")),  # seconds
        "detail_endpoint": float(os.getenv("TEST_PERF_DETAIL_ENDPOINT", "1.0")),  # seconds
        "create_endpoint": float(os.getenv("TEST_PERF_CREATE_ENDPOINT", "3.0")),  # seconds
    },
    "page_size": int(os.getenv("TEST_PAGE_SIZE", "5"))
}

def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API tests."""
    import requests
    
    if not TEST_CONFIG["admin_password"]:
        raise ValueError(
            "Please set TEST_ADMIN_PASSWORD environment variable or update tests/config.py"
        )
    
    login_data = {
        "email": TEST_CONFIG["admin_email"],
        "password": TEST_CONFIG["admin_password"]
    }
    
    response = requests.post(
        f"{TEST_CONFIG['base_url']}/api/v1/auth/login", 
        json=login_data,
        timeout=TEST_CONFIG["timeout"]
    )
    
    if response.status_code != 200:
        raise ValueError(f"Login failed: {response.status_code} - {response.text}")
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}