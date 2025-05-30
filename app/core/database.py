# ================================
# DATABASE CONNECTION (core/database.py)
# ================================

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import uuid

from app.config import settings

# Database Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tenant Context für Row-Level Security
def set_tenant_context(db: Session, tenant_id: uuid.UUID = None):
    """Setzt den Tenant-Kontext für RLS"""
    if tenant_id:
        db.execute(f"SET app.current_tenant_id = '{tenant_id}'")
    else:
        db.execute("SET app.current_tenant_id = ''")

@contextmanager
def get_db_session():
    """Database session mit automatischem cleanup"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()