#!/usr/bin/env python3
"""
Configure CORS for Hetzner Object Storage bucket
Based on: https://docs.hetzner.com/storage/object-storage/howto-protect-objects/cors/
"""

import boto3
import json
import sys
import os
from botocore.exceptions import ClientError

# Import settings from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.config import settings


def configure_cors():
    """Configure CORS for Hetzner Object Storage"""
    
    # Initialize S3 client for Hetzner
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL
    )
    
    bucket_name = settings.S3_BUCKET_NAME
    
    # CORS configuration for document preview
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'HEAD'],
                'AllowedOrigins': [
                    'http://localhost:3000',
                    'http://localhost:3001', 
                    'https://app.blackvesto.de',
                    'https://dev.blackvesto.de',
                    'https://blackvesto.de'
                ],
                'ExposeHeaders': [
                    'ETag',
                    'Content-Type',
                    'Content-Length',
                    'Content-Disposition'
                ],
                'MaxAgeSeconds': 3600
            }
        ]
    }
    
    try:
        # Check current CORS configuration
        print(f"Checking current CORS configuration for bucket: {bucket_name}")
        try:
            current_cors = s3_client.get_bucket_cors(Bucket=bucket_name)
            print("Current CORS configuration:")
            print(json.dumps(current_cors['CORSRules'], indent=2))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
                print("No CORS configuration currently set")
            else:
                print(f"Error checking CORS: {str(e)}")
        
        # Apply CORS configuration
        print("\nApplying CORS configuration...")
        response = s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        
        print(f"✅ CORS configuration applied successfully!")
        print(f"Response: {response['ResponseMetadata']['HTTPStatusCode']}")
        
        # Verify the configuration
        print("\nVerifying CORS configuration...")
        updated_cors = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("Updated CORS configuration:")
        print(json.dumps(updated_cors['CORSRules'], indent=2))
        
    except ClientError as e:
        print(f"❌ Error configuring CORS: {str(e)}")
        print(f"Error Code: {e.response['Error']['Code']}")
        print(f"Error Message: {e.response['Error']['Message']}")
        return False
    
    return True


def test_cors():
    """Instructions for testing CORS"""
    print("\n" + "="*50)
    print("TESTING CORS CONFIGURATION")
    print("="*50)
    print("\nTo test if CORS is working:")
    print("1. Open Chrome Developer Tools (F12)")
    print("2. Go to the Network tab")
    print("3. Try to preview a PDF document in your application")
    print("4. Look for the PDF request and check the response headers")
    print("5. You should see these headers:")
    print("   - Access-Control-Allow-Origin: <your-domain>")
    print("   - Access-Control-Allow-Methods: GET, HEAD")
    print("   - Access-Control-Expose-Headers: ...")
    print("\nIf you don't see these headers, CORS may not be working properly.")


if __name__ == "__main__":
    print("Hetzner Object Storage CORS Configuration")
    print("="*50)
    print(f"Endpoint: {settings.S3_ENDPOINT_URL}")
    print(f"Bucket: {settings.S3_BUCKET_NAME}")
    print(f"Region: {settings.S3_REGION}")
    print()
    
    if configure_cors():
        test_cors()
    else:
        print("\n❌ Failed to configure CORS")
        print("\nPossible issues:")
        print("1. Invalid credentials")
        print("2. Insufficient permissions")
        print("3. Bucket doesn't exist")
        print("4. Hetzner may have restrictions on CORS configuration")