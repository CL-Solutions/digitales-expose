# ================================
# MIDDLEWARE (core/middleware.py)
# ================================

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, set_tenant_context
from app.models.user import User
from app.core.security import verify_token
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware für automatische Tenant-Isolation"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Request ID für Logging
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Database Session
        db = SessionLocal()
        request.state.db = db
        
        try:
            # Tenant-Kontext aus JWT Token extrahieren
            tenant_id = await self._extract_tenant_from_request(request, db)
            request.state.tenant_id = tenant_id
            
            # RLS Kontext setzen
            if tenant_id:
                set_tenant_context(db, tenant_id)
            
            response = await call_next(request)
            
            # Response Headers
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def _extract_tenant_from_request(self, request: Request, db: Session) -> Optional[uuid.UUID]:
        """Extrahiert Tenant-ID aus Authorization Header"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # User aus DB laden für Tenant-Info
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Super-Admin Impersonation Check
        impersonated_tenant = payload.get("impersonated_tenant_id")
        if user.is_super_admin and impersonated_tenant:
            return uuid.UUID(impersonated_tenant)
        
        return user.tenant_id

class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware für Audit-Logging"""
    
    async def dispatch(self, request: Request, call_next):
        # Pre-request logging
        await self._log_request(request)
        
        response = await call_next(request)
        
        # Post-request logging
        await self._log_response(request, response)
        
        return response
    
    async def _log_request(self, request: Request):
        """Loggt eingehende Requests"""
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("User-Agent"),
                "ip_address": request.client.host if request.client else None
            }
        )
    
    async def _log_response(self, request: Request, response: Response):
        """Loggt ausgehende Responses"""
        logger.info(
            f"Response: {response.status_code}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "status_code": response.status_code,
                "process_time": response.headers.get("X-Process-Time")
            }
        )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware für Security Headers"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security Headers hinzufügen
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS für HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Einfaches Rate Limiting Middleware"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}  # In production: Redis verwenden
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Cleanup alte Einträge
        self._cleanup_old_requests(current_time)
        
        # Rate Limit Check
        if self._is_rate_limited(client_ip, current_time):
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Request tracking
        self._track_request(client_ip, current_time)
        
        return await call_next(request)
    
    def _cleanup_old_requests(self, current_time: float):
        """Entfernt alte Request-Tracking Einträge"""
        cutoff_time = current_time - 60  # 1 Minute zurück
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip] 
                if req_time > cutoff_time
            ]
            if not self.requests[ip]:
                del self.requests[ip]
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Prüft ob Client rate-limited ist"""
        if client_ip not in self.requests:
            return False
        
        recent_requests = len(self.requests[client_ip])
        return recent_requests >= self.calls_per_minute
    
    def _track_request(self, client_ip: str, current_time: float):
        """Tracked neuen Request"""
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)

class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware für Health Check Bypass"""
    
    async def dispatch(self, request: Request, call_next):
        # Health Check Endpoints bypassen normale Middleware
        if request.url.path in ["/health", "/metrics", "/ready"]:
            # Minimale Verarbeitung für Health Checks
            response = await call_next(request)
            return response
        
        return await call_next(request)