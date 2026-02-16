# Query Filter Data - Guia Completo

## 📋 Visão Geral

A nova query **`filter_data`** permite filtrar chunks de documentos baseado em propriedades de entidades e executar busca semântica (naive RAG) apenas nos chunks filtrados.

### Fluxo de Processamento

```
1. Filtrar Entidades
   ↓
2. Coletar Chunk IDs das Entidades Filtradas
   ↓
3. Recuperar Conteúdo dos Chunks
   ↓
4. Executar Semantic Search (opcional)
   ↓
5. Aplicar Reranking (opcional)
   ↓
6. Retornar Chunks Ordenados
```

---

## 🔧 Sintaxe Básica

### Versão Assíncrona

```python
result = await rag.afilter_data(
    query: str,
    filter_entities: list[str] | None = None,
    param: QueryParam = QueryParam()
) -> dict[str, Any]
```

### Versão Síncrona

```python
result = rag.filter_data(
    query: str,
    filter_entities: list[str] | None = None,
    param: QueryParam = QueryParam()
) -> dict[str, Any]
```

---

## 📝 Parâmetros

### `query` (obrigatório)
- **Tipo**: `str`
- **Descrição**: Texto a ser buscado semanticamente nos chunks filtrados
- **Exemplo**: `"What is the function of this component?"`
- **Nota**: Se vazio, retorna chunks sem scoring de similaridade

### `filter_entities` (opcional)
- **Tipo**: `list[str] | None`
- **Descrição**: Lista de IDs/nomes de entidades a filtrar
- **Padrão**: `None` (sem filtros, usa todas as entidades)
- **Exemplo**: `["entity_1", "entity_2", "entity_3"]`
- **Nota**: Caso a lista esteja vazia, todas as entidades serão incluídas

### `param` (opcional)
- **Tipo**: `QueryParam`
- **Descrição**: Configurações de query
- **Campos principais**:
  - `top_k: int` (padrão: 10) - Número máximo de chunks a retornar
  - `chunk_top_k: int` (padrão: 10) - Alias para top_k neste contexto
  - `enable_rerank: bool` (padrão: true) - Ativar reranking
  - `stream: bool` (padrão: false) - Streaming (não aplicável aqui)

---

## 🎯 Como Usar filter_entities

### Caso 1: Filtrar por IDs de Entidades Específicas
```python
filter_entities = ["entity_123", "entity_456", "entity_789"]

result = rag.filter_data(
    query="What is the function?",
    filter_entities=filter_entities
)
```
- **Use quando**: Você tem uma lista pré-determinada de entidades
- **Resultado**: Apenas chunks associados a estas entidades serão retornados

### Caso 2: Sem Filtro de Entidades
```python
result = rag.filter_data(
    query="search term",
    filter_entities=None  # Ou omitir o parâmetro
)
```
- **Use quando**: Quer buscar em todas as entidades do grafo
- **Resultado**: Todos os chunks são considerados

### Caso 3: Filtro Vazio
```python
result = rag.filter_data(
    query="search term",
    filter_entities=[]  # Lista vazia
)
```
- **Resultado**: Nenhum chunk é retornado

---

## 🎯 Exemplos de Uso

### Exemplo 1: Filtro Simples por Lista de Entidades
```python
from lightrag import LightRAG
from lightrag.base import QueryParam

rag = LightRAG(...)

# Busca em entidades específicas
entity_ids = ["impeller_1", "pump_2", "compressor_1"]
result = rag.filter_data(
    query="What is the main function?",
    filter_entities=entity_ids,
    param=QueryParam(top_k=5)
)

print(f"Status: {result['status']}")
print(f"Chunks encontrados: {result['metadata']['chunks_returned']}")
for chunk in result['chunks']:
    print(f"  - {chunk['source_entity']}: {chunk['content'][:100]}...")
```

**Output:**
```
Status: success
Chunks encontrados: 5
  - impeller_1: The impeller is a rotating component that...
  - pump_2: The pump redirects flow with pressure...
  ...
```

### Exemplo 2: Sem Filtro de Entidades
```python
# Busca em TODAS as entidades
result = rag.filter_data(
    query="performance specifications",
    filter_entities=None,  # Ou omitir
    param=QueryParam(top_k=10, enable_rerank=True)
)

print(f"Entidades encontradas: {result['metadata']['entities_after_filter']}")
print(f"Chunks após filtro: {result['metadata']['total_chunks_after_filter']}")
print(f"Chunks retornados: {result['metadata']['chunks_returned']}")
```

### Exemplo 3: Busca com Query Vazia
```python
# Apenas retorna chunks das entidades sem scoring de similaridade
entity_ids = ["entity_a", "entity_b"]
result = rag.filter_data(
    query="",  # Query vazia
    filter_entities=entity_ids
)

# Iterar pelos resultados
for i, chunk in enumerate(result['chunks'], 1):
    print(f"{i}. [{chunk['source_entity']}]")
    print(f"   {chunk['content'][:150]}...")
    print(f"   From: {chunk['file_path']}\n")
```

