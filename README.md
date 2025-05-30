# Enterprise Multi-Tenant System

A production-ready, enterprise-grade multi-tenant application with OAuth integration, comprehensive RBAC, and super admin capabilities.

## 🏗️ Architecture Overview

This system implements a **row-level multi-tenant architecture** with complete tenant isolation, OAuth integration for Microsoft Entra ID and Google Workspace, and a comprehensive role-based access control system.

### Key Features

- **Multi-Tenant Architecture**: Complete tenant isolation with row-level security
- **OAuth Integration**: Microsoft Entra ID and Google Workspace per-tenant configuration
- **Role-Based Access Control (RBAC)**: Granular permissions and role management
- **Super Admin System**: Cross-tenant administration with impersonation capabilities
- **Audit Logging**: Comprehensive tracking of all system activities
- **Enterprise Security**: Account lockouts, unified error messages, threat detection
- **AWS SES Integration**: Professional email delivery with fallback to SMTP
- **Business Logic APIs**: Projects and documents management as examples

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI App + Startup
│   ├── config.py                  # Environment Configuration
│   ├── dependencies.py            # FastAPI Dependencies & Permissions
│   │
│   ├── core/                      # Core Functionality
│   │   ├── __init__.py
│   │   ├── database.py            # DB Connection + Session + RLS
│   │   ├── security.py            # JWT + Password Handling
│   │   ├── middleware.py          # Custom Middleware (Tenant, Audit, Security)
│   │   └── exceptions.py          # Custom Exceptions
│   │
│   ├── models/                    # SQLAlchemy Models
│   │   ├── __init__.py            # Model Exports
│   │   ├── base.py               # Base Model Classes & Mixins
│   │   ├── tenant.py             # Tenant & Identity Provider Models
│   │   ├── user.py               # User & Authentication Models
│   │   ├── rbac.py               # Role & Permission Models
│   │   ├── business.py           # Business Logic Models (Projects/Documents)
│   │   ├── audit.py              # Audit & Monitoring Models
│   │   └── utils.py              # Model Utilities & Sample Data
│   │
│   ├── schemas/                   # Pydantic Schemas (v2)
│   │   ├── __init__.py           # Schema Collections & Exports
│   │   ├── base.py               # Base Schemas & Common Types
│   │   ├── tenant.py             # Tenant & Identity Provider Schemas
│   │   ├── user.py               # User Management Schemas
│   │   ├── auth.py               # Authentication & OAuth Schemas
│   │   ├── rbac.py               # RBAC & Permission Schemas
│   │   └── business.py           # Business Logic Schemas
│   │
│   ├── services/                  # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── auth_service.py       # Authentication & User Management
│   │   ├── oauth_service.py      # Enterprise OAuth Integration
│   │   ├── tenant_service.py     # Tenant Management
│   │   ├── user_service.py       # User Operations
│   │   └── rbac_service.py       # Role & Permission Management
│   │
│   ├── api/                       # API Routes
│   │   ├── __init__.py           # API Package Config
│   │   ├── dependencies.py       # Route-specific Dependencies
│   │   └── v1/
│   │       ├── __init__.py       # V1 Router Configuration
│   │       ├── auth.py           # Authentication & OAuth Routes
│   │       ├── users.py          # User Management Routes
│   │       ├── tenants.py        # Tenant Management Routes (Super Admin)
│   │       ├── projects.py       # Business Logic Routes
│   │       └── admin.py          # Super Admin Routes
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── email.py              # AWS SES Email Service
│       ├── oauth_clients.py      # OAuth Provider Clients
│       └── audit.py              # Audit Logging Utilities
│
├── alembic/                      # Database Migrations
├── tests/                        # Test Suite
├── requirements.txt              # Python Dependencies
├── .env.example                  # Environment Variables Template
└── README.md                     # This file
```

## 🗄️ Database Schema

### Core Tables

- **`tenants`**: Organization/tenant information with settings and limits
- **`tenant_identity_providers`**: Per-tenant OAuth configuration (Microsoft/Google)
- **`users`**: User accounts with multiple auth methods (local/OAuth)
- **`user_sessions`**: Session management with impersonation support
- **`oauth_tokens`**: Secure OAuth token storage (hashed)
- **`password_reset_tokens`**: Secure password reset functionality

### RBAC System

- **`permissions`**: Resource:action based permissions (e.g., "users:create")
- **`roles`**: Tenant-specific roles with system/custom types
- **`role_permissions`**: Many-to-many role-permission assignments
- **`user_roles`**: User role assignments with optional expiration

### Business Logic (Examples)

- **`projects`**: Sample business entity with tenant isolation
- **`documents`**: File management with project association
- **`audit_logs`**: Comprehensive activity tracking

### Key Features

- **Row-Level Security (RLS)**: Automatic tenant isolation at database level
- **UUID Primary Keys**: All tables use UUID for security and scalability
- **Audit Trails**: Every modification tracked with old/new values
- **Soft Deletes**: Users deactivated instead of deleted
- **Temporal Data**: Password reset tokens, session expiry, role expiration

## 🔐 Authentication & Authorization

### Authentication Methods

1. **Local Authentication**: Email/password with bcrypt hashing
2. **Microsoft Entra ID**: Per-tenant OAuth configuration
3. **Google Workspace**: Per-tenant OAuth configuration

### Security Features

- **Account Lockouts**: 5 failed attempts = 30-minute lockout
- **Unified Error Messages**: Generic "Invalid email or password" for security
- **Email Verification**: Optional email verification workflow
- **Session Management**: JWT + database sessions with refresh tokens
- **Super Admin Impersonation**: Cross-tenant access with full audit trail

### Authorization (RBAC)

```
Resource:Action Permissions:
├── users:create, users:read, users:update, users:delete, users:invite
├── projects:create, projects:read, projects:update, projects:delete
├── documents:create, documents:read, documents:update, documents:delete, documents:download
├── tenant:manage, tenant:billing
└── roles:create, roles:read, roles:update, roles:delete, roles:assign

