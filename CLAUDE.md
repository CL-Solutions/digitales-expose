# Backend Development Guide - Digitales Expose API

This guide provides backend-specific instructions for the FastAPI API. For general project information, see the root CLAUDE.md.

## Project Overview

**Digitales Expose** - A sophisticated property investment expose management system that enables real estate companies to:

### Core Business Functions
- **Project & Property Management**: Two-layer architecture where projects (buildings) contain multiple properties (units)
- **Property Portfolio Management**: Comprehensive property data with 25+ investment-specific fields
- **Investagon API Integration**: Automatic synchronization of projects and properties from external data provider
- **Investment Expose Generation**: Customizable templates for property investment presentations
- **Shareable Investment Links**: Secure, trackable links for potential investors with preset parameters
- **Multi-Media Asset Management**: Professional project, property and city image categorization
- **Location Intelligence**: Comprehensive city data with demographic and economic indicators
- **Financial Analytics**: Automatic yield calculations and investment metrics at both project and property levels
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
- `PropertyService` - Property CRUD operations and analytics with visibility filtering
- `ProjectService` - Project management with visibility status calculation
- `ExposeService` - Expose link generation and management
- `CityService` - City data management
- `InvestagonService` - External API integration with project status updates
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
- `/api/v1/projects` - Project CRUD, statistics, and image upload (4 categories)
- `/api/v1/properties` - Property CRUD, statistics, and image upload (13 categories)
- `/api/v1/cities` - City data management and image upload (12 categories)
- `/api/v1/exposes` - Expose template and link management with public access
- `/api/v1/investagon` - External API synchronization and testing
- `/api/v1/admin` - System administration and monitoring

## Common Development Tasks

### API Endpoint Pattern

Every protected API endpoint should follow this pattern:

```python
from app.dependencies import get_db, get_current_active_user, get_current_tenant_id, require_permission

@router.post("/resource", response_model=ResourceResponse)
async def create_resource(
    resource_data: ResourceCreate,  # Request body
    db: Session = Depends(get_db),  # Database session
    current_user: User = Depends(get_current_active_user),  # Authenticated user
    tenant_id: UUID = Depends(get_current_tenant_id),  # Current tenant context
    _: bool = Depends(require_permission("resource", "create"))  # Permission check
):
    """Create a new resource"""
    try:
        result = ResourceService.create_resource(
            db=db,
            data=resource_data,
            created_by=current_user.id,
            tenant_id=tenant_id
        )
        return ResourceResponse.model_validate(result)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
```

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Add business logic to appropriate service in `app/services/`
3. Create route handler in `app/api/v1/`
4. Add permission requirements using `Depends(require_permission("resource", "action"))`
5. Update API documentation if needed

**Important: Permission Usage**
```python
# CORRECT - Use as a dependency parameter
@router.get("/items")
async def list_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("items", "read"))  # ✓ Correct
):
    pass

# INCORRECT - Don't use as a decorator
@router.get("/items")
@require_permission("items", "read")  # ✗ Wrong - This will cause errors
async def list_items(...):
    pass
```

**Key Dependencies:**
- Always use `get_current_active_user` (not `get_current_user`) for user authentication
- `require_permission` takes two parameters: resource and action (e.g., "projects", "create")
- Place permission check as the last dependency parameter, typically named `_`

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

### Managing Project and Property Data

1. **Project-Property Architecture**: 
   - **Projects** represent buildings containing multiple properties (units)
   - Properties (units) MUST belong to a project - no orphan properties allowed
   - Projects are identified by address (street + house number)
   - Properties are identified by unit number (e.g., "WE1", "WE2" for Wohneinheit)
   - **Visibility Filtering**: Role-based access control for property visibility:
     - Sales people only see properties with visibility = 1 (active/published)
     - Tenant admins and property managers see all properties (visibility -1, 0, 1)
     - Projects inherit visibility from their properties (calculated dynamically)
     - Sales people cannot see projects without active properties

