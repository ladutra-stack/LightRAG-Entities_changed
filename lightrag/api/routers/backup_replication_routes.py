"""REST API Routes for Phase 5A - Backup, Replication, and Recovery

Provides endpoints for:
- Backup management (snapshots, restoration, cleanup)
- Replication management (targets, health checks, status)
- Disaster recovery (checkpoints, failover, health validation)
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from lightrag.backup import BackupManager, BackupStatus
from lightrag.replication import ReplicationManager, ReplicationTarget, ReplicationStatus
from lightrag.recovery import DisasterRecoveryManager, HealthStatus
from lightrag.api.models_recovery_db import (
    DatabaseManager,
    BackupMetadataDB,
    RecoveryPointDB,
    HealthEventDB,
    ReplicationEventDB,
    init_db,
    get_db_manager,
)
from lightrag.utils import logger

# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================


class SnapshotResponse(BaseModel):
    """Response model for backup snapshot."""
    backup_id: str
    graph_id: str
    status: str
    timestamp: datetime
    size_bytes: int
    data_hash: Optional[str] = None
    retention_until: Optional[datetime] = None
    checkpoint_path: str


class GraphBackupStatsResponse(BaseModel):
    """Response model for graph backup statistics."""
    graph_id: str
    total_snapshots: int
    total_size_bytes: int
    last_snapshot_time: Optional[datetime] = None


class BackupManagerStatsResponse(BaseModel):
    """Response model for backup manager statistics."""
    total_graphs: int
    total_snapshots: int
    total_size_bytes: int
    graphs: List[GraphBackupStatsResponse]


class ReplicationTargetResponse(BaseModel):
    """Response model for replication target."""
    target_id: str
    name: str
    base_url: str
    enabled: bool
    created_at: datetime


class ReplicationStatusResponse(BaseModel):
    """Response model for replication status."""
    graph_id: str
    total_targets: int
    enabled_targets: int
    targets: List[ReplicationTargetResponse]


class RecoveryPointResponse(BaseModel):
    """Response model for recovery checkpoint."""
    checkpoint_id: str
    graphs: List[str]
    description: str
    created_at: datetime
    validated: bool
    validation_timestamp: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    overall_status: str
    timestamp: datetime
    graphs: Dict[str, Any]
    backups: Dict[str, Any]
    replication: Dict[str, Any]


class CreateSnapshotRequest(BaseModel):
    """Request model for creating backup snapshot."""
    source_dir: str = Field(description="Path to working directory to backup")
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class RegisterTargetRequest(BaseModel):
    """Request model for registering replication target."""
    name: str = Field(description="Name of replication target")
    base_url: str = Field(description="Base URL of target LightRAG instance")
    api_key: str = Field(description="API key for authentication")


class CreateRecoveryPointRequest(BaseModel):
    """Request model for creating recovery checkpoint."""
    graph_ids: List[str] = Field(description="Graph IDs to include in checkpoint")
    description: str = Field(description="Description of recovery point")


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(
    prefix="/api/v1/backup-replication",
    tags=["backup-replication"],
    responses={404: {"description": "Not found"}},
)

# Global managers (would normally be injected via dependency injection)
_backup_manager: Optional[BackupManager] = None
_replication_manager: Optional[ReplicationManager] = None
_recovery_manager: Optional[DisasterRecoveryManager] = None
_db_manager: Optional[DatabaseManager] = None


def init_managers(
    backup_manager: BackupManager,
    replication_manager: ReplicationManager,
    recovery_manager: DisasterRecoveryManager,
    db_manager: Optional[DatabaseManager] = None,
):
    """Initialize managers for API routes."""
    global _backup_manager, _replication_manager, _recovery_manager, _db_manager
    _backup_manager = backup_manager
    _replication_manager = replication_manager
    _recovery_manager = recovery_manager
    _db_manager = db_manager or get_db_manager()
    logger.info("Backup/Replication/Recovery routes initialized with managers and DB persistence")


# ============================================================================
# Backup Endpoints
# ============================================================================


@router.post("/backup/graphs/{graph_id}/snapshots")
async def create_backup_snapshot(
    graph_id: str,
    request: CreateSnapshotRequest,
) -> SnapshotResponse:
    """Create a backup snapshot for a graph.
    
    Args:
        graph_id: ID of the graph to backup
        request: Snapshot creation request
        
    Returns:
        Created snapshot details
        
    Raises:
        HTTPException: If backup fails
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    try:
        graph_backup = _backup_manager.register_graph(graph_id)
        source_path = Path(request.source_dir)
        
        if not source_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Source directory not found: {request.source_dir}"
            )
        
        snapshot = await graph_backup.create_snapshot(
            source_path,
            metadata=request.metadata or {}
        )
        
        # Persist snapshot metadata to database
        if _db_manager:
            try:
                session = _db_manager.get_session()
                backup_record = BackupMetadataDB(
                    backup_id=snapshot.backup_id,
                    graph_id=snapshot.graph_id,
                    status=snapshot.status.value,
                    timestamp=snapshot.timestamp,
                    size_bytes=snapshot.size_bytes,
                    data_hash=snapshot.data_hash,
                    retention_until=snapshot.retention_until,
                    checkpoint_path=str(snapshot.checkpoint_path),
                    extra_metadata=request.metadata or {},
                )
                session.add(backup_record)
                session.commit()
                logger.info(f"Backup metadata persisted to DB: {snapshot.backup_id}")
            except Exception as e:
                logger.warning(f"Failed to persist backup metadata to DB: {e}")
                # Continue - backup still succeeded, just DB persistence failed
        
        return SnapshotResponse(
            backup_id=snapshot.backup_id,
            graph_id=snapshot.graph_id,
            status=snapshot.status.value,
            timestamp=snapshot.timestamp,
            size_bytes=snapshot.size_bytes,
            data_hash=snapshot.data_hash,
            retention_until=snapshot.retention_until,
            checkpoint_path=str(snapshot.checkpoint_path),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create snapshot: {str(exc)}"
        )