Default Roles per Tenant:
├── tenant_admin  (all permissions)
├── project_manager  (projects + documents + user:read)
├── user  (basic project/document access)
└── viewer  (read-only access)
```

## 🌐 API Endpoints

### Authentication (`/api/v1/auth/`)

```
POST /create-user              # Admin-only user creation
POST /login                    # Local authentication
POST /logout                   # Session termination
GET  /oauth/{provider}/login/{tenant}  # OAuth authorization URLs
POST /oauth/{provider}/callback/{tenant}  # OAuth callback handling
POST /impersonate              # Super admin impersonation
POST /end-impersonation        # End impersonation
POST /password-reset/request   # Password reset request
POST /password-reset/confirm   # Password reset confirmation
POST /verify-email             # Email verification
POST /change-password          # Password change
GET  /status                   # Authentication status
GET  /history                  # Login history
GET  /security-events          # Security events
```

### User Management (`/api/v1/users/`)

```
GET  /me                       # Current user profile
PUT  /me                       # Update current user
GET  /                         # List users (filtered, paginated)
GET  /{user_id}                # Get specific user
PUT  /{user_id}                # Update user
DELETE /{user_id}              # Deactivate user (soft delete)
GET  /{user_id}/sessions       # Active sessions
DELETE /{user_id}/sessions     # Terminate sessions
POST /invite                   # Invite new user
POST /bulk/create              # Bulk user creation
POST /bulk/action              # Bulk user actions
GET  /stats                    # User statistics
GET  /{user_id}/security       # Security information
```

### Tenant Management (`/api/v1/tenants/`) - Super Admin Only

```
POST /                         # Create tenant + admin
GET  /                         # List tenants (filtered, paginated)
GET  /{tenant_id}              # Get tenant details
PUT  /{tenant_id}              # Update tenant
DELETE /{tenant_id}            # Delete tenant (cascades)
POST /{tenant_id}/identity-providers/microsoft  # Configure Microsoft OAuth
POST /{tenant_id}/identity-providers/google     # Configure Google OAuth
GET  /{tenant_id}/identity-providers            # List identity providers
PUT  /{tenant_id}/identity-providers/{provider_id}  # Update provider
DELETE /{tenant_id}/identity-providers/{provider_id}  # Delete provider
GET  /stats                    # Global tenant statistics
GET  /{tenant_id}/stats        # Specific tenant statistics
POST /{tenant_id}/activate     # Activate tenant
POST /{tenant_id}/deactivate   # Deactivate tenant
```

### Projects & Documents (`/api/v1/projects/`)

```
POST /                         # Create project
GET  /                         # List projects (filtered, paginated)
GET  /{project_id}             # Get project details
PUT  /{project_id}             # Update project
DELETE /{project_id}           # Delete project
POST /{project_id}/documents   # Create document in project
GET  /documents                # List all documents
GET  /documents/{document_id}  # Get document details
PUT  /documents/{document_id}  # Update document
DELETE /documents/{document_id}  # Delete document
POST /documents/upload         # Initiate file upload
POST /documents/{document_id}/upload-complete  # Complete upload
GET  /activity                 # Activity feed
POST /search                   # Search projects/documents
GET  /stats                    # Project statistics
```

### Super Admin (`/api/v1/admin/`)

```
GET  /dashboard                # System overview dashboard
GET  /analytics/growth         # Growth analytics
GET  /audit/logs               # System audit logs
GET  /security/threats         # Security threat detection
POST /maintenance/cleanup      # System cleanup operations
GET  /maintenance/status       # Maintenance status
GET  /users/problematic        # Identify problematic users
POST /users/{user_id}/unlock   # Unlock user account
GET  /config/limits            # System configuration & limits
```

## 📧 Email Integration (AWS SES)

### Features

- **AWS SES Primary**: Production email delivery in EU region (Frankfurt)
- **SMTP Fallback**: Automatic fallback to SMTP if SES unavailable
- **Jinja2 Templates**: Professional HTML + plain text email templates
- **Template Types**: Welcome, password reset, email verification, security alerts
- **Bounce Handling**: Automatic suppression list management
- **Configuration Sets**: Email tracking and analytics support

### Email Templates

```
app/templates/email/
├── welcome.html & welcome.txt           # New user welcome
├── password_reset.html & password_reset.txt  # Password reset
├── email_verification.html & email_verification.txt  # Email verification
└── security_alert.html & security_alert.txt  # Security notifications
```

## 🛠️ Technology Stack

### Backend

- **FastAPI**: Modern Python web framework with automatic API docs
- **SQLAlchemy 2.0**: ORM with async support and modern patterns
- **Alembic**: Database migration management
- **Pydantic v2**: Data validation and serialization
- **PostgreSQL**: Primary database with JSON support
- **JWT**: Token-based authentication with refresh mechanism
- **bcrypt**: Password hashing
- **AWS SES**: Email delivery service
- **Jinja2**: Email template engine

### Authentication & OAuth

- **python-jose**: JWT token handling
- **authlib**: OAuth 2.0 client implementation
- **httpx**: Modern HTTP client for OAuth flows

### Development & Production

- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Static type checking
- **uvicorn**: ASGI server
- **gunicorn**: Production WSGI server

## 🚀 Setup & Installation

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd enterprise-multi-tenant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# PostgreSQL setup
createdb enterprise_multitenant

# Set environment variables
cp .env.example .env
# Edit .env with your database and AWS credentials

# Run migrations
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 3. Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/enterprise_multitenant

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# AWS SES
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=eu-central-1
AWS_SES_FROM_EMAIL=noreply@yourapp.com

# OAuth (per-tenant configuration via API)
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Application
APP_NAME=Enterprise Multi-Tenant App
BASE_URL=https://api.yourapp.com
FRONTEND_URL=https://app.yourapp.com

# Super Admin (initial setup)
SUPER_ADMIN_EMAIL=admin@yourapp.com
SUPER_ADMIN_PASSWORD=secure-password-here
```

