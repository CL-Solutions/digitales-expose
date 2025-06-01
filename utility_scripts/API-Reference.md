# Enterprise Multi-Tenant App

Enterprise Multi-Tenant API with OAuth Support

**Version:** 1.0.0

## Authentication
### BearerAuth
- **Type:** http
- **Scheme:** bearer
- **Description:** JWT Bearer token

## Endpoints

### Health

#### Health Check

**GET** `/health`

Basic health check endpoint

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

---

#### Detailed Health Check

**GET** `/health/detailed`

Detailed health check with dependencies

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

---

#### Readiness Check

**GET** `/ready`

Kubernetes readiness probe

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

---

### Authentication

#### Create User By Admin

**POST** `/api/v1/auth/create-user`

Creates a new user (admin only) - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `email` (string) (format: email) *(required)*: User email address
  - `first_name` (string) (minLength: 1, maxLength: 100) *(required)*: First name
  - `last_name` (string) (minLength: 1, maxLength: 100) *(required)*: Last name
  - `password` (unknown): User password (optional)
  - `role_ids` (array): Role IDs to assign
    **Array items:**
      **Type:** `string`
  - `send_welcome_email` (boolean): Send welcome email
  - `require_email_verification` (boolean): Require email verification
  - `tenant_id` (unknown): Tenant ID (only for super admin)