@router.get("/backup/graphs/{graph_id}/snapshots")
async def list_backup_snapshots(graph_id: str) -> List[SnapshotResponse]:
    """List all snapshots for a graph.
    
    Args:
        graph_id: ID of the graph
        
    Returns:
        List of snapshots
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    graph_backup = _backup_manager.get_graph_backup(graph_id)
    if not graph_backup:
        raise HTTPException(status_code=404, detail=f"Graph {graph_id} not found")
    
    snapshots = graph_backup.list_snapshots()
    
    return [
        SnapshotResponse(
            backup_id=s.backup_id,
            graph_id=s.graph_id,
            status=s.status.value,
            timestamp=s.timestamp,
            size_bytes=s.size_bytes,
            data_hash=s.data_hash,
            retention_until=s.retention_until,
            checkpoint_path=str(s.checkpoint_path),
        )
        for s in snapshots
    ]


@router.post("/backup/graphs/{graph_id}/snapshots/{snapshot_id}/restore")
async def restore_backup_snapshot(
    graph_id: str,
    snapshot_id: str,
    target_dir: str = Body(embed=True),
) -> Dict[str, str]:
    """Restore from a backup snapshot.
    
    Args:
        graph_id: ID of the graph
        snapshot_id: ID of the snapshot to restore
        target_dir: Target directory for restoration
        
    Returns:
        Restoration status
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    try:
        graph_backup = _backup_manager.get_graph_backup(graph_id)
        if not graph_backup:
            raise HTTPException(status_code=404, detail=f"Graph {graph_id} not found")
        
        await graph_backup.restore_snapshot(snapshot_id, Path(target_dir))
        
        return {
            "status": "success",
            "message": f"Restored snapshot {snapshot_id} to {target_dir}"
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore snapshot: {str(exc)}"
        )


@router.delete("/backup/graphs/{graph_id}/snapshots/{snapshot_id}")
async def delete_backup_snapshot(
    graph_id: str,
    snapshot_id: str,
) -> Dict[str, str]:
    """Delete a backup snapshot.
    
    Args:
        graph_id: ID of the graph
        snapshot_id: ID of snapshot to delete
        
    Returns:
        Deletion status
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    try:
        graph_backup = _backup_manager.get_graph_backup(graph_id)
        if not graph_backup:
            raise HTTPException(status_code=404, detail=f"Graph {graph_id} not found")
        
        success = await graph_backup.delete_snapshot(snapshot_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Snapshot {snapshot_id} not found"
            )
        
        return {"status": "success", "message": f"Deleted snapshot {snapshot_id}"}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete snapshot: {str(exc)}"
        )


@router.post("/backup/cleanup")
async def cleanup_old_snapshots() -> Dict[str, int]:
    """Clean up expired snapshots across all graphs.
    
    Returns:
        Number of snapshots deleted
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    try:
        result = await _backup_manager.cleanup_old_backups()
        deleted = sum(result.values())
        return {"deleted_snapshots": deleted}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup snapshots: {str(exc)}"
        )


