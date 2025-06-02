#!/usr/bin/env python3
"""
Quick test script for S3 service connection
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.s3_service import get_s3_service
from app.config import settings

async def test_s3_connection():
    """Test S3 service connection and basic operations"""
    
    print("🔍 Testing S3 Service Connection...")
    print(f"Endpoint: {settings.S3_ENDPOINT_URL}")
    print(f"Bucket: {settings.S3_BUCKET_NAME}")
    print(f"Region: {settings.S3_REGION}")
    print()
    
    # Get S3 service
    s3_service = get_s3_service()
    
    # Test 1: Check if service is configured
    print("1. Testing service configuration...")
    if s3_service.is_configured():
        print("✅ S3 service is properly configured")
    else:
        print("❌ S3 service is NOT configured")
        return
    
    # Test 2: Test bucket access
    print("\n2. Testing bucket access...")
    try:
        # Try to list objects (this will test bucket access)
        if s3_service.s3_client:
            response = s3_service.s3_client.list_objects_v2(
                Bucket=s3_service.bucket_name,
                MaxKeys=1
            )
            print("✅ Successfully connected to bucket")
            print(f"   Objects in bucket: {response.get('KeyCount', 0)}")
        else:
            print("❌ S3 client not initialized")
    except Exception as e:
        print(f"❌ Error accessing bucket: {e}")
        return
    
    # Test 3: Test upload with a small test image
    print("\n3. Testing image upload...")
    try:
        # Create a simple test image using PIL
        from PIL import Image
        from io import BytesIO
        
        # Create a small test image (100x100 red square)
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_content = img_bytes.getvalue()
        
        # Create a mock UploadFile object for the image
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content_type = content_type
                self._content = content
                self._position = 0
            
            async def read(self, size=-1):
                if self._position >= len(self._content):
                    return b''
                if size == -1:
                    result = self._content[self._position:]
                    self._position = len(self._content)
                else:
                    result = self._content[self._position:self._position + size]
                    self._position += len(result)
                return result
        
        test_file = MockUploadFile("test.png", img_content, "image/png")
        
        # Upload test file
        result = await s3_service.upload_image(
            file=test_file,
            folder="test",
            tenant_id="test-tenant",
            max_size_mb=1
        )
        
        print("✅ File uploaded successfully!")
        print(f"   URL: {result['url']}")
        print(f"   Size: {result['file_size']} bytes")
        print(f"   S3 Key: {result['s3_key']}")
        
        # Test 4: Test file deletion
        print("\n4. Testing file deletion...")
        if s3_service.delete_image(result['s3_key']):
            print("✅ File deleted successfully!")
        else:
            print("❌ File deletion failed")
            
    except Exception as e:
        print(f"❌ Error during upload test: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("\n🎉 S3 testing completed!")

if __name__ == "__main__":
    asyncio.run(test_s3_connection())