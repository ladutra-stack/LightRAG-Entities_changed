# 🔗 CURL Examples - Query Filter Data

## 📌 Endpoint Base

```
POST http://localhost:9621/query/filter_data
```

**Status:** ✅ Implementado e testado

---

## 📋 Parâmetros da Requisição

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `query` | string | Não | `""` | Texto para busca semântica dentro dos filtros |
| `filter_config` | object | Não | `null` | Configuração de filtros para entidades |
| `top_k` | int | Não | 10 | Número máximo de entidades a retornar |
| `chunk_top_k` | int | Não | `null` | Número de chunks a recuperar antes do reranking |
| `enable_rerank` | bool | Não | `null` | Ativar/desativar reranking para chunks |
| `mode` | string | Não | `"local"` | Modo de operação (`local`, `global`, `hybrid`, `mix`, `naive`, `bypass`) |
| `only_need_context` | bool | Não | false | Retornar apenas contexto |
| `include_references` | bool | Não | true | Incluir informações de referência |

### filter_config - Opções de Filtro

```json
{
  "entity_id": ["ent-abc123", "ent-def456"],
  "entity_name": ["Bearing", "Pump", "Compressor"],
  "entity_type": ["component", "equipment", "system", "manufacturer"],
  "has_property": ["function", "description"]
}
```

**Prioridade de Filtros (do mais rápido para o mais lento):**
1. **entity_id** (PRIMARY) - Busca direta por ID, mais rápida e precisa
2. **entity_name** - Busca por nome exato (case-insensitive)
3. **entity_type** - Filtro por tipo de entidade
4. **has_property** - Verifica se propriedade existe e não está vazia

**Lógica de Filtros:**
- **Dentro da mesma chave:** lógica **OR** (se a entidade corresponde a QUALQUER valor, inclua)
- **Entre chaves diferentes:** lógica **AND** (a entidade deve corresponder a TODAS as chaves)

---

## 🔄 Fluxo de Processamento do `/query/filter_data`

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣  ENTRADA: Request com query + filter_config     │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 2️⃣  RAG SEMÂNTICO: Recupera dados gerais           │
│  • Entidades: Todas as entidades relevantes         │
│  • Chunks: chunk_top_k chunks (default: N)          │
│  • Relacionamentos: Connections graph               │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 3️⃣  FILTRAGEM DE ENTIDADES: Aplica filter_config   │
│  • entity_id: Busca direta (se fornecido)           │
│  • entity_type: Filtra por tipo                     │
│  • entity_name: Filtra por nome                     │
│  • has_property: Verifica propriedades              │
│  RESULTADO: Entidades filtradas ⬇️                  │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 4️⃣  FILTRAGEM DE CHUNKS: Mantém apenas chunks que  │
│     mencionam as entidades filtradas                │
│  RESULTADO: chunks_filtrados ⬇️                     │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 5️⃣  RERANKING (Opcional):                          │
│  • Se enable_rerank=true: Reordena por relevância   │
│  • Seleciona top_k melhores chunks                  │
│  RESULTADO: top_k chunks reranqueados ⬇️            │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 6️⃣  SAÍDA: Response com:                           │
│  • Entidades filtradas                              │
│  • Chunks relacionados (opcionalmente reranqueados) │
│  • Referências e metadados                          │
└─────────────────────────────────────────────────────┘
```

**Pontos Importantes:**
- ✅ O `chunk_top_k` é recuperado **DOS CHUNKS DO RAG** (não pré-filtrado)
- ✅ Os chunks são filtrados para **APENAS mencionar entidades filtradas**
- ✅ Se `enable_rerank=true`, apenas os `top_k` melhores são retornados
- ✅ `filter_config` é aplicado **APÓS a recuperação semântica**, mas **ANTES do reranking**

---

## ⚡ Quick Test (Teste Rápido)

```bash
# Teste 1: Filtrar por entity_id (RECOMENDADO - mais rápido!)
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filter_config": {
      "entity_id": ["ent-abc123", "ent-def456"]
    },
    "top_k": 5
  }'

# Teste 2: Filtrar por tipo de entidade
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filter_config": {
      "entity_type": ["equipment"]
    },
    "top_k": 5
  }'

# Teste 3: Combinação - entity_id + busca semântica + reranking
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compression pressure",
    "filter_config": {
      "entity_id": ["ent-abc123", "ent-def456"]
    },
    "top_k": 5,
    "chunk_top_k": 20,
    "enable_rerank": true
  }'
