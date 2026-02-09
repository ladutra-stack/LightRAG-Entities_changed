# Phase 5B + 5C Implementation Plan

## 🎯 Overview

**Objetivo:** Integrar sistemas de Backup/Replication/Recovery (5A) ao servidor principal e adicionar observabilidade (5C)

**Timeline:** 5-7 dias
**Complexity:** HIGH (integração + observabilidade)
**Impact:** Production-ready monitoring + centralized control

---

## Phase 5B: Server Integration (3-4 dias)

### ✅ Objetivos
1. Integrar managers no `lightrag_server.py`
2. Wiring das rotas na aplicação FastAPI
3. Configuração via variáveis ambiente (.env)
4. Persistência em banco de dados para recovery points
5. Testes de integração end-to-end

### 📋 Tarefas

#### Task 1: Configuration System
**File:** `lightrag/api/config_backup_replication.py` (NEW)

```python
# Configuração centralizada para Backup/Replication/Recovery
class BackupReplicationConfig:
    - backup_storage_path: str  # from LIGHTRAG_BACKUP_STORAGE
    - backup_retention_days: int  # default 30
    - replication_enabled: bool  # LIGHTRAG_REPLICATION_ENABLED
    - recovery_db_url: str  # LIGHTRAG_RECOVERY_DB_URL (SQLite/PostgreSQL)
    - metrics_enabled: bool  # LIGHTRAG_METRICS_ENABLED
    - metrics_port: int  # LIGHTRAG_METRICS_PORT (9090)
```

**Env Vars:**
```
LIGHTRAG_BACKUP_STORAGE=/lightrag_backups
LIGHTRAG_BACKUP_RETENTION_DAYS=30
LIGHTRAG_REPLICATION_ENABLED=false
LIGHTRAG_RECOVERY_DB_URL=sqlite:///./lightrag_recovery.db
LIGHTRAG_METRICS_ENABLED=true
LIGHTRAG_METRICS_PORT=9090
```

#### Task 2: Database Models for Recovery
**File:** `lightrag/api/models/recovery_db.py` (NEW)

```python
# SQLAlchemy models for persistent storage
- RecoveryPointDB
- BackupMetadataDB
- ReplicationTargetDB
- HealthCheckEventDB
```

#### Task 3: Manager Initialization
**File:** `lightrag/api/lightrag_server.py` (MODIFY)

Ao redor da linha 1140, adicionar:

```python
# Initialize Backup/Replication/Recovery managers
backup_manager = BackupManager(storage_path=Path(config.backup_storage_path))
replication_manager = ReplicationManager()
recovery_manager = DisasterRecoveryManager()

# Wire into routes
app.include_router(
    create_backup_replication_routes(
        backup_manager,
        replication_manager, 
        recovery_manager,
        api_key
    )
)
```

#### Task 4: Database Persistence
**File:** `lightrag/api/routers/backup_replication_routes.py` (MODIFY)

Adicionar:
- Persistência de recovery points em DB
- Recovery points persistem entre restarts
- Migrations automáticas

#### Task 5: Integration Tests
**File:** `test_phase5b_server_integration.py` (NEW)

```python
class TestPhase5BIntegration:
    - test_managers_initialized
    - test_routes_registered
    - test_config_loading
    - test_recovery_points_persisted
    - test_backup_workflow_with_server
    - test_replication_workflow_with_server
    - test_health_check_integration
```

---

## Phase 5C: Monitoring & Analytics (2-3 dias)

### ✅ Objetivos
1. Prometheus metrics collection
2. Health check endpoints
3. Metrics dashboard HTTP interface
4. Query analytics and logging

### 📋 Tarefas

#### Task 1: Prometheus Metrics
**File:** `lightrag/monitoring/prometheus_metrics.py` (NEW)

```python
# Metrics definitions
- backup_snapshots_total (Counter)
- backup_size_bytes (Gauge)
- replication_lag_seconds (Gauge)
- replication_errors_total (Counter)
- recovery_points_total (Gauge)
- health_check_failures_total (Counter)
- request_duration_seconds (Histogram)
```

#### Task 2: Metrics Collector
**File:** `lightrag/monitoring/metrics_collector.py` (NEW)

```python
class MetricsCollector:
    - collect_backup_metrics()
    - collect_replication_metrics()
    - collect_recovery_metrics()
    - collect_health_metrics()
    - export_to_prometheus()
```

#### Task 3: Health Status Dashboard
**File:** `lightrag/api/routers/health_dashboard_routes.py` (NEW)

