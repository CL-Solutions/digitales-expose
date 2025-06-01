# Enterprise Multi-Tenant System

A production-ready, enterprise-grade multi-tenant application with OAuth integration, comprehensive RBAC, and super admin capabilities built with FastAPI.

## 🏗️ Architecture Overview

**Multi-tenant SaaS platform** with complete tenant isolation using PostgreSQL row-level security (RLS), OAuth integration for Microsoft Entra ID and Google Workspace, and comprehensive role-based access control.

### Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Authentication**: JWT + OAuth 2.0 (Microsoft/Google)
- **Email**: AWS SES with SMTP fallback
- **Security**: bcrypt, Row-Level Security (RLS)
- **Templates**: Jinja2 for email templates

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI App + Startup
│   ├── config.py                  # Environment Configuration
│   ├── dependencies.py            # FastAPI Dependencies & Permissions
│   │
│   ├── core/                      # Core Functionality
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
- **tenants**: Organization/tenant information with settings and limits
- **tenant_identity_providers**: Per-tenant OAuth configuration (Microsoft/Google)
- **users**: User accounts with multiple auth methods (local/OAuth)
- **user_sessions**: Session management with impersonation support
- **oauth_tokens**: Secure OAuth token storage (hashed)

### RBAC System
- **permissions**: Resource:action based permissions (e.g., "users:create")
- **roles**: Tenant-specific roles with system/custom types
- **role_permissions**: Many-to-many role-permission assignments
- **user_roles**: User role assignments with optional expiration

### Business Logic (Examples)
- **projects**: Sample business entity with tenant isolation
- **documents**: File management with project association
- **audit_logs**: Comprehensive activity tracking

## 🔐 Authentication & Authorization

### Authentication Methods
1. **Local**: Email/password with bcrypt hashing
2. **Microsoft Entra ID**: Per-tenant OAuth configuration
3. **Google Workspace**: Per-tenant OAuth configuration

### Security Features
- Account lockouts (5 failed attempts = 30-minute lockout)
- Unified error messages for security
- Email verification workflow
- Session management with JWT + refresh tokens
- Super admin impersonation with full audit trail

### Permission System (RBAC)

Your application uses a **granular Role-Based Access Control** system where permissions are defined as `resource:action` pairs and then grouped into roles.

#### How Permissions Work

**1. Atomic Permissions (Resource:Action format)**
```
Format: "{resource}:{action}"

Examples:
├── users:create     → Can create new users
├── users:read       → Can view user information  
├── users:update     → Can modify user data
├── users:delete     → Can deactivate users
├── users:invite     → Can send user invitations
├── projects:create  → Can create new projects
├── projects:read    → Can view projects
├── projects:update  → Can modify projects
├── projects:delete  → Can delete projects
├── documents:create → Can create/upload documents
├── documents:read   → Can view documents
├── documents:update → Can modify documents
├── documents:delete → Can delete documents
├── documents:download → Can download document files
├── tenant:manage    → Can modify tenant settings
├── tenant:billing   → Can access billing information
├── roles:create     → Can create custom roles
├── roles:read       → Can view roles
├── roles:update     → Can modify roles
├── roles:delete     → Can delete roles
└── roles:assign     → Can assign roles to users
```

**2. Roles Group Permissions**
Roles are collections of permissions that make sense for specific job functions:

```
┌─ tenant_admin (Full tenant control)
│  ├── ALL permissions listed above
│  ├── Can manage all users in tenant
│  ├── Can configure OAuth providers
│  └── Can access billing and tenant settings
│
├─ project_manager (Project oversight)
│  ├── users:read (can see user list)
│  ├── projects:* (all project permissions)
│  ├── documents:* (all document permissions)
│  ├── roles:read (can see available roles)
│  └── Cannot manage users or tenant settings
│
├─ user (Standard business user)
│  ├── users:read (can see colleagues)
│  ├── projects:read (can view assigned projects)
│  ├── documents:create, documents:read, documents:update, documents:download
│  └── Cannot delete projects or manage users
│
└─ viewer (Read-only access)
   ├── users:read
   ├── projects:read  
   ├── documents:read, documents:download
   └── No create, update, or delete permissions
```

**3. Permission Checking Process**

When a user tries to access an endpoint, the system checks:

```python
# Example: User wants to create a project
# Endpoint: POST /api/v1/projects/

1. Extract user from JWT token
2. Get user's tenant_id from token or user record
3. Find all roles assigned to user in that tenant
4. Collect all permissions from those roles
5. Check if "projects:create" permission exists
6. Allow or deny the request
```

**4. Multi-Tenant Isolation**

- **Roles are tenant-specific**: The same user can have different roles in different tenants
- **Permissions are always checked within tenant context**
- **Super admins bypass tenant restrictions** but actions are logged

**5. Permission Dependencies**

The `dependencies.py` file shows how permissions are enforced:

```python
# Decorator that requires specific permission
@require_permission("users", "create")
async def create_user_endpoint():
    # This endpoint requires "users:create" permission
    
# Decorator that allows resource owners OR permission holders
@require_own_resource_or_permission("documents", "update") 
async def update_document(document_id):
    # User can update IF they own the document OR have "documents:update"
```

**6. Special Permission Rules**

- **Super Admins**: Bypass all permission checks (but actions are audited)
- **Resource Ownership**: Users can often modify their own resources even without broader permissions
- **Tenant Isolation**: Permissions only apply within the user's current tenant context
- **Impersonation**: Super admins can impersonate tenants, inheriting that tenant's permission context

**7. Role Assignment Examples**

```http
# Assign "project_manager" role to a user
POST /api/v1/users/{user_id}/roles/{role_id}

# Create custom role with specific permissions
POST /api/v1/roles/
{
  "name": "document_specialist",
  "description": "Focused on document management",
  "permission_ids": [
    "documents:create", "documents:read", "documents:update", 
    "documents:delete", "documents:download"
  ]
}
```

**8. Dynamic Permission Checking**

Users can check their own permissions:
```http
GET /api/v1/auth/status
# Returns: permissions: ["users:read", "projects:create", ...]

# Check if user has specific permission
GET /api/v1/users/{user_id}/permissions/check?resource=projects&action=create
```

This system allows for:
- **Granular control** over what each user can do
- **Flexible role definitions** per tenant
- **Easy permission auditing** 
- **Scalable security** as you add new features

## 📋 API Endpoints Overview

All API endpoints are available at: **http://localhost:8000/docs**

### 🔐 Authentication Routes (`/api/v1/auth/`)

#### User Authentication
- `POST /api/v1/auth/create-user` - Admin-only user creation
- `POST /api/v1/auth/login` - Local authentication  
- `POST /api/v1/auth/logout` - Session termination
- `POST /api/v1/auth/refresh` - Refresh access token

#### Password Management
- `POST /api/v1/auth/password-reset/request` - Request password reset
- `POST /api/v1/auth/password-reset/confirm` - Confirm password reset
- `POST /api/v1/auth/change-password` - Change password (authenticated)
- `POST /api/v1/auth/verify-email` - Email verification

#### OAuth Authentication
- `GET /api/v1/auth/oauth/{provider}/login/{tenant_slug}` - Get OAuth authorization URL
- `POST /api/v1/auth/oauth/{provider}/callback/{tenant_slug}` - OAuth callback handling

#### Super Admin Impersonation
- `POST /api/v1/auth/impersonate` - Super admin impersonation
- `POST /api/v1/auth/end-impersonation` - End impersonation

#### Authentication Status & History
- `GET /api/v1/auth/status` - Authentication status
- `GET /api/v1/auth/history` - Login history
- `GET /api/v1/auth/security-events` - Security events
- `GET /api/v1/auth/sessions` - Get user sessions
- `DELETE /api/v1/auth/sessions/{session_id}` - Terminate specific session

### 👥 User Management Routes (`/api/v1/users/`)

#### User Profile & Management
- `GET /api/v1/users/me` - Current user profile
- `PUT /api/v1/users/me` - Update current user
- `GET /api/v1/users/` - List users (filtered, paginated)
- `GET /api/v1/users/{user_id}` - Get specific user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Deactivate user (soft delete)

#### User Sessions & Security
- `GET /api/v1/users/{user_id}/sessions` - Get user's active sessions
- `DELETE /api/v1/users/{user_id}/sessions` - Terminate user sessions
- `GET /api/v1/users/{user_id}/security` - User security information

#### User Invitations & Bulk Operations
- `POST /api/v1/users/invite` - Invite new user
- `POST /api/v1/users/bulk/create` - Bulk user creation
- `POST /api/v1/users/bulk/action` - Bulk user actions
- `GET /api/v1/users/export` - Export users (CSV/JSON)

