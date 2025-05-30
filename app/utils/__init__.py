# ================================
# UTILS PACKAGE INITIALIZATION (utils/__init__.py)
# ================================

"""
Utils Package

Utility modules for enterprise multi-tenant application including:
- Audit logging and compliance tracking
- Email services with AWS SES integration  
- OAuth client implementations
- Security and encryption utilities
- File and data processing helpers
"""

# Import core utilities
from app.utils.audit import AuditLogger, audit_action, audit_context
from app.utils.email import email_service
from app.utils.oauth_clients import (
    MicrosoftEnterpriseClient,
    GoogleEnterpriseClient, 
    GenericOIDCClient,
    OAuthClientFactory
)

# ================================
# AUDIT LOGGING
# ================================

# Default audit logger instance for application-wide use
default_audit_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    """Get the default audit logger instance"""
    return default_audit_logger

# ================================
# EMAIL SERVICES
# ================================

def get_email_service():
    """Get the configured email service instance"""
    return email_service

# ================================
# OAUTH CLIENTS
# ================================

def create_oauth_client(provider: str, **kwargs):
    """
    Factory function to create OAuth clients
    
    Args:
        provider: OAuth provider name ('microsoft', 'google', 'oidc')
        **kwargs: Provider-specific configuration
    
    Returns:
        Configured OAuth client instance
    """
    return OAuthClientFactory.create_client(provider, **kwargs)

def get_supported_oauth_providers() -> list[str]:
    """Get list of supported OAuth providers"""
    return OAuthClientFactory.get_supported_providers()

# ================================
# SECURITY UTILITIES
# ================================

import hashlib
import secrets
import base64
from typing import Union

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    
    Args:
        length: Length of the token in bytes
    
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)

def generate_api_key(prefix: str = "api", length: int = 32) -> str:
    """
    Generate an API key with prefix
    
    Args:
        prefix: Prefix for the API key
        length: Length of the random part
    
    Returns:
        Formatted API key string
    """
    random_part = secrets.token_urlsafe(length)
    return f"{prefix}_{random_part}"

def hash_sensitive_data(data: str, salt: str = None) -> tuple[str, str]:
    """
    Hash sensitive data with salt for secure storage
    
    Args:
        data: Data to hash
        salt: Optional salt (will generate if not provided)
    
    Returns:
        Tuple of (hashed_data, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use SHA-256 with salt
    hash_obj = hashlib.sha256()
    hash_obj.update((data + salt).encode('utf-8'))
    hashed_data = hash_obj.hexdigest()
    
    return hashed_data, salt

def verify_hashed_data(data: str, hashed_data: str, salt: str) -> bool:
    """
    Verify data against its hash
    
    Args:
        data: Original data to verify
        hashed_data: Previously hashed data
        salt: Salt used in original hash
    
    Returns:
        True if data matches hash
    """
    computed_hash, _ = hash_sensitive_data(data, salt)
    return computed_hash == hashed_data

# ================================
# DATA PROCESSING UTILITIES
# ================================

import json
from datetime import datetime, date
from decimal import Decimal
import uuid

class EnhancedJSONEncoder(json.JSONEncoder):
    """
    Enhanced JSON encoder that handles common Python types
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

def safe_json_dumps(data, **kwargs) -> str:
    """
    Safely serialize data to JSON with enhanced type support
    
    Args:
        data: Data to serialize
        **kwargs: Additional json.dumps arguments
    
    Returns:
        JSON string
    """
    return json.dumps(data, cls=EnhancedJSONEncoder, **kwargs)

def truncate_string(text: str, max_length: int = 255, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Ensure it's not empty
    if not filename:
        filename = f"file_{generate_secure_token(8)}"
    
    return filename

# ================================
# VALIDATION UTILITIES
# ================================

import re
from typing import Optional

def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email format is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_domain(domain: str) -> bool:
    """
    Validate domain name format
    
    Args:
        domain: Domain name to validate
    
    Returns:
        True if domain format is valid
    """
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'
    return bool(re.match(pattern, domain)) and len(domain) <= 253

def validate_slug(slug: str) -> bool:
    """
    Validate URL slug format
    
    Args:
        slug: Slug to validate
    
    Returns:
        True if slug format is valid
    """
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*'
    return bool(re.match(pattern, slug)) and 2 <= len(slug) <= 63

def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format
    
    Args:
        uuid_string: UUID string to validate
    
    Returns:
        True if UUID format is valid
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6)
    
    Args:
        ip: IP address to validate
    
    Returns:
        True if IP address is valid
    """
    try:
        from ipaddress import ip_address
        ip_address(ip)
        return True
    except ValueError:
        return False

# ================================
# RATE LIMITING UTILITIES
# ================================

from collections import defaultdict
from datetime import timedelta
import time

class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for development/testing
    For production, use Redis-based rate limiting
    """
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is allowed within rate limit
        
        Args:
            key: Unique identifier for rate limiting (e.g., user_id, ip_address)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if request is allowed
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Record this request
        self.requests[key].append(current_time)
        return True
    
    def get_remaining_requests(self, key: str, max_requests: int, window_seconds: int) -> int:
        """
        Get remaining requests in current window
        
        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            Number of remaining requests
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        return max(0, max_requests - len(self.requests[key]))

# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()

def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

# ================================
# CACHING UTILITIES
# ================================

from functools import wraps
import pickle
import hashlib

class SimpleCache:
    """
    Simple in-memory cache implementation
    For production, use Redis or Memcached
    """
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        self.cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        current_time = time.time()
        expired_keys = [
            key for key, (value, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)

# Global cache instance
_cache = SimpleCache()

def get_cache() -> SimpleCache:
    """Get the global cache instance"""
    return _cache

def cache_result(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    
    Usage:
        @cache_result(ttl=600, key_prefix="user")
        def get_user_data(user_id):
            return expensive_operation(user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{key_prefix}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = _cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# ================================
# FILE UTILITIES
# ================================

import os
import mimetypes
from pathlib import Path

def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename
    
    Args:
        filename: Name of the file
    
    Returns:
        File extension (without dot)
    """
    return Path(filename).suffix.lstrip('.')

