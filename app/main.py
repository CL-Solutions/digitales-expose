# ================================
# MAIN APPLICATION (main.py) - UPDATED WITH RBAC ROUTER
# ================================

from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

# Core imports
from app.config import settings
from app.core.exceptions import AppException, AuthenticationError, AuthorizationError
from app.core.middleware import (
    TenantMiddleware, 
    AuditMiddleware, 
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    HealthCheckMiddleware,
    TimeoutMiddleware
)

# API Routes - UPDATED TO INCLUDE RBAC
from app.api.v1 import auth, users, tenants, properties, cities, exposes, admin, rbac, investagon

import logging
import uvicorn

# ================================
# LOGGING CONFIGURATION
# ================================

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# APPLICATION LIFECYCLE
# ================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    await startup_tasks()
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")
    await shutdown_tasks()

async def startup_tasks():
    """Tasks to run on application startup"""
    
    # Initialize database
    await initialize_database()
    
    # Create super admin if not exists
    await create_initial_super_admin()
    
    # Initialize email service
    await initialize_email_service()
    
    # Initialize and start background scheduler
    await initialize_background_scheduler()
    
    # Run health checks
    await run_startup_health_checks()

async def shutdown_tasks():
    """Tasks to run on application shutdown"""
    
    # Stop background scheduler
    await stop_background_scheduler()
    
    # Close database connections
    from app.core.database import engine
    engine.dispose()
    
    logger.info("Application shutdown complete")

async def initialize_database():
    """Initialize database connection and run migrations"""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("Database connection established")
        
        # Run Alembic migrations in production
        if not settings.DEBUG:
            await run_database_migrations()
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def run_database_migrations():
    """Run Alembic database migrations"""
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migrations completed")
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise

async def create_initial_super_admin():
    """Create initial super admin user if configured"""
    
    if not settings.SUPER_ADMIN_EMAIL or not settings.SUPER_ADMIN_PASSWORD:
        logger.info("No super admin configuration found, skipping creation")
        return
    
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.core.security import get_password_hash
        
        with SessionLocal() as db:
            # Check if super admin already exists
            existing_admin = db.query(User).filter(
                User.email == settings.SUPER_ADMIN_EMAIL,
                User.is_super_admin == True
            ).first()
            
            if existing_admin:
                logger.info("Super admin already exists")
                return
            
            # Create super admin
            super_admin = User(
                email=settings.SUPER_ADMIN_EMAIL,
                tenant_id=None,  # Super admins have no tenant
                auth_method="local",
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
                first_name="Super",
                last_name="Admin",
                is_super_admin=True,
                is_active=True,
                is_verified=True
            )
            
            db.add(super_admin)
            db.commit()
            
            logger.info(f"Super admin created: {settings.SUPER_ADMIN_EMAIL}")
            
    except Exception as e:
        logger.error(f"Super admin creation failed: {e}")
        # Don't raise - application should continue even if super admin creation fails

async def initialize_email_service():
    """Initialize and test email service"""
    try:
        from app.utils.email import email_service
        
        # Test email service configuration
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            logger.info("AWS SES email service initialized")
        elif settings.SMTP_HOST:
            logger.info("SMTP email service initialized")
        else:
            logger.warning("No email service configured")
            
    except Exception as e:
        logger.error(f"Email service initialization failed: {e}")

async def initialize_background_scheduler():
    """Initialize and start the background task scheduler"""
    try:
        from app.core.scheduler import scheduler, initialize_scheduler
        
        # Initialize with default tasks
        initialize_scheduler()
        
        # Start the scheduler
        await scheduler.start()
        
        logger.info("Background scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {e}")
        # Don't raise - app should work even without scheduler

async def stop_background_scheduler():
    """Stop the background task scheduler"""
    try:
        from app.core.scheduler import scheduler
        
        await scheduler.stop()
        
        logger.info("Background scheduler stopped")
        
    except Exception as e:
        logger.error(f"Error stopping background scheduler: {e}")

async def run_startup_health_checks():
    """Run health checks on startup"""
    try:
        # Database health check
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("All startup health checks passed")
        
    except Exception as e:
        logger.error(f"Startup health check failed: {e}")
        raise

# ================================
# FASTAPI APPLICATION
# ================================

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Enterprise Multi-Tenant API with OAuth Support",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# ================================
# MIDDLEWARE CONFIGURATION
# ================================

