# API Testing Guide

This directory contains automated tests for the API endpoints.

## Quick Start

### 1. **Simple Test Runner** (Recommended for quick testing)

```bash
# Set your admin password
export TEST_ADMIN_PASSWORD="your-admin-password"

# Make sure your development server is running
uvicorn app.main:app --reload

# Run the simple test script
python run_api_tests.py
```

### 2. **pytest Tests** (More comprehensive)

```bash
# Set your admin password
export TEST_ADMIN_PASSWORD="your-admin-password"

# Run all API tests
pytest tests/test_simple_api.py -v

# Run specific test class
pytest tests/test_simple_api.py::TestPropertyAPI -v

# Run with performance info
pytest tests/test_simple_api.py -v -s
```

## Test Categories

### ✅ **Property API Tests**
- Properties list endpoint (`GET /api/v1/properties/`)
- Property detail endpoint (`GET /api/v1/properties/{id}`)
- Property filtering and pagination
- Response time performance tests

### ✅ **Investagon API Tests** 
- Sync status endpoint
- Sync history endpoint
- Error handling

### ✅ **Statistics Tests**
- Property overview statistics
- Data validation

### ✅ **Error Handling Tests**
- Invalid property IDs
- Unauthorized access
- Non-existent endpoints

## Configuration

### Environment Variables
```bash
export TEST_ADMIN_PASSWORD="your-password"
export TEST_BASE_URL="http://localhost:8000"  # Optional, defaults to localhost:8000
```

### Update Credentials
Edit `tests/config.py` or `run_api_tests.py` to change:
- Admin email
- Base URL
- Performance thresholds

## Sample Output

```
🔄 Starting API Tests...
Target: http://localhost:8000
--------------------------------------------------
✅ Server is running
✅ Authentication successful
✅ Properties list: 15 properties in 0.234s
✅ Property detail: loaded in 0.156s
✅ Property filtering: 8 apartments found
✅ Investagon sync: available
✅ Property stats: 15 total properties
--------------------------------------------------
📊 Test Results: 5/5 passed
🎉 All tests passed!
```

## Continuous Testing

### Watch Mode (Auto-run tests on file changes)
```bash
# Install pytest-watch
pip install pytest-watch

# Run tests automatically on changes
ptw tests/test_simple_api.py
```

### Integration with Development
Add to your development workflow:

```bash
# Start server
uvicorn app.main:app --reload &

# Run tests
export TEST_ADMIN_PASSWORD="your-password"
python run_api_tests.py

# Or use pytest for detailed output
pytest tests/test_simple_api.py -v
```

## Performance Benchmarks

Current performance targets:
- Properties list: < 2 seconds
- Property detail: < 1 second  
- Authentication: < 3 seconds

## Troubleshooting

### Common Issues

1. **Server not running**
   ```
   ❌ Server is not running. Start with: uvicorn app.main:app --reload
   ```
   → Start your development server first

2. **Authentication failed**
   ```
   ❌ Login failed: 401
   ```
   → Check your `TEST_ADMIN_PASSWORD` environment variable

3. **No properties found**
   ```
   No properties available for detail test
   ```
   → Run Investagon sync or create test properties

4. **Performance issues**
   ```
   Too slow: 3.45s
   ```
   → Check database performance or increase thresholds in config

## Adding New Tests

### Simple Function Test
```python
def test_new_endpoint(self, auth_headers):
    response = requests.get(f"{BASE_URL}/api/v1/new-endpoint", headers=auth_headers)
    assert response.status_code == 200
    assert "expected_field" in response.json()
```

### Performance Test
```python
def test_endpoint_performance(self, auth_headers):
    import time
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/v1/endpoint", headers=auth_headers)
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 1.0  # Should respond in under 1 second
```