**Generated Example:**
```json
{
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Type: `object`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Login Local User

**POST** `/api/v1/auth/login`

Local user login - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `email` (string) (format: email) *(required)*: User email
  - `password` (string) (minLength: 1) *(required)*: User password
  - `remember_me` (boolean): Extended session duration

**Generated Example:**
```json
{
  "email": "user@example.com",
  "password": "string",
  "remember_me": true
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TokenResponse`
  - Key Properties:
    - `access_token` (string) *(required)*: JWT access token
    - `refresh_token` (string) *(required)*: JWT refresh token
    - `token_type` (string): Token type
    - `expires_in` (integer) *(required)*: Token expiration in seconds
    - `user_id` (string) *(required)*: User ID

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Logout User

**POST** `/api/v1/auth/logout`

User logout - Uses AuthService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

---

#### Request Password Reset

**POST** `/api/v1/auth/password-reset/request`

Password reset request - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `email` (string) (format: email) *(required)*: User email address

**Generated Example:**
```json
{
  "email": "user@example.com"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Confirm Password Reset

**POST** `/api/v1/auth/password-reset/confirm`

Execute password reset - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `token` (string) *(required)*: Password reset token
  - `password` (string) (minLength: 8) *(required)*: New password

**Generated Example:**
```json
{
  "token": "string",
  "password": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Verify Email

**POST** `/api/v1/auth/verify-email`

Email verification - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `token` (string) *(required)*: Email verification token

**Generated Example:**
```json
{
  "token": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Change Password

**POST** `/api/v1/auth/change-password`

Change password for logged in users - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `current_password` (string) *(required)*: Current password
  - `password` (string) (minLength: 8) *(required)*: New password

**Generated Example:**
```json
{
  "current_password": "string",
  "password": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Oauth Login Url

**GET** `/api/v1/auth/oauth/{provider}/login/{tenant_slug}`

Generate OAuth login URL for specific tenant - Uses EnterpriseOAuthService

**Parameters:**

- `provider` (path) `string` *(required)*: 
- `tenant_slug` (path) `string` *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Oauth Callback

**POST** `/api/v1/auth/oauth/{provider}/callback/{tenant_slug}`

OAuth callback for tenant-specific authentication - Uses EnterpriseOAuthService

**Parameters:**

- `provider` (path) `string` *(required)*: 
- `tenant_slug` (path) `string` *(required)*: 

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `code` (string) *(required)*: Authorization code from OAuth provider
  - `state` (unknown): State parameter for CSRF protection

**Generated Example:**
```json
{
  "code": "string",
  "state": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Super Admin Impersonate

**POST** `/api/v1/auth/impersonate`

Super admin impersonation - Uses AuthService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `tenant_id` (string) (format: uuid) *(required)*: Tenant ID to impersonate
  - `reason` (unknown): Reason for impersonation

**Generated Example:**
```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "reason": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TokenResponse`
  - Key Properties:
    - `access_token` (string) *(required)*: JWT access token
    - `refresh_token` (string) *(required)*: JWT refresh token
    - `token_type` (string): Token type
    - `expires_in` (integer) *(required)*: Token expiration in seconds
    - `user_id` (string) *(required)*: User ID

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### End Impersonation

**POST** `/api/v1/auth/end-impersonation`

End super admin impersonation - Uses AuthService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

---

#### Get Auth Status

**GET** `/api/v1/auth/status`

Current authentication status

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `AuthStatusResponse`
  - Key Properties:
    - `is_authenticated` (boolean) *(required)*: User authentication status
    - `user_id` (unknown): User ID if authenticated
    - `tenant_id` (unknown): Current tenant ID
    - `is_super_admin` (boolean): Super admin status
    - `is_impersonating` (boolean): Currently impersonating another tenant
    - ... and 3 more properties

**401** - Authentication failed

**403** - Access denied

---

#### Get Login History

**GET** `/api/v1/auth/history`

Login history for current user

**Parameters:**

- `limit` (query) `integer`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Type: `array`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Security Events

**GET** `/api/v1/auth/security-events`

Security events for current user

**Parameters:**

- `limit` (query) `integer`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Type: `array`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Refresh Access Token

**POST** `/api/v1/auth/refresh`

Refresh access token with refresh token

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `refresh_token` (string) *(required)*: Valid refresh token

**Generated Example:**
```json
{
  "refresh_token": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TokenResponse`
  - Key Properties:
    - `access_token` (string) *(required)*: JWT access token
    - `refresh_token` (string) *(required)*: JWT refresh token
    - `token_type` (string): Token type
    - `expires_in` (integer) *(required)*: Token expiration in seconds
    - `user_id` (string) *(required)*: User ID

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User Sessions

**GET** `/api/v1/auth/sessions`

Get all active sessions for current user - Uses UserService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

---

#### Terminate All Sessions

**DELETE** `/api/v1/auth/sessions`

Terminate all sessions for current user - Uses UserService

**Parameters:**

- `keep_current` (query) `boolean`: Keep current session active

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Terminate Session

**DELETE** `/api/v1/auth/sessions/{session_id}`

Terminate a specific session - Uses UserService

**Parameters:**

- `session_id` (path) `string` (format: uuid) *(required)*: Session ID to terminate

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Security Settings

**GET** `/api/v1/auth/security/settings`

Get current user's security settings - Uses UserService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

---

#### Resend Email Verification

**POST** `/api/v1/auth/security/email/resend-verification`

Resend email verification

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication failed

**403** - Access denied

---

### User Management

#### Get Current User Profile

**GET** `/api/v1/users/me`

Get current user profile - Uses RBACService for permissions

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserProfileResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `email` (string) *(required)*: User email address
    - `first_name` (string) *(required)*: First name
    - `last_name` (string) *(required)*: Last name
    - ... and 12 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

---

#### Update Current User Profile

**PUT** `/api/v1/users/me`

Update current user profile - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `first_name` (unknown): 
  - `last_name` (unknown): 
  - `is_active` (unknown): 
  - `avatar_url` (unknown): Avatar image URL

**Generated Example:**
```json
{
  "first_name": {},
  "last_name": {},
  "is_active": {},
  "avatar_url": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `email` (string) *(required)*: User email address
    - `first_name` (string) *(required)*: First name
    - `last_name` (string) *(required)*: Last name
    - ... and 9 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Users

**GET** `/api/v1/users/`

List all users in tenant (with filtering/pagination)

**Parameters:**

- `search` (query) `string`: 
- `sort_by` (query) `string`: 
- `sort_order` (query) `string` (options: asc, desc): 
- `page` (query) `integer`: 
- `page_size` (query) `integer`: 
- `auth_method` (query) `string`: 
- `is_active` (query) `string`: 
- `is_verified` (query) `string`: 
- `role_id` (query) `string`: 
- `tenant_id` (query) `string`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserListResponse`
  - Key Properties:
    - `users` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `page` (integer) *(required)*: 
    - `page_size` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User By Id

**GET** `/api/v1/users/{user_id}`

Get specific user - Uses RBACService for permissions

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserProfileResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `email` (string) *(required)*: User email address
    - `first_name` (string) *(required)*: First name
    - `last_name` (string) *(required)*: Last name
    - ... and 12 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update User

**PUT** `/api/v1/users/{user_id}`

Update user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `first_name` (unknown): 
  - `last_name` (unknown): 
  - `is_active` (unknown): 
  - `avatar_url` (unknown): Avatar image URL

**Generated Example:**
```json
{
  "first_name": {},
  "last_name": {},
  "is_active": {},
  "avatar_url": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `email` (string) *(required)*: User email address
    - `first_name` (string) *(required)*: First name
    - `last_name` (string) *(required)*: Last name
    - ... and 9 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Deactivate User

**DELETE** `/api/v1/users/{user_id}`

Deactivate user (soft delete) - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User Sessions

**GET** `/api/v1/users/{user_id}/sessions`

Get active sessions for a user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ActiveSessionsResponse`
  - Key Properties:
    - `sessions` (array) *(required)*: 
    - `total_active` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Terminate User Sessions

**DELETE** `/api/v1/users/{user_id}/sessions`

Terminate user sessions - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `session_id` (unknown): Specific session to terminate (if not provided, terminates current session)
  - `terminate_all` (boolean): Terminate all sessions for user

**Generated Example:**
```json
{
  "session_id": {},
  "terminate_all": true
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Invite User

**POST** `/api/v1/users/invite`

Invite a new user - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `email` (string) (format: email) *(required)*: Email address to invite
  - `first_name` (string) (minLength: 1, maxLength: 100) *(required)*: 
  - `last_name` (string) (minLength: 1, maxLength: 100) *(required)*: 
  - `role_ids` (array) *(required)*: Role IDs to assign
    **Array items:**
      **Type:** `string`
  - `welcome_message` (unknown): Custom welcome message
  - `expires_in_days` (integer) (min: 1.0, max: 30.0): Invitation expiry in days

**Generated Example:**
```json
{
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string",
  "role_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserInviteResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `id` (string) *(required)*: 
    - `email` (string) *(required)*: 
    - `invited_by` (string) *(required)*: 
    - ... and 3 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Bulk Create Users

**POST** `/api/v1/users/bulk/create`

Create multiple users at once - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `users` (array) *(required)*: 
    **Array items:**
      **Type:** `object`
      **Properties:**
        - `email` (string) (format: email) *(required)*: User email address
        - `first_name` (string) (minLength: 1, maxLength: 100) *(required)*: First name
        - `last_name` (string) (minLength: 1, maxLength: 100) *(required)*: Last name
        - `is_active` (boolean): User active status
        - `password` (unknown): User password (optional, will generate if not provided)
        - `role_ids` (array): Role IDs to assign
          **Array items:**
            **Type:** `string`
        - `send_welcome_email` (boolean): Send welcome email to user
        - `require_email_verification` (boolean): Require email verification before login
        - `tenant_id` (unknown): Tenant ID (only for super admin)
  - `send_welcome_emails` (boolean): 
  - `default_role_id` (unknown): Default role to assign if user has no roles

**Generated Example:**
```json
{
  "users": [
    {
      "email": "user@example.com",
      "first_name": "string",
      "last_name": "string"
    }
  ],
  "send_welcome_emails": true,
  "default_role_id": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserBulkCreateResponse`
  - Key Properties:
    - `created_users` (array) *(required)*: 
    - `failed_users` (array) *(required)*: Users that failed to create with error details
    - `total_created` (integer) *(required)*: 
    - `total_failed` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Bulk User Action

**POST** `/api/v1/users/bulk/action`

Perform bulk actions on users - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `user_ids` (array) *(required)*: 
    **Array items:**
      **Type:** `string`
  - `action` (string) (options: activate, deactivate, verify, lock, unlock, delete) *(required)*: Action to perform
  - `reason` (unknown): Reason for the action

**Generated Example:**
```json
{
  "user_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "action": "activate",
  "reason": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserBulkActionResponse`
  - Key Properties:
    - `successful_user_ids` (array) *(required)*: 
    - `failed_user_ids` (array) *(required)*: 
    - `errors` (object) *(required)*: Error messages for failed actions
    - `total_processed` (integer) *(required)*: 
    - `total_successful` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User Stats

**GET** `/api/v1/users/stats`

User statistics for current tenant - Uses UserService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserStatsResponse`
  - Key Properties:
    - `total_users` (integer) *(required)*: 
    - `active_users` (integer) *(required)*: 
    - `verified_users` (integer) *(required)*: 
    - `users_by_auth_method` (object) *(required)*: 
    - `recent_logins` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

---

#### Get User Security Info

**GET** `/api/v1/users/{user_id}/security`

Security information for a user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `UserSecurityInfo`
  - Key Properties:
    - `user_id` (string) *(required)*: 
    - `failed_login_attempts` (integer) *(required)*: 
    - `locked_until` (unknown) *(required)*: 
    - `last_login_at` (unknown) *(required)*: 
    - `last_password_change` (unknown) *(required)*: 
    - ... and 3 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Change Current User Password

**POST** `/api/v1/users/me/change-password`

Change password for current user - Uses UserService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `current_password` (string) *(required)*: Current password
  - `new_password` (string) (minLength: 8) *(required)*: New password

**Generated Example:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Export Users

**GET** `/api/v1/users/export`

Export user list - Uses UserService

**Parameters:**

- `format` (query) `string`: Export format: csv, xlsx, json

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User Roles

**GET** `/api/v1/users/{user_id}/roles`

Get roles assigned to a user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `target_user_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Assign Role To User

**POST** `/api/v1/users/{user_id}/roles/{role_id}`

Assign a role to a user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `role_id` (path) `string` (format: uuid) *(required)*: Role ID
- `expires_in_days` (query) `string`: Role expiration in days

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Remove Role From User

**DELETE** `/api/v1/users/{user_id}/roles/{role_id}`

Remove a role from a user - Uses UserService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `role_id` (path) `string` (format: uuid) *(required)*: Role ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - User not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

### Role & Permission Management

#### Create Role

**POST** `/api/v1/rbac/roles`

Create a new role - Uses RBACService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (string) (minLength: 1, maxLength: 100) *(required)*: Role name
  - `description` (unknown): Role description
  - `is_system_role` (boolean): System-defined role
  - `permission_ids` (array): Permission IDs to assign
    **Array items:**
      **Type:** `string`

**Generated Example:**
```json
{
  "name": "string",
  "description": {},
  "is_system_role": true,
  "permission_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `RoleResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Role name
    - `description` (unknown): Role description
    - `is_system_role` (boolean): System-defined role
    - ... and 4 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Roles

**GET** `/api/v1/rbac/roles`

List all roles in tenant

**Parameters:**

- `page` (query) `integer`: 
- `page_size` (query) `integer`: 
- `search` (query) `string`: Search in role names
- `is_system_role` (query) `string`: Filter by system/custom roles

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `RoleListResponse`
  - Key Properties:
    - `roles` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `page` (integer) *(required)*: 
    - `page_size` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Role Details

**GET** `/api/v1/rbac/roles/{role_id}`

Get role with permissions - Uses RBACService

**Parameters:**

- `role_id` (path) `string` (format: uuid) *(required)*: Role ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `RoleDetailResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Role name
    - `description` (unknown): Role description
    - `is_system_role` (boolean): System-defined role
    - ... and 10 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Role

**PUT** `/api/v1/rbac/roles/{role_id}`

Update role - Uses RBACService

**Parameters:**

- `role_id` (path) `string` (format: uuid) *(required)*: Role ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (unknown): 
  - `description` (unknown): 
  - `permission_ids` (unknown): 

**Generated Example:**
```json
{
  "name": {},
  "description": {},
  "permission_ids": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `RoleResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Role name
    - `description` (unknown): Role description
    - `is_system_role` (boolean): System-defined role
    - ... and 4 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Delete Role

**DELETE** `/api/v1/rbac/roles/{role_id}`

Delete role - Uses RBACService

**Parameters:**

- `role_id` (path) `string` (format: uuid) *(required)*: Role ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Role Permissions

**PUT** `/api/v1/rbac/roles/{role_id}/permissions`

Update role permissions - Uses RBACService

**Parameters:**

- `role_id` (path) `string` (format: uuid) *(required)*: Role ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `add_permission_ids` (array): Permissions to add
    **Array items:**
      **Type:** `string`
  - `remove_permission_ids` (array): Permissions to remove
    **Array items:**
      **Type:** `string`

**Generated Example:**
```json
{
  "add_permission_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "remove_permission_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Clone Role

**POST** `/api/v1/rbac/roles/{role_id}/clone`

Clone an existing role - Uses RBACService

**Parameters:**

- `role_id` (path) `string` (format: uuid) *(required)*: Source role ID
- `new_role_name` (query) `string` *(required)*: New role name
- `new_role_description` (query) `string`: New role description

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Permissions

**GET** `/api/v1/rbac/permissions`

List all available permissions

**Parameters:**

- `resource` (query) `string`: Filter by resource

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Type: `array`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Create Permission

**POST** `/api/v1/rbac/permissions`

Create a new permission - Uses RBACService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `resource` (string) (minLength: 1, maxLength: 100) *(required)*: Resource name (e.g., 'users', 'projects')
  - `action` (string) (minLength: 1, maxLength: 50) *(required)*: Action name (e.g., 'create', 'read')
  - `description` (unknown): Permission description

**Generated Example:**
```json
{
  "resource": "string",
  "action": "string",
  "description": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `PermissionResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `resource` (string) *(required)*: Resource name (e.g., 'users', 'projects')
    - `action` (string) *(required)*: Action name (e.g., 'create', 'read')
    - `description` (unknown): Permission description
    - ... and 2 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Bulk Assign Roles

**POST** `/api/v1/rbac/roles/bulk-assign`

Assign roles to multiple users - Uses RBACService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `user_ids` (array) *(required)*: User IDs to assign roles to
    **Array items:**
      **Type:** `string`
  - `role_ids` (array) *(required)*: Role IDs to assign
    **Array items:**
      **Type:** `string`
  - `expires_at` (unknown): Optional expiration for role assignments

**Generated Example:**
```json
{
  "user_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "role_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "expires_at": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get User Permissions

**GET** `/api/v1/rbac/users/{user_id}/permissions`

Get all permissions for a user - Uses RBACService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Check User Permission

**GET** `/api/v1/rbac/users/{user_id}/permissions/check`

Check if user has specific permission - Uses RBACService

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID
- `resource` (query) `string` *(required)*: Resource name
- `action` (query) `string` *(required)*: Action name

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Rbac Statistics

**GET** `/api/v1/rbac/stats`

Get RBAC statistics - Uses RBACService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `RBACStatsResponse`
  - Key Properties:
    - `total_roles` (integer) *(required)*: 
    - `system_roles` (integer) *(required)*: 
    - `custom_roles` (integer) *(required)*: 
    - `total_permissions` (integer) *(required)*: 
    - `permissions_by_resource` (object) *(required)*: 
    - ... and 2 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

---

#### Get Role Usage Report

**GET** `/api/v1/rbac/reports/role-usage`

Get role usage report - Uses RBACService

**Parameters:**

- `days` (query) `integer`: Report period in days

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Permission Usage Report

**GET** `/api/v1/rbac/reports/permission-usage`

Get permission usage report - Uses RBACService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

---

#### Get Rbac Compliance Report

**GET** `/api/v1/rbac/reports/compliance`

Get RBAC compliance report - Uses RBACService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

---

#### Get Global Rbac Statistics

**GET** `/api/v1/rbac/global/stats`

Get global RBAC statistics (Super Admin only) - Uses RBACService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

---

#### Get Global Permission Usage Report

**GET** `/api/v1/rbac/global/reports/permission-usage`

Get global permission usage report (Super Admin only) - Uses RBACService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Role or permission not found

---

### Tenant Management

#### Create Tenant

**POST** `/api/v1/tenants/`

Create new tenant (Super Admin only)

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (string) (minLength: 2, maxLength: 255) *(required)*: Organization name
  - `domain` (unknown): Organization domain
  - `settings` (unknown): Tenant-specific settings
  - `subscription_plan` (string): Subscription plan
  - `max_users` (integer) (min: 1.0, max: 10000.0): Maximum number of users
  - `is_active` (boolean): Tenant active status
  - `slug` (string) (minLength: 2, maxLength: 100) *(required)*: URL-friendly identifier
  - `admin_email` (string) (format: email) *(required)*: Email of the first tenant admin
  - `admin_first_name` (string) (minLength: 1, maxLength: 100) *(required)*: 
  - `admin_last_name` (string) (minLength: 1, maxLength: 100) *(required)*: 
  - `admin_password` (unknown): Admin password (optional, will generate if not provided)

**Generated Example:**
```json
{
  "name": "string",
  "slug": "string",
  "admin_email": "user@example.com",
  "admin_first_name": "string",
  "admin_last_name": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TenantResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Organization name
    - `domain` (unknown): Organization domain
    - `settings` (unknown): Tenant-specific settings
    - ... and 6 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Tenants

**GET** `/api/v1/tenants/`

List all tenants (Super Admin only)

**Parameters:**

- `search` (query) `string`: 
- `sort_by` (query) `string`: 
- `sort_order` (query) `string` (options: asc, desc): 
- `page` (query) `integer`: 
- `page_size` (query) `integer`: 
- `subscription_plan` (query) `string`: 
- `is_active` (query) `string`: 
- `has_domain` (query) `string`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TenantListResponse`
  - Key Properties:
    - `tenants` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `page` (integer) *(required)*: 
    - `page_size` (integer) *(required)*: 

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Tenant By Id

**GET** `/api/v1/tenants/{tenant_id}`

Get specific tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TenantResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Organization name
    - `domain` (unknown): Organization domain
    - `settings` (unknown): Tenant-specific settings
    - ... and 6 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Tenant

**PUT** `/api/v1/tenants/{tenant_id}`

Update tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (unknown): 
  - `domain` (unknown): 
  - `settings` (unknown): 
  - `subscription_plan` (unknown): 
  - `max_users` (unknown): 
  - `is_active` (unknown): 

**Generated Example:**
```json
{}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TenantResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Organization name
    - `domain` (unknown): Organization domain
    - `settings` (unknown): Tenant-specific settings
    - ... and 6 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Delete Tenant

**DELETE** `/api/v1/tenants/{tenant_id}`

Delete tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Create Microsoft Identity Provider

**POST** `/api/v1/tenants/{tenant_id}/identity-providers/microsoft`

Configure Microsoft Entra ID Provider for tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `provider` (string): 
  - `provider_type` (string) (options: saml, oidc, oauth2): Protocol type
  - `client_id` (string) (minLength: 1) *(required)*: OAuth client ID
  - `discovery_endpoint` (unknown): OIDC discovery endpoint
  - `authorization_endpoint` (unknown): 
  - `token_endpoint` (unknown): 
  - `userinfo_endpoint` (unknown): 
  - `jwks_uri` (unknown): 
  - `user_attribute_mapping` (object): Map provider attributes to user fields
    **Type:** `object`
  - `role_attribute_mapping` (object): Map provider roles to system roles
    **Type:** `object`
  - `auto_provision_users` (boolean): Auto-create users on first login
  - `require_verified_email` (boolean): Require verified email from provider
  - `allowed_domains` (array): Restrict to specific email domains
    **Array items:**
      **Type:** `string`
  - `is_active` (boolean): Provider is active
  - `azure_tenant_id` (string) *(required)*: Microsoft Entra Tenant ID
  - `client_secret` (string) (minLength: 1) *(required)*: OAuth client secret
  - `default_role_name` (unknown): Default role for new users

**Generated Example:**
```json
{
  "client_id": "string",
  "azure_tenant_id": "string",
  "client_secret": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `IdentityProviderResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `provider` (string) *(required)*: OAuth provider type
    - `provider_type` (string): Protocol type
    - `client_id` (string) *(required)*: OAuth client ID
    - ... and 14 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Create Google Identity Provider

**POST** `/api/v1/tenants/{tenant_id}/identity-providers/google`

Configure Google Workspace Provider for tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `provider` (string): 
  - `provider_type` (string) (options: saml, oidc, oauth2): Protocol type
  - `client_id` (string) (minLength: 1) *(required)*: OAuth client ID
  - `discovery_endpoint` (unknown): OIDC discovery endpoint
  - `authorization_endpoint` (unknown): 
  - `token_endpoint` (unknown): 
  - `userinfo_endpoint` (unknown): 
  - `jwks_uri` (unknown): 
  - `user_attribute_mapping` (object): Map provider attributes to user fields
    **Type:** `object`
  - `role_attribute_mapping` (object): Map provider roles to system roles
    **Type:** `object`
  - `auto_provision_users` (boolean): Auto-create users on first login
  - `require_verified_email` (boolean): Require verified email from provider
  - `allowed_domains` (array): Restrict to specific email domains
    **Array items:**
      **Type:** `string`
  - `is_active` (boolean): Provider is active
  - `client_secret` (string) (minLength: 1) *(required)*: OAuth client secret
  - `default_role_name` (unknown): Default role for new users

**Generated Example:**
```json
{
  "client_id": "string",
  "client_secret": "string"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `IdentityProviderResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `provider` (string) *(required)*: OAuth provider type
    - `provider_type` (string): Protocol type
    - `client_id` (string) *(required)*: OAuth client ID
    - ... and 14 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Tenant Identity Providers

**GET** `/api/v1/tenants/{tenant_id}/identity-providers`

List all Identity Providers for a tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `IdentityProviderListResponse`
  - Key Properties:
    - `providers` (array) *(required)*: 
    - `total` (integer) *(required)*: 

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Identity Provider

**PUT** `/api/v1/tenants/{tenant_id}/identity-providers/{provider_id}`

Update Identity Provider configuration

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID
- `provider_id` (path) `string` (format: uuid) *(required)*: Provider ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `client_id` (unknown): 
  - `client_secret` (unknown): 
  - `azure_tenant_id` (unknown): 
  - `discovery_endpoint` (unknown): 
  - `user_attribute_mapping` (unknown): 
  - `role_attribute_mapping` (unknown): 
  - `auto_provision_users` (unknown): 
  - `require_verified_email` (unknown): 
  - `allowed_domains` (unknown): 
  - `is_active` (unknown): 

**Generated Example:**
```json
{}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `IdentityProviderResponse`
  - Key Properties:
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `provider` (string) *(required)*: OAuth provider type
    - `provider_type` (string): Protocol type
    - `client_id` (string) *(required)*: OAuth client ID
    - ... and 14 more properties

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Delete Identity Provider

**DELETE** `/api/v1/tenants/{tenant_id}/identity-providers/{provider_id}`

Delete Identity Provider

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID
- `provider_id` (path) `string` (format: uuid) *(required)*: Provider ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Tenant Statistics

**GET** `/api/v1/tenants/stats`

Get overall tenant statistics

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `TenantStatsResponse`
  - Key Properties:
    - `total_tenants` (integer) *(required)*: 
    - `active_tenants` (integer) *(required)*: 
    - `total_users` (integer) *(required)*: 
    - `tenants_by_plan` (object) *(required)*: 
    - `recent_signups` (integer) *(required)*: 

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

---

#### Get Tenant Details Stats

**GET** `/api/v1/tenants/{tenant_id}/stats`

Get detailed statistics for a specific tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Activate Tenant

**POST** `/api/v1/tenants/{tenant_id}/activate`

Activate tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Deactivate Tenant

**POST** `/api/v1/tenants/{tenant_id}/deactivate`

Deactivate tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Export Tenant Data

**GET** `/api/v1/tenants/{tenant_id}/export`

Export tenant data for backup/migration

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID
- `include_users` (query) `boolean`: Include user data
- `include_projects` (query) `boolean`: Include project data
- `include_audit_logs` (query) `boolean`: Include audit logs

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Tenant Usage Report

**GET** `/api/v1/tenants/{tenant_id}/usage-report`

Get detailed usage report for a tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID
- `days` (query) `integer`: Report period in days

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Tenant Health

**GET** `/api/v1/tenants/{tenant_id}/health`

Check tenant health

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Clone Tenant

**POST** `/api/v1/tenants/{tenant_id}/clone`

Clone an existing tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Source tenant ID
- `new_tenant_name` (query) `string` *(required)*: New tenant name
- `new_tenant_slug` (query) `string` *(required)*: New tenant slug
- `include_users` (query) `boolean`: Include users in clone
- `include_data` (query) `boolean`: Include business data in clone

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Tenant Maintenance Cleanup

**POST** `/api/v1/tenants/{tenant_id}/maintenance/cleanup`

Perform maintenance cleanup for specific tenant

**Parameters:**

- `tenant_id` (path) `string` (format: uuid) *(required)*: Tenant ID
- `cleanup_type` (query) `string` *(required)*: Type: sessions, audit_logs, inactive_users
- `days_old` (query) `integer`: Remove data older than N days

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**404** - Tenant not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

### Projects & Documents

#### Create Project

**POST** `/api/v1/projects/`

Create new project - Uses ProjectService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (string) (minLength: 1, maxLength: 255) *(required)*: Project name
  - `description` (unknown): Project description
  - `status` (string) (options: active, completed, archived): Project status

**Generated Example:**
```json
{
  "name": "string",
  "description": {},
  "status": "active"
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ProjectResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Project name
    - ... and 6 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List Projects

**GET** `/api/v1/projects/`

List all projects in tenant - Uses ProjectService

**Parameters:**

- `search` (query) `string`: 
- `sort_by` (query) `string`: 
- `sort_order` (query) `string` (options: asc, desc): 
- `page` (query) `integer`: 
- `page_size` (query) `integer`: 
- `status` (query) `string`: 
- `created_by` (query) `string`: 
- `has_documents` (query) `string`: 
- `created_after` (query) `string`: 
- `created_before` (query) `string`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ProjectListResponse`
  - Key Properties:
    - `projects` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `page` (integer) *(required)*: 
    - `page_size` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Delete Project

**DELETE** `/api/v1/projects/{project_id}`

Delete project - Uses ProjectService

**Parameters:**

- `project_id` (path) `string` (format: uuid) *(required)*: Project ID
- `resource_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Project By Id

**GET** `/api/v1/projects/{project_id}`

Get specific project - Uses ProjectService

**Parameters:**

- `project_id` (path) `string` (format: uuid) *(required)*: Project ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ProjectDetailResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Project name
    - ... and 11 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Project

**PUT** `/api/v1/projects/{project_id}`

Update project - Uses ProjectService

**Parameters:**

- `project_id` (path) `string` (format: uuid) *(required)*: Project ID
- `resource_id` (query) `string` (format: uuid) *(required)*: 

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `name` (unknown): 
  - `description` (unknown): 
  - `status` (unknown): 

**Generated Example:**
```json
{
  "name": {},
  "description": {},
  "status": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ProjectResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `name` (string) *(required)*: Project name
    - ... and 6 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Create Document

**POST** `/api/v1/projects/{project_id}/documents`

Create new document in project - Uses DocumentService

**Parameters:**

- `project_id` (path) `string` (format: uuid) *(required)*: Project ID

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `title` (string) (minLength: 1, maxLength: 255) *(required)*: Document title
  - `content` (unknown): Document content
  - `project_id` (unknown): Associated project ID
  - `tags` (array): Document tags
    **Array items:**
      **Type:** `string`

**Generated Example:**
```json
{
  "title": "string",
  "content": {},
  "project_id": {},
  "tags": [
    "string"
  ]
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `DocumentResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `title` (string) *(required)*: Document title
    - ... and 9 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### List All Documents

**GET** `/api/v1/projects/documents`

List all documents in tenant - Uses DocumentService

**Parameters:**

- `search` (query) `string`: 
- `sort_by` (query) `string`: 
- `sort_order` (query) `string` (options: asc, desc): 
- `page` (query) `integer`: 
- `page_size` (query) `integer`: 
- `project_id` (query) `string`: 
- `created_by` (query) `string`: 
- `mime_type` (query) `string`: 
- `has_content` (query) `string`: 
- `file_size_min` (query) `string`: 
- `file_size_max` (query) `string`: 

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`

**Generated Example:**
```json
{}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `DocumentListResponse`
  - Key Properties:
    - `documents` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `page` (integer) *(required)*: 
    - `page_size` (integer) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Document By Id

**GET** `/api/v1/projects/documents/{document_id}`

Get specific document - Uses DocumentService

**Parameters:**

- `document_id` (path) `string` (format: uuid) *(required)*: Document ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `DocumentDetailResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `title` (string) *(required)*: Document title
    - ... and 14 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Update Document

**PUT** `/api/v1/projects/documents/{document_id}`

Update document - Uses DocumentService

**Parameters:**

- `document_id` (path) `string` (format: uuid) *(required)*: Document ID
- `resource_id` (query) `string` (format: uuid) *(required)*: 

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `title` (unknown): 
  - `content` (unknown): 
  - `project_id` (unknown): 
  - `tags` (unknown): 

**Generated Example:**
```json
{
  "title": {},
  "content": {},
  "project_id": {},
  "tags": {}
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `DocumentResponse`
  - Key Properties:
    - `created_by` (string) *(required)*: User who created this resource
    - `updated_by` (unknown): User who last updated this resource
    - `created_at` (string) *(required)*: Creation timestamp
    - `updated_at` (string) *(required)*: Last update timestamp
    - `title` (string) *(required)*: Document title
    - ... and 9 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Delete Document

**DELETE** `/api/v1/projects/documents/{document_id}`

Delete document - Uses DocumentService

**Parameters:**

- `document_id` (path) `string` (format: uuid) *(required)*: Document ID
- `resource_id` (query) `string` (format: uuid) *(required)*: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Upload Document

**POST** `/api/v1/projects/documents/upload`

Initiate document upload (Pre-signed URL)

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `title` (string) (minLength: 1, maxLength: 255) *(required)*: 
  - `project_id` (unknown): 
  - `tags` (array): 
    **Array items:**
      **Type:** `string`
  - `replace_existing` (boolean): Replace existing document with same name

**Generated Example:**
```json
{
  "title": "string",
  "project_id": {},
  "tags": [
    "string"
  ],
  "replace_existing": true
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `DocumentUploadResponse`
  - Key Properties:
    - `document_id` (string) *(required)*: 
    - `upload_url` (string) *(required)*: Pre-signed upload URL
    - `fields` (object) *(required)*: Form fields for upload
    - `expires_at` (string) *(required)*: Upload URL expiration

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Complete Document Upload

**POST** `/api/v1/projects/documents/{document_id}/upload-complete`

Complete document upload after file is uploaded

**Parameters:**

- `document_id` (path) `string` (format: uuid) *(required)*: Document ID
- `file_size` (query) `integer` *(required)*: Uploaded file size
- `mime_type` (query) `string` *(required)*: File MIME type

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Project Statistics

**GET** `/api/v1/projects/stats`

Project statistics for current tenant - Uses ProjectService

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ProjectStatsResponse`
  - Key Properties:
    - `total_projects` (integer) *(required)*: 
    - `active_projects` (integer) *(required)*: 
    - `completed_projects` (integer) *(required)*: 
    - `archived_projects` (integer) *(required)*: 
    - `projects_by_month` (object) *(required)*: 
    - ... and 2 more properties

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

---

#### Get Project Activity

**GET** `/api/v1/projects/activity`

Activity feed for projects and documents - Uses BusinessSearchService

**Parameters:**

- `limit` (query) `integer`: 
- `project_id` (query) `string`: Filter by project ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `ActivityFeedResponse`
  - Key Properties:
    - `activities` (array) *(required)*: 
    - `total` (integer) *(required)*: 
    - `has_more` (boolean) *(required)*: 

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Search Projects And Documents

**POST** `/api/v1/projects/search`

Search in projects and documents - Uses BusinessSearchService

**Request Body:**

**Content-Type:** `application/json`

**Type:** `object`
**Properties:**
  - `query` (string) (minLength: 1) *(required)*: Search query
  - `resource_types` (array): Types of resources to search
    **Array items:**
      **Type:** `string`
  - `filters` (object): Additional search filters
    **Type:** `object`
  - `limit` (integer) (min: 1.0, max: 100.0): Maximum results per resource type

**Generated Example:**
```json
{
  "query": "string",
  "resource_types": [
    "project"
  ],
  "filters": {},
  "limit": 1.0
}
```

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`
  - Schema: `SearchResponse`
  - Key Properties:
    - `query` (string) *(required)*: 
    - `total_results` (integer) *(required)*: 
    - `results_by_type` (object) *(required)*: 
    - `search_time_ms` (integer) *(required)*: Search execution time in milliseconds
    - `suggestions` (array): Search suggestions

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Share Document

**POST** `/api/v1/projects/documents/{document_id}/share`

Share document with other users - Uses DocumentService

**Parameters:**

- `document_id` (path) `string` (format: uuid) *(required)*: Document ID
- `share_with_emails` (query) `array` *(required)*: Emails to share with
- `permission_level` (query) `string`: Permission level: read, write
- `message` (query) `string`: Optional message

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Export Project

**POST** `/api/v1/projects/{project_id}/export`

Export project with all documents - Uses ProjectService

**Parameters:**

- `project_id` (path) `string` (format: uuid) *(required)*: Project ID
- `format` (query) `string`: Export format: json, zip
- `include_documents` (query) `boolean`: Include document content

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Insufficient permissions

**404** - Resource not found

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

### Super Admin

#### Get Admin Dashboard

**GET** `/api/v1/admin/dashboard`

Super Admin Dashboard Overview

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

---

#### Emergency Disable Tenant

**POST** `/api/v1/admin/emergency/disable-tenant`

Emergency Tenant Deaktivierung

**Parameters:**

- `tenant_id` (query) `string` (format: uuid) *(required)*: Tenant ID to disable
- `reason` (query) `string` *(required)*: Reason for emergency disable

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Emergency Global Logout

**POST** `/api/v1/admin/emergency/global-logout`

Emergency Global Logout aller User

**Parameters:**

- `reason` (query) `string` *(required)*: Reason for global logout

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Create System Backup

**POST** `/api/v1/admin/backup/create`

System Backup erstellen

**Parameters:**

- `backup_type` (query) `string`: Backup type: full, incremental, config

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Growth Analytics

**GET** `/api/v1/admin/analytics/growth`

Growth Analytics über verschiedene Zeiträume

**Parameters:**

- `period` (query) `string`: Period: 7d, 30d, 90d, 1y

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Audit Logs

**GET** `/api/v1/admin/audit/logs`

Audit Logs für das gesamte System

**Parameters:**

- `limit` (query) `integer`: 
- `user_id` (query) `string`: 
- `tenant_id` (query) `string`: 
- `action` (query) `string`: 
- `success` (query) `string`: 
- `start_date` (query) `string`: 
- `end_date` (query) `string`: 
- `ip_address` (query) `string`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Security Threats

**GET** `/api/v1/admin/security/threats`

Security Threat Detection

**Parameters:**

- `hours` (query) `integer`: Hours to look back

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### System Cleanup

**POST** `/api/v1/admin/maintenance/cleanup`

System Cleanup Operations

**Parameters:**

- `cleanup_type` (query) `string` *(required)*: Type: sessions, audit_logs, deleted_users
- `days_old` (query) `integer`: Remove data older than N days

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Maintenance Status

**GET** `/api/v1/admin/maintenance/status`

System Maintenance Status

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

---

#### Get Problematic Users

**GET** `/api/v1/admin/users/problematic`

Users mit Problemen identifizieren

**Parameters:**

- `limit` (query) `integer`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Unlock User Account

**POST** `/api/v1/admin/users/{user_id}/unlock`

User Account entsperren

**Parameters:**

- `user_id` (path) `string` (format: uuid) *(required)*: User ID

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get System Limits

**GET** `/api/v1/admin/config/limits`

System-weite Limits und Konfiguration

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

---

#### Get Feature Configuration

**GET** `/api/v1/admin/config/features`

Get system feature configuration

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

---

#### Toggle Feature

**POST** `/api/v1/admin/config/features/{feature_name}/toggle`

Toggle system feature on/off

**Parameters:**

- `feature_name` (path) `string` *(required)*: Feature name to toggle
- `enabled` (query) `boolean` *(required)*: Enable or disable the feature

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Get Performance Metrics

**GET** `/api/v1/admin/performance/metrics`

Get system performance metrics

**Parameters:**

- `hours` (query) `integer`: 

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

#### Send System Notification

**POST** `/api/v1/admin/notifications/send`

Send system-wide notification

**Parameters:**

- `title` (query) `string` *(required)*: Notification title
- `message` (query) `string` *(required)*: Notification message
- `severity` (query) `string`: Severity: info, warning, critical
- `target_tenants` (query) `string`: Target specific tenants

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

**401** - Authentication required

**403** - Super admin access required

**422** - Validation Error
  - Content-Type: `application/json`
  - Schema: `HTTPValidationError`
  - Key Properties:
    - `detail` (array): 

---

### Root

#### Root

**GET** `/`

Root endpoint with API information

**Responses:**

**200** - Successful Response
  - Content-Type: `application/json`

---
