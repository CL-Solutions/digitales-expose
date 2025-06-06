# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

- This is the backend API (FastAPI) for the digitales-expose system
- Frontend application is located in `../digitales-expose-frontend/` (Next.js)
- Template folder `../backend-template/` should be ignored

## Project Overview

**Digitales Expose** - A sophisticated property investment expose management system that enables real estate companies to:

### Core Business Functions
- **Property Portfolio Management**: Comprehensive property data with 25+ investment-specific fields
- **Investagon API Integration**: Automatic synchronization with external property data provider
- **Investment Expose Generation**: Customizable templates for property investment presentations
- **Shareable Investment Links**: Secure, trackable links for potential investors with preset parameters
- **Multi-Media Asset Management**: Professional property and city image categorization
- **Location Intelligence**: Comprehensive city data with demographic and economic indicators
- **Financial Analytics**: Automatic yield calculations and investment metrics
- **Access Tracking**: Detailed analytics on expose views and investor engagement

### Technical Highlights
- **Multi-Tenant Architecture**: Complete tenant isolation with row-level security
- **Enterprise Authentication**: OAuth integration, RBAC, and audit trails
- **External API Integration**: Robust Investagon synchronization with error handling
- **File Storage**: S3-compatible storage with automatic image optimization
- **Background Processing**: Automated tasks including hourly property sync
- **Performance Optimized**: Proper pagination, caching, and query optimization

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

# The server includes background tasks for:
# - Hourly Investagon property sync (if enabled)
# - Expired session cleanup
# - Automated maintenance tasks
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
- External service integration (AWS SES, OAuth providers, Investagon API, Hetzner S3)
- Audit logging and activity tracking
- Background task processing

**Service Conventions:**
- Services receive database sessions via dependency injection
- All database operations use async/await
- Services return domain models, not schemas
- Error handling uses custom exceptions (app/core/exceptions.py)

**Key Services:**
- `PropertyService` - Property CRUD operations and analytics
- `ExposeService` - Expose link generation and management
- `CityService` - City data management
- `InvestagonSyncService` - External API integration
- `S3Service` - File upload and storage (Hetzner-compatible)

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

**Available API Modules:**
- `/api/v1/auth` - Authentication and OAuth flows
- `/api/v1/users` - User management and profiles
- `/api/v1/tenants` - Tenant administration (super admin only)
- `/api/v1/rbac` - Roles and permissions management
- `/api/v1/properties` - Property CRUD, statistics, and image upload (13 categories)
- `/api/v1/cities` - City data management and image upload (12 categories)
- `/api/v1/exposes` - Expose template and link management with public access
- `/api/v1/investagon` - External API synchronization and testing
- `/api/v1/admin` - System administration and monitoring

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

### Managing Property Data

1. **Creating Properties**: Use `PropertyService.create_property()` with comprehensive validation
2. **Property Fields**: 25+ investment-specific fields including:
   - Basic info: address, city, property type, size, rooms, construction year
   - Financial data: purchase price, monthly rent, additional costs, management fees
   - Transaction costs: broker, tax, notary, and registration rates
   - Operating costs: landlord, tenant, and reserve allocations
   - Investment metrics: object share, land share, depreciation settings
   - Geographic data: latitude, longitude, city relationship
   - Investagon integration: external ID, sync status, API data cache
3. **Image Upload**: Properties support 13 image categories with S3 upload:
   - `exterior` - Building exterior photos
   - `interior` - General interior shots
   - `floor_plan` - Floor plan diagrams (higher resolution retained)
   - `energy_certificate` - Energy efficiency documents
   - `bathroom` - Bathroom photos
   - `kitchen` - Kitchen photos
   - `bedroom` - Bedroom photos
   - `living_room` - Living room photos
   - `balcony` - Balcony/terrace photos
   - `garden` - Garden/outdoor space photos
   - `parking` - Parking space photos
   - `basement` - Basement/storage photos
   - `roof` - Rooftop/attic photos