# Request Timeout (first - to prevent infinite loops)
app.add_middleware(TimeoutMiddleware, timeout_seconds=30)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting
app.add_middleware(RateLimitMiddleware, calls_per_minute=60)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

# Health Check Bypass (before audit middleware)
app.add_middleware(HealthCheckMiddleware)

# Audit Logging
app.add_middleware(AuditMiddleware)

# Tenant Context (last middleware)
app.add_middleware(TenantMiddleware)

# ================================
# EXCEPTION HANDLERS
# ================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handler für Application-spezifische Exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Handler für Authentication Errors"""
    return JSONResponse(
        status_code=401,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(AuthorizationError)
async def authz_exception_handler(request: Request, exc: AuthorizationError):
    """Handler für Authorization Errors"""
    return JSONResponse(
        status_code=403,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler für Standard HTTP Exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler für unbehandelte Exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if not settings.DEBUG else str(exc),
            "error_code": "INTERNAL_ERROR",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# ================================
# HEALTH CHECK ENDPOINTS
# ================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0"
    }

@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with dependencies"""
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception:
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Email service check
    try:
        from app.utils.email import email_service
        if email_service.ses_client or settings.SMTP_HOST:
            health_status["checks"]["email"] = "available"
        else:
            health_status["checks"]["email"] = "not_configured"
    except Exception:
        health_status["checks"]["email"] = "unavailable"
    
    return health_status

@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")

@app.get("/test-timeout", tags=["Test"])
async def test_timeout():
    """Test endpoint that takes 60 seconds - should timeout at 30s"""
    import asyncio
    await asyncio.sleep(60)  # Sleep for 60 seconds
    return {"message": "This should never be reached due to 30s timeout"}

# ================================
# API ROUTES - UPDATED TO INCLUDE RBAC
# ================================

# Authentication routes
app.include_router(
    auth.router, 
    prefix="/api/v1/auth", 
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Access denied"}
    }
)

# User management routes
app.include_router(
    users.router, 
    prefix="/api/v1/users", 
    tags=["User Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "User not found"}
    }
)

# RBAC routes - NEW ADDITION
app.include_router(
    rbac.router, 
    prefix="/api/v1/rbac", 
    tags=["Role & Permission Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Role or permission not found"}
    }
)

# Tenant management routes (Super Admin only)
app.include_router(
    tenants.router, 
    prefix="/api/v1/tenants", 
    tags=["Tenant Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Super admin access required"},
        404: {"description": "Tenant not found"}
    }
)

# Property management routes
app.include_router(
    properties.router, 
    prefix="/api/v1/properties", 
    tags=["Properties"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

# City management routes
app.include_router(
    cities.router,
    prefix="/api/v1/cities",
    tags=["Cities"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

# Expose management routes
app.include_router(
    exposes.router,
    prefix="/api/v1/exposes",
    tags=["Exposes"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

# Investagon sync routes
app.include_router(
    investagon.router,
    prefix="/api/v1/investagon",
    tags=["Investagon Integration"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        502: {"description": "External API error"}
    }
)

# Super Admin routes
app.include_router(
    admin.router, 
    prefix="/api/v1/admin", 
    tags=["Super Admin"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Super admin access required"}
    }
)

# ================================
# ROOT ENDPOINT
# ================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health",
        "available_endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users", 
            "rbac": "/api/v1/rbac",
            "tenants": "/api/v1/tenants",
            "properties": "/api/v1/properties",
            "cities": "/api/v1/cities",
            "exposes": "/api/v1/exposes",
            "investagon": "/api/v1/investagon",
            "admin": "/api/v1/admin"
        }
    }

# ================================
# CUSTOM OPENAPI SCHEMA
# ================================

def custom_openapi():
    """Custom OpenAPI schema with security definitions"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Enterprise Multi-Tenant API with OAuth Support",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token"
        }
    }
    
    # Add security to all routes (except public ones)
    for path, path_item in openapi_schema["paths"].items():
        # Skip public endpoints
        if path in ["/", "/health", "/health/detailed", "/ready", "/docs", "/redoc", "/openapi.json"]:
            continue
        
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                operation["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ================================
# DEVELOPMENT SERVER
# ================================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )