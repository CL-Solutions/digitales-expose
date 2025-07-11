# ================================
# OAUTH SERVICE (services/oauth_service.py)
# ================================

from sqlalchemy.orm import Session
from app.models.user import User, OAuthToken
from app.models.tenant import TenantIdentityProvider
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from app.services.auth_service import AuthService
from app.utils.oauth_clients import MicrosoftEnterpriseClient, GoogleEnterpriseClient
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

class EnterpriseOAuthService:
    """OAuth Service für Enterprise-Integration mit Tenant-spezifischer Konfiguration"""
    
    @staticmethod
    async def get_tenant_oauth_config(
        db: Session, 
        tenant_id: uuid.UUID, 
        provider: str
    ) -> TenantIdentityProvider:
        """Lädt die Tenant-spezifische OAuth-Konfiguration"""
        
        config = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == tenant_id,
            TenantIdentityProvider.provider == provider,
            TenantIdentityProvider.is_active == True
        ).first()
        
        if not config:
            raise AppException(
                f"OAuth provider {provider} not configured for this tenant", 
                400, 
                "PROVIDER_NOT_CONFIGURED"
            )
        
        return config
    
    @staticmethod
    async def authenticate_microsoft_enterprise_user(
        db: Session, 
        auth_code: str, 
        tenant_id: uuid.UUID,
        ip_address: str = None,
        user_agent: str = None
    ) -> tuple[User, dict]:
        """Authentifiziert User über Microsoft Entra ID (Tenant-spezifisch)"""
        
        # Get tenant-specific Microsoft configuration
        oauth_config = await EnterpriseOAuthService.get_tenant_oauth_config(
            db, tenant_id, "microsoft"
        )
        
        # Create tenant-specific Microsoft client
        microsoft_client = MicrosoftEnterpriseClient(
            client_id=oauth_config.client_id,
            client_secret=EnterpriseOAuthService._decrypt_secret(oauth_config.client_secret_hash),
            azure_tenant_id=oauth_config.azure_tenant_id,
            discovery_endpoint=oauth_config.discovery_endpoint
        )
        
        try:
            # Exchange code for tokens
            token_data = await microsoft_client.exchange_code_for_tokens(auth_code)
            
            # Get user info from Microsoft Graph
            user_info = await microsoft_client.get_user_info(token_data["access_token"])
            
            # Apply user attribute mapping
            mapped_user_info = EnterpriseOAuthService._apply_user_mapping(
                user_info, oauth_config.user_attribute_mapping
            )
            
            # Domain validation (if configured)
            if oauth_config.allowed_domains:
                user_domain = mapped_user_info["email"].split("@")[1]
                if user_domain not in oauth_config.allowed_domains:
                    audit_logger.log_auth_event(
                        db, "OAUTH_LOGIN_FAILED", None, tenant_id,
                        {
                            "reason": "domain_not_allowed", 
                            "email": mapped_user_info["email"], 
                            "domain": user_domain,
                            "ip": ip_address
                        }
                    )
                    raise AppException("Domain not allowed for this tenant", 403, "DOMAIN_NOT_ALLOWED")
            
            # Find or create user
            user = await EnterpriseOAuthService._find_or_create_enterprise_oauth_user(
                db, mapped_user_info, "microsoft", oauth_config, tenant_id
            )
            
            # Store/update OAuth tokens
            await EnterpriseOAuthService._store_oauth_tokens(db, user, "microsoft", token_data)
            
            # Create session tokens
            tokens = await AuthService._create_user_session(db, user, ip_address)
            
            audit_logger.log_auth_event(
                db, "OAUTH_LOGIN_SUCCESS", user.id, tenant_id,
                {
                    "provider": "microsoft", 
                    "azure_tenant_id": oauth_config.azure_tenant_id
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return user, tokens
            
        except Exception as e:
            audit_logger.log_auth_event(
                db, "OAUTH_LOGIN_FAILED", None, tenant_id,
                {
                    "provider": "microsoft",
                    "error": str(e)
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise
    
    @staticmethod
    async def authenticate_google_enterprise_user(
        db: Session, 
        auth_code: str, 
        tenant_id: uuid.UUID,
        ip_address: str = None,
        user_agent: str = None
    ) -> tuple[User, dict]:
        """Authentifiziert User über Google Workspace (Tenant-spezifisch)"""
        
        # Get tenant-specific Google configuration
        oauth_config = await EnterpriseOAuthService.get_tenant_oauth_config(
            db, tenant_id, "google"
        )
        
        # Create tenant-specific Google client
        google_client = GoogleEnterpriseClient(
            client_id=oauth_config.client_id,
            client_secret=EnterpriseOAuthService._decrypt_secret(oauth_config.client_secret_hash),
            discovery_endpoint=oauth_config.discovery_endpoint
        )
        
        try:
            # Exchange code for tokens
            token_data = await google_client.exchange_code_for_tokens(auth_code)
            
            # Get user info from Google
            user_info = await google_client.get_user_info(token_data["access_token"])
            
            # Apply user attribute mapping
            mapped_user_info = EnterpriseOAuthService._apply_user_mapping(
                user_info, oauth_config.user_attribute_mapping
            )
            
            # Domain validation (if configured)
            if oauth_config.allowed_domains:
                user_domain = mapped_user_info["email"].split("@")[1]
                if user_domain not in oauth_config.allowed_domains:
                    audit_logger.log_auth_event(
                        db, "OAUTH_LOGIN_FAILED", None, tenant_id,
                        {
                            "reason": "domain_not_allowed", 
                            "email": mapped_user_info["email"], 
                            "domain": user_domain,
                            "ip": ip_address
                        }
                    )
                    raise AppException("Domain not allowed for this tenant", 403, "DOMAIN_NOT_ALLOWED")
            
            # Find or create user
            user = await EnterpriseOAuthService._find_or_create_enterprise_oauth_user(
                db, mapped_user_info, "google", oauth_config, tenant_id
            )
            
            # Store/update OAuth tokens
            await EnterpriseOAuthService._store_oauth_tokens(db, user, "google", token_data)
            
            # Create session tokens
            tokens = await AuthService._create_user_session(db, user, ip_address)
            
            audit_logger.log_auth_event(
                db, "OAUTH_LOGIN_SUCCESS", user.id, tenant_id,
                {
                    "provider": "google"
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return user, tokens
            
        except Exception as e:
            audit_logger.log_auth_event(
                db, "OAUTH_LOGIN_FAILED", None, tenant_id,
                {
                    "provider": "google",
                    "error": str(e)
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise
    
    @staticmethod
    async def get_oauth_authorization_url(
        db: Session,
        tenant_id: uuid.UUID,
        provider: str,
        redirect_uri: str,
        state: str = None
    ) -> str:
        """Generiert OAuth Authorization URL für Tenant"""
        
        oauth_config = await EnterpriseOAuthService.get_tenant_oauth_config(
            db, tenant_id, provider
        )
        
        if provider == "microsoft":
            client = MicrosoftEnterpriseClient(
                client_id=oauth_config.client_id,
                azure_tenant_id=oauth_config.azure_tenant_id
            )
        elif provider == "google":
            client = GoogleEnterpriseClient(
                client_id=oauth_config.client_id
            )
        else:
            raise AppException(f"Unsupported OAuth provider: {provider}", 400, "UNSUPPORTED_PROVIDER")
        
        return client.get_authorization_url(redirect_uri, state)
    
    @staticmethod
    def _apply_user_mapping(user_info: dict, mapping_config: dict) -> dict:
        """Wendet Tenant-spezifisches User-Attribute-Mapping an"""
        
        # Default mapping für verschiedene Provider
        default_mappings = {
            "microsoft": {
                "email": "mail",
                "first_name": "givenName", 
                "last_name": "surname",
                "user_id": "id",
                "display_name": "displayName"
            },
            "google": {
                "email": "email",
                "first_name": "given_name",
                "last_name": "family_name", 
                "user_id": "sub",
                "display_name": "name"
            }
        }
        
        # Provider-spezifisches Default-Mapping
        provider = "microsoft" if "givenName" in user_info else "google"
        default_mapping = default_mappings.get(provider, {})
        
        # Merge mit tenant-spezifischem Mapping
        mapping = {**default_mapping, **mapping_config}
        
        mapped_info = {}
        for our_field, provider_field in mapping.items():
            # Handle nested fields (z.B. "address.country")
            value = user_info
            for field_part in provider_field.split("."):
                value = value.get(field_part) if isinstance(value, dict) else None
                if value is None:
                    break
            mapped_info[our_field] = value
        
        # Fallback für required fields
        if not mapped_info.get("email"):
            mapped_info["email"] = user_info.get("userPrincipalName") or user_info.get("email")
        
        return mapped_info
    
    @staticmethod
    async def _find_or_create_enterprise_oauth_user(
        db: Session,
        user_info: dict,
        provider: str,
        oauth_config: TenantIdentityProvider,
        tenant_id: uuid.UUID
    ) -> User:
        """Findet oder erstellt OAuth User mit Enterprise-Einstellungen"""
        
        email = user_info["email"]
        if not email:
            raise AppException("No email address provided by OAuth provider", 400, "NO_EMAIL")
        
        user = db.query(User).filter(
            User.email == email,
            User.tenant_id == tenant_id
        ).first()
        
        if user:
            # Update existing user
            if user.auth_method != provider:
                raise AppException(
                    f"User exists with different auth method: {user.auth_method}",
                    400,
                    "AUTH_METHOD_CONFLICT"
                )
            
            # Update OAuth provider ID and last login
            user.oauth_provider_id = user_info.get("user_id")
            user.last_login_at = datetime.utcnow()
            
            # Update profile information if provided
            if user_info.get("first_name"):
                user.first_name = user_info["first_name"]