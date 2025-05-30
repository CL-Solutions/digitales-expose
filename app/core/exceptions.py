# ================================
# CUSTOM EXCEPTIONS (core/exceptions.py)
# ================================

class AppException(Exception):
    """Base Exception für Application-spezifische Fehler"""
    
    def __init__(self, detail: str, status_code: int = 400, error_code: str = None):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(detail)

class AuthenticationError(AppException):
    """Authentication-spezifische Fehler"""
    
    def __init__(self, detail: str = "Authentication failed", error_code: str = "AUTH_FAILED"):
        super().__init__(detail, 401, error_code)

class AuthorizationError(AppException):
    """Authorization-spezifische Fehler"""
    
    def __init__(self, detail: str = "Access denied", error_code: str = "ACCESS_DENIED"):
        super().__init__(detail, 403, error_code)

class TenantError(AppException):
    """Tenant-spezifische Fehler"""
    
    def __init__(self, detail: str, error_code: str = "TENANT_ERROR"):
        super().__init__(detail, 400, error_code)

class ValidationError(AppException):
    """Validation-spezifische Fehler"""
    
    def __init__(self, detail: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(detail, 422, error_code)