4. **Investagon Integration**: Full API synchronization with:
   - Individual property sync by Investagon ID
   - Bulk synchronization (full or incremental)
   - Automatic hourly sync (configurable)
   - Status tracking: active, pre_sale, draft flags
   - Comprehensive error handling and retry logic
5. **Financial Analytics**: Automatic calculations including:
   - Gross and net rental yields
   - Transaction cost percentages
   - Operating expense ratios
   - Investment return projections

### Managing City Data

1. **Creating Cities**: Use `CityService.create_city()` with demographic data
2. **Image Upload**: Cities support 12 image categories with file upload to S3:
   - `skyline` - City skyline photos
   - `landmark` - Important landmarks and monuments
   - `downtown` - Downtown/city center areas
   - `residential` - Residential neighborhoods
   - `commercial` - Commercial districts and shopping
   - `nature` - Parks, rivers, and natural areas
   - `transport` - Transportation hubs and infrastructure
   - `culture` - Museums, theaters, cultural sites
   - `nightlife` - Entertainment and dining areas
   - `education` - Schools, universities, educational facilities
   - `recreation` - Sports facilities, recreational areas
   - `overview` - General city overview photos
3. **Property Integration**: Cities are linked to properties for location data

### Working with Expose Links

1. **Templates**: Create reusable expose templates with:
   - Investment-focused content sections (benefits, location, financing, tax info)
   - Default calculation parameters (equity percentage, interest rates, loan terms)
   - Property type-specific customization
   - Active/inactive status management
2. **Link Generation**: Generate unique shareable links with:
   - Short, secure link IDs (8-character UUIDs)
   - Preset calculation parameters that override template defaults
   - Custom messages for personalization
   - Password protection and expiration dates
   - Visible section controls (show/hide specific content)
3. **Public Access**: Public expose viewing with:
   - No authentication required for investors
   - Password verification when protected
   - Automatic view tracking with visitor analytics
   - City information integration for location context
4. **Analytics**: Comprehensive tracking including:
   - View count and timestamps (first/last viewed)
   - Visitor information (IP, user agent, referrer)
   - Individual view records for detailed analysis
   - Link performance metrics

### External API Integration

**Investagon API Integration:**
- Full property synchronization with external property data provider
- Authentication via `organization_id` and `api_key` configuration
- Multiple sync modes:
  - **Manual Single Property**: Sync individual properties by Investagon ID
  - **Bulk Sync**: Full or incremental synchronization of all properties
  - **Automatic Sync**: Configurable hourly background synchronization
- Status tracking with active, pre_sale, and draft flags from Investagon
- Comprehensive error handling with retry logic and detailed logging
- Sync history tracking with creation/update/failure counts
- Connection testing endpoint for API validation
- Rate limiting and tenant context validation

**Hetzner S3-Compatible Storage:**
- Professional image upload and management system
- Automatic resizing and optimization based on image category
- Tenant-isolated file organization: `tenant_id/type/YYYY/MM/DD/filename`
- Path-style addressing for Hetzner compatibility
- Different processing rules by image type:
  - **Property Images**: 1920px max for photos, 2400px for floor plans (higher quality)
  - **City Images**: 1920px for landscapes/overviews, 1600px for culture/nature
- Image metadata tracking (dimensions, file size, MIME type)
- Automatic S3 cleanup when images are deleted from database
- Graceful degradation when storage service is unavailable

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

### Background Task Management

The application includes a built-in scheduler (`app/core/scheduler.py`) for automated tasks:

**Default Scheduled Tasks:**
- **Investagon Sync**: Hourly property synchronization (configurable via `ENABLE_AUTO_SYNC`)
- **Session Cleanup**: Expired JWT token cleanup every 6 hours
- **Daily Maintenance**: Database optimization and health checks

**Scheduler Features:**
- Async task execution with proper error handling
- Task status tracking (run count, error count, last run time)
- Individual task enable/disable controls
- Graceful startup and shutdown handling
- Comprehensive logging for debugging