```

---

## 🎯 Exemplo 1: Filtro por entity_id (PRIMARY - RECOMENDADO)

Recuperar entidades específicas por seu ID (mais rápido e preciso).

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filter_config": {
      "entity_id": ["ent-abc123", "ent-def456"]
    },
    "top_k": 10,
    "mode": "local"
  }'
```

**Vantagens:**
- ✅ Busca **direta** por ID (mais rápido)
- ✅ **Preciso** - evita ambiguidades de nomes
- ✅ Ideal para integração com sistemas externos
- ✅ Sem variações de case ou espaço

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 2 filtered entities",
  "data": {
    "entities": [
      {
        "entity_id": "ent-abc123",
        "entity_name": "Centrifugal Compressor",
        "entity_type": "equipment",
        "description": "Main compression equipment...",
        "function": "compress gas"
      }
    ]
  }
}
```

---

## 🎯 Exemplo 2: Filtro por Tipo de Entidade

Recuperar chunks apenas de componentes.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the function of this component?",
    "filter_config": {
      "entity_type": ["component"]
    },
    "top_k": 5,
    "mode": "local"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 5 filtered chunks",
  "chunks": [
    {
      "chunk_id": "chunk_123",
      "source_entity": "Bearing",
      "content": "The bearing supports the rotor assembly...",
      "similarity_score": 0.85
    },
    ...
  ],
  "metadata": {
    "chunks_returned": 5,
    "reranking_applied": false,
    "semantic_search_applied": true
  }
}
```

---

## 🎯 Exemplo 2: Filtro por Tipo de Entidade

Recuperar chunks apenas de componentes.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compression and pressure control",
    "filter_config": {
      "entity_type": ["equipment"],
      "has_property": ["function"]
    },
    "top_k": 10,
    "mode": "local"
  }'
```

**Lógica:** `entity_type == "equipment" AND has_property == "function"`

---

## 🎯 Exemplo 3: Múltiplos Valores (OR logic)

Buscar componentes E equipamentos.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "operational parameters",
    "filter_config": {
      "entity_type": ["component", "equipment"]
    },
    "top_k": 15
  }'
```

**Lógica:** `entity_type IN ["component", "equipment"]`

---

## 🎯 Exemplo 4: Sem Query (Recuperar sem Semantic Search)

Recuperar todos os chunks de um tipo sem busca semântica.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filter_config": {
      "entity_type": ["component"]
    },
    "top_k": 20
  }'
```

**Nota:** Com `query=""`, todos os chunks têm `similarity_score: 0.0`

---

## 🎯 Exemplo 5: Com Reranking (RAG Semântico Otimizado)

Usar reranking para melhorar a qualidade dos resultados recuperados.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compression and pressure control",
    "filter_config": {
      "entity_type": ["equipment"]
    },
    "top_k": 5,
    "chunk_top_k": 20,
    "enable_rerank": true
  }'
```

**Fluxo de Processamento:**

```
1. RAG recupera dados (semântico + entities)
2. Filtra entidades por filter_config (entity_type, entity_id, etc)
3. Recupera chunk_top_k (20) chunks APENAS das entidades filtradas
4. Aplica reranking (reordena por relevância)
5. Retorna top_k (5) melhores chunks após reranking
```

**Explicação:**
- `filter_config` - Filtros aplicados APÓS recuperação semântica inicial
- `chunk_top_k: 20` - Recupera 20 chunks SÓ das entidades filtradas
- `enable_rerank: true` - Aplica reranking (reordena por relevância)
- `top_k: 5` - Retorna apenas os 5 melhores após reranking
- Resulta em **melhor qualidade** mesmo com `top_k` pequeno

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 5 filtered entities, 20 related chunks",
  "data": {
    "entities": [
      {
        "entity_id": "ent-xyz",
        "entity_name": "Centrifugal Compressor",
        "entity_type": "equipment",
        "description": "Main compression equipment...",
        "function": "compress gas"
      }
    ],
    "chunks": [
      {
        "content": "The centrifugal compressor uses pressure control...",
        "similarity_score": 0.94,
        "rank": 1
      },
      {
        "content": "Pressure relief valve maintains system pressure...",
        "similarity_score": 0.91,
        "rank": 2
      }
    ]
  },
  "metadata": {
    "reranking_applied": true,
    "chunks_before_rerank": 20,
    "chunks_after_rerank": 5,
    "entities_found": 5,
    "entities_filtered": 1
  }
}
```

---

## 🎯 Exemplo 6: Reranking Desativado (Busca Rápida)

Desativar reranking para busca mais rápida (trade-off entre velocidade e qualidade).

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "bearing system",
    "filter_config": {
      "entity_type": ["component"]
    },
    "top_k": 5,
    "enable_rerank": false
  }'
```

