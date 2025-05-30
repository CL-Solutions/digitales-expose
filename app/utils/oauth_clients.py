# ================================
# OAUTH CLIENTS UTILITY (utils/oauth_clients.py)
# ================================

import httpx
import secrets
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class MicrosoftEnterpriseClient:
    """Microsoft Entra ID OAuth Client für Enterprise Integration"""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str = None,
        azure_tenant_id: str = None,
        discovery_endpoint: str = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.azure_tenant_id = azure_tenant_id
        self.discovery_endpoint = discovery_endpoint or f"https://login.microsoftonline.com/{azure_tenant_id}/v2.0/.well-known/openid_configuration"
        self.base_url = f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/v2.0"
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Generiert Authorization URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid profile email User.Read",
            "response_mode": "query",
            "state": state or secrets.token_urlsafe(32)
        }
        
        return f"{self.base_url}/authorize?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Tauscht Authorization Code gegen Tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "scope": "openid profile email User.Read"
        }
        
        if redirect_uri:
            data["redirect_uri"] = redirect_uri
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Microsoft token exchange failed: {response.text}")
                raise Exception(f"Token exchange failed: {response.text}")
            
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresht Access Token"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Microsoft token refresh failed: {response.text}")
                raise Exception(f"Token refresh failed: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Holt User-Info von Microsoft Graph"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.graph_url}/me",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Microsoft user info failed: {response.text}")
                raise Exception(f"User info request failed: {response.text}")
            
            return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """Widerruft Token"""
        # Microsoft doesn't have a standard revoke endpoint
        # Token expiration is handled automatically
        return True
    
    async def get_discovery_document(self) -> Dict[str, Any]:
        """Holt OpenID Connect Discovery Document"""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.discovery_endpoint)
            
            if response.status_code != 200:
                logger.error(f"Microsoft discovery failed: {response.text}")
                raise Exception(f"Discovery request failed: {response.text}")
            
            return response.json()

class GoogleEnterpriseClient:
    """Google Workspace OAuth Client für Enterprise Integration"""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str = None,
        discovery_endpoint: str = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.discovery_endpoint = discovery_endpoint or "https://accounts.google.com/.well-known/openid_configuration"
        self.base_url = "https://oauth2.googleapis.com"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Generiert Authorization URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "access_type": "offline",
            "prompt": "consent",
            "state": state or secrets.token_urlsafe(32)
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Tauscht Authorization Code gegen Tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        if redirect_uri:
            data["redirect_uri"] = redirect_uri
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                raise Exception(f"Token exchange failed: {response.text}")
            
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresht Access Token"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Google token refresh failed: {response.text}")
                raise Exception(f"Token refresh failed: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Holt User-Info von Google"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Google user info failed: {response.text}")
                raise Exception(f"User info request failed: {response.text}")
            
            return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """Widerruft Token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://oauth2.googleapis.com/revoke?token={token}"
            )
            
            return response.status_code == 200
    
    async def get_discovery_document(self) -> Dict[str, Any]:
        """Holt OpenID Connect Discovery Document"""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.discovery_endpoint)
            
            if response.status_code != 200:
                logger.error(f"Google discovery failed: {response.text}")
                raise Exception(f"Discovery request failed: {response.text}")
            
            return response.json()

class GenericOIDCClient:
    """Generic OpenID Connect Client für andere Provider"""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str,
        discovery_endpoint: str,
        provider_name: str = "oidc"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.discovery_endpoint = discovery_endpoint
        self.provider_name = provider_name
        self._discovery_cache = None
        
    async def _get_discovery_document(self) -> Dict[str, Any]:
        """Cached Discovery Document"""
        if not self._discovery_cache:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.discovery_endpoint)
                
                if response.status_code != 200:
                    raise Exception(f"Discovery request failed: {response.text}")
                
                self._discovery_cache = response.json()
        
        return self._discovery_cache
    
    async def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Generiert Authorization URL"""
        discovery = await self._get_discovery_document()
        auth_endpoint = discovery.get("authorization_endpoint")
        
        if not auth_endpoint:
            raise Exception("Authorization endpoint not found in discovery document")
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state or secrets.token_urlsafe(32)
        }
        
        return f"{auth_endpoint}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Tauscht Authorization Code gegen Tokens"""
        discovery = await self._get_discovery_document()
        token_endpoint = discovery.get("token_endpoint")
        
        if not token_endpoint:
            raise Exception("Token endpoint not found in discovery document")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        if redirect_uri:
            data["redirect_uri"] = redirect_uri
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"{self.provider_name} token exchange failed: {response.text}")
                raise Exception(f"Token exchange failed: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Holt User-Info vom Provider"""
        discovery = await self._get_discovery_document()
        userinfo_endpoint = discovery.get("userinfo_endpoint")
        
        if not userinfo_endpoint:
            raise Exception("Userinfo endpoint not found in discovery document")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_endpoint,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"{self.provider_name} user info failed: {response.text}")
                raise Exception(f"User info request failed: {response.text}")
            
            return response.json()

# ================================
# OAUTH CLIENT FACTORY
# ================================

class OAuthClientFactory:
    """Factory für OAuth Clients"""
    
    @staticmethod
    def create_client(provider: str, **kwargs):
        """Erstellt OAuth Client basierend auf Provider"""
        
        if provider.lower() == "microsoft":
            return MicrosoftEnterpriseClient(**kwargs)
        
        elif provider.lower() == "google":
            return GoogleEnterpriseClient(**kwargs)
        
        elif provider.lower() in ["oidc", "generic"]:
            return GenericOIDCClient(**kwargs)
        
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
    
    @staticmethod
    def get_supported_providers() -> list:
        """Liste unterstützter OAuth Provider"""
        return ["microsoft", "google", "oidc"]