**Configuration:**
```bash
# Enable/disable automatic sync
ENABLE_AUTO_SYNC=true

# Investagon API credentials
INVESTAGON_ORGANIZATION_ID=your-org-id
INVESTAGON_API_KEY=your-api-key
INVESTAGON_API_URL=https://api.investagon.com/api
```

### File Storage Integration

**S3-Compatible Storage (Hetzner):**
- Configure endpoint URL for Hetzner object storage
- Automatic image resizing and optimization based on category
- Tenant-isolated file organization by date: `tenant_id/type/YYYY/MM/DD/filename`
- Graceful degradation when storage is unavailable
- Support for multiple image categories with different processing rules

```bash
# Hetzner S3 configuration
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT_URL=https://fsn1.your-objectstorage.com
S3_BUCKET_NAME=digitales-expose
S3_REGION=fsn1
```

**Image Upload Endpoints:**
- Property images: `POST /api/v1/properties/{id}/images/upload`
- City images: `POST /api/v1/cities/{id}/images/upload`
- Both support multipart form data with file, type, title, description, and display_order

### Permission System for New Features

**Property Management Permissions:**
- `properties:create` - Create new properties
- `properties:read` - View properties
- `properties:update` - Edit property details
- `properties:delete` - Remove properties

**Image Management Permissions:**
- `images:upload` - Upload property/city images
- `images:delete` - Remove images

**Expose Management Permissions:**
- `expose:create` - Create expose templates and links
- `expose:read` - View exposes
- `expose:update` - Edit exposes
- `expose:delete` - Remove exposes

**City Management Permissions:**
- `cities:create` - Add city data
- `cities:read` - View city information
- `cities:update` - Edit city details
- `cities:delete` - Remove cities

**Investagon Integration Permissions:**
- `investagon:sync` - Trigger property synchronization

**Role Assignments:**
- `sales_person` - Can view properties, create expose links, sync data
- `property_manager` - Can edit property content, manage images and exposes
- `tenant_admin` - Full access to all tenant resources

## Current Implementation Status

### Recently Completed Features

**Database Schema (June 2025 Updates):**
- Complete multi-tenant property management schema
- Geographic data integration (latitude/longitude, city relationships)
- Enhanced Investagon API compatibility with status flags
- Advanced property investment fields (object share, depreciation settings)
- Comprehensive image management for properties and cities

**API Implementation:**
- Full CRUD operations for all core entities
- Advanced filtering and pagination for property lists
- Comprehensive image upload with category-based processing
- Public expose access endpoints for investor viewing
- Investagon synchronization with multiple sync modes
- Background task processing with error handling

**Integration Features:**
- Hetzner S3-compatible storage with automatic optimization
- OAuth authentication flows (Microsoft, Google)
- JWT-based session management with refresh tokens
- Role-based access control with granular permissions
- Audit logging for all administrative actions

### Testing Strategy

**Current Test Implementation:**
- Basic API endpoint testing (`tests/test_simple_api.py`)
- Property API functionality validation
- Investagon integration testing
- Performance benchmarking for property listings
- Error handling verification

**Recommended Test Expansion:**
- Use pytest fixtures for database setup/teardown
- Test with multiple tenant contexts for isolation verification
- Verify permission enforcement across all endpoints
- Mock external services (Investagon API, S3, email providers)
- Test error cases and edge conditions
- Integration tests for expose link generation and access
- Load testing for sync operations and image uploads

### Development Notes

**Performance Considerations:**
- Property list endpoint optimized for overview data (excludes heavy fields)
- Image uploads automatically resize based on category requirements
- Background sync operations handle large datasets efficiently
- Database queries use proper indexing for common filter patterns

**Security Implementation:**
- All tenant data isolated through row-level security
- JWT tokens include tenant context for automatic filtering
- Image uploads validated for file type and size limits
- Public expose links use secure, unpredictable identifiers
- Comprehensive audit trails for administrative actions