@router.get("/backup/stats")
async def get_backup_stats() -> BackupManagerStatsResponse:
    """Get backup manager statistics.
    
    Returns:
        Backup statistics
    """
    if not _backup_manager:
        raise HTTPException(status_code=500, detail="Backup manager not initialized")
    
    stats = _backup_manager.get_total_stats()
    graph_stats = []
    
    for graph_id, graph_backup in _backup_manager._graph_backups.items():
        snaps = graph_backup.list_snapshots()
        total_size = sum(s.size_bytes for s in snaps)
        
        graph_stats.append(GraphBackupStatsResponse(
            graph_id=graph_id,
            total_snapshots=len(snaps),
            total_size_bytes=total_size,
            last_snapshot_time=snaps[-1].timestamp if snaps else None,
        ))
    
    return BackupManagerStatsResponse(
        total_graphs=stats["total_graphs"],
        total_snapshots=stats["total_snapshots"],
        total_size_bytes=stats["total_size_bytes"],
        graphs=graph_stats,
    )


# ============================================================================
# Replication Endpoints
# ============================================================================


@router.post("/replication/targets")
async def register_replication_target(
    request: RegisterTargetRequest,
) -> ReplicationTargetResponse:
    """Register a replication target.
    
    Args:
        request: Target registration request
        
    Returns:
        Registered target details
    """
    if not _replication_manager:
        raise HTTPException(status_code=500, detail="Replication manager not initialized")
    
    try:
        target = ReplicationTarget(
            name=request.name,
            base_url=request.base_url,
            api_key=request.api_key,
        )
        
        success = _replication_manager.register_target(target)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to register target"
            )
        
        return ReplicationTargetResponse(
            target_id=target.target_id,
            name=target.name,
            base_url=target.base_url,
            enabled=target.enabled,
            created_at=target.created_at,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register target: {str(exc)}"
        )


@router.get("/replication/targets")
async def list_replication_targets() -> List[ReplicationTargetResponse]:
    """List all replication targets.
    
    Returns:
        List of targets
    """
    if not _replication_manager:
        raise HTTPException(status_code=500, detail="Replication manager not initialized")
    
    targets = _replication_manager.list_targets()
    
    return [
        ReplicationTargetResponse(
            target_id=t.target_id,
            name=t.name,
            base_url=t.base_url,
            enabled=t.enabled,
            created_at=t.created_at,
        )
        for t in targets
    ]


@router.get("/replication/targets/{target_id}/health")
async def check_target_health(target_id: str) -> Dict[str, Any]:
    """Check health of a replication target.
    
    Args:
        target_id: ID of the target
        
    Returns:
        Health status
    """
    if not _replication_manager:
        raise HTTPException(status_code=500, detail="Replication manager not initialized")
    
    try:
        target = None
        for t in _replication_manager.list_targets():
            if t.target_id == target_id:
                target = t
                break
        
        if not target:
            raise HTTPException(status_code=404, detail=f"Target {target_id} not found")
        
        replicator = _replication_manager.get_graph_replicator("_health_check")
        replicator.add_target(target)
        health = await replicator.check_target_health(target_id)
        
        return {"target_id": target_id, "status": health.value}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check target health: {str(exc)}"
        )


@router.delete("/replication/targets/{target_id}")
async def remove_replication_target(target_id: str) -> Dict[str, str]:
    """Remove a replication target.
    
    Args:
        target_id: ID of the target
        
    Returns:
        Removal status
    """
    if not _replication_manager:
        raise HTTPException(status_code=500, detail="Replication manager not initialized")
    
    try:
        # Remove from all graphs
        for graph_replicator in _replication_manager._graph_replicators.values():
            graph_replicator.remove_target(target_id)
        
        return {"status": "success", "message": f"Removed target {target_id}"}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove target: {str(exc)}"
        )


@router.get("/replication/graphs/{graph_id}/status")
async def get_replication_status(graph_id: str) -> ReplicationStatusResponse:
    """Get replication status for a graph.
    
    Args:
        graph_id: ID of the graph
        
    Returns:
        Replication status
    """
    if not _replication_manager:
        raise HTTPException(status_code=500, detail="Replication manager not initialized")
    
    replicator = _replication_manager.get_graph_replicator(graph_id)
    status = replicator.get_replication_status()
    
    targets = [
        ReplicationTargetResponse(
            target_id=t.target_id,
            name=t.name,
            base_url=t.base_url,
            enabled=t.enabled,
            created_at=t.created_at,
        )
        for t in replicator.list_targets()
    ]
    
    return ReplicationStatusResponse(
        graph_id=graph_id,
        total_targets=status["total_targets"],
        enabled_targets=status["enabled_targets"],
        targets=targets,
    )


# ============================================================================
# Disaster Recovery Endpoints
# ============================================================================