2. **Creating Projects**: Use `ProjectService.create_project()` with:
   - Building-level information: name, street, house number, city, state, country
   - Geographic data: latitude, longitude  
   - Investment metrics: total units, total building size
   - Image support: exterior, common areas, amenities, floor plans
   - Note: During Investagon sync, project addresses are extracted from property data, not project names

3. **Creating Properties**: Use `PropertyService.create_property()` with comprehensive validation
   - **Required**: project_id - property must belong to an existing project
   - **Unit identification**: unit_number only (apartment_number removed)
   - **Property Fields**: 25+ investment-specific fields including:
     - Basic info: unit_number, property type, size, rooms, construction year
     - Financial data: purchase price, monthly rent, additional costs, management fees
     - Transaction costs: broker, tax, notary, and registration rates
     - Operating costs: landlord, tenant, and reserve allocations
     - Investment metrics: object share, land share, depreciation settings
     - Geographic data: denormalized from project (city, state, zip_code, city_id)
     - Investagon integration: external ID, sync status, API data cache

4. **Image Upload**: 
   - **Projects** support 4 image categories:
     - `exterior` - Building exterior photos
     - `common_area` - Lobbies, hallways, shared spaces
     - `amenity` - Gyms, pools, gardens, parking
     - `floor_plan` - Building floor plan diagrams
   - **Properties** support 13 image categories:
     - `exterior` - Unit-specific exterior views
     - `interior` - General interior shots
     - `floor_plan` - Unit floor plan diagrams (higher resolution retained)
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

5. **Investagon Integration**: Full API synchronization with project support:
   - Projects are synced first, then properties with proper associations
   - Individual property sync automatically creates/updates parent project
   - Bulk synchronization handles project-property hierarchy
   - Automatic hourly sync (configurable)
   - Status tracking: active, pre_sale, draft flags
   - Comprehensive error handling and retry logic
   - Image import for both projects and properties
   - Project images come from /projects endpoint, not /api_projects
   - Duplicate image detection prevents re-importing existing images
   - **Project Status Update**: Automatically updates project status after syncing properties

6. **Financial Analytics**: Automatic calculations including:
   - Project-level statistics (total units, occupancy rates)
   - Property-level yields and returns
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
   - Default calculation parameters (equity percentage, interest rates)
   - Property type-specific customization
   - Active/inactive status management
2. **Link Generation**: Generate unique shareable links with:
   - Short, secure link IDs (8-character UUIDs)
   - Comprehensive preset calculation parameters:
     - `preset_equity_percentage` (Float) - Equity percentage (0-100)
     - `preset_interest_rate` (Float) - Interest rate percentage
     - `preset_repayment_rate` (Float) - Repayment rate percentage
     - `preset_gross_income` (Decimal) - Annual gross income in EUR
     - `preset_is_married` (Boolean) - Marital status for tax calculations
     - `preset_monthly_rent` (Decimal) - Monthly rent override
   - Custom messages for personalization
   - Password protection and expiration dates
   - Visible section controls (show/hide specific content)
3. **Public Access**: Public expose viewing with:
   - No authentication required for investors
   - Password verification when protected
   - Automatic view tracking with visitor analytics
   - City information integration for location context
   - All financial parameters from link presets applied to calculations
4. **Analytics**: Comprehensive tracking including:
   - View count and timestamps (first/last viewed)
   - Visitor information (IP, user agent, referrer)
   - Individual view records for detailed analysis
   - Link performance metrics

**Note**: The deprecated fields `preset_equity_amount` and `preset_loan_term_years` have been removed. Loan terms are now calculated automatically from interest and repayment rates using the annuity loan formula.

### Property Display Optimizations

