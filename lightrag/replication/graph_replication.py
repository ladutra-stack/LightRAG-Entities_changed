"""Graph Replication System - Cross-Instance Replication

This module handles replication of graph snapshots to remote instances,
including target management, health checks, and replication coordination.

Components:
- ReplicationTarget: Remote instance configuration
- ReplicationLog: Track replication operations
- GraphReplicator: Replicate single graph to targets
- ReplicationManager: Manage all replications
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

import aiohttp

from lightrag.utils import logger


class ReplicationStatus(str, Enum):
    """Status of a replication operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"


class TargetStatus(str, Enum):
    """Health status of a replication target."""
    HEALTHY = "healthy"
    UNREACHABLE = "unreachable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ReplicationTarget:
    """Configuration for a replication target (remote instance).
    
    Attributes:
        name: Human-readable name
        base_url: Base URL of remote LightRAG instance
        api_key: API key for authentication
        enabled: Whether replication to this target is enabled
        max_concurrent: Max concurrent operations to this target
    """
    
    target_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this target"""
    
    name: str = field(default="")
    """Human-readable name for this target"""
    
    base_url: str = field(default="")
    """Base URL of remote LightRAG instance"""
    
    api_key: str = field(default="")
    """API key for authentication"""
    
    enabled: bool = field(default=True)
    """Whether this target is active"""
    
    max_concurrent: int = field(default=3)
    """Max concurrent operations to this target"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional target metadata"""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    """When this target was registered"""
    
    last_health_check: Optional[datetime] = field(default=None)
    """Timestamp of last health check"""
    
    last_error: Optional[str] = field(default=None)
    """Last error message if any"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.last_health_check:
            data["last_health_check"] = self.last_health_check.isoformat()
        return data


@dataclass
class ReplicationLog:
    """Log entry for a replication operation.
    
    Attributes:
        operation_id: Unique operation identifier
        target_id: Target this replication is for
        backup_id: Backup being replicated
        graph_id: Graph being replicated
        status: Current status
        error_message: Error details if failed
    """
    
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this operation"""
    
    target_id: str = field(default="")
    """ID of target instance"""
    
    backup_id: str = field(default="")
    """ID of backup being replicated"""
    
    graph_id: str = field(default="")
    """ID of graph being replicated"""
    
    status: ReplicationStatus = field(default=ReplicationStatus.PENDING)
    """Current status"""
    
    started_at: datetime = field(default_factory=datetime.utcnow)
    """When operation started"""
    
    completed_at: Optional[datetime] = field(default=None)
    """When operation completed"""
    
    data_hash: str = field(default="")
    """Hash for integrity verification"""
    
    error_message: Optional[str] = field(default=None)
    """Error details if failed"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional operation metadata"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        data["status"] = self.status.value
        return data
    
    def duration_seconds(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class GraphReplicator:
    """Handles replication for a single graph.
    
    Manages replication of graph snapshots to multiple remote targets,
    including target health monitoring for graph.
    """
    
    def __init__(
        self,
        graph_id: str,
        targets: Optional[List[ReplicationTarget]] = None,
    ):
        """Initialize replicator for a graph.
        
        Args:
            graph_id: ID of graph to replicate
            targets: Initial list of targets
        """
        self.graph_id = graph_id
        self._targets: Dict[str, ReplicationTarget] = {}
        self._logs: List[ReplicationLog] = []
        self._lock = threading.Lock()
        
        if targets:
            for target in targets:
                self._targets[target.target_id] = target
        
        logger.info(f"GraphReplicator initialized for graph '{graph_id}'")
    
    def add_target(self, target: ReplicationTarget) -> bool:
        """Add a replication target.
        
        Args:
            target: Target to add
            
        Returns:
            True if added, False if already exists
        """
        with self._lock:
            if target.target_id in self._targets:
                return False
            self._targets[target.target_id] = target
            logger.info(f"Added replication target {target.name} for graph {self.graph_id}")
            return True
    
    def remove_target(self, target_id: str) -> bool:
        """Remove a replication target.
        
        Args:
            target_id: ID of target to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if target_id not in self._targets:
                return False
            del self._targets[target_id]
            logger.info(f"Removed replication target {target_id} from graph {self.graph_id}")
            return True
    
    def get_target(self, target_id: str) -> Optional[ReplicationTarget]:
        """Get target by ID.
        
        Args:
            target_id: ID of target
            
        Returns:
            ReplicationTarget or None
        """
        return self._targets.get(target_id)
    
    def list_targets(self, enabled_only: bool = True) -> List[ReplicationTarget]:
        """List all targets for this graph.
        
        Args:
            enabled_only: Only return enabled targets
            
        Returns:
            List of targets
        """
        with self._lock:
            targets = list(self._targets.values())
        
        if enabled_only:
            targets = [t for t in targets if t.enabled]
        
        return targets
    
    async def replicate_snapshot(
        self,
        backup_id: str,
        snapshot_file: bytes,
        data_hash: str,
    ) -> Dict[str, bool]:
        """Replicate a snapshot to all enabled targets.
        
        Args:
            backup_id: ID of backup snapshot
            snapshot_file: Binary data of snapshot
            data_hash: Hash of snapshot for verification
            
        Returns:
            Dictionary mapping target_id to success/failure
        """
        targets = self.list_targets(enabled_only=True)
        
        # Replicate concurrently to all targets
        tasks = [
            self._replicate_to_target(target, backup_id, snapshot_file, data_hash)
            for target in targets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert results to dict
        target_results = {}
        for target, result in zip(targets, results):
            if isinstance(result, Exception):
                logger.error(f"Replication to {target.name} failed: {result}")
                target_results[target.target_id] = False
            else:
                target_results[target.target_id] = result
        
        return target_results
    
    async def check_target_health(self, target_id: str) -> TargetStatus:
        """Check health of a replication target.
        
        Args:
            target_id: ID of target to check
            
        Returns:
            TargetStatus enum value
        """
        target = self.get_target(target_id)
        if target is None:
            return TargetStatus.UNKNOWN
        
        if not target.enabled:
            return TargetStatus.UNKNOWN
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try to connect to target health endpoint
                health_url = f"{target.base_url}/health"
                async with session.get(
                    health_url,
                    headers={"Authorization": f"Bearer {target.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    target.last_health_check = datetime.utcnow()
                    
                    if resp.status == 200:
                        target.last_error = None
                        logger.info(f"Health check passed for target {target.name}")
                        return TargetStatus.HEALTHY
                    else:
                        target.last_error = f"Health check returned {resp.status}"
                        logger.warning(f"Health check failed for target {target.name}: {resp.status}")
                        return TargetStatus.DEGRADED
        
        except asyncio.TimeoutError:
            target.last_error = "Health check timeout"
            logger.warning(f"Health check timeout for target {target.name}")
            return TargetStatus.DEGRADED
        except Exception as e:
            target.last_error = str(e)
            logger.error(f"Health check failed for target {target.name}: {e}")
            return TargetStatus.UNREACHABLE
    
    async def check_all_targets_health(self) -> Dict[str, TargetStatus]:
        """Check health of all targets.
        
        Returns:
            Dictionary mapping target_id to status
        """
        targets = list(self._targets.values())
        tasks = [self.check_target_health(t.target_id) for t in targets]
        
        statuses = await asyncio.gather(*tasks)
        
        return {
            target.target_id: status
            for target, status in zip(targets, statuses)
        }
    
    def get_replication_logs(self, limit: int = 100) -> List[ReplicationLog]:
        """Get recent replication logs.
        
        Args:
            limit: Max number of logs to return
            
        Returns:
            List of most recent logs
        """
        with self._lock:
            logs = sorted(
                self._logs,
                key=lambda l: l.started_at,
                reverse=True,
            )[:limit]
        return logs
    
    def get_replication_status(self) -> dict:
        """Get replication status for this graph.
        
        Returns:
            Status dictionary
        """
        total_targets = len(self._targets)
        enabled_targets = sum(1 for t in self._targets.values() if t.enabled)
        
        logs = self.get_replication_logs(limit=10)
        successful_ops = sum(1 for l in logs if l.status == ReplicationStatus.COMPLETED)
        failed_ops = sum(1 for l in logs if l.status == ReplicationStatus.FAILED)
        
        return {
            "graph_id": self.graph_id,
            "total_targets": total_targets,
            "enabled_targets": enabled_targets,
            "recent_operations": len(logs),
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "last_replication": logs[0].started_at if logs else None,
        }
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    async def _replicate_to_target(
        self,
        target: ReplicationTarget,
        backup_id: str,
        snapshot_file: bytes,
        data_hash: str,
    ) -> bool:
        """Replicate snapshot to a single target.
        
        Args:
            target: Target to replicate to
            backup_id: Backup ID
            snapshot_file: Snapshot data
            data_hash: Data hash
            
        Returns:
            True if successful
        """
        log = ReplicationLog(
            target_id=target.target_id,
            backup_id=backup_id,
            graph_id=self.graph_id,
            status=ReplicationStatus.IN_PROGRESS,
            data_hash=data_hash,
        )
        
        try:
            logger.info(f"Starting replication to target {target.name}")
            
            # Check target health first
            health = await self.check_target_health(target.target_id)
            if health == TargetStatus.UNREACHABLE:
                raise ConnectionError(f"Target {target.name} is unreachable")
            
            # Send snapshot to target
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {target.api_key}"}
                
                # Upload endpoint
                upload_url = f"{target.base_url}/backup/snapshots/upload"
                
                data = aiohttp.FormData()
                data.add_field("graph_id", self.graph_id)
                data.add_field("backup_id", backup_id)
                data.add_field("data_hash", data_hash)
                data.add_field("snapshot", snapshot_file, filename="snapshot.tar.gz")
                
                async with session.post(
                    upload_url,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300),  # 5 minutes
                ) as resp:
                    if resp.status != 200:
                        raise IOError(f"Upload failed with status {resp.status}")
                    
                    result = await resp.json()
                    if not result.get("success"):
                        raise IOError(f"Upload returned error: {result.get('error')}")
            
            log.status = ReplicationStatus.VALIDATED
            log.completed_at = datetime.utcnow()
            
            logger.info(
                f"Replication to target {target.name} completed successfully "
                f"in {log.duration_seconds():.2f}s"
            )
            
            return True
        
        except Exception as e:
            log.status = ReplicationStatus.FAILED
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            
            logger.error(f"Replication to target {target.name} failed: {e}")
            
            return False
        
        finally:
            with self._lock:
                self._logs.append(log)


class ReplicationManager:
    """Manages replication across all graphs.
    
    Coordinates replication of graph snapshots to multiple remote instances.
    """
    
    def __init__(self):
        """Initialize replication manager."""
        self._graph_replicators: Dict[str, GraphReplicator] = {}
        self._targets: Dict[str, ReplicationTarget] = {}
        self._lock = threading.Lock()
        
        logger.info("ReplicationManager initialized")
    
    def register_target(self, target: ReplicationTarget) -> bool:
        """Register a replication target globally.
        
        Args:
            target: Target to register
            
        Returns:
            True if registered, False if already exists
        """
        with self._lock:
            if target.target_id in self._targets:
                return False
            
            self._targets[target.target_id] = target
            
            # Add to all existing graphs
            for replicator in self._graph_replicators.values():
                replicator.add_target(target)
        
        logger.info(f"Registered replication target: {target.name}")
        return True
    
    def get_graph_replicator(self, graph_id: str) -> GraphReplicator:
        """Get replicator for a graph (create if not exists).
        
        Args:
            graph_id: ID of graph
            
        Returns:
            GraphReplicator instance
        """
        with self._lock:
            if graph_id not in self._graph_replicators:
                replicator = GraphReplicator(
                    graph_id=graph_id,
                    targets=list(self._targets.values()),
                )
                self._graph_replicators[graph_id] = replicator
            
            return self._graph_replicators[graph_id]
    
    def list_targets(self) -> List[ReplicationTarget]:
        """List all registered targets.
        
        Returns:
            List of targets
        """
        return list(self._targets.values())
    
    async def check_all_health(self) -> Dict[str, Dict[str, str]]:
        """Check health of all targets.
        
        Returns:
            Dictionary mapping target_id to health status
        """
        health_results = {}
        
        for replicator in self._graph_replicators.values():
            graph_health = await replicator.check_all_targets_health()
            for target_id, status in graph_health.items():
                if target_id not in health_results:
                    health_results[target_id] = {}
                health_results[target_id][replicator.graph_id] = status.value
        
        return health_results
    
    def get_replication_metrics(self) -> dict:
        """Get aggregate replication metrics.
        
        Returns:
            Metrics dictionary
        """
        total_targets = len(self._targets)
        total_graphs = len(self._graph_replicators)
        
        all_logs = []
        for replicator in self._graph_replicators.values():
            all_logs.extend(replicator.get_replication_logs(limit=1000))
        
        return {
            "total_targets": total_targets,
            "total_graphs": total_graphs,
            "total_operations": len(all_logs),
            "successful_operations": sum(
                1 for l in all_logs
                if l.status == ReplicationStatus.COMPLETED
            ),
            "failed_operations": sum(
                1 for l in all_logs
                if l.status == ReplicationStatus.FAILED
            ),
        }


if __name__ == "__main__":
    # Example usage
    async def demo():
        mgr = ReplicationManager()
        
        # Register targets
        target1 = ReplicationTarget(
            name="Secondary",
            base_url="http://localhost:8001",
            api_key="test-key-1",
        )
        mgr.register_target(target1)
        
        # Get replicator
        replicator = mgr.get_graph_replicator("demo_graph")
        
        # Check health
        health = await replicator.check_all_targets_health()
        print(f"Health check results: {json.dumps({k: v.value for k, v in health.items()}, indent=2)}")
        
        # Get status
        status = replicator.get_replication_status()
        print(f"Replication status: {json.dumps(status, indent=2, default=str)}")
    
    asyncio.run(demo())
