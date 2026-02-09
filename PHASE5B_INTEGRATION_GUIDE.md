"""
Phase 5B Integration Guide - How to integrate Backup/Replication/Recovery into lightrag_server.py

This document shows exactly where and how to integrate the Phase 5A+5B components
into the existing LightRAG FastAPI server.
"""

# ============================================================================
# STEP 1: Add imports at the top of lightrag/api/lightrag_server.py (line ~53)
# ============================================================================

# Add these imports:
from lightrag.api.config_backup_replication import (
    BackupReplicationConfig,
    init_config,
    get_config,
)
from lightrag.api.routers.backup_replication_factory import (
    create_backup_replication_managers,
    create_backup_replication_router,
    can_initialize_backup_replication,
    get_config_summary,
)


# ============================================================================
# STEP 2: Initialize configuration early in create_app() function
# ============================================================================

# Location: Around line 350 in lightrag_server.py, after load_dotenv()
# Add this code:

def create_app(args):
    """
    Original docstring...
    """
    
    # ... existing code ...
    
    # Initialize Backup/Replication/Recovery configuration
    br_config = BackupReplicationConfig.from_env()
    init_config(br_config)
    logger.info(f"Backup/Replication/Recovery Configuration: {br_config.to_dict()}")
    
    # ... rest of create_app() ...


# ============================================================================
# STEP 3: Initialize managers in create_app() before routes
# ============================================================================

# Location: Around line 1130 in lightrag_server.py, before "# Add routes"
# Add this code:

    # Initialize Backup/Replication/Recovery if enabled
    backup_manager = None
    replication_manager = None
    recovery_manager = None
    
    if can_initialize_backup_replication():
        try:
            backup_manager, replication_manager, recovery_manager = (
                create_backup_replication_managers(br_config)
            )
            logger.info("Backup/Replication/Recovery managers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Backup/Replication/Recovery: {e}")
            # Continue without these features, don't fail server startup
    else:
        logger.info("Backup/Replication/Recovery features are disabled")


# ============================================================================
# STEP 4: Register routes with the FastAPI app
# ============================================================================

# Location: Around line 1160 in lightrag_server.py, after "# Add routes"
# Add this code:

    # Add Backup/Replication/Recovery routes if managers are initialized
    if backup_manager and replication_manager and recovery_manager:
        try:
            br_router = create_backup_replication_router(
                backup_manager,
                replication_manager,
                recovery_manager,
                api_key=api_key,
            )
            app.include_router(br_router)
            logger.info("Backup/Replication/Recovery routes registered")
        except Exception as e:
            logger.error(f"Failed to register Backup/Replication/Recovery routes: {e}")


# ============================================================================
# STEP 5: Add startup/shutdown events (optional but recommended)
# ============================================================================

