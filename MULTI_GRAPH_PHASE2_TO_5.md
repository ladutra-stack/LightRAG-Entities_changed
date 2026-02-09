# Multi-Graph Implementation Roadmap: Phases 2-5

## Executive Summary
Phase 1 ✅ laid the infrastructure for multi-graph support. Phases 2-5 will connect this infrastructure to existing data ingestion, querying, and UI systems.

---

## Phase 2: Insert API Modification

### Objective
Enable document insertion into specific graphs with automatic graph creation support.

### Changes Required

#### 1. DocumentRoutes Modification (`lightrag/api/routers/document_routes.py`)
Modify `/insert` endpoint (POST /insert):

**Before**:
```python
async def insert(
    kg_name: str = Form(...),
    file: UploadFile = File(...),
    chunk_size: int = Form(None),
    chunk_overlap_size: int = Form(None),
):
    # Insert to default working_dir only
```

**After**:
```python
async def insert(
    kg_name: str = Form(...),
    file: UploadFile = File(...),
    graph_id: str = Form(...),              # MANDATORY
    create: bool = Form(...),               # MANDATORY
    chunk_size: int = Form(None),
    chunk_overlap_size: int = Form(None),
):
    # 1. Validate graph_id parameter provided
    # 2. Check if graph exists via graph_manager.graph_exists(graph_id)
    # 3. If not exists and create=true: graph_manager.create_graph(...)
    # 4. Get graph working_dir: graph_manager.get_graph_working_dir(graph_id)
    # 5. Initialize LightRAG with graph-specific working_dir
    # 6. Proceed with document insertion
```

#### 2. Error Handling
- ❌ **400 Bad Request**: `graph_id` not provided
- ❌ **400 Bad Request**: Graph doesn't exist and `create=false`
- ❌ **409 Conflict**: Graph already exists and `create=true`

#### 3. Updated Request Model
```python
class DocumentInsertRequest:
    kg_name: str                    # Knowledge graph name/document category
    graph_id: str                   # REQUIRED: which graph to insert into
    create: bool                    # REQUIRED: auto-create graph if missing
    file: UploadFile                # Document file to insert
    chunk_size: Optional[int] = None
    chunk_overlap_size: Optional[int] = None
```

#### 4. Response Enhancement
```json
{
    "status": "success",
    "message": "Document inserted successfully",
    "document_id": "doc-123456",
    "graph_id": "testgraph_1234567890",
    "graph_created": false,
    "chunks_created": 147,
    "entities_extracted": 42
}
```

### Integration Points
- Uses: `GraphManager` instance passed to document routes
- Affects: DocumentManager class initialization
- Related: Entity extraction still uses global entity types
- Side-effect: Updates graph metadata stats (document_count)

### Testing
- Test case 1: Insert with existing graph
- Test case 2: Insert with `create=true` auto-creates graph
- Test case 3: Missing `graph_id` returns 400
- Test case 4: `create=false` on non-existent graph returns 400
- Test case 5: Concurrent inserts to different graphs work independently

---

## Phase 3: Query API Modification

### Objective
Make `graph_id` mandatory on all query endpoints to ensure queries only search within a specific graph.

### Endpoints to Modify (8 total)

#### 1. `/query/filter_data`
```python
async def filter_data(
    filter_config: FilterDataConfig,
    graph_id: str = Query(...),  # ADD: MANDATORY
):
    # Get graph working_dir
    working_dir = graph_manager.get_graph_working_dir(graph_id)
    # Load graph-specific storage
    # Execute filter query on that graph only
```

#### 2. `/query/graph/label/list`
```python
async def get_graph_labels(
    graph_id: str = Query(...),  # ADD: MANDATORY
):
    # Return labels from specific graph
```

#### 3. `/query/graph/label/popular`
```python
async def get_popular_labels(
    graph_id: str = Query(...),  # ADD: MANDATORY
    limit: int = Query(300),
):
```

#### 4-8. Other Query Endpoints
- `/query/graph/visual` - Get graph visualization for specific graph
- `/query/search` - Semantic search within specific graph
- `/query/traverse` - Graph traversal within specific graph
- `/query/global` - Global query within specific graph context
- `/query/hybrid` - Hybrid query within specific graph

### Validation Pattern
```python
# Add to each endpoint
if not graph_manager.graph_exists(graph_id):
    raise HTTPException(
        status_code=404,
        detail=f"Graph '{graph_id}' not found"
    )

# Get graph-specific storage
working_dir = graph_manager.get_graph_working_dir(graph_id)
# Use working_dir instead of args.working_dir
```

