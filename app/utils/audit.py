# ================================
# AUDIT LOGGING UTILITY (utils/audit.py)
# ================================

from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.user import User
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address
from decimal import Decimal
import uuid
import json
import logging

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Enterprise-grade audit logging utility for comprehensive system tracking.
    
    Features:
    - Comprehensive action logging with context
    - User and tenant isolation
    - IP address and user agent tracking
    - Structured data logging with JSON serialization
    - Performance optimized with bulk operations
    - Security-focused with sensitive data protection
    """
    
    def __init__(self, buffer_size: int = 100):
        """
        Initialize the audit logger.
        
        Args:
            buffer_size: Number of log entries to buffer before bulk insert
        """
        self.buffer_size = buffer_size
        self._log_buffer = []
    
    def log_auth_event(
        self,
        db: Session,
        action: str,
        user_id: Optional[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[Union[str, IPv4Address, IPv6Address]] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        impersonating_admin_id: Optional[uuid.UUID] = None
    ) -> AuditLog:
        """
        Log an authentication or authorization event.
        
        Args:
            db: Database session
            action: Action performed (e.g., 'LOGIN_SUCCESS', 'USER_CREATED')
            user_id: ID of user performing action
            tenant_id: Tenant context for the action
            details: Additional structured data about the event
            ip_address: Client IP address
            user_agent: Client user agent string
            resource_type: Type of resource affected (optional)
            resource_id: ID of affected resource (optional)
            old_values: Previous values before change (for updates)
            impersonating_admin_id: Super admin ID if impersonating
        
        Returns:
            Created AuditLog instance
        """
        try:
            # Sanitize and prepare data
            sanitized_details = self._sanitize_sensitive_data(details or {})
            sanitized_old_values = self._sanitize_sensitive_data(old_values or {})
            
            # Create audit log entry
            audit_entry = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                impersonating_super_admin_id=impersonating_admin_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=sanitized_old_values if sanitized_old_values else None,
                new_values=sanitized_details if sanitized_details else None,
                ip_address=self._normalize_ip_address(ip_address),
                user_agent=user_agent[:500] if user_agent else None  # Truncate long user agents
            )
            
            db.add(audit_entry)
            
            # Log to application logger as well
            self._log_to_application_logger(action, user_id, tenant_id, sanitized_details)
            
            return audit_entry
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            # Don't raise exception to avoid breaking the main flow
            return None
    
    def log_business_event(
        self,
        db: Session,
        action: str,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log business logic events (CRUD operations on business entities).
        
        Args:
            db: Database session
            action: Business action (e.g., 'PROJECT_CREATED', 'DOCUMENT_UPDATED')
            user_id: User performing the action
            tenant_id: Tenant context
            resource_type: Type of business resource ('project', 'document', etc.)
            resource_id: ID of the affected resource
            old_values: Previous values (for updates/deletes)
            new_values: New values (for creates/updates)
            additional_context: Extra context information
        
        Returns:
            Created AuditLog instance
        """
        # Combine new values with additional context
        combined_details = {**(new_values or {}), **(additional_context or {})}
        
        return self.log_auth_event(
            db=db,
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            details=combined_details,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values
        )
    
    def log_security_event(
        self,
        db: Session,
        action: str,
        severity: str,
        user_id: Optional[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
        threat_details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log security-related events with enhanced context.
        
        Args:
            db: Database session
            action: Security action (e.g., 'SUSPICIOUS_LOGIN', 'BRUTE_FORCE_DETECTED')
            severity: Severity level ('low', 'medium', 'high', 'critical')
            user_id: User ID if applicable
            tenant_id: Tenant context if applicable
            threat_details: Detailed information about the security event
            ip_address: Source IP address
            user_agent: User agent string
        
        Returns:
            Created AuditLog instance
        """
        enhanced_details = {
            "security_event": True,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            **threat_details
        }
        
        return self.log_auth_event(
            db=db,
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            details=enhanced_details,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="security"
        )
    
    def log_admin_action(
        self,
        db: Session,
        action: str,
        admin_user_id: uuid.UUID,
        target_tenant_id: Optional[uuid.UUID],
        target_user_id: Optional[uuid.UUID],
        admin_details: Dict[str, Any],
        impersonation_context: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log super admin and tenant admin actions.
        
        Args:
            db: Database session
            action: Admin action performed
            admin_user_id: ID of admin performing action
            target_tenant_id: Tenant being affected
            target_user_id: User being affected (if applicable)
            admin_details: Details about the admin action
            impersonation_context: Context if action performed during impersonation
        
        Returns:
            Created AuditLog instance
        """
        enhanced_details = {
            "admin_action": True,
            "target_user_id": str(target_user_id) if target_user_id else None,
            "impersonation_context": impersonation_context,
            **admin_details
        }
        
        return self.log_auth_event(
            db=db,
            action=action,
            user_id=admin_user_id,
            tenant_id=target_tenant_id,
            details=enhanced_details,
            resource_type="admin"
        )
    
    def log_system_event(
        self,
        db: Session,
        action: str,
        system_context: Dict[str, Any],
        triggered_by_user: Optional[uuid.UUID] = None
    ) -> AuditLog:
        """
        Log system-level events (maintenance, cleanup, etc.).
        
        Args:
            db: Database session
            action: System action performed
            system_context: Context about the system event
            triggered_by_user: User who triggered the system event (if applicable)
        
        Returns:
            Created AuditLog instance
        """
        enhanced_details = {
            "system_event": True,
            "triggered_at": datetime.utcnow().isoformat(),
            **system_context
        }
        
        return self.log_auth_event(
            db=db,
            action=action,
            user_id=triggered_by_user,
            tenant_id=None,  # System events are global
            details=enhanced_details,
            resource_type="system"
        )
    
    # ================================
    # BULK OPERATIONS
    # ================================
    
    def bulk_log_events(
        self,
        db: Session,
        events: list[Dict[str, Any]]
    ) -> int:
        """
        Efficiently log multiple events in a single database operation.
        
        Args:
            db: Database session
            events: List of event dictionaries with audit log data
        
        Returns:
            Number of events successfully logged
        """
        try:
            audit_entries = []
            
            for event in events:
                # Sanitize each event
                sanitized_details = self._sanitize_sensitive_data(event.get('details', {}))
                sanitized_old_values = self._sanitize_sensitive_data(event.get('old_values', {}))
                
                audit_entry = AuditLog(
                    tenant_id=event.get('tenant_id'),
                    user_id=event.get('user_id'),
                    action=event['action'],
                    resource_type=event.get('resource_type'),
                    resource_id=event.get('resource_id'),
                    old_values=sanitized_old_values if sanitized_old_values else None,
                    new_values=sanitized_details if sanitized_details else None,
                    ip_address=self._normalize_ip_address(event.get('ip_address')),
                    user_agent=event.get('user_agent', '')[:500]
                )
                audit_entries.append(audit_entry)
            
            db.add_all(audit_entries)
            return len(audit_entries)
            
        except Exception as e:
            logger.error(f"Failed to bulk log events: {e}", exc_info=True)
            return 0
    
    # ================================
    # QUERY HELPERS
    # ================================
    
    def get_user_activity_summary(
        self,
        db: Session,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific user.
        
        Args:
            db: Database session
            user_id: User ID to analyze
            tenant_id: Tenant context
            days: Number of days to look back
        
        Returns:
            Dictionary with activity summary
        """
        try:
            from sqlalchemy import func, and_
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get activity counts by action type
            activity_counts = db.query(
                AuditLog.action,
                func.count(AuditLog.id).label('count')
            ).filter(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= start_date
                )
            ).group_by(AuditLog.action).all()
            
            # Get recent activities
            recent_activities = db.query(AuditLog).filter(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= start_date
                )
            ).order_by(AuditLog.created_at.desc()).limit(10).all()
            
            return {
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "period_days": days,
                "activity_counts": {activity.action: activity.count for activity in activity_counts},
                "total_activities": sum(activity.count for activity in activity_counts),
                "recent_activities": [
                    {
                        "action": activity.action,
                        "timestamp": activity.created_at.isoformat(),
                        "resource_type": activity.resource_type,
                        "ip_address": str(activity.ip_address) if activity.ip_address else None
                    }
                    for activity in recent_activities
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get user activity summary: {e}", exc_info=True)
            return {}
    
    def get_tenant_security_events(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        severity_filter: Optional[str] = None,
        hours: int = 24
    ) -> list[Dict[str, Any]]:
        """
        Get security events for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID to analyze
            severity_filter: Filter by severity level
            hours: Number of hours to look back
        
        Returns:
            List of security events
        """
        try:
            from sqlalchemy import and_
            
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(AuditLog).filter(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= start_time,
                    AuditLog.action.like('%FAILED%') | 
                    AuditLog.action.like('%LOCKED%') |
                    AuditLog.action.like('%SUSPICIOUS%')
                )
            )
            
            if severity_filter:
                query = query.filter(
                    AuditLog.new_values.contains({"severity": severity_filter})
                )
            
            events = query.order_by(AuditLog.created_at.desc()).limit(100).all()
            
            return [
                {
                    "id": str(event.id),
                    "action": event.action,
                    "timestamp": event.created_at.isoformat(),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "ip_address": str(event.ip_address) if event.ip_address else None,
                    "details": event.new_values or {},
                    "severity": event.new_values.get("severity", "unknown") if event.new_values else "unknown"
                }
                for event in events
            ]
            
        except Exception as e:
            logger.error(f"Failed to get tenant security events: {e}", exc_info=True)
            return []
    
    # ================================
    # UTILITY METHODS
    # ================================
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or mask sensitive information from audit data.
        
        Args:
            data: Dictionary that may contain sensitive data
        
        Returns:
            Sanitized dictionary
        """
        if not data:
            return {}
        
        sensitive_keys = {
            'password', 'password_hash', 'client_secret', 'client_secret_hash',
            'token', 'access_token', 'refresh_token', 'api_key', 'secret',
            'private_key', 'credit_card', 'ssn', 'social_security'
        }
        
        sanitized = {}
        for key, value in data.items():
            # Convert key to string to handle both string and numeric keys
            key_str = str(key)
            key_lower = key_str.lower()
            
            if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_sensitive_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_sensitive_data(item) if isinstance(item, dict) 
                    else float(item) if isinstance(item, Decimal)
                    else item
                    for item in value
                ]
            else:
                # Convert Decimal to float for JSON serialization
                if isinstance(value, Decimal):
                    sanitized[key] = float(value)
                # Truncate very long strings to prevent log bloat
                elif isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "...[TRUNCATED]"
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _normalize_ip_address(self, ip_address: Optional[Union[str, IPv4Address, IPv6Address]]) -> Optional[str]:
        """
        Normalize IP address for consistent storage.
        
        Args:
            ip_address: IP address in various formats
        
        Returns:
            Normalized IP address string or None
        """
        if not ip_address:
            return None
        
        try:
            if isinstance(ip_address, (IPv4Address, IPv6Address)):
                return str(ip_address)
            elif isinstance(ip_address, str):
                # Handle forwarded IPs (take the first one)
                if ',' in ip_address:
                    ip_address = ip_address.split(',')[0].strip()
                
                # Validate and normalize
                from ipaddress import ip_address as parse_ip
                parsed_ip = parse_ip(ip_address)
                return str(parsed_ip)
            else:
                return str(ip_address)[:45]  # Max length for IPv6
                
        except Exception as e:
            logger.warning(f"Failed to normalize IP address {ip_address}: {e}")
            return str(ip_address)[:45] if ip_address else None
    
    def _log_to_application_logger(
        self,
        action: str,
        user_id: Optional[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
        details: Dict[str, Any]
    ):
        """
        Also log to application logger for immediate visibility.
        
        Args:
            action: Action being logged
            user_id: User performing action
            tenant_id: Tenant context
            details: Additional details
        """
        try:
            log_message = f"AUDIT: {action}"
            if user_id:
                log_message += f" | User: {user_id}"
            if tenant_id:
                log_message += f" | Tenant: {tenant_id}"
            
            # Add key details without sensitive data
            if details:
                safe_details = {k: v for k, v in details.items() if not self._is_sensitive_key(k)}
                if safe_details:
                    log_message += f" | Details: {json.dumps(safe_details, default=str)}"
            
            logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Failed to log to application logger: {e}")
    
    def _is_sensitive_key(self, key: str) -> bool:
        """
        Check if a key contains sensitive information.
        
        Args:
            key: Dictionary key to check
        
        Returns:
            True if key likely contains sensitive data
        """
        sensitive_patterns = ['password', 'secret', 'token', 'key', 'hash']
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)

# ================================
# AUDIT DECORATORS
# ================================

from functools import wraps
from fastapi import Request
from typing import Callable

def audit_action(action: str, resource_type: str = None):
    """
    Decorator to automatically audit function calls.
    
    Args:
        action: Action name to log
        resource_type: Type of resource being affected
    
    Usage:
        @audit_action("USER_CREATED", "user")
        async def create_user(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract common parameters
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            audit_logger = AuditLogger()
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Log successful action
                if db and current_user:
                    ip_address = getattr(request, 'client', {}).get('host') if request else None
                    user_agent = getattr(request, 'headers', {}).get('user-agent') if request else None
                    
                    audit_logger.log_auth_event(
                        db=db,
                        action=action,
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        details={"function": func.__name__, "success": True},
                        ip_address=ip_address,
                        user_agent=user_agent,
                        resource_type=resource_type
                    )
                
                return result
                
            except Exception as e:
                # Log failed action
                if db and current_user:
                    audit_logger.log_auth_event(
                        db=db,
                        action=f"{action}_FAILED",
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        details={
                            "function": func.__name__, 
                            "error": str(e), 
                            "success": False
                        },
                        resource_type=resource_type
                    )
                
                raise  # Re-raise the exception
        
        return wrapper
    return decorator

# ================================
# AUDIT CONTEXT MANAGER
# ================================

from contextlib import contextmanager

@contextmanager
def audit_context(
    db: Session,
    action: str,
    user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None,
    **kwargs
):
    """
    Context manager for auditing operations with automatic success/failure logging.
    
    Usage:
        with audit_context(db, "USER_UPDATE", user.id, tenant.id) as audit:
            # Perform operations
            audit.add_detail("updated_fields", ["name", "email"])
    """
    audit_logger = AuditLogger()
    context_details = {"operation_started": datetime.utcnow().isoformat()}
    
    class AuditContext:
        def __init__(self):
            self.details = {}
        
        def add_detail(self, key: str, value: Any):
            self.details[key] = value
        
        def add_resource(self, resource_type: str, resource_id: uuid.UUID):
            self.details["resource_type"] = resource_type
            self.details["resource_id"] = str(resource_id)
    
    audit_ctx = AuditContext()
    
    try:
        yield audit_ctx
        
        # Log successful completion
        final_details = {**context_details, **audit_ctx.details, "success": True}
        audit_logger.log_auth_event(
            db=db,
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            details=final_details,
            **kwargs
        )
        
    except Exception as e:
        # Log failure
        final_details = {
            **context_details, 
            **audit_ctx.details, 
            "success": False, 
            "error": str(e)
        }
        audit_logger.log_auth_event(
            db=db,
            action=f"{action}_FAILED",
            user_id=user_id,
            tenant_id=tenant_id,
            details=final_details,
            **kwargs
        )
        raise

# ================================
# EXPORTS
# ================================

__all__ = [
    "AuditLogger",
    "audit_action",
    "audit_context"
]