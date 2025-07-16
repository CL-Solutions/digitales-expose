# ================================
# S3 SERVICE (services/s3_service.py)
# ================================

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import UploadFile
from typing import Optional, Dict, Any, Tuple, BinaryIO
import uuid
import mimetypes
from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image
import logging

from app.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

class S3Service:
    """Service for handling S3-compatible operations for image storage (Hetzner Object Storage)"""
    
    def __init__(self):
        """Initialize S3 client for Hetzner Object Storage"""
        self.bucket_name = None
        self.s3_client = None
        
        # Check if S3 credentials are configured
        if not settings.S3_ACCESS_KEY_ID or not settings.S3_SECRET_ACCESS_KEY:
            logger.warning("S3 credentials not configured. Image upload functionality will be disabled.")
            return
            
        try:
            # Initialize S3 client with Hetzner endpoint
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION,
                endpoint_url=settings.S3_ENDPOINT_URL,
                config=boto3.session.Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'path'}  # Hetzner uses path-style addressing
                )
            )
            self.bucket_name = settings.S3_BUCKET_NAME
            
            # Verify bucket exists and we have access
            self._verify_bucket_access()
            
        except NoCredentialsError:
            logger.error("S3 credentials not found")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    def is_configured(self) -> bool:
        """Check if S3 service is properly configured"""
        return self.s3_client is not None
    
    def _verify_bucket_access(self):
        """Verify we can access the S3 bucket"""
        if not self.s3_client:
            return
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket not found: {self.bucket_name}")
                self.s3_client = None
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket: {self.bucket_name}")
                self.s3_client = None
            else:
                logger.error(f"Error accessing S3 bucket: {str(e)}")
                self.s3_client = None
    
    async def upload_image(
        self,
        file: UploadFile,
        folder: str,
        tenant_id: str,
        max_size_mb: Optional[int] = None,
        allowed_types: Optional[list] = None,
        resize_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload an image to S3-compatible storage
        
        Args:
            file: FastAPI UploadFile object
            folder: Folder path in S3 (e.g., 'properties', 'cities')
            tenant_id: Tenant ID for organization
            max_size_mb: Maximum file size in MB
            allowed_types: List of allowed MIME types
            resize_options: Dict with resize settings (width, height, quality)
        
        Returns:
            Dict with upload details including URL, size, dimensions
        """
        if not self.is_configured():
            raise AppException(
                status_code=503,
                detail="Image storage service is not available"
            )
            
        try:
            # Default allowed types
            if allowed_types is None:
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            
            # Validate file type
            if file.content_type not in allowed_types:
                raise AppException(
                    status_code=400,
                    detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
                )
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Validate file size
            # Use configured max size if not specified
            if max_size_mb is None:
                max_size_mb = settings.MAX_FILE_SIZE_MB
            
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                raise AppException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
                )
            
            # Process image if resize options provided
            image_data = content
            width, height = None, None
            
            if resize_options:
                image_data, (width, height) = await self._process_image(
                    content, 
                    file.content_type,
                    resize_options
                )
                file_size = len(image_data)
            else:
                # Get image dimensions without resizing
                try:
                    img = Image.open(BytesIO(content))
                    width, height = img.size
                except Exception:
                    # If we can't read dimensions, continue without them
                    pass
            
            # Generate unique filename
            file_extension = mimetypes.guess_extension(file.content_type) or '.jpg'
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create S3 key with tenant isolation
            s3_key = f"{tenant_id}/{folder}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{unique_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType=file.content_type,
                # Make the object publicly readable
                ACL='public-read',
                Metadata={
                    'tenant_id': tenant_id,
                    'original_filename': file.filename or 'unknown',
                    'uploaded_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate public URL for Hetzner Object Storage
            # Format: https://{bucket}.{endpoint}/{key}
            endpoint_base = settings.S3_ENDPOINT_URL.replace('https://', '')
            url = f"https://{self.bucket_name}.{endpoint_base}/{s3_key}"
            
            return {
                'url': url,
                's3_key': s3_key,
                'file_size': file_size,
                'mime_type': file.content_type,
                'width': width,
                'height': height,
                'original_filename': file.filename
            }
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to upload image"
            )
    
    async def _process_image(
        self,
        image_data: bytes,
        content_type: str,
        resize_options: Dict[str, Any]
    ) -> Tuple[bytes, Tuple[int, int]]:
        """Process image with resize options"""
        try:
            # Open image
            img = Image.open(BytesIO(image_data))
            
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # Resize if dimensions specified
            target_width = resize_options.get('width')
            target_height = resize_options.get('height')
            
            if target_width or target_height:
                # Calculate dimensions maintaining aspect ratio
                if target_width and target_height:
                    # Fit within box
                    img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                elif target_width:
                    # Resize by width
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                else:
                    # Resize by height
                    ratio = target_height / img.height
                    new_width = int(img.width * ratio)
                    img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = BytesIO()
            quality = resize_options.get('quality', 85)
            
            if content_type == 'image/png':
                img.save(output, format='PNG', optimize=True)
            else:
                img.save(output, format='JPEG', quality=quality, optimize=True)
            
            output.seek(0)
            return output.getvalue(), img.size
            
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to process image"
            )
    
    def delete_image(self, s3_key: str) -> bool:
        """
        Delete an image from S3-compatible storage
        
        Args:
            s3_key: The S3 key of the image to delete
        
        Returns:
            True if successful
        """
        if not self.is_configured():
            logger.warning("S3 service not configured. Cannot delete image.")
            return False
            
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted image from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image from S3: {str(e)}")
            return False
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary private access
        
        Args:
            s3_key: The S3 key of the object
            expiration: URL expiration time in seconds
        
        Returns:
            Presigned URL or None if service not configured
        """
        if not self.is_configured():
            return None
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
    
    def get_image_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about an image in S3
        
        Args:
            s3_key: The S3 key of the image
        
        Returns:
            Dict with image metadata or None
        """
        if not self.is_configured():
            return None
            
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'size': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                logger.error(f"Failed to get image info: {str(e)}")
                return None
    
    async def upload_image_from_bytes(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        folder: str,
        tenant_id: str,
        resize_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload image data directly from bytes (for importing from external sources)
        
        Args:
            file_data: Raw image bytes
            filename: Filename for the upload
            content_type: MIME type of the image
            folder: Folder path in S3
            tenant_id: Tenant ID for organization
            resize_options: Dict with resize settings
        
        Returns:
            Dict with upload details including URL, size, dimensions
        """
        if not self.is_configured():
            raise AppException(
                status_code=503,
                detail="Image storage service is not available"
            )
            
        try:
            # Process image if resize options provided
            image_data = file_data
            width, height = None, None
            file_size = len(file_data)
            
            if resize_options:
                image_data, (width, height) = await self._process_image(
                    file_data, 
                    content_type,
                    resize_options
                )
                file_size = len(image_data)
            else:
                # Get image dimensions without resizing
                try:
                    img = Image.open(BytesIO(file_data))
                    width, height = img.size
                except Exception:
                    pass
            
            # Generate unique filename
            file_extension = mimetypes.guess_extension(content_type) or '.jpg'
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create S3 key with tenant isolation
            s3_key = f"{tenant_id}/{folder}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{unique_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
                ACL='public-read',
                Metadata={
                    'tenant_id': tenant_id,
                    'original_filename': filename,
                    'uploaded_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate public URL
            endpoint_base = settings.S3_ENDPOINT_URL.replace('https://', '')
            url = f"https://{self.bucket_name}.{endpoint_base}/{s3_key}"
            
            return {
                'url': url,
                's3_key': s3_key,
                'file_size': file_size,
                'mime_type': content_type,
                'width': width,
                'height': height,
                'original_filename': filename
            }
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload image from bytes: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to upload image"
            )
    
    async def upload_project_image(
        self,
        file: BinaryIO,
        filename: str,
        tenant_id: str,
        project_id: str,
        image_type: str
    ) -> str:
        """Upload project image to S3"""
        try:
            # Read file data
            file_data = file.read()
            
            # Create folder path
            folder = f"projects/{project_id}/{image_type}"
            
            # Determine max dimensions based on image type
            if image_type == 'floor_plan':
                max_width, max_height = 2400, 2400  # Higher resolution for floor plans
            elif image_type in ['exterior', 'common_area']:
                max_width, max_height = 1920, 1920  # Full resolution for main images
            else:
                max_width, max_height = 1600, 1600  # Standard resolution
            
            # Upload using existing method
            result = await self.upload_image_from_bytes(
                file_data=file_data,
                filename=filename,
                tenant_id=tenant_id,
                folder=folder,
                max_width=max_width,
                max_height=max_height
            )
            
            return result['url']
            
        except Exception as e:
            logger.error(f"Failed to upload project image: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to upload project image"
            )
    
    async def upload_file(
        self,
        file: UploadFile,
        folder: str,
        tenant_id: str,
        max_size_mb: Optional[int] = None,
        allowed_types: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Upload a general file to S3-compatible storage (documents, PDFs, etc)
        
        Args:
            file: FastAPI UploadFile object
            folder: Folder path in S3 (e.g., 'documents/projects')
            tenant_id: Tenant ID for organization
            max_size_mb: Maximum file size in MB
            allowed_types: List of allowed MIME types
        
        Returns:
            Dict with upload details including URL and size
        """
        if not self.is_configured():
            raise AppException(
                status_code=503,
                detail="File storage service is not available"
            )
            
        try:
            # Default allowed types for documents
            if allowed_types is None:
                allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            
            # Validate file type
            if file.content_type not in allowed_types:
                raise AppException(
                    status_code=400,
                    detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
                )
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Validate file size
            if max_size_mb is None:
                max_size_mb = settings.MAX_FILE_SIZE_MB
            
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                raise AppException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
                )
            
            # Generate unique filename
            file_extension = mimetypes.guess_extension(file.content_type) or '.pdf'
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create S3 key with tenant isolation
            s3_key = f"{tenant_id}/{folder}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{unique_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type,
                # Make the object publicly readable
                ACL='public-read',
                Metadata={
                    'tenant_id': tenant_id,
                    'original_filename': file.filename or 'unknown',
                    'uploaded_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate public URL for Hetzner Object Storage
            endpoint_base = settings.S3_ENDPOINT_URL.replace('https://', '')
            url = f"https://{self.bucket_name}.{endpoint_base}/{s3_key}"
            
            return {
                'url': url,
                's3_key': s3_key,
                's3_bucket': self.bucket_name,
                'file_size': file_size,
                'mime_type': file.content_type,
                'original_filename': file.filename
            }
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to upload file"
            )
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3-compatible storage
        
        Args:
            s3_key: The S3 key of the file to delete
        
        Returns:
            True if successful
        """
        if not self.is_configured():
            logger.warning("S3 service not configured. Cannot delete file.")
            return False
            
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted file from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            return False

# Create singleton instance - will initialize when first imported
s3_service = None

def get_s3_service():
    """Get or create S3 service instance"""
    global s3_service
    if s3_service is None:
        s3_service = S3Service()
    return s3_service