### Exemplo 4: Versão Assíncrona Completa
```python
import asyncio

async def search_equipment():
    rag = LightRAG(...)
    await rag.initialize_storages()
    
    result = await rag.afilter_data(
        query="operational parameters",
        filter_config={
            "entity_type": ["equipment", "component"],      # Equipamentos OU componentes
            "description_contains": ["pressure", "flow"],   # Com "pressure" OU "flow"
            "has_property": ["function"]                    # E que têm "function"
        },
        param=QueryParam(
            top_k=20,
            enable_rerank=True,
            chunk_top_k=15
        )
    )
    
    await rag.finalize_storages()
    return result

# Executar
result = asyncio.run(search_equipment())
```

### Exemplo 5: Sem Query (Recuperar Chunks)
```python
# Recuperar todos os chunks de entidades específicas, sem semantic search
result = rag.filter_data(
    query="",  # Vazio = sem semantic search
    filter_entities=["entity_1", "entity_2", "entity_3"]
)

# Todos os chunks têm similarity_score = 0.0
for chunk in result['chunks']:
    print(f"Chunk ID: {chunk['chunk_id']}")
    print(f"Entity: {chunk['source_entity']}")
    print(f"Content: {chunk['content']}\n")
```

---

## 📤 Formato da Resposta

### Sucesso
```json
{
  "status": "success",
  "message": "Retrieved 10 filtered chunks",
  "chunks": [
    {
      "chunk_id": "chunk-abc123def456",
      "content": "The impeller rotates at high speeds to...",
      "file_path": "compressor_manual.pdf",
      "similarity_score": 0.8743,
      "source_entity": "entity_1",
      "rank": 1
    },
    {
      "chunk_id": "chunk-xyz789uvw012",
      "content": "Performance characteristics include...",
      "file_path": "technical_specs.pdf",
      "similarity_score": 0.7891,
      "source_entity": "entity_2",
      "rank": 2
    }
  ],
  "metadata": {
    "query": "What is the function?",
    "filters_applied": ["entity_1", "entity_2"],
    "entities_found": 150,
    "entities_after_filter": 2,
    "total_chunks_before_filter": 234,
    "total_chunks_after_filter": 89,
    "chunks_returned": 10,
    "reranking_applied": true,
    "semantic_search_applied": true
  }
}
```

### Erro
```json
{
  "status": "error",
  "message": "No chunks found for filtered entities",
  "chunks": [],
  "metadata": {
    "filter_entities": ["nonexistent_entity"],
    "error_details": "Details of the error..."
  }
}
```

### Sem Resultados
```json
{
  "status": "success",
  "message": "No chunks found for filtered entities",
  "chunks": [],
  "metadata": {
    "query": "...",
    "filters_applied": {...},
    "entities_found": 0,
    "entities_after_filter": 0,
    "total_chunks_before_filter": 0,
    "total_chunks_after_filter": 0,
    "chunks_returned": 0,
    "reranking_applied": false,
    "semantic_search_applied": false
  }
}
```

---

## 📊 Campos de Resposta Explicados

### Chunk Fields
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `chunk_id` | str | ID único do chunk |
| `content` | str | Conteúdo do texto |
| `file_path` | str | Arquivo de origem |
| `similarity_score` | float | Score de similaridade (0.0-1.0) |
| `source_entity` | str | Entidade que originou este chunk |
| `rank` | int | Posição no ranking (1-indexed) |

### Metadata Fields
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `query` | str | Query executada |
| `filters_applied` | dict | Filtros que foram aplicados |
| `entities_found` | int | Total de entidades no KG |
| `entities_after_filter` | int | Entidades após aplicar filtros |
| `total_chunks_before_filter` | int | Chunks totais de todas as entidades |
| `total_chunks_after_filter` | int | Chunks após filtrar entidades |
| `chunks_returned` | int | Chunks retornados no resultado |
| `reranking_applied` | bool | Se reranking foi aplicado |
| `semantic_search_applied` | bool | Se busca semântica foi aplicada |

---

## ⚙️ Configurações Avançadas

### Ajustar Top-K
```python
# Retornar mais chunks
result = rag.filter_data(
    query="...",
    param=QueryParam(top_k=50)
)

# Retornar menos chunks
result = rag.filter_data(
    query="...",
    param=QueryParam(top_k=5)
)
```

### Desativar Reranking
```python
result = rag.filter_data(
    query="...",
    param=QueryParam(enable_rerank=False)
)
```