Endpoints:
```
GET /api/v1/health-dashboard/status
GET /api/v1/health-dashboard/metrics
GET /api/v1/health-dashboard/graphs/{id}/status
GET /api/v1/health-dashboard/backups/summary
GET /api/v1/health-dashboard/replication/status
```

HTML dashboard em `/health` que mostra:
- Status dos grafos (HEALTHY/DEGRADED/OFFLINE)
- Backups recentes
- Histórico de replicação
- Eventos críticos

#### Task 4: Query & Event Analytics
**File:** `lightrag/monitoring/event_logger.py` (NEW)

```python
class EventLogger:
    - log_backup_event(graph_id, event_type, details)
    - log_replication_event(graph_id, target_id, event_type)
    - log_recovery_event(checkpoint_id, event_type)
    - get_events_for_graph(graph_id, time_range)
```

#### Task 5: Monitoring Tests
**File:** `test_phase5c_monitoring.py` (NEW)

```python
class TestPhase5CMonitoring:
    - test_metrics_collection
    - test_prometheus_export
    - test_health_dashboard
    - test_event_logging
    - test_analytics_queries
```

---

## 📊 Implementation Sequence

```
Week 1 - Phase 5B:
┌─────────────────────────────────────────┐
│ Day 1: Configuration System + DB Models │
├─────────────────────────────────────────┤
│ Day 2: Manager Initialization + Routing │
├─────────────────────────────────────────┤
│ Day 3: Persistence + Integration Tests  │
└─────────────────────────────────────────┘

Week 2 - Phase 5C:
┌─────────────────────────────────────────┐
│ Day 1: Prometheus Metrics + Collectors  │
├─────────────────────────────────────────┤
│ Day 2: Dashboard + Event Logging        │
├─────────────────────────────────────────┤
│ Day 3: Monitoring Tests + Documentation │
└─────────────────────────────────────────┘
```

---

## 🔧 Code Structure

```
lightrag/
├── api/
│   ├── lightrag_server.py (MODIFY - add managers initialization)
│   ├── config_backup_replication.py (NEW)
│   ├── models/
│   │   └── recovery_db.py (NEW)
│   └── routers/
│       ├── backup_replication_routes.py (MODIFY - add DB persistence)
│       └── health_dashboard_routes.py (NEW)
├── monitoring/
│   ├── __init__.py (NEW)
│   ├── prometheus_metrics.py (NEW)
│   ├── metrics_collector.py (NEW)
│   └── event_logger.py (NEW)
├── backup/ (existing from 5A)
├── replication/ (existing from 5A)
└── recovery/ (existing from 5A)

tests/
├── test_phase5b_server_integration.py (NEW)
└── test_phase5c_monitoring.py (NEW)

examples/
└── phase5b_5c_integration_demo.py (NEW)
```

---

## 📝 Success Criteria

### Phase 5B
- ✅ All managers initialized without errors
- ✅ Routes accessible via API
- ✅ Recovery points persist across restarts
- ✅ Configuration loaded from env vars
- ✅ 15+ integration tests passing
- ✅ No regressions from Phase 5A

### Phase 5C
- ✅ Prometheus metrics exported correctly
- ✅ Health dashboard accessible
- ✅ Analytics data queryable
- ✅ Event logging working
- ✅ 10+ monitoring tests passing
- ✅ Dashboard UI functional

---

## 🚀 Deployment Impact

### Phase 5B Changes
- Server startup time +~500ms (initialization)
- Memory usage +~50MB (managers in memory)
- Disk usage +existing backups
- No API breaking changes

### Phase 5C Changes
- Metrics port +1 (9090)
- CPU usage +~5% (metrics collection)
- Memory usage +~30MB (dashboard)
- Optional - can disable with env var

---

## ✨ Next Steps After 5B+5C

1. **Phase 5D (Cloud Storage):** S3/Azure backend support
2. **Phase 5E (Advanced Features):** Incremental backups, encryption
3. **Phase 6:** Performance optimization
4. **Phase 7:** Advanced query features

---

## 📋 Checklist

Phase 5B:
- [ ] Task 1: Configuration system
- [ ] Task 2: Database models
- [ ] Task 3: Manager initialization
- [ ] Task 4: Database persistence
- [ ] Task 5: Integration tests
- [ ] Code review
- [ ] Commit to main

Phase 5C:
- [ ] Task 1: Prometheus metrics
- [ ] Task 2: Metrics collector
- [ ] Task 3: Health dashboard
- [ ] Task 4: Event analytics
- [ ] Task 5: Monitoring tests
- [ ] Code review
- [ ] Commit to main

---

**Status:** Ready for implementation  
**Effort:** ~40 hours  
**Risk:** Low (extends existing code, no breaking changes)