#### User Analytics
- `GET /api/v1/users/stats` - User statistics

#### User Role Management
- `GET /api/v1/users/{user_id}/roles` - Get user roles
- `POST /api/v1/users/{user_id}/roles/{role_id}` - Assign role to user
- `DELETE /api/v1/users/{user_id}/roles/{role_id}` - Remove role from user

### 🛡️ **RBAC Routes (`/api/v1/rbac/`) - NEW!**

#### Role Management
- `POST /api/v1/rbac/roles` - Create a new role
- `GET /api/v1/rbac/roles` - List all roles in tenant
- `GET /api/v1/rbac/roles/{role_id}` - Get role with permissions
- `PUT /api/v1/rbac/roles/{role_id}` - Update role
- `DELETE /api/v1/rbac/roles/{role_id}` - Delete role

#### Role Permissions Management
- `PUT /api/v1/rbac/roles/{role_id}/permissions` - Update role permissions
- `POST /api/v1/rbac/roles/{role_id}/clone` - Clone an existing role

#### Permission Management
- `GET /api/v1/rbac/permissions` - List all available permissions
- `POST /api/v1/rbac/permissions` - Create a new permission

#### Bulk Role Operations
- `POST /api/v1/rbac/roles/bulk-assign` - Assign roles to multiple users

#### User Permission Checks
- `GET /api/v1/rbac/users/{user_id}/permissions` - Get all permissions for a user
- `GET /api/v1/rbac/users/{user_id}/permissions/check` - Check if user has specific permission

#### RBAC Statistics & Reports
- `GET /api/v1/rbac/stats` - Get RBAC statistics
- `GET /api/v1/rbac/reports/role-usage` - Get role usage report
- `GET /api/v1/rbac/reports/permission-usage` - Get permission usage report
- `GET /api/v1/rbac/reports/compliance` - Get RBAC compliance report

#### Super Admin RBAC Operations
- `GET /api/v1/rbac/global/stats` - Get global RBAC statistics (Super Admin only)
- `GET /api/v1/rbac/global/reports/permission-usage` - Get global permission usage report

### 🏢 Tenant Management Routes (`/api/v1/tenants/`) - Super Admin Only

#### Tenant CRUD
- `POST /api/v1/tenants/` - Create tenant + admin
- `GET /api/v1/tenants/` - List tenants (filtered, paginated)
- `GET /api/v1/tenants/{tenant_id}` - Get tenant details
- `PUT /api/v1/tenants/{tenant_id}` - Update tenant
- `DELETE /api/v1/tenants/{tenant_id}` - Delete tenant (cascades)

#### Identity Provider Management
- `POST /api/v1/tenants/{tenant_id}/identity-providers/microsoft` - Configure Microsoft OAuth
- `POST /api/v1/tenants/{tenant_id}/identity-providers/google` - Configure Google OAuth
- `GET /api/v1/tenants/{tenant_id}/identity-providers` - List identity providers
- `PUT /api/v1/tenants/{tenant_id}/identity-providers/{provider_id}` - Update provider
- `DELETE /api/v1/tenants/{tenant_id}/identity-providers/{provider_id}` - Delete provider

#### Tenant Operations & Analytics
- `POST /api/v1/tenants/{tenant_id}/activate` - Activate tenant
- `POST /api/v1/tenants/{tenant_id}/deactivate` - Deactivate tenant
- `GET /api/v1/tenants/stats` - Global tenant statistics
- `GET /api/v1/tenants/{tenant_id}/stats` - Specific tenant statistics
- `GET /api/v1/tenants/{tenant_id}/usage-report` - Detailed usage report

### 📁 Projects & Documents Routes (`/api/v1/projects/`)

