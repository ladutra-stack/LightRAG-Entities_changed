#!/usr/bin/env python3
"""
Phase 5A Integration Example - Backup, Replication & Disaster Recovery

This example demonstrates how to use the complete Phase 5A system including:
- Automated backup snapshots with retention policies
- Cross-instance replication with target health monitoring
- Disaster recovery checkpoints and failover capabilities
"""

import asyncio
from pathlib import Path
import tempfile

from lightrag.backup import BackupManager
from lightrag.replication import ReplicationManager, ReplicationTarget
from lightrag.recovery import DisasterRecoveryManager


async def main():
    """Run Phase 5A integration example."""
    
    print("=" * 80)
    print("Phase 5A - Backup, Replication & Disaster Recovery System")
    print("=" * 80)
    
    # ========================================================================
    # Setup: Create temporary working directories
    # ========================================================================
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create sample working directories for multiple graphs
        graph_a_dir = tmpdir / "graphs" / "graph_a"
        graph_a_dir.mkdir(parents=True)
        (graph_a_dir / "entities.json").write_text('{"entities": ["A", "B"]}')
        (graph_a_dir / "relations.json").write_text('{"relations": []}')
        
        graph_b_dir = tmpdir / "graphs" / "graph_b"
        graph_b_dir.mkdir(parents=True)
        (graph_b_dir / "entities.json").write_text('{"entities": ["C", "D"]}')
        (graph_b_dir / "relations.json").write_text('{"relations": []}')
        
        backup_storage = tmpdir / "backups"
        
        print("\n1. BACKUP SUBSYSTEM")
        print("-" * 80)
        
        # Initialize backup manager
        backup_mgr = BackupManager(
            storage_path=backup_storage,
            retention_days=30,
        )
        
        # Register graphs and create snapshots
        print("\n  Creating backups for multiple graphs...")
        for graph_id, graph_dir in [("graph_a", graph_a_dir), ("graph_b", graph_b_dir)]:
            graph_backup = backup_mgr.register_graph(graph_id)
            snapshot = await graph_backup.create_snapshot(
                graph_dir,
                metadata={"version": "1.0", "timestamp": "2024-01-01"},
            )
            print(f"    ✓ {graph_id}: {snapshot.backup_id} ({snapshot.size_bytes} bytes)")
        
        # List snapshots
        print("\n  Snapshot inventory:")
        stats = backup_mgr.get_total_stats()
        print(f"    Total graphs: {stats['total_graphs']}")
        print(f"    Total snapshots: {stats['total_snapshots']}")
        print(f"    Total size: {stats['total_size_bytes']} bytes")
        
        print("\n2. REPLICATION SUBSYSTEM")
        print("-" * 80)
        
        # Initialize replication manager
        replication_mgr = ReplicationManager()
        
        # Register replication targets
        targets = [
            ReplicationTarget(
                name="Replica DC2",
                base_url="http://replica-dc2.example.com:8000",
                api_key="key-replica-dc2",
            ),
            ReplicationTarget(
                name="Replica DC3",
                base_url="http://replica-dc3.example.com:8000",
                api_key="key-replica-dc3",
            ),
        ]
        
        print("\n  Registering replication targets...")
        for target in targets:
            replication_mgr.register_target(target)
            print(f"    ✓ {target.name} ({target.base_url})")
        
        # Setup replication for graphs
        print("\n  Configuring graph replication...")
        for graph_id in ["graph_a", "graph_b"]:
            replicator = replication_mgr.get_graph_replicator(graph_id)
            for target in targets:
                replicator.add_target(target)
            
            status = replicator.get_replication_status()
            print(
                f"    ✓ {graph_id}: "
                f"{status['enabled_targets']}/{status['total_targets']} targets enabled"
            )
        
        # Check target health
        print("\n  Target health check...")
        for target in targets:
            replicator = replication_mgr.get_graph_replicator("graph_a")
            replicator.add_target(target)
            health = await replicator.check_target_health(target.target_id)
            print(f"    ℹ {target.name}: {health.value}")
        
        print("\n3. DISASTER RECOVERY SUBSYSTEM")
        print("-" * 80)
        
        # Initialize recovery manager
        recovery_mgr = DisasterRecoveryManager()
        
        # Create recovery checkpoints
        print("\n  Creating recovery checkpoints...")
        
        # Checkpoint 1: Pre-maintenance
        checkpoint_a = await recovery_mgr.create_recovery_point(
            graph_ids=["graph_a", "graph_b"],
            description="Pre-maintenance checkpoint",
        )
        print(f"    ✓ Pre-maintenance: {checkpoint_a.checkpoint_id}")
        
        # Checkpoint 2: After specific update
        checkpoint_b = await recovery_mgr.create_recovery_point(
            graph_ids=["graph_a"],
            description="After entity deduplication on graph_a",
        )
        print(f"    ✓ Post-dedup: {checkpoint_b.checkpoint_id}")
        
        # List recovery points
        print("\n  Recovery point inventory:")
        points = recovery_mgr.list_recovery_points()
        print(f"    Total checkpoints: {len(points)}")
        for point in points:
            graphs_str = ", ".join(point.graphs)
            print(f"      • {point.checkpoint_id} ({graphs_str})")
        
        # Validate recovery points
        print("\n  Validating recovery points...")
        for point in points:
            is_valid = await recovery_mgr.validate_recovery_point(point.checkpoint_id)
            status = "✓ VALID" if is_valid else "✗ INVALID"
            print(f"    {status}: {point.checkpoint_id}")
        
        # Get recovery status
        print("\n  Recovery system status:")
        status = recovery_mgr.get_recovery_status()
        print(f"    Total checkpoints: {status.get('total_checkpoints', 0)}")
        print(f"    Failover in progress: {status.get('failover_in_progress', False)}")
        
        # Perform comprehensive health check
        print("\n4. COMPREHENSIVE HEALTH CHECK")
        print("-" * 80)
        
        health = await recovery_mgr.health_check()
        print(f"\n  Overall status: {health['overall_status']}")
        print(f"  Timestamp: {health.get('timestamp', 'N/A')}")
        
        if "graphs" in health:
            print(f"\n  Graph health:")
            for gid, gstatus in health["graphs"].items():
                print(f"    • {gid}: {gstatus.get('status', 'unknown')}")
        
        if "backups" in health:
            print(f"\n  Backup health:")
            for key, val in health["backups"].items():
                print(f"    • {key}: {val}")
        
        if "replication" in health:
            print(f"\n  Replication health:")
            for key, val in health["replication"].items():
                print(f"    • {key}: {val}")
        
        print("\n5. WORKFLOW EXAMPLE - DISASTER RECOVERY SCENARIO")
        print("-" * 80)
        
        print("\n  Scenario: System degradation, initiating controlled failover...")
        
        # Initiate failover to pre-maintenance checkpoint
        print(f"    Failing over to checkpoint: {checkpoint_a.checkpoint_id}")
        success = await recovery_mgr.initiate_failover(checkpoint_a.checkpoint_id)
        
        if success:
            print(f"    ✓ Failover completed successfully")
        else:
            print(f"    ✗ Failover failed")
        
        print("\n6. API INTEGRATION")
        print("-" * 80)
        
        print("""
  The Phase 5A system provides REST API endpoints for integration:
  
  Backup Endpoints:
    POST   /api/v1/backup-replication/backup/graphs/{graph_id}/snapshots
    GET    /api/v1/backup-replication/backup/graphs/{graph_id}/snapshots
    POST   /api/v1/backup-replication/backup/graphs/{graph_id}/snapshots/{id}/restore
    DELETE /api/v1/backup-replication/backup/graphs/{graph_id}/snapshots/{id}
    POST   /api/v1/backup-replication/backup/cleanup
    GET    /api/v1/backup-replication/backup/stats
  
  Replication Endpoints:
    POST   /api/v1/backup-replication/replication/targets
    GET    /api/v1/backup-replication/replication/targets
    GET    /api/v1/backup-replication/replication/targets/{id}/health
    DELETE /api/v1/backup-replication/replication/targets/{id}
    GET    /api/v1/backup-replication/replication/graphs/{graph_id}/status
  
  Recovery Endpoints:
    POST   /api/v1/backup-replication/recovery/checkpoints
    GET    /api/v1/backup-replication/recovery/checkpoints
    GET    /api/v1/backup-replication/recovery/checkpoints/{id}
    POST   /api/v1/backup-replication/recovery/checkpoints/{id}/validate
    POST   /api/v1/backup-replication/recovery/checkpoints/{id}/failover
    GET    /api/v1/backup-replication/recovery/health
    GET    /api/v1/backup-replication/recovery/status
  
  See backup_replication_routes.py for full endpoint documentation.
        """)
        
        print("\n" + "=" * 80)
        print("Phase 5A Example Completed Successfully")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
