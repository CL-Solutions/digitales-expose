#!/usr/bin/env python3
"""
Super Admin Initialization Script
Enterprise Multi-Tenant System

This script creates the initial super admin user and sets up
basic system permissions and data.

Usage:
    python scripts/init_super_admin.py
    python init_super_admin.py  # If placed in project root
    
Environment Variables (from .env file):
    - DATABASE_URL: PostgreSQL connection string
    - SUPER_ADMIN_EMAIL: Email for super admin (optional, will prompt)
    - SUPER_ADMIN_PASSWORD: Password for super admin (optional, will prompt)
"""

import os
import sys
import getpass
import re
from typing import Optional
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent if 'scripts' in str(Path(__file__).parent) else Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.user import User
from app.models.rbac import Permission
from app.models.utils import create_default_permissions
from app.models.audit import AuditLog


class SuperAdminInitializer:
    """Handles super admin initialization"""
    
    def __init__(self):
        self.db: Optional[Session] = None
        
    def __enter__(self):
        self.db = SessionLocal()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Za-z]', password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password should contain at least one special character"
        
        return True, "Password is valid"
    
    def get_user_input(self) -> dict:
        """Get user input for super admin creation"""
        print("=== Super Admin Initialization ===\n")
        
        # Get email
        email = os.getenv('SUPER_ADMIN_EMAIL')
        while not email or not self.validate_email(email):
            email = input("Super Admin Email: ").strip()
            if not self.validate_email(email):
                print("❌ Invalid email format. Please try again.")
                email = None
        
        # Get password
        password = os.getenv('SUPER_ADMIN_PASSWORD')
        while not password:
            password = getpass.getpass("Super Admin Password: ")
            if not password:
                print("❌ Password cannot be empty.")
                continue
                
            is_valid, message = self.validate_password(password)
            if not is_valid:
                print(f"❌ {message}")
                password = None
                continue
                
            # Confirm password
            confirm_password = getpass.getpass("Confirm Password: ")
            if password != confirm_password:
                print("❌ Passwords do not match.")
                password = None
                continue
        
        # Get first name
        first_name = os.getenv('SUPER_ADMIN_FIRST_NAME', 'Super')
        if not first_name or first_name == 'Super':
            first_name = input(f"First Name [{first_name}]: ").strip() or first_name
        
        # Get last name  
        last_name = os.getenv('SUPER_ADMIN_LAST_NAME', 'Admin')
        if not last_name or last_name == 'Admin':
            last_name = input(f"Last Name [{last_name}]: ").strip() or last_name
        
        return {
            'email': email.lower(),
            'password': password,
            'first_name': first_name,
            'last_name': last_name
        }
    
    def check_existing_super_admin(self) -> bool:
        """Check if a super admin already exists"""
        existing = self.db.query(User).filter(User.is_super_admin == True).first()
        return existing is not None
    
    def create_database_tables(self):
        """Create all database tables"""
        print("🔧 Creating database tables...")
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Failed to create database tables: {e}")
            raise
    
    def create_default_permissions(self):
        """Create default system permissions"""
        print("🔧 Creating default permissions...")
        try:
            permissions = create_default_permissions(self.db)
            self.db.commit()
            print(f"✅ Created {len(permissions)} default permissions")
        except Exception as e:
            print(f"❌ Failed to create default permissions: {e}")
            self.db.rollback()
            raise
    
    def create_super_admin(self, admin_data: dict) -> User:
        """Create the super admin user"""
        print("🔧 Creating super admin user...")
        
        try:
            # Check if user with this email already exists
            existing_user = self.db.query(User).filter(User.email == admin_data['email']).first()
            if existing_user:
                if existing_user.is_super_admin:
                    print(f"⚠️  Super admin with email {admin_data['email']} already exists")
                    return existing_user
                else:
                    print(f"❌ User with email {admin_data['email']} already exists but is not a super admin")
                    raise ValueError("User already exists")
            
            # Create super admin
            super_admin = User(
                email=admin_data['email'],
                tenant_id=None,  # Super admins are not tied to any tenant
                auth_method="local",
                is_super_admin=True,
                password_hash=get_password_hash(admin_data['password']),
                first_name=admin_data['first_name'],
                last_name=admin_data['last_name'],
                is_active=True,
                is_verified=True  # Super admins are pre-verified
            )
            
            self.db.add(super_admin)
            self.db.flush()  # Get the ID
            
            # Create audit log entry
            audit_log = AuditLog(
                tenant_id=None,
                user_id=super_admin.id,
                action="CREATE",
                resource_type="user",
                resource_id=super_admin.id,
                old_values=None,
                new_values={
                    "email": super_admin.email,
                    "is_super_admin": True,
                    "auth_method": "local"
                },
                ip_address=None,
                user_agent="System Initialization Script"
            )
            self.db.add(audit_log)
            
            self.db.commit()
            print(f"✅ Super admin created successfully: {admin_data['email']}")
            return super_admin
            
        except IntegrityError as e:
            self.db.rollback()
            print(f"❌ Failed to create super admin (integrity error): {e}")
            raise
        except Exception as e:
            self.db.rollback()
            print(f"❌ Failed to create super admin: {e}")
            raise
    
    def verify_setup(self, super_admin: User):
        """Verify the setup was successful"""
        print("🔍 Verifying setup...")
        
        # Check super admin exists
        db_admin = self.db.query(User).filter(
            User.id == super_admin.id,
            User.is_super_admin == True
        ).first()
        
        if not db_admin:
            raise Exception("Super admin not found in database")
        
        # Check permissions exist
        permissions_count = self.db.query(Permission).count()
        if permissions_count == 0:
            raise Exception("No permissions found in database")
        
        print(f"✅ Setup verified:")
        print(f"   - Super Admin: {db_admin.email}")
        print(f"   - Full Name: {db_admin.full_name}")
        print(f"   - Permissions: {permissions_count} system permissions created")
        print(f"   - User ID: {db_admin.id}")
    
    def run(self, force: bool = False):
        """Run the initialization process"""
        try:
            print("🚀 Starting Super Admin Initialization\n")
            
            # Check if super admin already exists
            if not force and self.check_existing_super_admin():
                print("⚠️  A super admin already exists in the system.")
                response = input("Do you want to create another super admin? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("❌ Initialization cancelled")
                    return False
            
            # Create database tables
            self.create_database_tables()
            
            # Create default permissions
            self.create_default_permissions()
            
            # Get user input
            admin_data = self.get_user_input()
            
            # Create super admin
            super_admin = self.create_super_admin(admin_data)
            
            # Verify setup
            self.verify_setup(super_admin)
            
            print("\n🎉 Super Admin initialization completed successfully!")
            print("\nNext steps:")
            print("1. Start your FastAPI application")
            print("2. Login with the super admin credentials")
            print("3. Create your first tenant and tenant admin")
            print("4. Configure OAuth providers for tenants")
            
            return True
            
        except KeyboardInterrupt:
            print("\n❌ Initialization cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Initialization failed: {e}")
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Super Admin for Enterprise Multi-Tenant System")
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force creation even if super admin already exists"
    )
    parser.add_argument(
        "--check-env", 
        action="store_true", 
        help="Check if required environment variables are set"
    )
    
    args = parser.parse_args()
    
    # Check environment variables
    if args.check_env:
        required_vars = ["DATABASE_URL"]
        optional_vars = [
            "SUPER_ADMIN_EMAIL", 
            "SUPER_ADMIN_PASSWORD", 
            "SUPER_ADMIN_FIRST_NAME", 
            "SUPER_ADMIN_LAST_NAME"
        ]
        
        print("Environment Variables Check:")
        for var in required_vars:
            value = os.getenv(var)
            status = "✅ SET" if value else "❌ MISSING"
            print(f"  {var}: {status}")
        
        for var in optional_vars:
            value = os.getenv(var)
            status = "✅ SET" if value else "⚠️  NOT SET (will prompt)"
            print(f"  {var}: {status}")
        
        return
    
    # Check database URL
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable is required")
        print("   Example: DATABASE_URL=postgresql://user:password@localhost/dbname")
        sys.exit(1)
    
    # Initialize super admin
    with SuperAdminInitializer() as initializer:
        success = initializer.run(force=args.force)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()