1. **Thumbnail Strategy**: Properties inherit thumbnails from projects when they don't have their own images
   - Property service checks property images first
   - Falls back to project images if no property-specific images exist
   - Requires eager loading of project.images relationship using subqueryload
   - Consistent with PropertyResponse behavior in detail views
   - Implemented in both backend PropertyService and frontend objects page

2. **Visibility Filtering**: Role-based access control for properties and projects
   - PropertyService checks user permissions via `properties:update` permission
   - Sales people (without update permission) only see properties with visibility = 1
   - Tenant admins and property managers see all properties (-1, 0, 1)
   - ProjectService filters projects based on property visibility using subqueries
   - Avoids DISTINCT on JSON columns by using Project.id subquery
   - Project visibility_status calculated dynamically from property visibility values

3. **Address Display**: Properties show full project address with unit number
   - Format: "Street HouseNumber - WE UnitNumber" (e.g., "Gotenstraße 69 - WE 103")
   - PropertyOverview schema includes project_name, project_street, project_house_number
   - Extracted from project relationship during list operations
   - Fallback to project name if address fields not available

4. **Schema Validation**: Manual construction of overview objects for complex computed properties
   - PropertyService constructs PropertyOverview objects explicitly
   - ProjectService includes visibility_status in ProjectOverview schema
   - Avoids Pydantic validation issues with SQLAlchemy ORM objects
   - Consistent pattern across services
   - Enables inclusion of computed properties like thumbnail_url and visibility_status

5. **Frontend Filter Improvements**: 
   - Range sliders for construction year (projects), price, size, and rental yield (properties)
   - Real-time value display on sliders
   - Configurable ranges: price (€0-1M), size (0-200m²), year (1900-2024), rental yield (0-10%)
   - No API calls until slider release for performance

6. **Rental Yield (Bruttomietrendite) Calculation**:
   - Automatically calculated for all properties: (annual rent / purchase price) × 100
   - Displayed on property cards in list views and project detail views
   - Projects show rental yield range (min-max) of their properties
   - Filterable via range slider (0-10%)
   - Calculated in PropertyService for list views
   - Calculated in project detail endpoint for nested properties
   - Backend filtering supports min/max rental yield parameters

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
- Energy consumption mapping: `power_consumption` from Investagon → `energy_consumption` field
- Primary energy consumption field available for manual entry (not synced from Investagon)

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

**Project Management Permissions:**
- `projects:create` - Create new projects
- `projects:read` - View projects
- `projects:update` - Edit project details
- `projects:delete` - Remove projects

**Property Management Permissions:**
- `properties:create` - Create new properties
- `properties:read` - View properties
- `properties:update` - Edit property details
- `properties:delete` - Remove properties

**Image Management Permissions:**
- `images:upload` - Upload property/city/project images
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
- `investagon:sync` - Trigger property and project synchronization

### Investagon Active Status Values

The `active` field from Investagon represents the property sale status with these specific values:
- `0` = Verkauft (Sold)
- `1` = Frei (Available)
- `5` = Angefragt (Requested/Inquired)
- `6` = Reserviert (Reserved)
- `7` = Notartermin (Notary Appointment)
- `9` = Notarvorbereitung (Notary Preparation)

**Implementation Notes:**
- The `status` field has been removed from the Property model - use `active` field directly
- Frontend displays German labels based on the `active` value
- No mapping/transformation during sync - store Investagon values as-is
- The `active` field is preserved exactly as received from Investagon
- Project status is calculated from property active values:
  - If any property has `active=1` (Frei) → project is 'available'
  - If all properties have `active=0,7,9` (sold/sale process) → project is 'sold'
  - If all properties have `active=5,6` (reserved/inquired) → project is 'reserved'
  - Mixed status defaults to 'reserved' if any reserved properties exist

**Role Assignments:**
- `sales_person` - Can view projects and properties, create expose links
- `property_manager` - Can manage projects, properties, images and exposes, sync from Investagon
- `tenant_admin` - Full access to all tenant resources including projects

## Current Implementation Status