### Error Handling
- ❌ **400 Bad Request**: `graph_id` not provided
- ❌ **404 Not Found**: Graph doesn't exist

### Response Format (unchanged)
Query responses remain the same, with implicit graph context.

### Testing
- Test each of 8 endpoints with valid graph_id
- Test each endpoint with invalid graph_id (404)
- Test each endpoint without graph_id (400)
- Verify results come from correct graph
- Test with multiple graphs in parallel

---

## Phase 4: LightRAG Integration

### Objective
Modify LightRAG class to support per-graph initialization and storage management.

### Changes in `lightrag/lightrag.py`

#### 1. Constructor Modification
```python
class LightRAG:
    def __init__(
        self,
        working_dir: str,
        graph_id: Optional[str] = None,  # NEW
        graph_manager: Optional[GraphManager] = None,  # NEW
        ...
    ):
        self.graph_id = graph_id
        self.graph_manager = graph_manager
        
        # If graph_id provided and graph_manager provided:
        # Use graph-specific working directory
        if graph_id and graph_manager:
            self.working_dir = graph_manager.get_graph_working_dir(graph_id)
        else:
            self.working_dir = working_dir
            
        # Rest of initialization...
```

#### 2. Storage Path Adjustments
```python
# Currently:
self.working_dir = working_dir

# After:
# - {working_dir}/graphs/{graph_id}/ contains all graph-specific data
# - NameSpace paths: {working_dir}/graphs/{graph_id}/default/...
# - This automatic via working_dir assignment
```

#### 3. Multi-Graph Instantiation Pattern
```python
# In document_routes.py or query_routes.py:
graph_working_dir = graph_manager.get_graph_working_dir(graph_id)
rag = LightRAG(
    graph_id=graph_id,
    graph_manager=graph_manager,
    working_dir=base_working_dir,  # Still pass base, but LightRAG will override
    ...other_params...
)

# Now rag.working_dir == graph_working_dir automatically
```

### Entity Type Specifications

#### Option A: Global (Current Proposal)
- Entity types defined globally via environment
- All graphs use same entity specification
- Simpler management, less flexibility
- **Recommended for Phase 4**

#### Option B: Per-Graph (Future)
- Each graph can have custom entity types
- More flexible but complex
- Requires additional metadata storage
- **Discuss for Phase 6**

### Testing
- Test LightRAG init with graph_id (creates correct working_dir)
- Test LightRAG init without graph_id (uses provided working_dir)
- Test storage isolation: two graphs don't interfere
- Test concurrent LightRAG instances for different graphs
- Test that NameSpace correctly loads from graph-specific dir

---

## Phase 5: WebUI Updates

### Objective
Add UI components to select and manage graphs.

### Components to Add

#### 1. GraphSelector Component (`lightrag_webui/src/components/GraphSelector.tsx`)
```typescript
interface GraphSelectorProps {
    selectedGraphId: string;
    graphs: Graph[];
    onSelect: (graphId: string) => void;
    onRefresh: () => Promise<void>;
}

export const GraphSelector: React.FC<GraphSelectorProps> = ({
    selectedGraphId,
    graphs,
    onSelect,
    onRefresh
}) => {
    return (
        <div className="graph-selector">
            <select 
                value={selectedGraphId}
                onChange={(e) => onSelect(e.target.value)}
            >
                {graphs.map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                ))}
            </select>
            <button onClick={onRefresh}>Refresh</button>
        </div>
    );
};
```

#### 2. GraphManager Component (`lightrag_webui/src/components/GraphManager.tsx`)
- List all graphs with metadata
- Create new graph dialog
- Delete graph confirmation
- Update graph name/description
- Set default graph

#### 3. Layout Integration
- Add GraphSelector to sidebar
- Display selected graph name prominently
- Show graph stats (docs, entities, relations)
- Add "Graph Settings" menu item

#### 4. API Hook Updates (`lightrag_webui/src/hooks/api.ts`)
```typescript
// Add graph API functions
const useGraphAPI = () => {
    const listGraphs = async () => { /* /graphs */ }
    const createGraph = async (name, description) => { /* POST /graphs */ }
    const deleteGraph = async (graphId) => { /* DELETE /graphs/{graphId} */ }
    const updateGraph = async (graphId, updates) => { /* PUT /graphs/{graphId} */ }
    const setDefaultGraph = async (graphId) => { /* POST /graphs/{graphId}/set-default */ }
};
```

#### 5. AppContext Updates
```typescript
interface AppContextType {
    selectedGraphId: string;
    setSelectedGraphId: (id: string) => void;
    graphs: Graph[];
    refreshGraphs: () => Promise<void>;
    // ... existing fields
}
```