### Usar Diferentes QueryParam Presets
```python
# Preset: Busca detalhada
detailed_param = QueryParam(
    top_k=50,
    chunk_top_k=50,
    enable_rerank=True
)

result = rag.filter_data(
    query="...",
    param=detailed_param
)

# Preset: Busca rápida
quick_param = QueryParam(
    top_k=5,
    chunk_top_k=5,
    enable_rerank=False
)

result = rag.filter_data(
    query="...",
    param=quick_param
)
```

---

## 🔍 Casos de Uso

### Caso 1: Busca em Documentação Técnica
```python
# Encontrar instruções de operação em componentes específicos
result = rag.filter_data(
    query="How to operate safely?",
    filter_config={
        "entity_type": ["equipment", "component"],
        "description_contains": ["safety", "operation", "procedure"]
    }
)
```

### Caso 2: Análise de Especificações
```python
# Comparar especificações de diferentes equipamentos
result = rag.filter_data(
    query="Performance specifications",
    filter_config={
        "entity_type": ["equipment"],
        "has_property": ["function", "source_id"]
    },
    param=QueryParam(top_k=100)
)
```

### Caso 3: Rastreamento de Problemas
```python
# Encontrar informações sobre falhas conhecidas
result = rag.filter_data(
    query="failure modes and fault diagnosis",
    filter_config={
        "description_contains": ["failure", "fault", "problem"],
    }
)
```

### Caso 4: Extração de Dados Estruturados
```python
# Recuperar todos os chunks de um sistema sem busca semântica
result = rag.filter_data(
    query="",  # Sem query = sem semantic search
    filter_config={
        "entity_name": ["Centrifugal Compressor", "Electric Motor"]
    }
)

# Processar chunks para extração de dados
for chunk in result['chunks']:
    process_and_extract_data(chunk)
```

---

## ⚠️ Tratamento de Erros

### Verificar Status
```python
result = rag.filter_data(...)

if result['status'] == 'error':
    print(f"Erro: {result['message']}")
    print(f"Detalhes: {result['metadata'].get('error_details')}")
elif result['status'] == 'success' and result['metadata']['chunks_returned'] == 0:
    print("Nenhum chunk encontrado com os filtros especificados")
else:
    print(f"Sucesso: {result['metadata']['chunks_returned']} chunks retornados")
```

### Filtros Sem Match
```python
# Se nenhuma entidade corresponde aos filtros:
result = rag.filter_data(
    query="test",
    filter_config={"entity_type": ["nonexistent"]}
)

# result['metadata']['entities_after_filter'] == 0
# result['chunks'] == []
# result['status'] == 'success' (sem erro, apenas sem resultados)
```

---

## 🚀 Integração com Aplicações

### FastAPI Example
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
rag = LightRAG(...)

class FilterRequest(BaseModel):
    query: str
    filter_config: dict | None = None
    top_k: int = 10

@app.post("/api/filter-data")
async def filter_data_api(request: FilterRequest):
    from lightrag.base import QueryParam
    
    result = await rag.afilter_data(
        query=request.query,
        filter_config=request.filter_config,
        param=QueryParam(top_k=request.top_k)
    )
    
    return result
```

### CLI Usage
```bash
# Fazer query via CLI (exemplo)
python -c "
import asyncio
from lightrag import LightRAG
from lightrag.base import QueryParam

rag = LightRAG(...)

async def main():
    await rag.initialize_storages()
    result = await rag.afilter_data(
        'What is the function?',
        {'entity_type': ['component']},
        QueryParam(top_k=5)
    )
    print(f'Chunks: {result[\"metadata\"][\"chunks_returned\"]}')

asyncio.run(main())
"
```

---

## 📋 Checklist de Deploy

- [ ] Verificar se `self.text_chunks` está inicializado
- [ ] Verificar se `self.entity_chunks` está inicializado
- [ ] Verificar se `self.chunk_entity_relation_graph` está inicializado
- [ ] Verificar se `self.embedding_func` está configurada (se usar semantic search)
- [ ] Verificar se `self.rerank_model_func` está configurada (se enable_rerank=true)
- [ ] Testar com filter_config vazio (sem filtros)
- [ ] Testar com query vazia (sem semantic search)
- [ ] Testar com filtros que não combinam (empty result)
- [ ] Testar com reranking ativado/desativado
- [ ] Testar com diferentes valores de top_k

---

## 🎓 Melhorias Futuras

- [ ] Suporte a filtros com regex
- [ ] Filtros aninhados (nested filters)
- [ ] Caching de resultados de filtros
- [ ] Histórico de queries
- [ ] Exportação de resultados (JSON, CSV, Excel)
- [ ] Visualização em gráfico

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verificar logs em `lightrag.log`
2. Validar `filter_config` com exemplos fornecidos
3. Verificar se storages estão inicializados com `await rag.initialize_storages()`
4. Verificar se dados existem no KG com `await rag.get_graph_labels()`