### 4. Initialize Sample Data

```python
from app.core.database import SessionLocal
from app.models.utils import create_sample_data

with SessionLocal() as db:
    create_sample_data(db)
```

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the API documentation at: `http://localhost:8000/docs`

## 🔧 Configuration

### Multi-Tenant OAuth Setup

Each tenant can have their own OAuth configuration:

```python
# Microsoft Entra ID Setup
POST /api/v1/tenants/{tenant_id}/identity-providers/microsoft
{
    "client_id": "your-azure-app-client-id",
    "client_secret": "your-azure-app-client-secret",
    "azure_tenant_id": "your-azure-tenant-id",
    "auto_provision_users": true,
    "allowed_domains": ["company.com"],
    "default_role_name": "user"
}

# Google Workspace Setup
POST /api/v1/tenants/{tenant_id}/identity-providers/google
{
    "client_id": "your-google-client-id",
    "client_secret": "your-google-client-secret",
    "auto_provision_users": true,
    "allowed_domains": ["company.com"],
    "default_role_name": "user"
}
```

### Row-Level Security

The system automatically filters all data by tenant using PostgreSQL RLS:

```sql
-- Example RLS policy
CREATE POLICY tenant_isolation_policy ON projects
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run tests for specific functionality
pytest -k "test_multi_tenant"
```

### Test Categories

- **Unit Tests**: Individual function/method testing
- **Integration Tests**: API endpoint testing
- **Multi-Tenant Tests**: Tenant isolation verification
- **Security Tests**: Authentication and authorization
- **OAuth Tests**: OAuth flow testing

## 📋 API Usage Examples

### 1. User Registration & Login

```bash
# Create user (admin only)
curl -X POST "http://localhost:8000/api/v1/auth/create-user" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "send_welcome_email": true
  }'

# Local login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@company.com",
    "password": "user-password"
  }'
```

### 2. OAuth Authentication

