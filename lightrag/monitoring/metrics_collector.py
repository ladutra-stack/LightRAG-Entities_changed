"""
Metrics Collector for Phase 5C - Monitoring & Analytics

Collects metrics from Backup, Replication, and Recovery managers
and exports them in Prometheus format.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

from lightrag.utils import logger
from lightrag.monitoring.prometheus_metrics import MetricsRegistry, MetricType
from lightrag.api.models_recovery_db import (
    DatabaseManager,
    BackupMetadataDB,
    RecoveryPointDB,
    HealthEventDB,
    ReplicationEventDB,
)


@dataclass
class CollectorConfig:
    """Configuration for metrics collector."""
    
    enabled: bool = True
    collection_interval_seconds: int = 60
    retention_days: int = 7
    export_format: str = "prometheus"  # prometheus, json, csv


class MetricsCollector:
    """Collects and aggregates system metrics."""
    
    def __init__(
        self,
        metrics_registry: MetricsRegistry,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[CollectorConfig] = None,
    ):
        """Initialize metrics collector.
        
        Args:
            metrics_registry: Registry containing metric definitions
            db_manager: Database manager for persistence
            config: Collector configuration
        """
        self.registry = metrics_registry
        self.db_manager = db_manager
        self.config = config or CollectorConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_collection: Dict[str, datetime] = {}
        
        logger.info(f"MetricsCollector initialized with interval={self.config.collection_interval_seconds}s")
    
    def start(self):
        """Start metrics collection in background thread."""
        if self._running:
            logger.warning("Metrics collection already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._collect_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self._thread.start()
        logger.info("Metrics collection started")
    
    def stop(self):
        """Stop metrics collection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Metrics collection stopped")
    
    def _collect_loop(self):
        """Background collection loop."""
        while self._running:
            try:
                self.collect()
            except Exception as e:
                logger.error(f"Error during metrics collection: {e}")
            
            time.sleep(self.config.collection_interval_seconds)
    
    def collect(self):
        """Collect all metrics."""
        try:
            if not self.db_manager:
                logger.debug("No database manager, skipping metric collection")
                return
            
            session = self.db_manager.get_session()
            
            # Collect backup metrics
            self._collect_backup_metrics(session)
            
            # Collect recovery metrics
            self._collect_recovery_metrics(session)
            
            # Collect replication metrics
            self._collect_replication_metrics(session)
            
            # Collect health metrics
            self._collect_health_metrics(session)
            
            session.close()
            logger.debug("Metrics collection completed")
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    def _collect_backup_metrics(self, session):
        """Collect backup-related metrics."""
        try:
            # Count total backups
            backup_count = session.query(BackupMetadataDB).count()
            self._update_metric("lightrag_backup_snapshots_total", backup_count)
            
            # Calculate total size
            total_size = 0
            all_backups = session.query(BackupMetadataDB).all()
            for backup in all_backups:
                total_size += backup.size_bytes or 0
            self._update_metric("lightrag_backup_size_bytes", total_size)
            
            # Count backup errors
            error_count = session.query(BackupMetadataDB).filter_by(status="failed").count()
            self._update_metric("lightrag_backup_errors_total", error_count)
            
            logger.debug(f"Backup metrics collected: count={backup_count}, size={total_size}, errors={error_count}")
        except Exception as e:
            logger.error(f"Failed to collect backup metrics: {e}")
    
    def _collect_recovery_metrics(self, session):
        """Collect recovery-related metrics."""
        try:
            # Count total recovery points
            recovery_count = session.query(RecoveryPointDB).count()
            self._update_metric("lightrag_recovery_points_total", recovery_count)
            
            # Count validations
            validated_count = session.query(RecoveryPointDB).filter_by(validated=True).count()
            self._update_metric("lightrag_recovery_validations_total", validated_count)
            
            # Count validation failures (not validated)
            unvalidated_count = session.query(RecoveryPointDB).filter_by(validated=False).count()
            self._update_metric("lightrag_recovery_validation_failures_total", unvalidated_count)
            
            logger.debug(f"Recovery metrics collected: points={recovery_count}, validated={validated_count}")
        except Exception as e:
            logger.error(f"Failed to collect recovery metrics: {e}")
    
    def _collect_replication_metrics(self, session):
        """Collect replication-related metrics."""
        try:
            # Count total replication operations
            repl_count = session.query(ReplicationEventDB).count()
            self._update_metric("lightrag_replication_operations_total", repl_count)
            
            # Count replication errors
            repl_errors = session.query(ReplicationEventDB).filter_by(status="failed").count()
            self._update_metric("lightrag_replication_errors_total", repl_errors)
            
            # Calculate bytes transferred
            total_bytes = 0
            all_events = session.query(ReplicationEventDB).all()
            for event in all_events:
                total_bytes += event.bytes_transferred or 0
            self._update_metric("lightrag_replication_bytes_transferred_total", total_bytes)
            
            logger.debug(f"Replication metrics collected: ops={repl_count}, errors={repl_errors}, bytes={total_bytes}")
        except Exception as e:
            logger.error(f"Failed to collect replication metrics: {e}")
    
    def _collect_health_metrics(self, session):
        """Collect health-related metrics."""
        try:
            # Get latest health events
            recent_cutoff = datetime.utcnow() - timedelta(days=1)
            recent_events = session.query(HealthEventDB).filter(
                HealthEventDB.created_at >= recent_cutoff
            ).all()
            
            # Count by severity
            critical_count = sum(1 for e in recent_events if e.severity >= 3)
            warning_count = sum(1 for e in recent_events if e.severity == 2)
            
            self._update_metric("lightrag_health_check_failures_total", critical_count + warning_count)
            
            logger.debug(f"Health metrics collected: critical={critical_count}, warning={warning_count}")
        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")
    
    def _update_metric(self, metric_name: str, value: float):
        """Update a metric value."""
        try:
            if hasattr(self.registry, '_metrics') and metric_name in self.registry._metrics:
                metric = self.registry._metrics[metric_name]
                metric.value = value
                metric.timestamp = datetime.utcnow()
        except Exception as e:
            logger.warning(f"Failed to update metric {metric_name}: {e}")
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Prometheus format metrics text
        """
        lines = ["# HELP lightrag_backup_snapshots_total Total number of backup snapshots created"]
        lines.append("# TYPE lightrag_backup_snapshots_total counter")
        
        try:
            for metric_name, metric in self.registry._metrics.items():
                lines.append(f"# HELP {metric_name} {metric.help}")
                lines.append(f"# TYPE {metric_name} {metric.type.value}")
                lines.append(f"{metric_name} {metric.value}")
        except Exception as e:
            logger.error(f"Error exporting Prometheus format: {e}")
        
        return "\n".join(lines)
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get all metrics as dictionary.
        
        Returns:
            Dictionary of metrics with their current values
        """
        metrics_dict = {}
        try:
            for metric_name, metric in self.registry._metrics.items():
                metrics_dict[metric_name] = {
                    "value": metric.value,
                    "type": metric.type.value,
                    "help": metric.help,
                    "timestamp": metric.timestamp.isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting metrics dictionary: {e}")
        
        return metrics_dict
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of key metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        return {
            "collector_enabled": self.config.enabled,
            "collection_interval": self.config.collection_interval_seconds,
            "last_collection": datetime.utcnow().isoformat(),
            "metrics_count": len(self.registry._metrics) if hasattr(self.registry, '_metrics') else 0,
            "status": "running" if self._running else "stopped",
        }


# Global collector instance
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get global metrics collector instance.
    
    Returns:
        MetricsCollector or None if not initialized
    """
    return _collector


def init_metrics_collector(
    metrics_registry: MetricsRegistry,
    db_manager: Optional[DatabaseManager] = None,
    config: Optional[CollectorConfig] = None,
    start: bool = True,
) -> MetricsCollector:
    """Initialize global metrics collector.
    
    Args:
        metrics_registry: Registry with metric definitions
        db_manager: Database manager for persistence
        config: Collector configuration
        start: Whether to start collection immediately
        
    Returns:
        Initialized MetricsCollector
    """
    global _collector
    _collector = MetricsCollector(metrics_registry, db_manager, config)
    
    if start:
        _collector.start()
    
    return _collector
