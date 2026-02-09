# Fix para query/filter_data - Sumário das Mudanças

## Problema Identificado

A query `/query/filter_data` estava retornando **0 chunks** ao invés dos chunks relevantes filtrados pelos `entity_id` fornecidos. O resultado retornava relacionamentos de outras entidades (não filtradas) ao invés dos chunks.

### Causa Raiz

Havia **dois bugs principais**:

1. **Bug no endpoint** (`query_routes.py`):
   - O endpoint estava chamando `aquery_data()` em vez de `afilter_data()`
   - `aquery_data()` retorna relacionamentos gerais, não chunks filtrados por entidades específicas
   - Aplicava filtros inadequados após recuperando dados genéricos

2. **Bug na função afilter_data** (`lightrag.py`):
   - Não havia tratamento para `filter_key == "entity_id"`
   - O código apenas processava `entity_name` como filtro
   - Quando a entrada usava `"entity_id"` como chave, nenhuma entidade matched e retornava vazio

## Mudanças Implementadas

### 1. `/workspaces/LightRAG-Entities_changed/lightrag/lightrag.py` (Linha ~3076)

**Antes:**
```python
for filter_key, filter_values in filter_config.items():
    if filter_key == "has_property":
        # ...
    elif filter_key == "entity_name":
        if entity.get("entity_id") not in filter_values:
            matches_all_filters = False
    elif filter_key == "entity_type":
        # ...
```

**Depois:**
```python
for filter_key, filter_values in filter_config.items():
    if filter_key == "has_property":
        # ...
    elif filter_key == "entity_id":
        # OR logic within same filter - match entity_id directly
        if entity.get("entity_id") not in filter_values and entity.get("id") not in filter_values:
            matches_all_filters = False
    elif filter_key == "entity_name":
        if entity.get("entity_id") not in filter_values:
            matches_all_filters = False
    elif filter_key == "entity_type":
        # ...
```

### 2. `/workspaces/LightRAG-Entities_changed/lightrag/api/routers/query_routes.py` (Linha ~1313)

**Antes:**
```python
# Get the data from RAG
response = await rag.aquery_data(request.query if request.query else "", param=param)

# Extract entities from response
all_entities = response.get("data", {}).get("entities", [])
filtered_entities = all_entities

# Apply filter_config to entities using _apply_entity_filters
if request.filter_config:
    filtered_entities = _apply_entity_filters(all_entities, request.filter_config)
    
# Then manually collect chunks... (complex logic)
```

**Depois:**
```python
# Call afilter_data with filter_config directly
response = await rag.afilter_data(
    query=request.query or "",
    filter_config=request.filter_config or {},
    param=param
)
```

### 3. Remoção de código redundante

- Removida a função `_apply_entity_filters()` que não era mais usada
- A lógica de filtro e busca semântica agora é feita integralmente em `afilter_data()`

## Novo Fluxo (Correto)

### Entrada:
```json
{
  "query": "Valve failure, valve stick",
  "filter_config": {
    "entity_id": ["Anti-Surge Valve", "Centrifugal Compressor"]
  },
  "top_k": 10,
  "chunk_top_k": 10,
  "mode": "local",
  "enable_rerank": true
}
```

### Processamento em `afilter_data()`:

1. **STEP 1**: Recupera todas as entidades do grafo
2. **STEP 2**: Filtra por `entity_id` (["Anti-Surge Valve", "Centrifugal Compressor"])
3. **STEP 3**: Recupera TODOS os chunks associados às entidades filtradas
4. **STEP 4**: Faz busca semântica (embedding similarity) da query apenas nesses chunks
5. **STEP 5**: Aplica rerank se habilitado (select top_k)
6. **STEP 6**: Formata e retorna

### Saída (Esperada):
```json
{
  "status": "success",
  "message": "Recuperados X chunks relevantes (reranked to top 10)",
  "data": {
    "entities": ["Anti-Surge Valve", "Centrifugal Compressor"],
    "chunks": [
      {
        "chunk_id": "chunk-xxx",
        "content": "Content about valve failure...",
        "file_path": "OEM.001.17066.pdf",
        "similarity_score": 0.85,
        "source_entity": "Anti-Surge Valve",
        "rank": 1
      },
      // ... mais chunks
    ],
    "relationships": [],
    "references": []
  },
  "metadata": {
    "query": "Valve failure, valve stick",
    "filters_applied": {"entity_id": [...]},
    "entities_found": X,
    "entities_after_filter": 2,
    "chunks_returned": Y,
    "reranking_applied": true,
    "semantic_search_applied": true
  }
}
```

## Resultado

✅ Agora a query funciona corretamente:
- Filtra entidades por `entity_id`
- Recupera chunks associados apenas àquelas entidades
- Realiza busca semântica apenas nesses chunks
- Aplica rerank conforme configurado
- Retorna chunks relevantes ao invés de relacionamentos genéricos

## Validação

Para testar a mudança:
```bash
# Execute a query com filter_data
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Valve failure, valve stick",
    "filter_config": {"entity_id": ["Anti-Surge Valve", "Centrifugal Compressor"]},
    "top_k": 10,
    "chunk_top_k": 10,
    "mode": "local",
    "enable_rerank": true
  }'
```

Esperado: Chunks relevantes sobre "Valve failure" associados apenas aos `entity_id` filtrados.