### Recently Completed Features

**Database Schema (June 2025 Updates):**
- Complete multi-tenant property management schema
- Geographic data integration (latitude/longitude, city relationships)
- Enhanced Investagon API compatibility with status flags
- Advanced property investment fields (object share, depreciation settings)
- Comprehensive image management for properties and cities
- Removed redundant apartment_number field (consolidated into unit_number)
- Property visibility field for role-based access control
- Added primary_energy_consumption field to properties table for Primärenergieverbrauch

**API Implementation:**
- Full CRUD operations for all core entities
- Advanced filtering and pagination for property lists
- Comprehensive image upload with category-based processing
- Public expose access endpoints for investor viewing
- Investagon synchronization with multiple sync modes
- Background task processing with error handling
- Project address extraction from property data during Investagon sync
- Construction year filtering for projects
- **Role-based visibility filtering**: Properties filtered based on user permissions in service layer
- **Project visibility calculation**: Dynamic visibility_status based on contained properties
- **Investagon sync improvements**: Automatic project status update after property sync
- **User parameter support**: Services accept current_user for permission-based filtering
- **Rental yield calculation**: Automatic Bruttomietrendite calculation for all properties
- **Advanced property filtering**: Support for rental yield range filtering
- **Return to previous page**: Save and restore location after login/logout
- **Natural sorting**: Properties sorted by unit number in project views

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
- Rental yield filtering done post-query for computed fields (consider database column for optimization)
- Natural number sorting for unit numbers in project detail views

**Security Implementation:**
- All tenant data isolated through row-level security
- JWT tokens include tenant context for automatic filtering
- Image uploads validated for file type and size limits
- Public expose links use secure, unpredictable identifiers
- Comprehensive audit trails for administrative actions

### Mapper Pattern for ORM to Response Conversion

Use the mapper pattern when Pydantic's `model_validate()` fails with complex ORM relationships or computed fields.

**Location**: `app/mappers/` directory

**Existing Mappers:**
- `property_mapper.py`: Handles property-to-response conversions with computed fields
- `expose_mapper.py`: Handles expose link conversions

**When to Use:**
- Complex ORM relationships need special handling
- Computed fields (e.g., `gross_rental_yield`, `thumbnail_url`)
- Response format differs from ORM structure
- Fallback logic required (e.g., property → project images)

**Best Practices:**
- Check relationships exist before accessing: `if prop.project:`
- Keep mappers pure - no database queries
- Handle None values gracefully
- Document complex calculations

### Energy Field Synchronization

**Investagon Mappings:**
- `energy_efficiency_class` → `energy_class` (auto-converted to UPPERCASE)
- `power_consumption` → `energy_consumption` (float with null checks)
- `energy_certificate_type` → `energy_certificate_type`
- `heating_type` → `heating_type`
- `primary_energy_consumption` - Manual entry only (not from Investagon)

**Key Points:**
- Investagon sends lowercase energy classes ("c") - converted to uppercase ("C")
- Handle null values with `is not None` checks
- Projects inherit energy data from first property during sync

### Common Audit Logger Errors

**Error: `'AuditLogger' object has no attribute 'log_event'`**

**Correct Methods:**
- `log_business_event()` - CRUD operations
- `log_auth_event()` - Authentication events  
- `log_security_event()` - Security events
- `log_admin_action()` - Admin actions
- `log_system_event()` - System events

**Example:**
```python
audit_logger.log_business_event(
    db=db,
    action="CITY_CREATED",
    user_id=current_user.id,
    tenant_id=current_user.tenant_id,
    resource_type="city",
    resource_id=city.id,
    new_values={"name": city.name}
)
```

## Audit Logger Usage Guide

The audit logger (`app/utils/audit.py`) provides comprehensive activity tracking across the application. Here's how to use it:

### Import and Instantiation
```python
from app.utils.audit import AuditLogger

# Create an instance (typically at module level)
audit_logger = AuditLogger()
```

