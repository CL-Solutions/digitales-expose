# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Then edit .env with your values
```

### Database Operations
```bash
# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Rollback last migration
alembic downgrade -1

# Initialize super admin user
python utility_scripts/init_super_admin.py
```

### Development Server
```bash
# Run the development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
# http://localhost:8000/docs
```

### Code Quality Commands
```bash
# Format code with black
black app/

# Sort imports
isort app/

# Run linting
flake8 app/

# Type checking
mypy app/

# Run tests (when implemented)
pytest
pytest --cov=app  # With coverage
```

## High-Level Architecture

### Multi-Tenant Architecture with Row-Level Security

This application implements complete tenant isolation at the database level using PostgreSQL Row-Level Security (RLS). Every request automatically sets the tenant context through middleware, ensuring data isolation without explicit filtering in queries.

**Key Points:**
- The `TenantMiddleware` (app/core/middleware.py:84-127) automatically extracts tenant_id from JWT tokens
- Database session sets `app.current_tenant_id` for RLS policies
- Super admins can impersonate tenants while maintaining audit trails
- All models inherit from `TenantMixin` for automatic tenant association

### Authentication & Authorization Flow

The system supports multiple authentication methods with a unified JWT token approach:

1. **Local Authentication**: Email/password with bcrypt hashing
2. **OAuth Integration**: Per-tenant Microsoft Entra ID and Google Workspace
3. **Super Admin**: Special users who can access all tenants

**Permission System:**
- Permissions follow `resource:action` format (e.g., "users:create")
- Roles group permissions (e.g., tenant_admin has all permissions)
- The `@require_permission` decorator (app/dependencies.py:142-182) enforces access control
- Resource ownership provides implicit permissions (users can edit their own data)

### Service Layer Pattern

Business logic is isolated in service classes (app/services/) that handle:
- Complex database operations with proper transaction management
- Cross-entity operations and validations
- External service integration (AWS SES, OAuth providers)
- Audit logging and activity tracking

**Service Conventions:**
- Services receive database sessions via dependency injection
- All database operations use async/await
- Services return domain models, not schemas
- Error handling uses custom exceptions (app/core/exceptions.py)

### API Structure

Routes follow RESTful conventions with consistent patterns:
- Versioned endpoints (`/api/v1/`)
- Resource-based URLs
- Standard HTTP methods
- Pagination, filtering, and sorting support
- Consistent error responses

**Route Organization:**
- Each domain has its own router file
- Dependencies handle authentication and permissions
- Schemas validate input/output
- Services contain business logic

## Common Development Tasks

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Add business logic to appropriate service in `app/services/`
3. Create route handler in `app/api/v1/`
4. Add permission requirements using decorators
5. Update API documentation if needed

### Creating a New Database Model

1. Define model in `app/models/` inheriting from appropriate mixins
2. Add relationships and constraints
3. Create corresponding schemas
4. Run `alembic revision --autogenerate -m "Add [model name]"`
5. Review and run migration

### Adding a New Permission

1. Add permission to `app/models/utils.py` SAMPLE_PERMISSIONS
2. Create migration to insert permission
3. Update relevant roles to include new permission
4. Use `@require_permission` decorator on endpoints

### Implementing OAuth for a New Provider

1. Create client class in `app/utils/oauth_clients.py`
2. Add provider configuration to `TenantIdentityProvider` model
3. Implement OAuth flow in `app/services/oauth_service.py`
4. Add routes in `app/api/v1/auth.py`
5. Update frontend OAuth callback handling

## Critical Implementation Details

### Tenant Context Management

The tenant context is automatically managed but requires understanding:
- JWT tokens include tenant_id claim
- Middleware sets database session context
- All queries automatically filter by current tenant
- Super admin queries bypass RLS when impersonating

### Session and Transaction Handling

- Use `async with` for database sessions
- Transactions auto-commit on success, rollback on exception
- Bulk operations should use `session.execute()` for performance
- Long-running operations should commit in batches

### Security Considerations

- Never log sensitive data (passwords, tokens, secrets)
- Use constant-time comparison for security tokens
- Sanitize user input for email templates
- Rate limit authentication endpoints
- Audit all administrative actions

### Performance Patterns

- Use eager loading for related entities to avoid N+1 queries
- Implement pagination for list endpoints
- Cache frequently accessed data (permissions, roles)
- Use database indexes for common query patterns
- Background tasks for heavy operations

## Testing Strategy

When implementing tests:
- Use pytest fixtures for database setup/teardown
- Test with multiple tenant contexts
- Verify permission enforcement
- Mock external services (AWS SES, OAuth)
- Test error cases and edge conditions