# ================================
# CONFIGURATION (config.py)
# ================================

from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OAuth Settings
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: Optional[str] = None
    
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # AWS SES Email Settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "eu-central-1"  # Frankfurt region (näher zu Deutschland)
    AWS_SES_FROM_EMAIL: str = "noreply@yourapp.com"
    AWS_SES_FROM_NAME: str = "Your App Name"
    AWS_SES_REPLY_TO: Optional[str] = None
    AWS_SES_CONFIGURATION_SET: Optional[str] = None  # Für tracking/analytics
    
    # Hetzner S3-compatible Object Storage Settings
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_ENDPOINT_URL: str = "https://fsn1.your-objectstorage.com"  # Update with your Hetzner endpoint
    S3_BUCKET_NAME: str = "digitales-expose"  # Update with your actual bucket name
    S3_REGION: str = "fsn1"  # Hetzner region (fsn1 = Falkenstein, nbg1 = Nuremberg, hel1 = Helsinki)
    
    # Investagon API Settings
    INVESTAGON_API_URL: str = "https://api.investagon.com/api"
    INVESTAGON_ORGANIZATION_ID: Optional[str] = None
    INVESTAGON_API_KEY: Optional[str] = None
    ENABLE_AUTO_SYNC: bool = True  # Enable automatic hourly sync
    
    # OpenAI API Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ASSISTANT_ID: Optional[str] = None
    
    # Fallback SMTP (falls SES nicht verfügbar)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Email Templates
    EMAIL_TEMPLATES_DIR: str = "app/templates/email"
    
    # App Settings
    APP_NAME: str = "Enterprise Multi-Tenant App"
    BASE_URL: str = "https://yourapp.com"
    FRONTEND_URL: str = "https://app.yourapp.com"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Super Admin Settings
    SUPER_ADMIN_EMAIL: Optional[str] = None
    SUPER_ADMIN_PASSWORD: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

settings = settings()