**Vantagens:**
- ✅ Mais rápido (sem overhead de reranking)
- ❌ Pode ter qualidade menor

---

## 🎯 Exemplo 7: Sem Filtro (Usar Todos)

Busca semântica em todos os chunks, sem filtros.

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "bearing and seal system",
    "top_k": 10
  }'
```

---

## 🎯 Exemplo 8: Com Modo Local (Sem Resumo LLM)

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "centrifugal compressor operation",
    "filter_config": {
      "entity_type": ["equipment"]
    },
    "mode": "local",
    "top_k": 5
  }'
```

---

## 🎯 Exemplo 9: Com API Key

Se você tem autenticação configurada:

```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "query": "pressure relief valve",
    "filter_config": {
      "entity_type": ["component"]
    },
    "top_k": 5
  }'
```

---

## 🎯 Exemplo 10: Com Query Param (Alternativo)

Você também pode usar query params se preferir:

```bash
curl -X POST "http://localhost:9621/query/filter_data?top_k=10&mode=local" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "bearing cover system",
    "filter_config": {
      "entity_type": ["component"]
    }
  }'
```

---

## 🔐 Com Token JWT

Se usar autenticação com token:

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "oil pump system",
    "filter_config": {
      "entity_type": ["equipment"]
    },
    "top_k": 10
  }'
```

---

## 📊 Parâmetros Disponíveis

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `query` | string | Sim | - | Texto a buscar semanticamente |
| `filter_config` | object | Não | `{}` | Filtros para entidades |
| `top_k` | int | Não | 10 | Número máximo de chunks |
| `mode` | string | Não | `"local"` | Modo de operação (`local`, `global`, `hybrid`) |
| `only_need_context` | bool | Não | false | Retornar apenas contexto |
| `include_references` | bool | Não | true | Incluir referências |

### filter_config Opções

```json
{
  "entity_type": ["component", "equipment", "system", "manufacturer", "other"],
  "has_property": ["function", "description"],
  "entity_name": ["Bearing", "Pump"]
}
```

---

## ✅ Exemplos de Resposta

### Sucesso (200)
```json
{
  "status": "success",
  "message": "Retrieved 5 filtered chunks",
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "source_entity": "Bearing",
      "entity_type": "component",
      "content": "...",
      "similarity_score": 0.87
    }
  ],
  "metadata": {
    "query": "bearing function",
    "filters_applied": {"entity_type": ["component"]},
    "chunks_returned": 5,
    "reranking_applied": false,
    "semantic_search_applied": true
  }
}
```

### Erro (400/500)
```json
{
  "status": "error",
  "message": "Invalid filter config",
  "detail": "Filter key 'invalid_key' not supported"
}
```

---

## 🧪 Testar Local

```bash
# Com httpie (melhor para debugging)
http POST localhost:9621/query/filter_data \
  query="bearing system" \
  filter_config:='{"entity_type": ["component"]}' \
  top_k:=5

# Com Python
python -c "
import requests

response = requests.post(
    'http://localhost:9621/query/filter_data',
    json={
        'query': 'bearing system',
        'filter_config': {'entity_type': ['component']},
        'top_k': 5
    }
)
print(response.json())
"
```

---

## 🚀 Casos de Uso

### 1. Análise de Componentes
```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "maintenance requirements",
    "filter_config": {
      "entity_type": ["component", "system"]
    },
    "top_k": 20
  }'
```

### 2. Encontrar Equipamentos Específicos
```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "centrifugal compressor",
    "filter_config": {
      "entity_type": ["equipment"]
    },
    "top_k": 10
  }'
```

### 3. Busca sem Contexto (Apenas Índice)
```bash
curl -X POST http://localhost:9621/query/filter_data \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "filter_config": {
      "entity_type": ["manufacturer"]
    },
    "top_k": 50,
    "only_need_context": false
  }'
```

---

## 📝 Notas

- Use `mode: "local"` para análise de dados (sem LLM)
- Use `query: ""` quando quiser apenas chunks de um tipo
- Múltiplos valores em um filtro usam lógica **OR**
- Múltiplos filtros usam lógica **AND**
- `similarity_score` é 0.0 quando `query` está vazio

---

**Version:** 1.0  
**Last Updated:** 2024-12-XX  
**Endpoint:** `/query/filter_data`
