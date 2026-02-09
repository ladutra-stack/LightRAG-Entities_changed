"""
Configuration Management for Backup, Replication, and Recovery Systems

Handles loading, validation, and management of configuration for Phase 5B/5C features.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
from lightrag.utils import logger, get_env_value


@dataclass
class BackupReplicationConfig:
    """Configuration for Backup/Replication/Recovery systems."""
    
    # Backup Configuration
    backup_enabled: bool = True
    backup_storage_path: Path = field(default_factory=lambda: Path("/tmp/lightrag_backups"))
    backup_retention_days: int = 30
    auto_backup_interval_hours: int = 24
    
    # Replication Configuration
    replication_enabled: bool = False
    replication_targets: dict = field(default_factory=dict)
    replication_health_check_interval_seconds: int = 300
    
    # Recovery Configuration
    recovery_enabled: bool = True
    recovery_db_url: str = "sqlite:///./lightrag_recovery.db"
    recovery_checkpoint_interval_hours: int = 12
    
    # Monitoring Configuration
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_collection_interval_seconds: int = 60
    health_check_enabled: bool = True
    
    # Event Logging
    event_logging_enabled: bool = True
    event_log_retention_days: int = 90
    
    @classmethod
    def from_env(cls) -> "BackupReplicationConfig":
        """Load configuration from environment variables.
        
        Returns:
            BackupReplicationConfig with values loaded from env
        """
        backup_storage = get_env_value(
            "LIGHTRAG_BACKUP_STORAGE",
            "/tmp/lightrag_backups"
        )
        
        recovery_db = get_env_value(
            "LIGHTRAG_RECOVERY_DB_URL",
            "sqlite:///./lightrag_recovery.db"
        )
        
        return cls(
            backup_enabled=get_env_value("LIGHTRAG_BACKUP_ENABLED", "true").lower() == "true",
            backup_storage_path=Path(backup_storage),
            backup_retention_days=int(get_env_value("LIGHTRAG_BACKUP_RETENTION_DAYS", "30")),
            auto_backup_interval_hours=int(get_env_value("LIGHTRAG_AUTO_BACKUP_INTERVAL", "24")),
            
            replication_enabled=get_env_value("LIGHTRAG_REPLICATION_ENABLED", "false").lower() == "true",
            replication_health_check_interval_seconds=int(
                get_env_value("LIGHTRAG_REPLICATION_HEALTH_CHECK_INTERVAL", "300")
            ),
            
            recovery_enabled=get_env_value("LIGHTRAG_RECOVERY_ENABLED", "true").lower() == "true",
            recovery_db_url=recovery_db,
            recovery_checkpoint_interval_hours=int(
                get_env_value("LIGHTRAG_RECOVERY_CHECKPOINT_INTERVAL", "12")
            ),
            
            metrics_enabled=get_env_value("LIGHTRAG_METRICS_ENABLED", "true").lower() == "true",
            metrics_port=int(get_env_value("LIGHTRAG_METRICS_PORT", "9090")),
            metrics_collection_interval_seconds=int(
                get_env_value("LIGHTRAG_METRICS_COLLECTION_INTERVAL", "60")
            ),
            health_check_enabled=get_env_value("LIGHTRAG_HEALTH_CHECK_ENABLED", "true").lower() == "true",
            
            event_logging_enabled=get_env_value("LIGHTRAG_EVENT_LOGGING_ENABLED", "true").lower() == "true",
            event_log_retention_days=int(get_env_value("LIGHTRAG_EVENT_LOG_RETENTION", "90")),
        )
    
    def validate(self) -> bool:
        """Validate configuration.
        
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate backup config
        if self.backup_enabled:
            if not self.backup_storage_path:
                raise ValueError("backup_storage_path is required when backup_enabled=True")
            if self.backup_retention_days <= 0:
                raise ValueError("backup_retention_days must be positive")
        
        # Validate recovery config
        if self.recovery_enabled:
            if not self.recovery_db_url:
                raise ValueError("recovery_db_url is required when recovery_enabled=True")
        
        # Validate metrics config
        if self.metrics_enabled:
            if self.metrics_port <= 0 or self.metrics_port > 65535:
                raise ValueError("metrics_port must be valid port number")
        
        logger.info("Backup/Replication/Recovery configuration validated successfully")
        return True
    
    def ensure_storage_paths(self):
        """Ensure all required storage paths exist."""
        if self.backup_enabled:
            self.backup_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Backup storage path ready: {self.backup_storage_path}")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "backup": {
                "enabled": self.backup_enabled,
                "storage_path": str(self.backup_storage_path),
                "retention_days": self.backup_retention_days,
                "auto_backup_interval_hours": self.auto_backup_interval_hours,
            },
            "replication": {
                "enabled": self.replication_enabled,
                "health_check_interval_seconds": self.replication_health_check_interval_seconds,
            },
            "recovery": {
                "enabled": self.recovery_enabled,
                "db_url": self.recovery_db_url,
                "checkpoint_interval_hours": self.recovery_checkpoint_interval_hours,
            },
            "monitoring": {
                "metrics_enabled": self.metrics_enabled,
                "metrics_port": self.metrics_port,
                "metrics_collection_interval_seconds": self.metrics_collection_interval_seconds,
                "health_check_enabled": self.health_check_enabled,
                "event_logging_enabled": self.event_logging_enabled,
                "event_log_retention_days": self.event_log_retention_days,
            },
        }


# Global configuration instance
_config: Optional[BackupReplicationConfig] = None


def get_config() -> BackupReplicationConfig:
    """Get global configuration instance.
    
    Returns:
        BackupReplicationConfig instance
    """
    global _config
    if _config is None:
        _config = BackupReplicationConfig.from_env()
        _config.validate()
        _config.ensure_storage_paths()
    return _config


def init_config(config: BackupReplicationConfig) -> None:
    """Initialize global configuration instance.
    
    Args:
        config: Configuration to use globally
    """
    global _config
    config.validate()
    config.ensure_storage_paths()
    _config = config
    logger.info("Global Backup/Replication/Recovery configuration initialized")