#### 6. Automatic graph_id Injection
```typescript
// Update all API calls to include graph_id
const queryData = async (config: FilterConfig) => {
    const response = await fetch('/query/filter_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...config,
            graph_id: appContext.selectedGraphId  // ADD THIS
        })
    });
};
```

### UI Mockup
```
┌─────────────────────────────────────────────┐
│  LightRAG                                  [≡]│
├─────────────────────────────────────────────┤
│                                             │
│ Graph: [default               ▼] [Refresh] │
│ ────────────────────────────────          │
│                                             │
│ 📊 Graph Stats                              │
│   • 42 documents                            │
│   • 156 entities                            │
│   • 289 relations                           │
│                                             │
│ ⚙️ Graph Settings                           │
│ ➕ Create Graph                             │
│ 📁 Manage Graphs                            │
│ 🏠 Home                                    │
│ 📖 Documents                                │
│ 🔍 Query                                   │
│ 📊 Visualization                            │
│ ⚙️ Settings                                 │
│                                             │
└─────────────────────────────────────────────┘
```

### Key Behaviors
- On app load: Fetch list of graphs, select default
- On graph select: Show stats, reload query context
- On create: Update list, optionally auto-select new graph
- On delete: If current graph deleted, switch to default

### Testing
- Test graph selector renders all graphs
- Test selecting graph updates context
- Test API calls include graph_id
- Test query results are graph-specific
- Test concurrent graph management

---

## Summary of Parameter Changes

### Phase 2 (Insert API)
| Parameter | Phase 1 | Phase 2 | Status |
|-----------|---------|---------|--------|
| `graph_id` | N/A | REQUIRED | New ✨ |
| `create` | N/A | REQUIRED | New ✨ |
| `kg_name` | Optional | Optional | Unchanged |

### Phase 3 (Query APIs)
| Parameter | Phase 1 | Phase 3 | Status |
|-----------|---------|---------|--------|
| `graph_id` | N/A | REQUIRED | New ✨ |
| `filter_config` | - | - | Unchanged |
| Other query params | Optional | Optional | Unchanged |

### Server Integration Changes

#### Phase 1 ✅
- [x] GraphManager instantiation
- [x] Graph routes registration
- [x] Error handling for GraphManager init

#### Phase 2 📋
- [ ] Pass GraphManager to document_routes
- [ ] Pass graph_id from request to LightRAG init
- [ ] Update DocumentManager to handle per-graph storage

#### Phase 3 📋
- [ ] Pass GraphManager to query_routes
- [ ] Validate graph_id on each query endpoint
- [ ] Pass graph_id to LightRAG query methods

#### Phase 4 📋
- [ ] LightRAG __init__ accept graph_id & graph_manager
- [ ] Auto-resolve working_dir from graph_manager
- [ ] Test per-graph storage isolation

#### Phase 5 📋
- [ ] Build GraphSelector component
- [ ] Create GraphManager modal
- [ ] Update app context with selectedGraphId
- [ ] Inject graph_id into all API calls

---

## Estimated Effort

| Phase | Components | Estimated Lines | Complexity |
|-------|-----------|-----------------|------------|
| 1 ✅ | GraphManager, Routes | 650 | **Medium** |
| 2 📋 | Insert API, Doc Routes | 100 | **Low** |
| 3 📋 | 8 Query Endpoints | 80 | **Low** |
| 4 📋 | LightRAG Integration | 50 | **Low** |
| 5 📋 | WebUI Components | 500 | **Medium** |

**Total**: ~1,380 lines across all components

---

## Risk Mitigation

### Backward Compatibility
- Phase 1: ✅ Fully backward compatible (additive only)
- Phase 2+: ⚠️ Breaking changes (graph_id required)
  - Mitigation: Clear error messages, documentation, migration guide

### Data Migration
- Existing single-graph data can be migrated to "default" graph
- Migration script: Rename `{working_dir}/default/` → `{working_dir}/graphs/default/`

### Testing Strategy
- Unit tests for each phase component
- Integration tests for phase-to-phase connections
- End-to-end tests with multiple graphs

---

## Next Steps

1. **Review Phase 1** ✅ (Completed)
2. **Plan Phase 2** - Coordinate document insertion flow
3. **Implement Phase 2** - Add graph_id to insert endpoint
4. **Review Phase 2** - Test document isolation
5. **Continue to Phase 3-5** - Modular implementation

**Would you like us to proceed with Phase 2 implementation?**
