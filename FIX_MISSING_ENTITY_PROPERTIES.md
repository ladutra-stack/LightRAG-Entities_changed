# Fix: Missing Entity Properties (including `function`)

## Problem
The `/query/data` endpoint was not returning ALL properties of entities and relationships from the database. Specifically, the `function` property was missing, along with any other custom properties that weren't explicitly hardcoded in the response formatter.

## Root Cause
In `lightrag/utils.py`, the `convert_to_user_format()` function was manually selecting only specific fields when formatting entities and relationships:

**Before (Hardcoded fields only)**:
```python
formatted_entities.append({
    "entity_name": original_entity.get("entity_name", entity_name),
    "entity_type": original_entity.get("entity_type", "UNKNOWN"),
    "description": original_entity.get("description", ""),
    "source_id": original_entity.get("source_id", ""),
    "file_path": original_entity.get("file_path", "unknown_source"),
    "created_at": original_entity.get("created_at", ""),  # Missing: function, and any other properties!
})
```

This approach meant that:
- Only pre-defined fields were returned
- Any custom properties like `function` were ignored
- New properties added to the database wouldn't appear in responses

## Solution
Modified `convert_to_user_format()` to return ALL properties from the original entity/relationship data, preserving the complete data structure:

**After (All properties included)**:
```python
formatted_entities = []
for entity in entities_context:
    entity_name = entity.get("entity", "")
    
    if entity_id_to_original and entity_name in entity_id_to_original:
        original_entity = entity_id_to_original[entity_name]
        
        # Copy ALL properties from original entity
        formatted_entity = original_entity.copy()
        
        # Ensure mandatory fields are present
        if "entity_name" not in formatted_entity:
            formatted_entity["entity_name"] = entity_name
            
        formatted_entities.append(formatted_entity)
```

This ensures:
- ALL properties from the original database record are included
- No properties are lost during conversion
- Custom fields like `function` are preserved
- Backward compatibility is maintained (if no original data, fallback still works)

## Files Modified

**lightrag/utils.py** - Function: `convert_to_user_format()`

### Change 1: Entity properties (Lines ~3189-3205)
- Changed from hardcoded field selection to `.copy()` of entire entity
- Ensures all properties including `function` are returned

### Change 2: Relationship properties (Lines ~3218-3240)
- Changed from hardcoded field selection to `.copy()` of entire relationship
- Ensures all relationship properties are returned

## Impact

### What Gets Fixed
✅ Entity property `function` now appears in responses  
✅ ALL custom entity properties are returned  
✅ ALL custom relationship properties are returned  
✅ Future properties added to database automatically appear in responses  

### Backward Compatibility
✓ Maintains fallback for LLM context data (when no original DB data available)  
✓ Ensures mandatory fields are present  
✓ API response structure unchanged  
✓ No breaking changes  

## Example Response

### Query
```json
{
  "query": "Centrifugal compressor",
  "mode": "local",
  "top_k": 2
}
```

### Response (After Fix)
```json
{
  "status": "success",
  "message": "Query processed successfully",
  "data": {
    "entities": [
      {
        "entity_name": "Impeller",
        "entity_type": "component",
        "description": "Rotating components...",
        "source_id": "chunk-xxx",
        "file_path": "ETO00001.pdf",
        "created_at": 1770142560,
        "function": "Primary rotating component",  // ← NOW INCLUDED!
        "rotation_speed": "15000 RPM",              // ← NOW INCLUDED!
        "material": "Steel",                        // ← NOW INCLUDED!
        // ... any other properties from database
      }
    ],
    "relationships": [
      {
        "src_id": "Centrifugal Compressor",
        "tgt_id": "Impeller",
        "description": "...",
        "keywords": "...",
        "weight": 4,
        "source_id": "chunk-xxx",
        "file_path": "ETO00001.pdf",
        "created_at": 1770142539,
        "custom_relation_field": "value",  // ← NOW INCLUDED!
        // ... any other properties from database
      }
    ]
  }
}
```

## Testing

### Verify All Properties Are Returned
```bash
curl -X POST http://localhost:9621/query/data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Centrifugal compressor",
    "mode": "local",
    "top_k": 2
  }' | jq '.data.entities[0] | keys'
```

Expected output should include: `["entity_name", "entity_type", "description", "source_id", "file_path", "created_at", "function", ...]`

## Why This Approach?

1. **Flexibility**: Supports custom properties without code changes
2. **Completeness**: Returns all available data from the database
3. **Maintainability**: No need to update code when new properties are added
4. **Consistency**: Mirrors the data as it exists in the database
5. **Performance**: Minimal overhead - just copying the original dict
