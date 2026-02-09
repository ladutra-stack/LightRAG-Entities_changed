"""
SQLAlchemy Database Models for Backup, Replication, and Recovery Systems

Provides persistent storage for recovery points, backup metadata, and health events.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, 
    Boolean, Float, Text, JSON, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
from lightrag.utils import logger

Base = declarative_base()


class RecoveryPointDB(Base):
    """Database model for recovery checkpoints."""
    
    __tablename__ = "recovery_points"
    
    checkpoint_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    validated = Column(Boolean, default=False)
    validation_timestamp = Column(DateTime, nullable=True)
    description = Column(Text, default="")
    graphs = Column(JSON, default=[])  # List of graph IDs
    extra_metadata = Column(JSON, default={})
    created_by = Column(String(255), default="system")
    
    # Relationships
    health_events = relationship("HealthEventDB", back_populates="recovery_point", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_recovery_created_at", "created_at"),
        Index("idx_recovery_validated", "validated"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "validated": self.validated,
            "validation_timestamp": self.validation_timestamp.isoformat() if self.validation_timestamp is not None else None,
            "description": self.description,
            "graphs": self.graphs,
            "extra_metadata": self.extra_metadata,
            "created_by": self.created_by,
        }


class BackupMetadataDB(Base):
    """Database model for backup snapshot metadata."""
    
    __tablename__ = "backup_metadata"
    
    backup_id = Column(String(36), primary_key=True)
    graph_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(50), default="completed")  # pending, in_progress, completed, failed
    size_bytes = Column(Integer, default=0)
    data_hash = Column(String(64))  # SHA256 hash
    retention_until = Column(DateTime, index=True)
    checkpoint_path = Column(Text)
    extra_metadata = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_backup_graph_created", "graph_id", "created_at"),
        Index("idx_backup_retention", "retention_until"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "backup_id": self.backup_id,
            "graph_id": self.graph_id,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "status": self.status,
            "size_bytes": self.size_bytes,
            "data_hash": self.data_hash,
            "retention_until": self.retention_until.isoformat() if self.retention_until is not None else None,
            "checkpoint_path": self.checkpoint_path,
            "extra_metadata": self.extra_metadata,
            "error_message": self.error_message,
        }


class ReplicationTargetDB(Base):
    """Database model for replication target configuration."""
    
    __tablename__ = "replication_targets"
    
    target_id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True)
    base_url = Column(String(255))
    api_key = Column(String(255))  # Should be encrypted in production
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_health_check = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    extra_metadata = Column(JSON, default={})
    max_concurrent = Column(Integer, default=3)
    
    __table_args__ = (
        Index("idx_replication_enabled", "enabled"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "target_id": self.target_id,
            "name": self.name,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check is not None else None,
            "last_error": self.last_error,
            "extra_metadata": self.extra_metadata,
            "max_concurrent": self.max_concurrent,
        }


class HealthEventDB(Base):
    """Database model for health check events."""
    
    __tablename__ = "health_events"
    
    event_id = Column(String(36), primary_key=True)
    checkpoint_id = Column(String(36), ForeignKey("recovery_points.checkpoint_id"), index=True)
    component_id = Column(String(255), index=True)
    component_type = Column(String(50))  # graph, storage, replication, etc
    event_type = Column(String(50))  # check, error, warning, success
    status = Column(String(50))  # healthy, degraded, critical, offline
    message = Column(Text)
    details = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    severity = Column(Integer, default=0)  # 0=info, 1=warning, 2=error, 3=critical
    
    # Relationships
    recovery_point = relationship("RecoveryPointDB", back_populates="health_events")
    
    __table_args__ = (
        Index("idx_health_component_type", "component_id", "component_type"),
        Index("idx_health_created", "created_at"),
        Index("idx_health_severity", "severity"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "checkpoint_id": self.checkpoint_id,
            "component_id": self.component_id,
            "component_type": self.component_type,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "severity": self.severity,
        }


class ReplicationEventDB(Base):
    """Database model for replication operation events."""
    
    __tablename__ = "replication_events"
    
    event_id = Column(String(36), primary_key=True)
    graph_id = Column(String(255), index=True)
    target_id = Column(String(36), index=True)
    status = Column(String(50))  # pending, in_progress, completed, failed
    operation_type = Column(String(50))  # sync, validate, health_check
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    bytes_transferred = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, default={})
    
    __table_args__ = (
        Index("idx_replication_graph_target", "graph_id", "target_id"),
        Index("idx_replication_started", "started_at"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "graph_id": self.graph_id,
            "target_id": self.target_id,
            "status": self.status,
            "operation_type": self.operation_type,
            "started_at": self.started_at.isoformat() if self.started_at is not None else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at is not None else None,
            "duration_seconds": self.duration_seconds,
            "bytes_transferred": self.bytes_transferred,
            "error_message": self.error_message,
            "details": self.details,
        }


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_url: str = "sqlite:///./lightrag_recovery.db"):
        """Initialize database manager.
        
        Args:
            db_url: Database URL (SQLAlchemy format)
        """
        self.db_url = db_url
        self.engine = None
        self.SessionLocal = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection and create tables."""
        # Use StaticPool for SQLite in-memory or file-based databases
        if "sqlite" in self.db_url:
            self.engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool if ":memory:" in self.db_url else None,
            )
        else:
            self.engine = create_engine(self.db_url)
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info(f"Database initialized: {self.db_url}")
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            SQLAlchemy Session
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database manager not properly initialized")
        return self.SessionLocal()
    
    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_url: str = "sqlite:///./lightrag_recovery.db") -> DatabaseManager:
    """Get global database manager instance.
    
    Args:
        db_url: Database URL for initialization
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_url)
    return _db_manager


def init_db(db_url: str) -> DatabaseManager:
    """Initialize global database manager.
    
    Args:
        db_url: Database URL
        
    Returns:
        Initialized DatabaseManager
    """
    global _db_manager
    _db_manager = DatabaseManager(db_url)
    return _db_manager