def get_mime_type(filename: str) -> str:
    """
    Get MIME type for a file
    
    Args:
        filename: Name of the file
    
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def is_allowed_file_type(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Check if file type is allowed
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (without dots)
    
    Returns:
        True if file type is allowed
    """
    extension = get_file_extension(filename).lower()
    return extension in [ext.lower() for ext in allowed_extensions]

# ================================
# DATE/TIME UTILITIES
# ================================

from datetime import timezone

def utc_now() -> datetime:
    """Get current UTC datetime with timezone info"""
    return datetime.now(timezone.utc)

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Format datetime for display
    
    Args:
        dt: Datetime object
        format_str: Format string
    
    Returns:
        Formatted datetime string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(format_str)

def parse_iso_datetime(datetime_str: str) -> datetime:
    """
    Parse ISO format datetime string
    
    Args:
        datetime_str: ISO format datetime string
    
    Returns:
        Datetime object
    """
    # Handle various ISO formats
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'
    
    return datetime.fromisoformat(datetime_str)

def days_ago(days: int) -> datetime:
    """
    Get datetime N days ago
    
    Args:
        days: Number of days ago
    
    Returns:
        Datetime object
    """
    return utc_now() - timedelta(days=days)

def is_recent(dt: datetime, hours: int = 24) -> bool:
    """
    Check if datetime is within recent time window
    
    Args:
        dt: Datetime to check
        hours: Time window in hours
    
    Returns:
        True if datetime is recent
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    cutoff = utc_now() - timedelta(hours=hours)
    return dt > cutoff

# ================================
# ENVIRONMENT UTILITIES
# ================================

def is_production() -> bool:
    """Check if running in production environment"""
    from app.config import settings
    return not settings.DEBUG

def is_development() -> bool:
    """Check if running in development environment"""
    from app.config import settings
    return settings.DEBUG

def get_app_version() -> str:
    """Get application version"""
    try:
        # Try to read from version file or package
        return "1.0.0"  # Default version
    except:
        return "unknown"

# ================================
# LOGGING UTILITIES
# ================================

import logging

def setup_logging(level: str = "INFO") -> None:
    """
    Setup application logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log') if is_production() else logging.NullHandler()
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    Get logger with standard configuration
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# ================================
# HEALTH CHECK UTILITIES
# ================================

def check_database_health() -> dict:
    """
    Check database connectivity and health
    
    Returns:
        Health check results
    """
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {"status": "healthy", "latency_ms": 0}  # Would measure actual latency
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def check_email_service_health() -> dict:
    """
    Check email service health
    
    Returns:
        Health check results
    """
    try:
        # Check if email service is configured
        if email_service.ses_client:
            return {"status": "healthy", "provider": "aws_ses"}
        elif email_service.smtp_host:
            return {"status": "healthy", "provider": "smtp"}
        else:
            return {"status": "not_configured", "provider": "none"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def run_health_checks() -> dict:
    """
    Run all health checks
    
    Returns:
        Complete health check results
    """
    return {
        "database": check_database_health(),
        "email_service": check_email_service_health(),
        "timestamp": utc_now().isoformat(),
        "version": get_app_version()
    }

# ================================
# EXPORTS
# ================================

__all__ = [
    # Audit logging
    "AuditLogger", "audit_action", "audit_context", "get_audit_logger",
    
    # Email services
    "email_service", "get_email_service",
    
    # OAuth clients
    "MicrosoftEnterpriseClient", "GoogleEnterpriseClient", "GenericOIDCClient",
    "OAuthClientFactory", "create_oauth_client", "get_supported_oauth_providers",
    
    # Security utilities
    "generate_secure_token", "generate_api_key", "hash_sensitive_data", "verify_hashed_data",
    
    # Data processing
    "EnhancedJSONEncoder", "safe_json_dumps", "truncate_string", "sanitize_filename",
    
    # Validation
    "validate_email", "validate_domain", "validate_slug", "validate_uuid", "validate_ip_address",
    
    # Rate limiting
    "InMemoryRateLimiter", "get_rate_limiter",
    
    # Caching
    "SimpleCache", "get_cache", "cache_result",
    
    # File utilities
    "get_file_extension", "get_mime_type", "format_file_size", "is_allowed_file_type",
    
    # Date/time utilities
    "utc_now", "format_datetime", "parse_iso_datetime", "days_ago", "is_recent",
    
    # Environment utilities
    "is_production", "is_development", "get_app_version",
    
    # Logging utilities
    "setup_logging", "get_logger",
    
    # Health checks
    "check_database_health", "check_email_service_health", "run_health_checks"
]