"""
Database integration for AgniAPI with SQLAlchemy ORM support.

This module provides comprehensive database capabilities including:
- SQLAlchemy ORM integration
- Async and sync database operations
- Model base class with common functionality
- Database connection management
- Migration support preparation
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional, Type, TypeVar, Union
from datetime import datetime

try:
    from sqlalchemy import create_engine, MetaData, Column, Integer, DateTime, String, Boolean, Text, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Provide fallback classes
    class Column:
        def __init__(self, *args, **kwargs):
            pass
    class Integer:
        pass
    class String:
        def __init__(self, *args, **kwargs):
            pass
    class DateTime:
        pass
    class Boolean:
        pass
    class Text:
        pass
    class ForeignKey:
        def __init__(self, *args, **kwargs):
            pass

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    ASYNC_SQLALCHEMY_AVAILABLE = True
except ImportError:
    ASYNC_SQLALCHEMY_AVAILABLE = False

try:
    from alembic import command
    from alembic.config import Config
    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False

ModelType = TypeVar('ModelType', bound='Model')


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class Database:
    """
    Main database class that manages connections and sessions.
    Supports both sync and async operations.
    """
    
    def __init__(
        self,
        database_url: str,
        *,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        **engine_kwargs
    ):
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is not available. Install with: pip install sqlalchemy")
        
        self.database_url = database_url
        self.echo = echo
        
        # Engine configuration
        engine_config = {
            'echo': echo,
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': pool_recycle,
            **engine_kwargs
        }
        
        # Handle SQLite special case
        if database_url.startswith('sqlite'):
            # Remove pool settings for SQLite
            engine_config = {
                'echo': echo,
                'poolclass': StaticPool,
                'connect_args': {'check_same_thread': False},
                **{k: v for k, v in engine_kwargs.items() if k not in ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']}
            }
        
        # Create sync engine
        self.engine = create_engine(database_url, **engine_config)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Add SQLAlchemy types for convenience
        self.Column = Column
        self.Integer = Integer
        self.String = String
        self.DateTime = DateTime
        self.Boolean = Boolean
        self.Text = Text
        self.ForeignKey = ForeignKey
        
        # Create async engine if available
        self.async_engine = None
        self.AsyncSessionLocal = None
        
        if ASYNC_SQLALCHEMY_AVAILABLE and not database_url.startswith('sqlite'):
            # Convert sync URL to async URL
            async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
            async_url = async_url.replace('mysql://', 'mysql+aiomysql://')
            
            if async_url != database_url:  # Only if we have an async driver
                try:
                    self.async_engine = create_async_engine(async_url, **engine_config)
                    self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine)
                except Exception:
                    # Fallback to sync only
                    pass
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a sync database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if not self.AsyncSessionLocal:
            raise DatabaseError("Async sessions not available")
        
        session = self.AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def create_all(self, metadata: MetaData) -> None:
        """Create all tables."""
        metadata.create_all(bind=self.engine)
    
    async def create_all_async(self, metadata: MetaData) -> None:
        """Create all tables asynchronously."""
        if not self.async_engine:
            raise DatabaseError("Async engine not available")
        
        async with self.async_engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
    
    def drop_all(self, metadata: MetaData) -> None:
        """Drop all tables."""
        metadata.drop_all(bind=self.engine)
    
    async def drop_all_async(self, metadata: MetaData) -> None:
        """Drop all tables asynchronously."""
        if not self.async_engine:
            raise DatabaseError("Async engine not available")
        
        async with self.async_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
        if self.async_engine:
            asyncio.create_task(self.async_engine.dispose())


# Create base model class
if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class Model(Base):
        """
        Base model class with common functionality.
        Provides CRUD operations and utility methods.
        """
        __abstract__ = True
        
        # Common columns
        id = Column(Integer, primary_key=True, index=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
        
        @classmethod
        def create(cls: Type[ModelType], db: Session, **kwargs) -> ModelType:
            """Create a new instance."""
            instance = cls(**kwargs)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance
        
        @classmethod
        async def create_async(cls: Type[ModelType], db: AsyncSession, **kwargs) -> ModelType:
            """Create a new instance asynchronously."""
            instance = cls(**kwargs)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)
            return instance
        
        @classmethod
        def get(cls: Type[ModelType], db: Session, id: Any) -> Optional[ModelType]:
            """Get instance by ID."""
            return db.query(cls).filter(cls.id == id).first()
        
        @classmethod
        async def get_async(cls: Type[ModelType], db: AsyncSession, id: Any) -> Optional[ModelType]:
            """Get instance by ID asynchronously."""
            from sqlalchemy import select
            result = await db.execute(select(cls).where(cls.id == id))
            return result.scalar_one_or_none()
        
        @classmethod
        def get_all(cls: Type[ModelType], db: Session, skip: int = 0, limit: int = 100) -> list[ModelType]:
            """Get all instances with pagination."""
            return db.query(cls).offset(skip).limit(limit).all()
        
        @classmethod
        async def get_all_async(cls: Type[ModelType], db: AsyncSession, skip: int = 0, limit: int = 100) -> list[ModelType]:
            """Get all instances with pagination asynchronously."""
            from sqlalchemy import select
            result = await db.execute(select(cls).offset(skip).limit(limit))
            return result.scalars().all()
        
        def update(self, db: Session, **kwargs) -> None:
            """Update instance."""
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(self)
        
        async def update_async(self, db: AsyncSession, **kwargs) -> None:
            """Update instance asynchronously."""
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(self)
        
        def delete(self, db: Session) -> None:
            """Delete instance."""
            db.delete(self)
            db.commit()
        
        async def delete_async(self, db: AsyncSession) -> None:
            """Delete instance asynchronously."""
            await db.delete(self)
            await db.commit()
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert instance to dictionary."""
            result = {}
            for column in self.__table__.columns:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
            return result
        
        @classmethod
        def from_dict(cls: Type[ModelType], data: Dict[str, Any]) -> ModelType:
            """Create instance from dictionary."""
            # Filter out keys that don't correspond to columns
            valid_keys = {column.name for column in cls.__table__.columns}
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered_data)
        
        def __repr__(self) -> str:
            return f"<{self.__class__.__name__}(id={self.id})>"