```bash
# Get OAuth authorization URL
curl "http://localhost:8000/api/v1/auth/oauth/microsoft/login/company-tenant"

# OAuth callback (handled by frontend)
curl -X POST "http://localhost:8000/api/v1/auth/oauth/microsoft/callback/company-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "oauth-authorization-code"
  }'
```

### 3. Super Admin Operations

```bash
# Create new tenant
curl -X POST "http://localhost:8000/api/v1/tenants/" \
  -H "Authorization: Bearer <super-admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Company",
    "slug": "new-company",
    "admin_email": "admin@newcompany.com",
    "admin_first_name": "Admin",
    "admin_last_name": "User"
  }'

# Impersonate tenant
curl -X POST "http://localhost:8000/api/v1/auth/impersonate" \
  -H "Authorization: Bearer <super-admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-uuid-here",
    "reason": "Customer support request"
  }'
```

## 🔍 Monitoring & Observability

### Audit Logging

Every action is logged with:
- User ID and tenant context
- Action type and resource affected
- Old and new values for updates
- IP address and user agent
- Timestamp and request ID

### Health Checks

```bash
# Basic health check
curl "http://localhost:8000/health"

# Detailed health check
curl "http://localhost:8000/health/detailed"

# Kubernetes readiness probe
curl "http://localhost:8000/ready"
```

### Security Monitoring

- Failed login attempt tracking
- Account lockout logging
- Suspicious IP detection
- Multi-tenant access patterns
- Super admin impersonation audit

## 🚀 Production Deployment

### Docker Setup

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Environment Considerations

- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis for session storage and rate limiting
- **File Storage**: AWS S3 for document uploads
- **Email**: AWS SES with bounce handling
- **Monitoring**: Structured logging with ELK stack
- **Secrets**: AWS Secrets Manager or Kubernetes secrets

## 🔒 Security Considerations

### Implemented Security Measures

- **Row-Level Security**: Database-level tenant isolation
- **JWT Security**: Short-lived access tokens with refresh mechanism
- **Password Security**: bcrypt hashing with failed attempt tracking
- **OAuth Security**: State parameter validation, secure token storage
- **Audit Logging**: Comprehensive activity tracking
- **Rate Limiting**: Configurable per-endpoint limits
- **HTTPS Only**: Force secure connections in production
- **Security Headers**: XSS, CSRF, and clickjacking protection

### Recommended Additional Measures

- **2FA Implementation**: TOTP or SMS-based two-factor authentication
- **API Rate Limiting**: Redis-based distributed rate limiting
- **WAF Integration**: Web Application Firewall for additional protection
- **Security Scanning**: Regular dependency and vulnerability scanning
- **Backup Encryption**: Encrypted database backups
- **Secret Rotation**: Regular rotation of JWT secrets and OAuth credentials

## 📚 Development Guidelines

### Code Standards

- **Type Hints**: All functions must have type hints
- **Pydantic v2**: Use latest Pydantic patterns and validation
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes
- **Documentation**: All public APIs documented with docstrings
- **Testing**: Minimum 80% test coverage for new features

### Database Patterns

- **Migrations**: All schema changes via Alembic migrations
- **Indexes**: Performance-critical queries must have indexes
- **Constraints**: Use database constraints for data integrity
- **Audit Fields**: All business tables should have created_by/updated_by

### API Patterns

- **RESTful Design**: Follow REST conventions for all endpoints
- **Pagination**: All list endpoints support pagination
- **Filtering**: Implement filtering via query parameters
- **Versioning**: API versioning via URL path (/v1/, /v2/)
- **Error Responses**: Standardized error format across all endpoints

## 🤝 Contributing

### Development Workflow

1. Create feature branch from `main`
2. Implement feature with tests
3. Run full test suite
4. Submit pull request with description
5. Code review and approval
6. Merge to main and deploy

### Testing Requirements

- Unit tests for all new functions
- Integration tests for API endpoints
- Multi-tenant isolation tests
- Security-focused tests for auth changes
- Performance tests for critical paths

## 📞 Support & Maintenance

### Regular Maintenance Tasks

- **Daily**: Monitor failed logins and security alerts
- **Weekly**: Review audit logs for suspicious activity
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and rotate OAuth client secrets

### Troubleshooting

Common issues and solutions:

1. **OAuth Login Failures**: Check tenant-specific OAuth configuration
2. **Tenant Isolation Issues**: Verify RLS policies are active
3. **Email Delivery Issues**: Check AWS SES configuration and limits
4. **Performance Issues**: Review database query performance and indexes

---

This system provides a solid foundation for enterprise multi-tenant applications with comprehensive security, scalability, and maintainability features. The modular architecture allows for easy extension and customization based on specific business requirements.