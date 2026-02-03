# Fix for Centrifugal Compressor Query Issue

## Problem Summary
When querying "Centrifugal compressor", the system had two issues:
1. The specific entity "Centrifugal Compressor" was not being returned even though it existed in the database
2. Entity properties (especially `file_path` and `created_at`) were missing or incomplete in the response

## Root Causes Identified

### Issue 1: Missing Exact Entity Match
- **Location**: `lightrag/operate.py`, function `_get_node_data` (line ~4215)
- **Problem**: The function only performed vector similarity search, not exact name matching
- **Example**: Query "Centrifugal compressor" would not find the entity "Centrifugal Compressor" if it didn't appear in the top vector search results

### Issue 2: Lost Entity Properties
- **Location**: `lightrag/operate.py`, function `_apply_token_truncation` (line ~3725)
- **Problem**: When truncating entities and relationships for token limits, the function removed `file_path` and `created_at` fields for calculation but didn't restore them afterward
- **Result**: These fields were missing in the final `convert_to_user_format` output

## Solutions Implemented

### Fix 1: Enhanced Entity Search with Exact Matching
**File**: `lightrag/operate.py`, function `_get_node_data` (lines 4215-4294)

**Changes**:
- Added exact entity name lookup before vector search
- Attempts to find the entity using the exact query string first
- Prioritizes exact matches over vector similarity results
- Deduplicates and merges results, maintaining priority order

**Code Flow**:
```python
# 1. Try exact match with normalized query
exact_node_data = await knowledge_graph_inst.get_nodes_batch([query_normalized])

# 2. Get vector similarity results
results = await entities_vdb.query(query, top_k=query_param.top_k)

# 3. Combine: exact_matches + vector_results
all_results = exact_match_results + results

# 4. Deduplicate while preserving order (exact matches first)
```

### Fix 2: Preserve Entity Properties After Token Truncation
**File**: `lightrag/operate.py`, function `_apply_token_truncation` (lines 3726-3795)

**Changes**:
- Create metadata mappings before truncation
- Remove `file_path` and `created_at` temporarily for token calculation
- Restore these fields after truncation for each entity/relationship
- Ensures all properties are available for `convert_to_user_format`

**Code Flow**:
```python
# 1. Create metadata mappings
entity_metadata_map = {}
for entity in entities_context:
    entity_metadata_map[entity["entity"]] = {
        "file_path": entity.get("file_path"),
        "created_at": entity.get("created_at"),
    }

# 2. Remove fields for truncation
entity_copy.pop("file_path", None)
entity_copy.pop("created_at", None)

# 3. Restore after truncation
for entity in entities_context:
    entity_name = entity["entity"]
    if entity_name in entity_metadata_map:
        entity["file_path"] = entity_metadata_map[entity_name]["file_path"]
        entity["created_at"] = entity_metadata_map[entity_name]["created_at"]
```

## Expected Behavior After Fix

### Query Example:
```json
{
  "query": "Centrifugal compressor",
  "mode": "local",
  "only_need_context": true,
  "top_k": 2
}
```

### Expected Response:
```json
{
  "status": "success",
  "message": "Query processed successfully",
  "data": {
    "entities": [
      {
        "entity_name": "Centrifugal Compressor",
        "entity_type": "CONCEPT",
        "description": "A type of compressor...",
        "source_id": "chunk-xxx<SEP>chunk-yyy",
        "file_path": "ETO00001.pdf",
        "created_at": 1770142560
      }
    ],
    "relationships": [...],
    "chunks": [],
    "references": [...]
  },
  "metadata": {...}
}
```

## Files Modified

1. **lightrag/operate.py**
   - Modified `_get_node_data()` function (lines 4215-4294)
   - Modified `_apply_token_truncation()` function (lines 3726-3795)

## Testing Recommendations

### Unit Tests
```bash
# Run syntax validation
python -m py_compile lightrag/operate.py

# Check for import errors
python -c "from lightrag.operate import _get_node_data, _apply_token_truncation; print('✓ Imports OK')"
```

### Integration Tests
```bash
# 1. Start the API server
python -m lightrag.api.lightrag_server

# 2. Run test query
curl -X POST http://localhost:9621/query/data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Centrifugal compressor",
    "mode": "local",
    "only_need_context": true,
    "top_k": 2
  }'
```

### Verification Checklist
- [ ] Query for exact entity name returns the entity
- [ ] Entity includes all properties: entity_name, entity_type, description, source_id, file_path, created_at
- [ ] Vector similarity search still works for partial matches
- [ ] Exact matches are prioritized over vector results
- [ ] No duplicate entities in response
- [ ] Relationships also include all properties
- [ ] Token truncation still works correctly

## Backward Compatibility

These changes are backward compatible:
- No API signature changes
- The exact entity lookup is performed before vector search (non-breaking addition)
- Properties are restored using the same field names
- Existing queries continue to work as before

## Performance Impact

Minimal performance impact:
- One additional `get_nodes_batch()` call per query (typically very fast - direct DB lookup)
- Only when vector search would be performed anyway
- Metadata mapping is O(n) where n is number of entities (negligible)
- Property restoration is O(n) (same complexity as before, just organized differently)