@router.post("/recovery/checkpoints")
async def create_recovery_checkpoint(
    request: CreateRecoveryPointRequest,
) -> RecoveryPointResponse:
    """Create a recovery checkpoint.
    
    Args:
        request: Checkpoint creation request
        
    Returns:
        Created checkpoint details
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    try:
        checkpoint = await _recovery_manager.create_recovery_point(
            graph_ids=request.graph_ids,
            description=request.description,
        )
        
        # Persist recovery point to database
        if _db_manager:
            try:
                session = _db_manager.get_session()
                recovery_record = RecoveryPointDB(
                    checkpoint_id=checkpoint.checkpoint_id,
                    graphs=checkpoint.graphs,
                    description=checkpoint.description,
                    created_at=checkpoint.timestamp,
                    validated=checkpoint.validated,
                    validation_timestamp=checkpoint.validation_timestamp,
                )
                session.add(recovery_record)
                session.commit()
                logger.info(f"Recovery point persisted to DB: {checkpoint.checkpoint_id}")
            except Exception as e:
                logger.warning(f"Failed to persist recovery point to DB: {e}")
                # Continue - checkpoint still succeeded, just DB persistence failed
        
        return RecoveryPointResponse(
            checkpoint_id=checkpoint.checkpoint_id,
            graphs=checkpoint.graphs,
            description=checkpoint.description,
            created_at=checkpoint.timestamp,
            validated=checkpoint.validated,
            validation_timestamp=checkpoint.validation_timestamp,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkpoint: {str(exc)}"
        )


@router.get("/recovery/checkpoints")
async def list_recovery_checkpoints() -> List[RecoveryPointResponse]:
    """List all recovery checkpoints.
    
    Returns:
        List of checkpoints
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    checkpoints = _recovery_manager.list_recovery_points()
    
    return [
        RecoveryPointResponse(
            checkpoint_id=c.checkpoint_id,
            graphs=c.graphs,
            description=c.description,
            created_at=c.timestamp,
            validated=c.validated,
            validation_timestamp=c.validation_timestamp,
        )
        for c in checkpoints
    ]


@router.get("/recovery/checkpoints/{checkpoint_id}")
async def get_recovery_checkpoint(checkpoint_id: str) -> RecoveryPointResponse:
    """Get details of a specific checkpoint.
    
    Args:
        checkpoint_id: ID of the checkpoint
        
    Returns:
        Checkpoint details
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    checkpoint = _recovery_manager.get_recovery_point(checkpoint_id)
    if not checkpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint {checkpoint_id} not found"
        )
    
    return RecoveryPointResponse(
        checkpoint_id=checkpoint.checkpoint_id,
        graphs=checkpoint.graphs,
        description=checkpoint.description,
        created_at=checkpoint.timestamp,
        validated=checkpoint.validated,
        validation_timestamp=checkpoint.validation_timestamp,
    )


@router.post("/recovery/checkpoints/{checkpoint_id}/validate")
async def validate_recovery_checkpoint(checkpoint_id: str) -> Dict[str, bool]:
    """Validate a recovery checkpoint.
    
    Args:
        checkpoint_id: ID of the checkpoint
        
    Returns:
        Validation result
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    try:
        is_valid = await _recovery_manager.validate_recovery_point(checkpoint_id)
        return {"valid": is_valid}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate checkpoint: {str(exc)}"
        )


@router.post("/recovery/checkpoints/{checkpoint_id}/failover")
async def initiate_failover(checkpoint_id: str) -> Dict[str, bool]:
    """Initiate failover to a recovery checkpoint.
    
    Args:
        checkpoint_id: ID of the checkpoint
        
    Returns:
        Failover result
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    try:
        success = await _recovery_manager.initiate_failover(checkpoint_id)
        return {"success": success}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate failover: {str(exc)}"
        )


@router.get("/recovery/health")
async def get_recovery_health() -> HealthCheckResponse:
    """Get comprehensive health check.
    
    Returns:
        Health status
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    try:
        health = await _recovery_manager.health_check()
        
        # Persist health check to database
        if _db_manager:
            try:
                session = _db_manager.get_session()
                health_record = HealthEventDB(
                    status=health["overall_status"],
                    timestamp=health.get("timestamp", datetime.utcnow()),
                    details=health,
                )
                session.add(health_record)
                session.commit()
                logger.debug(f"Health check persisted to DB: {health['overall_status']}")
            except Exception as e:
                logger.warning(f"Failed to persist health check to DB: {e}")
                # Continue - health check still succeeded, just DB persistence failed
        
        return HealthCheckResponse(
            overall_status=health["overall_status"],
            timestamp=health.get("timestamp", datetime.utcnow()),
            graphs=health.get("graphs", {}),
            backups=health.get("backups", {}),
            replication=health.get("replication", {}),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health check: {str(exc)}"
        )


@router.get("/recovery/status")
async def get_recovery_status() -> Dict[str, Any]:
    """Get recovery system status.
    
    Returns:
        Recovery status
    """
    if not _recovery_manager:
        raise HTTPException(status_code=500, detail="Recovery manager not initialized")
    
    return _recovery_manager.get_recovery_status()
