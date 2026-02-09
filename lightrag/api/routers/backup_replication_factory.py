"""
Factory and initialization functions for Backup/Replication/Recovery routes

Provides configuration-aware route creation and manager initialization for 
integration with lightrag_server.py
"""

from typing import Optional
from pathlib import Path
from fastapi import APIRouter
from lightrag.backup import BackupManager
from lightrag.replication import ReplicationManager
from lightrag.recovery import DisasterRecoveryManager
from lightrag.api.config_backup_replication import (
    BackupReplicationConfig,
    get_config,
)
from lightrag.api.models_recovery_db import (
    init_db,
    get_db_manager,
)
from lightrag.api.routers.backup_replication_routes import (
    router as backup_replication_router,
    init_managers,
)
from lightrag.utils import logger


def create_backup_replication_managers(
    config: Optional[BackupReplicationConfig] = None,
) -> tuple[BackupManager, ReplicationManager, DisasterRecoveryManager]:
    """Create and initialize Backup/Replication/Recovery managers.
    
    Args:
        config: Configuration object (uses global if None)
        
    Returns:
        Tuple of (BackupManager, ReplicationManager, DisasterRecoveryManager)
    """
    if config is None:
        config = get_config()
    
    logger.info("Initializing Backup/Replication/Recovery managers...")
    
    # Initialize database if recovery is enabled
    if config.recovery_enabled:
        init_db(config.recovery_db_url)
        logger.info(f"Recovery database initialized: {config.recovery_db_url}")
    
    # Create managers
    backup_manager = BackupManager(
        storage_path=config.backup_storage_path,
        retention_days=config.backup_retention_days,
        auto_cleanup_interval_hours=config.auto_backup_interval_hours,
    )
    logger.info(f"BackupManager initialized with storage: {config.backup_storage_path}")
    
    replication_manager = ReplicationManager()
    logger.info("ReplicationManager initialized")
    
    recovery_manager = DisasterRecoveryManager()
    logger.info("DisasterRecoveryManager initialized")
    
    # Wire managers into routes
    init_managers(backup_manager, replication_manager, recovery_manager)
    logger.info("Managers wired into backup_replication_routes")
    
    return backup_manager, replication_manager, recovery_manager


def create_backup_replication_router(
    backup_manager: BackupManager,
    replication_manager: ReplicationManager,
    recovery_manager: DisasterRecoveryManager,
    api_key: Optional[str] = None,
) -> APIRouter:
    """Create backup/replication/recovery API router.
    
    Args:
        backup_manager: Initialized BackupManager
        replication_manager: Initialized ReplicationManager
        recovery_manager: Initialized DisasterRecoveryManager
        api_key: Optional API key for authentication
        
    Returns:
        Configured FastAPI Router
    """
    # Wire managers into routes (already done in create_backup_replication_managers)
    return backup_replication_router


def can_initialize_backup_replication() -> bool:
    """Check if backup/replication can be initialized.
    
    Returns:
        True if configuration allows initialization
    """
    try:
        config = get_config()
        if not config.backup_enabled and not config.replication_enabled and not config.recovery_enabled:
            logger.warning("All Backup/Replication/Recovery features are disabled")
            return False
        return True
    except Exception as e:
        logger.error(f"Cannot initialize Backup/Replication/Recovery: {e}")
        return False


def get_config_summary() -> dict:
    """Get summary of current Backup/Replication/Recovery configuration.
    
    Returns:
        Dictionary with configuration summary
    """
    config = get_config()
    return {
        "backup": {
            "enabled": config.backup_enabled,
            "storage_path": str(config.backup_storage_path),
            "retention_days": config.backup_retention_days,
        },
        "replication": {
            "enabled": config.replication_enabled,
        },
        "recovery": {
            "enabled": config.recovery_enabled,
            "db_url": config.recovery_db_url,
        },
        "monitoring": {
            "metrics_enabled": config.metrics_enabled,
            "metrics_port": config.metrics_port,
            "health_check_enabled": config.health_check_enabled,
        },
    }
