"""
Monitoring and Analytics Routes for Phase 5C

Provides REST API endpoints for health monitoring, metrics collection,
and dashboard visualization.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from lightrag.utils import logger
from lightrag.monitoring.metrics_collector import get_metrics_collector
from lightrag.api.models_recovery_db import (
    get_db_manager,
    BackupMetadataDB,
    RecoveryPointDB,
    HealthEventDB,
    ReplicationEventDB,
)


# ============================================================================
# Pydantic Models
# ============================================================================

class MetricResponse(BaseModel):
    """Response model for metric data."""
    name: str
    value: float
    type: str
    help: str
    timestamp: str


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary."""
    collector_enabled: bool
    collection_interval: int
    last_collection: str
    metrics_count: int
    status: str


class HealthStatusResponse(BaseModel):
    """Response model for health status."""
    overall_status: str  # healthy, degraded, critical, offline
    last_check: str
    backup_status: str
    recovery_status: str
    replication_status: str
    details: Dict[str, Any]


class BackupStatsResponse(BaseModel):
    """Response model for backup statistics."""
    total_backups: int
    total_size_bytes: int
    recent_backups: int
    failed_backups: int
    average_size_bytes: float
    oldest_backup: Optional[str]
    newest_backup: Optional[str]


class RecoveryStatsResponse(BaseModel):
    """Response model for recovery statistics."""
    total_checkpoints: int
    validated_checkpoints: int
    failed_validations: int
    oldest_checkpoint: Optional[str]
    newest_checkpoint: Optional[str]
    validation_success_rate: float


# ============================================================================
# Router Implementation
# ============================================================================