# Location: In create_app(), after app routes are set up
# Add this code:

    @app.on_event("startup")
    async def startup_event():
        """Handle startup events for Backup/Replication/Recovery."""
        if can_initialize_backup_replication():
            logger.info("Backup/Replication/Recovery system ready")
            config = get_config()
            logger.info(f"Configuration: {config.to_dict()}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Handle shutdown events for Backup/Replication/Recovery."""
        logger.info("Shutting down Backup/Replication/Recovery system")
        # TODO: Add cleanup logic if needed


# ============================================================================
# STEP 6: Add health check endpoint for monitoring
# ============================================================================

# Location: In create_app(), after other endpoints (around line 1190)
# Add this code:

    @app.get("/api/v1/system/status")
    async def get_system_status():
        """Get system status including Backup/Replication/Recovery."""
        try:
            br_config = get_config_summary()
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "backup_replication_recovery": br_config,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# ============================================================================
# ENVIRONMENT VARIABLES NEEDED
# ============================================================================

# Add to .env file:
"""
# Backup Configuration
LIGHTRAG_BACKUP_ENABLED=true
LIGHTRAG_BACKUP_STORAGE=/path/to/lightrag_backups
LIGHTRAG_BACKUP_RETENTION_DAYS=30
LIGHTRAG_AUTO_BACKUP_INTERVAL=24

# Replication Configuration
LIGHTRAG_REPLICATION_ENABLED=false
LIGHTRAG_REPLICATION_HEALTH_CHECK_INTERVAL=300

# Recovery Configuration
LIGHTRAG_RECOVERY_ENABLED=true
LIGHTRAG_RECOVERY_DB_URL=sqlite:///./lightrag_recovery.db
LIGHTRAG_RECOVERY_CHECKPOINT_INTERVAL=12

# Monitoring Configuration
LIGHTRAG_METRICS_ENABLED=true
LIGHTRAG_METRICS_PORT=9090
LIGHTRAG_METRICS_COLLECTION_INTERVAL=60
LIGHTRAG_HEALTH_CHECK_ENABLED=true
LIGHTRAG_EVENT_LOGGING_ENABLED=true
LIGHTRAG_EVENT_LOG_RETENTION=90
"""


# ============================================================================
# EXAMPLE COMPLETE INTEGRATION
# ============================================================================

"""
Here's what the create_app() function looks like after integration:

def create_app(args):
    # ... existing code ...
    
    # NEW: Initialize Backup/Replication/Recovery configuration
    br_config = BackupReplicationConfig.from_env()
    init_config(br_config)
    logger.info(f"BR Configuration: {br_config.to_dict()}")
    
    # ... existing code ...
    
    # NEW: Initialize managers
    backup_manager = None
    replication_manager = None
    recovery_manager = None
    
    if can_initialize_backup_replication():
        try:
            backup_manager, replication_manager, recovery_manager = (
                create_backup_replication_managers(br_config)
            )
            logger.info("Managers initialized")
        except Exception as e:
            logger.error(f"Failed to init managers: {e}")
    
    # Existing route registration...
    app.include_router(create_document_routes(...))
    app.include_router(create_query_routes(...))
    app.include_router(create_graph_routes(...))
    app.include_router(create_graph_manager_routes(...))
    
    # NEW: Register Backup/Replication/Recovery routes
    if backup_manager and replication_manager and recovery_manager:
        try:
            br_router = create_backup_replication_router(
                backup_manager,
                replication_manager,
                recovery_manager,
                api_key=api_key,
            )
            app.include_router(br_router)
            logger.info("BR routes registered")
        except Exception as e:
            logger.error(f"Failed to register BR routes: {e}")
    
    # Existing endpoints...
    @app.on_event("startup")
    async def startup_event():
        logger.info("Server started successfully")
    
    return app
"""


# ============================================================================
# DEPENDENCIES NEEDED
# ============================================================================

"""
Add to requirements.txt or pyproject.toml:

sqlalchemy>=2.0.0
"""


# ============================================================================
# TESTING THE INTEGRATION
# ============================================================================

"""
After making changes:

1. Start the server:
   python -m lightrag.api.lightrag_server --working_dir /tmp/test

2. Check if routes are available:
   curl http://localhost:8000/api/v1/backup-replication/backup/stats

3. Check system status:
   curl http://localhost:8000/api/v1/system/status

4. View database:
   ls -la ./lightrag_recovery.db  (SQLite file)

5. View backups:
   ls -la /path/to/lightrag_backups
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
Issue: Routes not appearing in Swagger UI
- Solution: Check if managers initialized successfully (check logs)
- Verify env vars are set correctly

Issue: Database initialization fails
- Solution: Check LIGHTRAG_RECOVERY_DB_URL is valid
- Ensure directory has write permissions

Issue: Backups not working
- Solution: Check LIGHTRAG_BACKUP_STORAGE directory exists
- Verify read/write permissions

Issue: Performance degradation
- Solution: Can disable metrics with LIGHTRAG_METRICS_ENABLED=false
- Can set LIGHTRAG_AUTO_BACKUP_INTERVAL higher
"""
