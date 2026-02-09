"""Graph Backup System - Core Backup Management

This module provides automated backup, snapshot management, and restoration
capabilities for individual graphs in the multi-graph system.

Components:
- BackupSnapshot: Represents a single backup snapshot
- GraphBackup: Manages backups for a single graph
- BackupManager: Manages backups across all graphs
"""

from __future__ import annotations

import asyncio
import json
import shutil
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from lightrag.utils import logger


class BackupStatus(str, Enum):
    """Status of a backup snapshot."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"
    RESTORED = "restored"


@dataclass
class BackupSnapshot:
    """Represents a single backup snapshot of a graph."""
    
    backup_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this backup"""
    
    graph_id: str = field(default="")
    """ID of the graph being backed up"""
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    """When this snapshot was created"""
    
    checkpoint_path: Path = field(default_factory=Path)
    """Path where snapshot data is stored"""
    
    status: BackupStatus = field(default=BackupStatus.PENDING)
    """Current status of the backup"""
    
    size_bytes: int = field(default=0)
    """Size of backup data in bytes"""
    
    data_hash: str = field(default="")
    """Hash of backup data for integrity verification"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional backup metadata"""
    
    error_message: Optional[str] = field(default=None)
    """Error details if backup failed"""
    
    retention_until: Optional[datetime] = field(default=None)
    """When this backup should be deleted (TTL)"""
    
    def to_dict(self) -> dict:
        """Convert snapshot to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.retention_until:
            data["retention_until"] = self.retention_until.isoformat()
        data["checkpoint_path"] = str(self.checkpoint_path)
        data["status"] = self.status.value
        return data
    
    def is_expired(self) -> bool:
        """Check if backup has passed retention date."""
        if self.retention_until is None:
            return False
        return datetime.utcnow() > self.retention_until
    
    def is_valid(self) -> bool:
        """Check if snapshot is valid and usable."""
        return (
            self.status == BackupStatus.COMPLETED
            and self.checkpoint_path.exists()
            and not self.is_expired()
        )


class GraphBackup:
    """Manages backups for a single graph.
    
    Responsibilities:
    - Create snapshots
    - Manage snapshot storage
    - Restore from snapshots
    - Cleanup old backups
    """
    
    def __init__(
        self,
        graph_id: str,
        storage_path: Path,
        retention_days: int = 30,
    ):
        """Initialize backup manager for a graph.
        
        Args:
            graph_id: ID of graph to manage backups for
            storage_path: Base path for storing backups
            retention_days: How long to keep backups (days)
        """
        self.graph_id = graph_id
        self.storage_path = Path(storage_path) / self.graph_id
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        
        self._snapshots: Dict[str, BackupSnapshot] = {}
        self._lock = threading.Lock()
        
        logger.info(f"GraphBackup initialized for graph '{graph_id}'")
    
    async def create_snapshot(
        self,
        source_working_dir: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackupSnapshot:
        """Create a backup snapshot of the graph.
        
        Args:
            source_working_dir: Path to graph working directory
            metadata: Additional metadata to store
            
        Returns:
            BackupSnapshot object
            
        Raises:
            FileNotFoundError: If source working directory not found
            IOError: If backup creation fails
        """
        if not source_working_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_working_dir}")
        
        snapshot = BackupSnapshot(
            graph_id=self.graph_id,
            metadata=metadata or {},
            status=BackupStatus.IN_PROGRESS,
        )
        
        try:
            # Create checkpoint directory
            snapshot.checkpoint_path = self.storage_path / snapshot.backup_id
            snapshot.checkpoint_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating snapshot {snapshot.backup_id} for graph {self.graph_id}")
            
            # Copy working directory
            await self._copy_working_dir(source_working_dir, snapshot.checkpoint_path)
            
            # Calculate size and hash
            snapshot.size_bytes = await self._calculate_dir_size(snapshot.checkpoint_path)
            snapshot.data_hash = await self._calculate_dir_hash(snapshot.checkpoint_path)
            
            # Set retention
            snapshot.retention_until = (
                datetime.utcnow() + timedelta(days=self.retention_days)
            )
            
            # Mark as completed
            snapshot.status = BackupStatus.COMPLETED
            
            # Store in cache
            with self._lock:
                self._snapshots[snapshot.backup_id] = snapshot
            
            logger.info(
                f"Snapshot {snapshot.backup_id} created successfully "
                f"({snapshot.size_bytes} bytes)"
            )
            
            return snapshot
            
        except Exception as e:
            snapshot.status = BackupStatus.FAILED
            snapshot.error_message = str(e)
            logger.error(f"Failed to create snapshot: {e}")
            raise
    
    async def restore_snapshot(self, snapshot_id: str, target_dir: Path) -> bool:
        """Restore graph from a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            target_dir: Where to restore the graph
            
        Returns:
            True if restore succeeded, False otherwise
            
        Raises:
            ValueError: If snapshot not found or invalid
            IOError: If restore operation fails
        """
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot not found: {snapshot_id}")
        
        if not snapshot.is_valid():
            raise ValueError(f"Snapshot is not valid: {snapshot_id}")
        
        try:
            logger.info(f"Restoring snapshot {snapshot_id} to {target_dir}")
            
            # Backup current state before restore
            if target_dir.exists():
                backup_dir = target_dir.parent / f"{target_dir.name}_pre_restore"
                shutil.move(str(target_dir), str(backup_dir))
                logger.info(f"Pre-restore backup saved to {backup_dir}")
            
            # Copy from snapshot
            await self._copy_working_dir(snapshot.checkpoint_path, target_dir)
            
            # Verify integrity
            restored_hash = await self._calculate_dir_hash(target_dir)
            if restored_hash != snapshot.data_hash:
                raise IOError("Snapshot integrity check failed after restore")
            
            # Update snapshot status
            snapshot.status = BackupStatus.RESTORED
            
            logger.info(f"Snapshot {snapshot_id} restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            raise
    
    def get_snapshot(self, snapshot_id: str) -> Optional[BackupSnapshot]:
        """Get snapshot by ID.
        
        Args:
            snapshot_id: ID of snapshot to retrieve
            
        Returns:
            BackupSnapshot or None if not found
        """
        return self._snapshots.get(snapshot_id)
    
    def list_snapshots(self) -> List[BackupSnapshot]:
        """List all snapshots for this graph.
        
        Returns:
            List of BackupSnapshot objects, sorted by timestamp (newest first)
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to delete
            
        Returns:
            True if deleted, False if not found
        """
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            return False
        
        try:
            if snapshot.checkpoint_path.exists():
                shutil.rmtree(snapshot.checkpoint_path)
                logger.info(f"Deleted snapshot {snapshot_id}")
            
            with self._lock:
                del self._snapshots[snapshot_id]
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False
    
    async def cleanup_old_snapshots(self) -> int:
        """Delete expired snapshots based on retention policy.
        
        Returns:
            Number of snapshots deleted
        """
        deleted_count = 0
        with self._lock:
            expired_ids = [
                sid for sid, snap in self._snapshots.items()
                if snap.is_expired()
            ]
        
        for snapshot_id in expired_ids:
            if await self.delete_snapshot(snapshot_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired snapshots for graph {self.graph_id}")
        
        return deleted_count
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for this graph.
        
        Returns:
            Dictionary with storage stats
        """
        snapshots = self.list_snapshots()
        total_size = sum(s.size_bytes for s in snapshots)
        
        return {
            "graph_id": self.graph_id,
            "total_snapshots": len(snapshots),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "oldest_snapshot": snapshots[-1].timestamp if snapshots else None,
            "newest_snapshot": snapshots[0].timestamp if snapshots else None,
            "expired_snapshots": sum(1 for s in snapshots if s.is_expired()),
        }
    
    # =========================================================================
    # Private Utility Methods
    # =========================================================================
    
    async def _copy_working_dir(self, source: Path, destination: Path) -> None:
        """Copy working directory recursively.
        
        Args:
            source: Source directory
            destination: Destination directory
        """
        # Create destination parent if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove destination if exists
        if destination.exists():
            shutil.rmtree(destination)
        
        # Copy directory
        await asyncio.to_thread(shutil.copytree, source, destination)
    
    async def _calculate_dir_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes.
        
        Args:
            directory: Directory to measure
            
        Returns:
            Total size in bytes
        """
        total = 0
        for entry in directory.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
        return total
    
    async def _calculate_dir_hash(self, directory: Path) -> str:
        """Calculate hash of directory contents for integrity checking.
        
        Args:
            directory: Directory to hash
            
        Returns:
            Hash string
        """
        import hashlib
        
        hasher = hashlib.sha256()
        
        # Process files in sorted order for consistency
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                hasher.update(file_path.relative_to(directory).as_posix().encode())
                with open(file_path, "rb") as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()


class BackupManager:
    """Manages backups across all graphs.
    
    Responsibilities:
    - Create and manage per-graph backup instances
    - Schedule automatic backups
    - Manage retention policies
    - Provide unified backup interface
    """
    
    def __init__(
        self,
        storage_path: Path,
        retention_days: int = 30,
        auto_cleanup_interval_hours: int = 24,
    ):
        """Initialize backup manager.
        
        Args:
            storage_path: Base path for all backups
            retention_days: Default retention period
            auto_cleanup_interval_hours: How often to cleanup old backups
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.auto_cleanup_interval = timedelta(hours=auto_cleanup_interval_hours)
        
        self._graph_backups: Dict[str, GraphBackup] = {}
        self._lock = threading.Lock()
        self._last_cleanup = datetime.utcnow()
        
        logger.info(f"BackupManager initialized with storage path: {storage_path}")
    
    def register_graph(self, graph_id: str) -> GraphBackup:
        """Register a graph for backup management.
        
        Args:
            graph_id: ID of graph to register
            
        Returns:
            GraphBackup instance for this graph
        """
        with self._lock:
            if graph_id in self._graph_backups:
                return self._graph_backups[graph_id]
            
            backup = GraphBackup(
                graph_id=graph_id,
                storage_path=self.storage_path,
                retention_days=self.retention_days,
            )
            self._graph_backups[graph_id] = backup
            return backup
    
    def get_graph_backup(self, graph_id: str) -> Optional[GraphBackup]:
        """Get backup manager for a specific graph.
        
        Args:
            graph_id: ID of graph
            
        Returns:
            GraphBackup instance or None if not registered
        """
        return self._graph_backups.get(graph_id)
    
    def list_graphs(self) -> List[str]:
        """List all registered graphs.
        
        Returns:
            List of graph IDs
        """
        return list(self._graph_backups.keys())
    
    async def get_all_snapshots(self) -> Dict[str, List[BackupSnapshot]]:
        """Get all snapshots across all graphs.
        
        Returns:
            Dictionary mapping graph_id to list of snapshots
        """
        result = {}
        for graph_id, backup in self._graph_backups.items():
            result[graph_id] = backup.list_snapshots()
        return result
    
    async def cleanup_old_backups(self) -> Dict[str, int]:
        """Cleanup expired backups across all graphs.
        
        Returns:
            Dictionary mapping graph_id to number of deleted snapshots
        """
        # Check if cleanup is needed
        now = datetime.utcnow()
        if now - self._last_cleanup < self.auto_cleanup_interval:
            return {}
        
        self._last_cleanup = now
        result = {}
        
        for graph_id, backup in self._graph_backups.items():
            deleted_count = await backup.cleanup_old_snapshots()
            if deleted_count > 0:
                result[graph_id] = deleted_count
        
        return result
    
    def get_total_stats(self) -> dict:
        """Get aggregate backup statistics.
        
        Returns:
            Dictionary with total statistics
        """
        total_size = 0
        total_snapshots = 0
        graph_stats = {}
        
        for graph_id, backup in self._graph_backups.items():
            stats = backup.get_storage_stats()
            graph_stats[graph_id] = stats
            total_size += stats["total_size_bytes"]
            total_snapshots += stats["total_snapshots"]
        
        return {
            "total_graphs": len(self._graph_backups),
            "total_snapshots": total_snapshots,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "retention_days": self.retention_days,
            "per_graph_stats": graph_stats,
        }


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def demo():
        # Create backup manager
        backup_mgr = BackupManager(
            storage_path=Path("/tmp/lightrag_backups"),
            retention_days=30,
        )
        
        # Register a graph
        graph_backup = backup_mgr.register_graph("demo_graph")
        
        # Create a test directory
        test_dir = Path("/tmp/demo_graph_working")
        test_dir.mkdir(exist_ok=True)
        (test_dir / "test_file.txt").write_text("test content")
        
        # Create snapshot
        snapshot = await graph_backup.create_snapshot(test_dir)
        print(f"Created snapshot: {snapshot.backup_id}")
        print(f"Snapshot size: {snapshot.size_bytes} bytes")
        
        # List snapshots
        snapshots = graph_backup.list_snapshots()
        print(f"Total snapshots: {len(snapshots)}")
        
        # Get stats
        stats = backup_mgr.get_total_stats()
        print(f"Backup stats: {json.dumps(stats, indent=2, default=str)}")
    
    asyncio.run(demo())