### Available Methods

#### 1. Business Event Logging
For CRUD operations and business logic changes:
```python
audit_logger.log_business_event(
    db=db,                          # Database session
    action="RESOURCE_CREATED",      # Action type (e.g., USER_UPDATED, PROJECT_DELETED)
    user_id=current_user.id,        # User performing the action
    tenant_id=tenant_id,            # Current tenant context
    resource_type="resource_name",  # Type of resource (e.g., "user", "project", "property")
    resource_id=resource.id,        # ID of the affected resource
    old_values={"field": "old"},    # Optional: Previous values for updates
    new_values={"field": "new"}     # Optional: New values for creates/updates
)
```

#### 2. Authentication Event Logging
For login, logout, and authentication-related events:
```python
audit_logger.log_auth_event(
    db=db,
    action="LOGIN_SUCCESS",         # Action type (LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, etc.)
    user_id=user.id,               # User ID (if available)
    tenant_id=tenant_id,           # Tenant ID (if available)
    details={                      # Additional details
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "reason": "Invalid password"
    }
)
```

#### 3. Security Event Logging
For security-related incidents:
```python
audit_logger.log_security_event(
    db=db,
    action="UNAUTHORIZED_ACCESS",   # Security event type
    user_id=user_id,               # User ID if known
    tenant_id=tenant_id,           # Tenant ID if applicable
    severity="HIGH",               # Severity level (LOW, MEDIUM, HIGH, CRITICAL)
    details={                      # Event details
        "endpoint": "/api/v1/admin",
        "ip_address": request.client.host
    }
)
```

#### 4. Admin Action Logging
For administrative operations:
```python
audit_logger.log_admin_action(
    db=db,
    action="TENANT_SETTINGS_UPDATED",  # Admin action type
    admin_id=current_user.id,          # Admin user ID
    tenant_id=tenant_id,               # Affected tenant
    target_type="tenant_settings",     # Type of target
    target_id=tenant.id,               # Target ID
    details={                          # Action details
        "settings_changed": ["max_users", "billing_plan"]
    }
)
```

#### 5. System Event Logging
For system-level events and background tasks:
```python
audit_logger.log_system_event(
    db=db,
    action="SYNC_COMPLETED",        # System event type
    component="InvestagonSync",     # System component
    details={                       # Event details
        "properties_synced": 150,
        "duration_seconds": 45.3,
        "errors": 0
    }
)
```

### Common Action Types

**Business Events:**
- `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`, `USER_PROVISION_UPDATED`
- `PROJECT_CREATED`, `PROJECT_UPDATED`, `PROJECT_DELETED`
- `PROPERTY_CREATED`, `PROPERTY_UPDATED`, `PROPERTY_DELETED`
- `EXPOSE_CREATED`, `EXPOSE_ACCESSED`, `EXPOSE_DELETED`
- `IMAGE_UPLOADED`, `IMAGE_DELETED`

**Authentication Events:**
- `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`
- `PASSWORD_CHANGED`, `PASSWORD_RESET_REQUESTED`
- `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`
- `EMAIL_VERIFIED`, `USER_INVITED`

**Security Events:**
- `UNAUTHORIZED_ACCESS`, `PERMISSION_DENIED`
- `SUSPICIOUS_ACTIVITY`, `RATE_LIMIT_EXCEEDED`
- `INVALID_TOKEN`, `SESSION_HIJACK_ATTEMPT`

**Admin Actions:**
- `USER_ROLE_ASSIGNED`, `USER_ROLE_REMOVED`
- `TENANT_CREATED`, `TENANT_UPDATED`
- `PERMISSION_GRANTED`, `PERMISSION_REVOKED`
- `BULK_USER_ACTION`, `SYSTEM_CONFIG_CHANGED`

