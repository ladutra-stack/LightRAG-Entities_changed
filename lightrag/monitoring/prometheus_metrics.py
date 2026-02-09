"""
Prometheus Metrics for Backup, Replication, and Recovery Systems

Provides comprehensive metrics collection for Phase 5C monitoring.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
import threading
from lightrag.utils import logger


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Base metric class."""
    
    name: str
    type: MetricType
    help: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    

class MetricsRegistry:
    """Registry for all system metrics."""
    
    def __init__(self):
        """Initialize metrics registry."""
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._init_metrics()
        logger.info("MetricsRegistry initialized")
    
    def _init_metrics(self):
        """Initialize all standard metrics."""
        # Backup metrics
        self.register_metric(
            "lightrag_backup_snapshots_total",
            MetricType.COUNTER,
            "Total number of backup snapshots created"
        )
        self.register_metric(
            "lightrag_backup_size_bytes",
            MetricType.GAUGE,
            "Current total backup storage size in bytes"
        )
        self.register_metric(
            "lightrag_backup_restore_duration_seconds",
            MetricType.HISTOGRAM,
            "Backup restore operation duration in seconds"
        )
        self.register_metric(
            "lightrag_backup_errors_total",
            MetricType.COUNTER,
            "Total number of backup errors"
        )
        
        # Replication metrics
        self.register_metric(
            "lightrag_replication_operations_total",
            MetricType.COUNTER,
            "Total number of replication operations"
        )
        self.register_metric(
            "lightrag_replication_lag_seconds",
            MetricType.GAUGE,
            "Replication lag in seconds"
        )
        self.register_metric(
            "lightrag_replication_errors_total",
            MetricType.COUNTER,
            "Total number of replication errors"
        )
        self.register_metric(
            "lightrag_replication_bytes_transferred_total",
            MetricType.COUNTER,
            "Total bytes transferred during replication"
        )
        
        # Recovery metrics
        self.register_metric(
            "lightrag_recovery_points_total",
            MetricType.GAUGE,
            "Total number of recovery checkpoints"
        )
        self.register_metric(
            "lightrag_recovery_validations_total",
            MetricType.COUNTER,
            "Total number of recovery validations"
        )
        self.register_metric(
            "lightrag_recovery_validation_failures_total",
            MetricType.COUNTER,
            "Total number of failed recovery validations"
        )
        self.register_metric(
            "lightrag_recovery_failovers_total",
            MetricType.COUNTER,
            "Total number of failover operations"
        )
        
        # Health metrics
        self.register_metric(
            "lightrag_health_check_duration_seconds",
            MetricType.HISTOGRAM,
            "Health check operation duration"
        )
        self.register_metric(
            "lightrag_health_check_failures_total",
            MetricType.COUNTER,
            "Total number of health check failures"
        )
        self.register_metric(
            "lightrag_component_health_status",
            MetricType.GAUGE,
            "Component health status (1=healthy, 0.5=degraded, 0=critical)"
        )
        
        # Graph metrics
        self.register_metric(
            "lightrag_graphs_total",
            MetricType.GAUGE,
            "Total number of graphs"
        )
        self.register_metric(
            "lightrag_graph_entities_total",
            MetricType.GAUGE,
            "Total number of entities per graph"
        )
        self.register_metric(
            "lightrag_graph_relations_total",
            MetricType.GAUGE,
            "Total number of relations per graph"
        )
        
        logger.info(f"Initialized {len(self._metrics)} standard metrics")
    
    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        help_text: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Register a new metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric
            help_text: Help text for metric
            labels: Optional labels
            
        Returns:
            Registered Metric
        """
        with self._lock:
            if name in self._metrics:
                logger.warning(f"Metric already registered: {name}")
                return self._metrics[name]
            
            metric = Metric(
                name=name,
                type=metric_type,
                help=help_text,
                labels=labels or {},
            )
            self._metrics[name] = metric
            logger.debug(f"Registered metric: {name} ({metric_type.value})")
            return metric
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric.
        
        Args:
            name: Metric name
            value: Amount to increment
            labels: Optional labels
        """
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if metric.type == MetricType.COUNTER:
                    metric.value += value
                    metric.timestamp = datetime.utcnow()
                    if labels:
                        metric.labels.update(labels)
                else:
                    logger.warning(f"Metric {name} is not a counter")
            else:
                logger.warning(f"Metric not found: {name}")
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric.
        
        Args:
            name: Metric name
            value: Value to set
            labels: Optional labels
        """
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if metric.type == MetricType.GAUGE:
                    metric.value = value
                    metric.timestamp = datetime.utcnow()
                    if labels:
                        metric.labels.update(labels)
                else:
                    logger.warning(f"Metric {name} is not a gauge")
            else:
                logger.warning(f"Metric not found: {name}")
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Metric or None if not found
        """
        with self._lock:
            return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all registered metrics.
        
        Returns:
            Dictionary of all metrics
        """
        with self._lock:
            return dict(self._metrics)
    
    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Prometheus format string
        """
        lines = []
        
        with self._lock:
            for metric_name, metric in sorted(self._metrics.items()):
                # Add help line
                lines.append(f"# HELP {metric_name} {metric.help}")
                
                # Add type line
                lines.append(f"# TYPE {metric_name} {metric.type.value}")
                
                # Add metric value
                labels_str = ""
                if metric.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"
                
                timestamp_ms = int(metric.timestamp.timestamp() * 1000)
                lines.append(f"{metric_name}{labels_str} {metric.value} {timestamp_ms}")
                lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, dict]:
        """Export metrics as dictionary.
        
        Returns:
            Dictionary representation of all metrics
        """
        with self._lock:
            return {
                name: {
                    "type": metric.type.value,
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "labels": metric.labels,
                    "help": metric.help,
                }
                for name, metric in self._metrics.items()
            }


# Global metrics registry
_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry instance.
    
    Returns:
        MetricsRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def init_metrics_registry() -> MetricsRegistry:
    """Initialize global metrics registry.
    
    Returns:
        Initialized MetricsRegistry
    """
    global _registry
    _registry = MetricsRegistry()
    return _registry
