# ================================
# RBAC SERVICE (services/rbac_service.py)
# ================================

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.schemas.rbac import RoleCreate, RoleUpdate, PermissionCreate
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

audit_logger = AuditLogger()

class RBACService:
    """Service for Role-Based Access Control operations"""
    
    @staticmethod
    def create_permission(
        db: Session,
        permission_data: PermissionCreate
    ) -> Permission:
        """Create a new permission"""
        # Check if permission already exists
        existing = db.query(Permission).filter(
            Permission.resource == permission_data.resource,
            Permission.action == permission_data.action
        ).first()
        
        if existing:
            raise AppException("Permission already exists", 400, "PERMISSION_EXISTS")
        
        permission = Permission(
            resource=permission_data.resource,
            action=permission_data.action,
            description=permission_data.description
        )
        
        db.add(permission)
        return permission
    
    @staticmethod
    def create_role(
        db: Session,
        role_data: RoleCreate,
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Role:
        """Create a new role for a tenant"""
        # Check if role name already exists in tenant
        existing = db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == role_data.name
        ).first()
        
        if existing:
            raise AppException("Role name already exists in this tenant", 400, "ROLE_EXISTS")
        
        # Create role
        role = Role(
            tenant_id=tenant_id,
            name=role_data.name,
            description=role_data.description,
            is_system_role=role_data.is_system_role
        )
        
        db.add(role)
        db.flush()  # Get role.id
        
        # Assign permissions to role
        if role_data.permission_ids:
            RBACService._assign_permissions_to_role(db, role.id, role_data.permission_ids)
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_CREATED", current_user.id, tenant_id,
            {
                "role_id": str(role.id),
                "role_name": role.name,
                "permission_count": len(role_data.permission_ids)
            }
        )
        
        return role
    
    @staticmethod
    def update_role(
        db: Session,
        role_id: uuid.UUID,
        role_update: RoleUpdate,
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Role:
        """Update an existing role"""
        role = db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id
        ).first()
        
        if not role:
            raise AppException("Role not found", 404, "ROLE_NOT_FOUND")
        
        # Store old values for audit
        old_values = {
            "name": role.name,
            "description": role.description
        }
        
        # Update fields
        update_data = {}
        if role_update.name is not None:
            # Check name uniqueness
            existing = db.query(Role).filter(
                Role.tenant_id == tenant_id,
                Role.name == role_update.name,
                Role.id != role_id
            ).first()
            if existing:
                raise AppException("Role name already exists", 400, "ROLE_NAME_EXISTS")
            
            role.name = role_update.name
            update_data["name"] = role_update.name
        
        if role_update.description is not None:
            role.description = role_update.description
            update_data["description"] = role_update.description
        
        # Update permissions if provided
        if role_update.permission_ids is not None:
            # Remove existing permissions
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
            
            # Add new permissions
            RBACService._assign_permissions_to_role(db, role_id, role_update.permission_ids)
            update_data["permissions_updated"] = True
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_UPDATED", current_user.id, tenant_id,
            {
                "role_id": str(role_id),
                "role_name": role.name,
                "old_values": old_values,
                "new_values": update_data
            }
        )
        
        return role
    
    @staticmethod
    def delete_role(
        db: Session,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Delete a role and its assignments"""
        role = db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id
        ).first()
        
        if not role:
            raise AppException("Role not found", 404, "ROLE_NOT_FOUND")
        
        # Check if role is system role
        if role.is_system_role:
            raise AppException("Cannot delete system role", 400, "SYSTEM_ROLE_DELETE")
        
        # Count affected users
        affected_users = db.query(UserRole).filter(UserRole.role_id == role_id).count()
        
        # Audit log before deletion
        audit_logger.log_auth_event(
            db, "ROLE_DELETED", current_user.id, tenant_id,
            {
                "role_id": str(role_id),
                "role_name": role.name,
                "affected_users": affected_users
            }
        )
        
        # Delete role (cascade will handle role_permissions and user_roles)
        db.delete(role)
        
        return {"affected_users": affected_users}
    
    @staticmethod
    def get_role_with_permissions(
        db: Session,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get role with its permissions"""
        role = db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id
        ).first()
        
        if not role:
            raise AppException("Role not found", 404, "ROLE_NOT_FOUND")
        
        # Get role permissions
        permissions = db.query(Permission).join(RolePermission).filter(
            RolePermission.role_id == role_id
        ).all()
        
        # Get user count
        user_count = db.query(UserRole).filter(UserRole.role_id == role_id).count()
        
        return {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "tenant_id": str(role.tenant_id),
            "user_count": user_count,
            "permissions": [
                {
                    "id": str(perm.id),
                    "resource": perm.resource,
                    "action": perm.action,
                    "description": perm.description,
                    "name": f"{perm.resource}:{perm.action}"
                }
                for perm in permissions
            ],
            "created_at": role.created_at.isoformat(),
            "updated_at": role.updated_at.isoformat()
        }
    
    @staticmethod
    def update_role_permissions(
        db: Session,
        role_id: uuid.UUID,
        add_permission_ids: List[uuid.UUID],
        remove_permission_ids: List[uuid.UUID],
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Update role permissions by adding/removing specific permissions"""
        role = db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id
        ).first()
        
        if not role:
            raise AppException("Role not found", 404, "ROLE_NOT_FOUND")
        
        # Remove permissions
        removed_count = 0
        if remove_permission_ids:
            removed_count = db.query(RolePermission).filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id.in_(remove_permission_ids)
            ).delete()
        
        # Add new permissions
        added_count = 0
        if add_permission_ids:
            # Verify permissions exist
            existing_permissions = db.query(Permission.id).filter(
                Permission.id.in_(add_permission_ids)
            ).all()
            
            existing_ids = [p.id for p in existing_permissions]
            
            # Check for already assigned permissions
            already_assigned = db.query(RolePermission.permission_id).filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id.in_(existing_ids)
            ).all()
            
            already_assigned_ids = [p.permission_id for p in already_assigned]
            
            # Add only new permissions
            new_permission_ids = [pid for pid in existing_ids if pid not in already_assigned_ids]
            
            for permission_id in new_permission_ids:
                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=permission_id
                )
                db.add(role_permission)
                added_count += 1
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_PERMISSIONS_UPDATED", current_user.id, tenant_id,
            {
                "role_id": str(role_id),
                "role_name": role.name,
                "permissions_added": added_count,
                "permissions_removed": removed_count
            }
        )
        
        return {
            "permissions_added": added_count,
            "permissions_removed": removed_count
        }
    
    @staticmethod
    def clone_role(
        db: Session,
        source_role_id: uuid.UUID,
        new_role_name: str,
        new_role_description: Optional[str],
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Role:
        """Clone an existing role with all its permissions"""
        source_role = db.query(Role).filter(
            Role.id == source_role_id,
            Role.tenant_id == tenant_id
        ).first()
        
        if not source_role:
            raise AppException("Source role not found", 404, "ROLE_NOT_FOUND")
        
        # Check if new role name already exists
        existing = db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == new_role_name
        ).first()
        
        if existing:
            raise AppException("Role name already exists", 400, "ROLE_NAME_EXISTS")
        
        # Create new role
        new_role = Role(
            tenant_id=tenant_id,
            name=new_role_name,
            description=new_role_description or f"Cloned from {source_role.name}",
            is_system_role=False  # Cloned roles are always custom
        )
        
        db.add(new_role)
        db.flush()  # Get new role ID
        
        # Clone permissions
        source_permissions = db.query(RolePermission).filter(
            RolePermission.role_id == source_role_id
        ).all()
        
        for role_perm in source_permissions:
            new_role_permission = RolePermission(
                role_id=new_role.id,
                permission_id=role_perm.permission_id
            )
            db.add(new_role_permission)
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_CLONED", current_user.id, tenant_id,
            {
                "source_role_id": str(source_role_id),
                "source_role_name": source_role.name,
                "new_role_id": str(new_role.id),
                "new_role_name": new_role_name,
                "permissions_cloned": len(source_permissions)
            }
        )
        
        return new_role
    
    @staticmethod
    def bulk_assign_roles(
        db: Session,
        user_ids: List[uuid.UUID],
        role_ids: List[uuid.UUID],
        tenant_id: uuid.UUID,
        expires_at: Optional[datetime],
        current_user: User
    ) -> Dict[str, Any]:
        """Assign roles to multiple users"""
        # Verify users exist and belong to tenant
        users = db.query(User).filter(
            User.id.in_(user_ids),
            User.tenant_id == tenant_id
        ).all()
        
        if len(users) != len(user_ids):
            raise AppException("Some users not found or don't belong to tenant", 400, "INVALID_USERS")
        
        # Verify roles exist and belong to tenant
        roles = db.query(Role).filter(
            Role.id.in_(role_ids),
            Role.tenant_id == tenant_id
        ).all()
        
        if len(roles) != len(role_ids):
            raise AppException("Some roles not found or don't belong to tenant", 400, "INVALID_ROLES")
        
        successful_assignments = 0
        failed_assignments = 0
        assignment_details = []
        
        for user in users:
            for role in roles:
                try:
                    # Check if assignment already exists
                    existing = db.query(UserRole).filter(
                        UserRole.user_id == user.id,
                        UserRole.role_id == role.id,
                        UserRole.tenant_id == tenant_id
                    ).first()
                    
                    if existing:
                        assignment_details.append({
                            "user_id": str(user.id),
                            "role_id": str(role.id),
                            "status": "already_assigned"
                        })
                        continue
                    
                    # Create assignment
                    user_role = UserRole(
                        user_id=user.id,
                        role_id=role.id,
                        tenant_id=tenant_id,
                        granted_by=current_user.id,
                        expires_at=expires_at
                    )
                    db.add(user_role)
                    
                    successful_assignments += 1
                    assignment_details.append({
                        "user_id": str(user.id),
                        "role_id": str(role.id),
                        "status": "assigned"
                    })
                    
                except Exception as e:
                    failed_assignments += 1
                    assignment_details.append({
                        "user_id": str(user.id),
                        "role_id": str(role.id),
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Audit log
        audit_logger.log_auth_event(
            db, "BULK_ROLE_ASSIGNMENT", current_user.id, tenant_id,
            {
                "user_count": len(user_ids),
                "role_count": len(role_ids),
                "successful_assignments": successful_assignments,
                "failed_assignments": failed_assignments
            }
        )
        
        return {
            "successful_assignments": successful_assignments,
            "failed_assignments": failed_assignments,
            "assignment_details": assignment_details
        }
    
    @staticmethod
    def check_user_permission(
        db: Session,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        resource: str,
        action: str
    ) -> Dict[str, Any]:
        """Check if user has specific permission"""
        # Query: user_roles -> role_permissions -> permissions
        permission_exists = db.query(Permission).join(
            RolePermission, Permission.id == RolePermission.permission_id
        ).join(
            UserRole, RolePermission.role_id == UserRole.role_id
        ).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Permission.resource == resource,
                Permission.action == action
            )
        ).first()
        
        # Get roles that grant this permission
        granted_via_roles = []
        if permission_exists:
            roles = db.query(Role).join(
                RolePermission, Role.id == RolePermission.role_id
            ).join(
                UserRole, Role.id == UserRole.role_id
            ).join(
                Permission, RolePermission.permission_id == Permission.id
            ).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.tenant_id == tenant_id,
                    Permission.resource == resource,
                    Permission.action == action
                )
            ).all()
            
            granted_via_roles = [role.name for role in roles]
        
        return {
            "has_permission": permission_exists is not None,
            "granted_via_roles": granted_via_roles
        }
    
    @staticmethod
    def get_user_permissions(
        db: Session,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get all permissions for a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Get user roles
        user_roles = db.query(Role).join(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        ).all()
        
        # Get all permissions through roles
        permissions = db.query(Permission).join(
            RolePermission, Permission.id == RolePermission.permission_id
        ).join(
            UserRole, RolePermission.role_id == UserRole.role_id
        ).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id
            )
        ).distinct().all()
        
        # Group permissions by resource
        permission_groups = {}
        for perm in permissions:
            if perm.resource not in permission_groups:
                permission_groups[perm.resource] = []
            permission_groups[perm.resource].append({
                "id": str(perm.id),
                "action": perm.action,
                "description": perm.description
            })
        
        return {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                    "is_system_role": role.is_system_role
                }
                for role in user_roles
            ],
            "permissions": [
                {
                    "id": str(perm.id),
                    "resource": perm.resource,
                    "action": perm.action,
                    "description": perm.description,
                    "name": f"{perm.resource}:{perm.action}"
                }
                for perm in permissions
            ],
            "permission_groups": [
                {
                    "resource": resource,
                    "permissions": perms
                }
                for resource, perms in permission_groups.items()
            ]
        }
    
    @staticmethod
    def get_rbac_statistics(
        db: Session,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get RBAC statistics for tenant or global"""
        # Base filters
        role_filter = Role.tenant_id == tenant_id if tenant_id else True
        user_role_filter = UserRole.tenant_id == tenant_id if tenant_id else True
        
        # Role statistics
        total_roles = db.query(Role).filter(role_filter).count()
        system_roles = db.query(Role).filter(
            role_filter,
            Role.is_system_role == True
        ).count()
        custom_roles = total_roles - system_roles
        
        # Permission statistics
        total_permissions = db.query(Permission).count()
        
        # Permissions by resource
        permissions_by_resource = db.query(
            Permission.resource,
            func.count(Permission.id).label('count')
        ).group_by(Permission.resource).all()
        
        permissions_by_resource_dict = {
            stat.resource: stat.count for stat in permissions_by_resource
        }
        
        # Users without roles
        users_without_roles = 0
        if tenant_id:
            all_users = db.query(User).filter(User.tenant_id == tenant_id).count()
            users_with_roles = db.query(func.count(func.distinct(UserRole.user_id))).filter(
                UserRole.tenant_id == tenant_id
            ).scalar() or 0
            users_without_roles = all_users - users_with_roles
        
        # Most assigned roles
        most_assigned_roles = db.query(
            Role.name,
            func.count(UserRole.user_id).label('user_count')
        ).join(UserRole).filter(
            role_filter,
            user_role_filter
        ).group_by(Role.name).order_by(
            func.count(UserRole.user_id).desc()
        ).limit(5).all()
        
        most_assigned_roles_list = [
            {"role_name": role.name, "user_count": role.user_count}
            for role in most_assigned_roles
        ]
        
        return {
            "total_roles": total_roles,
            "system_roles": system_roles,
            "custom_roles": custom_roles,
            "total_permissions": total_permissions,
            "permissions_by_resource": permissions_by_resource_dict,
            "users_without_roles": users_without_roles,
            "most_assigned_roles": most_assigned_roles_list
        }
    
    @staticmethod
    def get_role_usage_report(
        db: Session,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get role usage report for a tenant"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        roles = db.query(Role).filter(Role.tenant_id == tenant_id).all()
        
        usage_report = []
        for role in roles:
            # Total users with this role
            total_users = db.query(UserRole).filter(UserRole.role_id == role.id).count()
            
            # Active users (logged in recently)
            active_users = db.query(func.count(func.distinct(UserRole.user_id))).join(
                User, UserRole.user_id == User.id
            ).filter(
                UserRole.role_id == role.id,
                User.last_login_at >= start_date
            ).scalar() or 0
            
            # Recent assignments
            recent_assignments = db.query(UserRole).filter(
                UserRole.role_id == role.id,
                UserRole.granted_at >= start_date
            ).count()
            
            # Permission count
            permission_count = db.query(RolePermission).filter(
                RolePermission.role_id == role.id
            ).count()
            
            # Last used (last time someone with this role logged in)
            last_used = db.query(func.max(User.last_login_at)).join(
                UserRole, User.id == UserRole.user_id
            ).filter(UserRole.role_id == role.id).scalar()
            
            usage_report.append({
                "role_id": str(role.id),
                "role_name": role.name,
                "total_users": total_users,
                "active_users": active_users,
                "recent_assignments": recent_assignments,
                "permission_count": permission_count,
                "last_used": last_used.isoformat() if last_used else None
            })
        
        return usage_report
    
    @staticmethod
    def get_permission_usage_report(
        db: Session,
        tenant_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get permission usage report"""
        permissions = db.query(Permission).all()
        
        usage_report = []
        for permission in permissions:
            # Roles that have this permission
            roles_with_permission = db.query(Role).join(RolePermission).filter(
                RolePermission.permission_id == permission.id
            )
            
            if tenant_id:
                roles_with_permission = roles_with_permission.filter(Role.tenant_id == tenant_id)
            
            total_roles_assigned = roles_with_permission.count()
            
            # Users with this permission (through roles)
            users_with_permission = db.query(func.count(func.distinct(UserRole.user_id))).join(
                RolePermission, UserRole.role_id == RolePermission.role_id
            ).filter(RolePermission.permission_id == permission.id)
            
            if tenant_id:
                users_with_permission = users_with_permission.filter(UserRole.tenant_id == tenant_id)
            
            total_users_with_permission = users_with_permission.scalar() or 0
            
            usage_report.append({
                "permission_id": str(permission.id),
                "resource": permission.resource,
                "action": permission.action,
                "total_roles_assigned": total_roles_assigned,
                "total_users_with_permission": total_users_with_permission,
                "usage_frequency": total_users_with_permission  # Simple frequency measure
            })
        
        # Sort by usage frequency
        usage_report.sort(key=lambda x: x["usage_frequency"], reverse=True)
        
        return usage_report
    
    @staticmethod
    def get_rbac_compliance_report(
        db: Session,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generate RBAC compliance report for a tenant"""
        # Basic counts
        total_users = db.query(User).filter(User.tenant_id == tenant_id).count()
        
        users_with_roles = db.query(func.count(func.distinct(UserRole.user_id))).filter(
            UserRole.tenant_id == tenant_id
        ).scalar() or 0
        
        users_without_roles = total_users - users_with_roles
        
        # Orphaned permissions (permissions not assigned to any role in this tenant)
        assigned_permission_ids = db.query(func.distinct(RolePermission.permission_id)).join(
            Role, RolePermission.role_id == Role.id
        ).filter(Role.tenant_id == tenant_id).subquery()
        
        total_permissions = db.query(Permission).count()
        assigned_permissions = db.query(Permission).filter(
            Permission.id.in_(assigned_permission_ids)
        ).count()
        
        orphaned_permissions = total_permissions - assigned_permissions
        
        # Unused roles (roles with no users assigned)
        roles_with_users = db.query(func.count(func.distinct(UserRole.role_id))).filter(
            UserRole.tenant_id == tenant_id
        ).scalar() or 0
        
        total_roles = db.query(Role).filter(Role.tenant_id == tenant_id).count()
        unused_roles = total_roles - roles_with_users
        
        # Calculate compliance score
        compliance_score = 100.0
        
        # Deduct points for issues
        if total_users > 0:
            if users_without_roles > 0:
                compliance_score -= (users_without_roles / total_users) * 30  # Max 30 points
        
        if total_roles > 0:
            if unused_roles > 0:
                compliance_score -= (unused_roles / total_roles) * 20  # Max 20 points
        
        if orphaned_permissions > 5:
            compliance_score -= 15  # Deduct for too many orphaned permissions
        
        compliance_score = max(0, compliance_score)  # Don't go below 0
        
        # Generate recommendations
        recommendations = []
        if users_without_roles > 0:
            recommendations.append(f"Assign roles to {users_without_roles} users without roles")
        
        if unused_roles > 0:
            recommendations.append(f"Review {unused_roles} unused roles for potential cleanup")
        
        if orphaned_permissions > 5:
            recommendations.append(f"Review {orphaned_permissions} unassigned permissions")
        
        if compliance_score < 80:
            recommendations.append("Consider implementing regular RBAC audits")
        
        return {
            "tenant_id": str(tenant_id),
            "total_users": total_users,
            "users_with_roles": users_with_roles,
            "users_without_roles": users_without_roles,
            "orphaned_permissions": orphaned_permissions,
            "unused_roles": unused_roles,
            "compliance_score": round(compliance_score, 2),
            "recommendations": recommendations
        }