**System Events:**
- `SYNC_STARTED`, `SYNC_COMPLETED`, `SYNC_FAILED`
- `BACKUP_CREATED`, `MAINTENANCE_PERFORMED`
- `ERROR_THRESHOLD_EXCEEDED`, `RESOURCE_CLEANUP`

### Best Practices

1. **Always log significant actions**: User modifications, resource changes, authentication events
2. **Include relevant context**: User ID, tenant ID, resource IDs, and meaningful details
3. **Use appropriate severity levels**: For security events, choose LOW, MEDIUM, HIGH, or CRITICAL
4. **Avoid logging sensitive data**: Never log passwords, tokens, or personal information
5. **Be consistent with action names**: Use RESOURCE_ACTION format (e.g., USER_UPDATED)
6. **Log both success and failure**: Track failed attempts for security analysis

### Example Usage in Context

```python
@router.put("/{user_id}/provision")
async def update_user_provision(
    user_id: uuid.UUID,
    provision_percentage: int,
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    # ... validation logic ...
    
    # Store old value for audit
    old_provision = target_user.provision_percentage
    
    # Update the value
    target_user.provision_percentage = provision_percentage
    
    # Log the business event
    audit_logger.log_business_event(
        db=db,
        action="USER_PROVISION_UPDATED",
        user_id=current_user.id,
        tenant_id=effective_tenant_id,
        resource_type="user",
        resource_id=user_id,
        old_values={"provision_percentage": old_provision},
        new_values={"provision_percentage": provision_percentage}
    )
    
    db.commit()
    return UserResponse.model_validate(target_user)
```

### Common Schema Errors and Solutions

**Error: `Field required` for 'id' in request schemas**
- **Cause**: Using `BaseSchema` for request schemas when it includes an `id` field
- **Solution**: Use `BaseSchema` for request schemas and `BaseResponseSchema` for response schemas
- **Pattern**:
  ```python
  # For requests (no ID needed)
  class LoginRequest(BaseSchema):
      email: str
      password: str
  
  # For responses (ID included automatically)
  class UserResponse(BaseResponseSchema):
      email: str
      name: str
      # id: UUID is inherited from BaseResponseSchema
  ```

### Common Permission Errors and Solutions

**Error: `AttributeError: 'function' object has no attribute 'is_super_admin'`**
- **Cause**: Using `require_permission` as a decorator instead of a dependency
- **Solution**: Use `_: bool = Depends(require_permission("resource", "action"))` as a function parameter

**Error: `TypeError: require_permission() missing 1 required positional argument: 'action'`**
- **Cause**: Using colon notation like `"projects:create"` instead of separate parameters
- **Solution**: Use two parameters: `require_permission("projects", "create")`

**Error: User authentication issues**
- **Cause**: Using `get_current_user` instead of `get_current_active_user`
- **Solution**: Always import and use `get_current_active_user` for authenticated endpoints

**Correct Import Pattern:**
```python
from app.dependencies import (
    get_db,
    get_current_active_user,  # ✓ Use this for authenticated endpoints
    get_current_tenant_id,
    require_permission
)
```

## Micro Location Feature

See root CLAUDE.md for complete documentation. Backend-specific notes:

**Service**: `app/services/chatgpt_service.py`
- Uses OpenAI Assistants API v2 (synchronous)
- Requires pre-configured assistant in OpenAI dashboard
- Auto-fetches on project creation
- Manual refresh via `POST /api/v1/projects/{id}/refresh-micro-location`

**Configuration**:
```bash
OPENAI_API_KEY=your-key
OPENAI_ASSISTANT_ID=your-assistant-id
```

## Recent Updates (January 2025)

See root CLAUDE.md for complete documentation on:
- Micro Location Feature
- Expose Link Parameter Updates  
- Financial Calculations & Display Updates

Backend-specific implementations:
- `property_mapper.py` - Calculates total purchase price and monthly rent
- `expose_mapper.py` - Maps new expose link parameters
- Energy field mappings in Investagon sync