else:
    # Fallback if SQLAlchemy is not available
    class Base:
        pass
    
    class Model:
        pass


# Dependency injection helpers
def get_db_session(database: Database):
    """Dependency to get database session."""
    def _get_session():
        with database.session() as session:
            yield session
    return _get_session


def get_async_db_session(database: Database):
    """Dependency to get async database session."""
    async def _get_session():
        async with database.async_session() as session:
            yield session
    return _get_session


# Migration support
class MigrationManager:
    """Manager for database migrations using Alembic."""
    
    def __init__(self, database: Database, alembic_cfg_path: str = "alembic.ini"):
        if not ALEMBIC_AVAILABLE:
            raise ImportError("Alembic is not available. Install with: pip install alembic")
        
        self.database = database
        self.alembic_cfg = Config(alembic_cfg_path)
        self.alembic_cfg.set_main_option("sqlalchemy.url", database.database_url)
    
    def init(self, directory: str = "migrations") -> None:
        """Initialize migration repository."""
        command.init(self.alembic_cfg, directory)
    
    def revision(self, message: str, autogenerate: bool = True) -> None:
        """Create a new migration revision."""
        command.revision(self.alembic_cfg, message=message, autogenerate=autogenerate)
    
    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to a revision."""
        command.upgrade(self.alembic_cfg, revision)
    
    def downgrade(self, revision: str) -> None:
        """Downgrade database to a revision."""
        command.downgrade(self.alembic_cfg, revision)
    
    def current(self) -> None:
        """Show current revision."""
        command.current(self.alembic_cfg)
    
    def history(self) -> None:
        """Show migration history."""
        command.history(self.alembic_cfg)


# Global database instance (can be configured by the application)
db: Optional[Database] = None


def configure_database(database_url: str, **kwargs) -> Database:
    """Configure and return a database instance."""
    global db
    db = Database(database_url, **kwargs)
    return db


def get_database() -> Optional[Database]:
    """Get the configured database instance."""
    return db