router = APIRouter(
    prefix="/api/monitoring",
    tags=["Monitoring & Analytics"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Metrics Endpoints
# ============================================================================

@router.get("/metrics", response_model=Dict[str, MetricResponse])
async def get_metrics() -> Dict[str, MetricResponse]:
    """Get all current metrics.
    
    Returns:
        Dictionary of all metrics with their values
    """
    collector = get_metrics_collector()
    if not collector:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized")
    
    metrics_dict = collector.get_metrics_dict()
    
    # Convert to response format
    result = {}
    for name, data in metrics_dict.items():
        result[name] = MetricResponse(
            name=name,
            value=data["value"],
            type=data["type"],
            help=data["help"],
            timestamp=data["timestamp"],
        )
    
    return result


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_metrics_prometheus() -> str:
    """Get metrics in Prometheus text format.
    
    Returns:
        Prometheus format metrics
    """
    collector = get_metrics_collector()
    if not collector:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized")
    
    return collector.export_prometheus()


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary() -> MetricsSummaryResponse:
    """Get metrics collection summary.
    
    Returns:
        Summary of metrics collector status
    """
    collector = get_metrics_collector()
    if not collector:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized")
    
    summary = collector.get_metrics_summary()
    
    return MetricsSummaryResponse(
        collector_enabled=summary["collector_enabled"],
        collection_interval=summary["collection_interval"],
        last_collection=summary["last_collection"],
        metrics_count=summary["metrics_count"],
        status=summary["status"],
    )


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health", response_model=HealthStatusResponse)
async def get_health_status() -> HealthStatusResponse:
    """Get current health status.
    
    Returns:
        Health status of all components
    """
    try:
        db_manager = get_db_manager()
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        session = db_manager.get_session()
        
        # Get recent health events
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_events = session.query(HealthEventDB).filter(
            HealthEventDB.created_at >= cutoff
        ).order_by(HealthEventDB.created_at.desc()).first()
        
        # Determine component status
        backup_status = "unknown"
        recovery_status = "unknown"
        replication_status = "unknown"
        
        if recent_events:
            # Analyze events to determine status
            events_by_type = {}
            for evt in session.query(HealthEventDB).filter(
                HealthEventDB.created_at >= cutoff
            ).all():
                events_by_type.setdefault(evt.component_type, []).append(evt)
            
            backup_status = events_by_type.get("backup", [{"status": "unknown"}])[0].status
            recovery_status = events_by_type.get("recovery", [{"status": "unknown"}])[0].status
            replication_status = events_by_type.get("replication", [{"status": "unknown"}])[0].status
        
        # Determine overall status
        all_statuses = [backup_status, recovery_status, replication_status]
        if any(s == "critical" for s in all_statuses):
            overall_status = "critical"
        elif any(s == "degraded" for s in all_statuses):
            overall_status = "degraded"
        elif all(s in ["healthy", "unknown"] for s in all_statuses):
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        session.close()
        
        return HealthStatusResponse(
            overall_status=overall_status,
            last_check=datetime.utcnow().isoformat(),
            backup_status=backup_status,
            recovery_status=recovery_status,
            replication_status=replication_status,
            details={
                "checked_at": datetime.utcnow().isoformat(),
                "last_events_count": len(all_statuses),
            },
        )
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health status: {str(e)}")


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/backups", response_model=BackupStatsResponse)
async def get_backup_stats() -> BackupStatsResponse:
    """Get backup statistics.
    
    Returns:
        Backup statistics and trends
    """
    try:
        db_manager = get_db_manager()
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        session = db_manager.get_session()
        
        # Query backup data
        all_backups = session.query(BackupMetadataDB).all()
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_backups = session.query(BackupMetadataDB).filter(
            BackupMetadataDB.created_at >= recent_cutoff
        ).count()
        failed_backups = session.query(BackupMetadataDB).filter_by(status="failed").count()
        
        # Calculate statistics
        total_size = 0
        for b in all_backups:
            if b.size_bytes is not None and isinstance(b.size_bytes, int):
                total_size += b.size_bytes
        
        average_size = float(total_size / len(all_backups)) if all_backups else 0.0
        
        oldest = min(all_backups, key=lambda b: b.created_at).created_at.isoformat() if all_backups else None
        newest = max(all_backups, key=lambda b: b.created_at).created_at.isoformat() if all_backups else None
        
        session.close()
        
        return BackupStatsResponse(
            total_backups=len(all_backups),
            total_size_bytes=int(total_size) if isinstance(total_size, (int, float)) else 0,
            recent_backups=recent_backups,
            failed_backups=failed_backups,
            average_size_bytes=float(average_size),
            oldest_backup=oldest,
            newest_backup=newest,
        )
    except Exception as e:
        logger.error(f"Error getting backup stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backup stats: {str(e)}")


@router.get("/stats/recovery", response_model=RecoveryStatsResponse)
async def get_recovery_stats() -> RecoveryStatsResponse:
    """Get recovery statistics.
    
    Returns:
        Recovery checkpoint statistics and trends
    """
    try:
        db_manager = get_db_manager()
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        session = db_manager.get_session()
        
        # Query recovery data
        all_checkpoints = session.query(RecoveryPointDB).all()
        validated_checkpoints = session.query(RecoveryPointDB).filter_by(validated=True).count()
        failed_validations = session.query(RecoveryPointDB).filter_by(validated=False).count()
        
        # Calculate statistics
        total_checkpoints = len(all_checkpoints)
        success_rate = (validated_checkpoints / total_checkpoints * 100) if total_checkpoints > 0 else 0
        
        oldest = min(all_checkpoints, key=lambda c: c.created_at).created_at.isoformat() if all_checkpoints else None
        newest = max(all_checkpoints, key=lambda c: c.created_at).created_at.isoformat() if all_checkpoints else None
        
        session.close()
        
        return RecoveryStatsResponse(
            total_checkpoints=total_checkpoints,
            validated_checkpoints=validated_checkpoints,
            failed_validations=failed_validations,
            oldest_checkpoint=oldest,
            newest_checkpoint=newest,
            validation_success_rate=success_rate,
        )
    except Exception as e:
        logger.error(f"Error getting recovery stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recovery stats: {str(e)}")


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard() -> str:
    """Get HTML dashboard for monitoring.
    
    Returns:
        HTML dashboard page
    """
    try:
        collector = get_metrics_collector()
        db_manager = get_db_manager()
        
        # Fetch current data
        backup_stats = None
        recovery_stats = None
        health_status = None
        
        if db_manager:
            try:
                session = db_manager.get_session()
                all_backups = session.query(BackupMetadataDB).count()
                all_recovery = session.query(RecoveryPointDB).count()
                session.close()
                
                backup_stats = {"total": all_backups}
                recovery_stats = {"total": all_recovery}
            except:
                pass
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>LightRAG Monitoring Dashboard</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                header {{ background: #2c3e50; color: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; }}
                h1 {{ margin:  0; }}
                .status {{ font-size: 14px; margin-top: 10px; opacity: 0.9; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .card h2 {{ font-size: 14px; color: #666; margin-bottom: 10px; text-transform: uppercase; }}
                .card-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
                .card-unit {{ font-size: 12px; color: #999; margin-top: 5px; }}
                .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
                .status-healthy {{ background: #27ae60; }}
                .status-warning {{ background: #f39c12; }}
                .status-error {{ background: #e74c3c; }}
                .metrics {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metrics h2 {{ margin-bottom: 15px; }}
                .metric-item {{ padding: 10px 0; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; }}
                .metric-item:last-child {{ border-bottom: none; }}
                .metric-name {{ color: #666; }}
                .metric-value {{ font-weight: bold; color: #2c3e50; }}
                footer {{ margin-top: 30px; padding: 20px; text-align: center; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🔍 LightRAG Monitoring Dashboard</h1>
                    <div class="status">
                        <span class="status-indicator status-healthy"></span>
                        System Status: Operational
                    </div>
                </header>
                
                <div class="grid">
                    <div class="card">
                        <h2>Backups</h2>
                        <div class="card-value">{backup_stats['total'] if backup_stats else 'N/A'}</div>
                        <div class="card-unit">Total Snapshots</div>
                    </div>
                    
                    <div class="card">
                        <h2>Recovery Points</h2>
                        <div class="card-value">{recovery_stats['total'] if recovery_stats else 'N/A'}</div>
                        <div class="card-unit">Checkpoints</div>
                    </div>
                    
                    <div class="card">
                        <h2>Metrics</h2>
                        <div class="card-value">{len(collector.get_metrics_dict()) if collector else 'N/A'}</div>
                        <div class="card-unit">Active Metrics</div>
                    </div>
                </div>
                
                <div class="metrics">
                    <h2>System Information</h2>
                    <div class="metric-item">
                        <span class="metric-name">Last Updated</span>
                        <span class="metric-value">{datetime.utcnow().isoformat()}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-name">Collector Status</span>
                        <span class="metric-value">{'Running' if collector and collector.config.enabled else 'Disabled'}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-name">Collection Interval</span>
                        <span class="metric-value">{collector.config.collection_interval_seconds if collector else 'N/A'}s</span>
                    </div>
                </div>
                
                <footer>
                    <p>LightRAG Phase 5C - Monitoring & Analytics</p>
                    <p><a href="/api/monitoring/metrics/prometheus" style="color: #3498db; text-decoration: none;">View Prometheus Metrics</a></p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return f"<h1>Dashboard Error</h1><p>{str(e)}</p>"


@router.post("/metrics/collect")
async def trigger_collection():
    """Manually trigger metrics collection.
    
    Returns:
        Collection status
    """
    collector = get_metrics_collector()
    if not collector:
        raise HTTPException(status_code=503, detail="Metrics collector not initialized")
    
    try:
        collector.collect()
        return {"status": "success", "message": "Metrics collection triggered"}
    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")