#### Project Management
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/` - List projects (filtered, paginated)
- `GET /api/v1/projects/{project_id}` - Get project details
- `PUT /api/v1/projects/{project_id}` - Update project
- `DELETE /api/v1/projects/{project_id}` - Delete project
- `POST /api/v1/projects/{project_id}/export` - Export project

#### Document Management
- `POST /api/v1/projects/{project_id}/documents` - Create document in project
- `GET /api/v1/projects/documents` - List all documents
- `GET /api/v1/projects/documents/{document_id}` - Get document details
- `PUT /api/v1/projects/documents/{document_id}` - Update document
- `DELETE /api/v1/projects/documents/{document_id}` - Delete document

#### File Upload & Sharing
- `POST /api/v1/projects/documents/upload` - Initiate file upload
- `POST /api/v1/projects/documents/{document_id}/upload-complete` - Complete upload
- `POST /api/v1/projects/documents/{document_id}/share` - Share document with users

#### Search & Analytics
- `GET /api/v1/projects/activity` - Activity feed
- `POST /api/v1/projects/search` - Search projects/documents
- `GET /api/v1/projects/stats` - Project statistics

### 🔧 Super Admin Routes (`/api/v1/admin/`)

#### System Overview & Analytics
- `GET /api/v1/admin/dashboard` - System overview dashboard
- `GET /api/v1/admin/analytics/growth` - Growth analytics
- `GET /api/v1/admin/audit/logs` - System audit logs
- `GET /api/v1/admin/security/threats` - Security threat detection

#### Emergency Operations
- `POST /api/v1/admin/emergency/disable-tenant` - Emergency tenant disable
- `POST /api/v1/admin/emergency/global-logout` - Emergency global logout

#### System Maintenance
- `POST /api/v1/admin/maintenance/cleanup` - System cleanup operations
- `GET /api/v1/admin/maintenance/status` - Maintenance status
- `POST /api/v1/admin/backup/create` - Create system backup

## 🔧 Key Features

### Multi-Tenant Architecture
- **Row-Level Security**: Automatic tenant isolation at database level
- **Per-Tenant OAuth**: Each tenant can configure their own Microsoft/Google OAuth
- **Tenant-Specific Roles**: Custom roles and permissions per tenant
- **Resource Isolation**: Complete data separation between tenants

### Enterprise Security
- **Account Lockouts**: Failed login protection
- **Audit Logging**: Comprehensive activity tracking
- **Super Admin Impersonation**: Cross-tenant access with audit trail
- **Session Management**: JWT with refresh tokens
- **Email Verification**: Optional verification workflow

### OAuth Integration
- **Microsoft Entra ID**: Per-tenant configuration with Azure tenant ID
- **Google Workspace**: Per-tenant Google OAuth setup
- **Auto-Provisioning**: Automatic user creation on first OAuth login
- **Domain Restrictions**: Restrict OAuth access to specific domains
- **Role Mapping**: Map OAuth claims to internal roles

### Business Logic Examples
- **Projects**: Sample business entities with full CRUD
- **Documents**: File management with project association
- **Activity Feeds**: Track all user and system activities
- **Search**: Full-text search across projects and documents

## 🔑 Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

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

## 🚀 Quick Start

1. **Setup Environment**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Database**
```bash
# Set DATABASE_URL in .env
alembic upgrade head
```

3. **Run Development Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Access API Documentation**
```
http://localhost:8000/docs
```

## 📋 Common Use Cases

### Creating a New Tenant (Super Admin)
```http
POST /api/v1/tenants/
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "admin_email": "admin@acme.com",
  "admin_first_name": "John",
  "admin_last_name": "Doe"
}
```

### Setting Up OAuth for Tenant
```http
POST /api/v1/tenants/{tenant_id}/identity-providers/microsoft
{
  "client_id": "your-azure-app-client-id",
  "client_secret": "your-azure-app-client-secret",
  "azure_tenant_id": "your-azure-tenant-id",
  "auto_provision_users": true,
  "allowed_domains": ["acme.com"]
}
```

### User Login with OAuth
```http
# 1. Get OAuth URL
GET /api/v1/auth/oauth/microsoft/login/acme-corp

# 2. Handle callback after user auth
POST /api/v1/auth/oauth/microsoft/callback/acme-corp
{
  "code": "oauth-authorization-code"
}
```

### Super Admin Impersonation
```http
POST /api/v1/auth/impersonate
{
  "tenant_id": "tenant-uuid-here",
  "reason": "Customer support request"
}
```

## 🔍 Monitoring & Observability

Every action is logged with:
- User ID and tenant context
- Action type and resource affected
- Old and new values for updates
- IP address and user agent
- Timestamp and request ID

Use `/api/v1/admin/audit/logs` and `/api/v1/admin/security/threats` for comprehensive monitoring.

---

**This system provides a solid foundation for enterprise multi-tenant applications with comprehensive security, scalability, and maintainability features.**