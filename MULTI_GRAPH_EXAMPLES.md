# Exemplos de Uso: Multi-Graph Architecture

## 1. EXEMPLOS DE API

### 1.1 Listar Graphs Disponíveis

**Request:**
```bash
GET /api/graphs
```

**Response:**
```json
{
  "status": "success",
  "graphs": [
    {
      "id": "equipment_manuals",
      "name": "Equipment Manuals",
      "description": "OEM documentation for compressors",
      "created_at": "2026-02-01T10:00:00Z",
      "updated_at": "2026-02-07T15:30:00Z",
      "document_count": 12,
      "entity_count": 245,
      "relation_count": 1203
    },
    {
      "id": "maintenance_logs",
      "name": "Maintenance Logs",
      "description": "Historical maintenance records",
      "created_at": "2026-02-05T08:30:00Z",
      "updated_at": "2026-02-07T14:00:00Z",
      "document_count": 45,
      "entity_count": 523,
      "relation_count": 2100
    },
    {
      "id": "technical_specs",
      "name": "Technical Specifications",
      "description": "Product technical specifications",
      "created_at": "2026-02-06T09:15:00Z",
      "updated_at": "2026-02-07T16:45:00Z",
      "document_count": 8,
      "entity_count": 189,
      "relation_count": 456
    }
  ]
}
```

---

### 1.2 Criar Novo Graph

**Request:**
```bash
POST /api/graphs
Content-Type: application/json

{
  "name": "Supplier Documentation",
  "description": "Supplier manuals and technical documents"
}
```

**Response:**
```json
{
  "status": "success",
  "graph_id": "supplier_docs_xyz123",
  "message": "Graph 'Supplier Documentation' created successfully",
  "graph": {
    "id": "supplier_docs_xyz123",
    "name": "Supplier Documentation",
    "description": "Supplier manuals and technical documents",
    "created_at": "2026-02-07T17:30:00Z"
  }
}
```

---

### 1.3 Ingerir Documento a um Graph Específico

**Request:**
```bash
POST /api/insert?graph_id=equipment_manuals
Content-Type: multipart/form-data

files: [OEM.001.17066.pdf, Compressor_Users_Guide.pdf]
```

**Response:**
```json
{
  "status": "success",
  "message": "2 documents inserted successfully",
  "graph_id": "equipment_manuals",
  "inserted_documents": [
    {
      "file_name": "OEM.001.17066.pdf",
      "status": "success",
      "doc_id": "doc-123abc",
      "added_chunks": 156,
      "entities_extracted": 45
    },
    {
      "file_name": "Compressor_Users_Guide.pdf",
      "status": "success",
      "doc_id": "doc-456def",
      "added_chunks": 203,
      "entities_extracted": 67
    }
  ]
}
```

---

### 1.4 Query um Graph Específico

**Request:**
```bash
POST /api/query/filter_data
Content-Type: application/json

{
  "query": "Valve failure, valve stick",
  "graph_id": "equipment_manuals",
  "filter_config": {
    "entity_labels": ["Anti-Surge Valve", "Centrifugal Compressor"]
  },
  "chunk_top_k": 5,
  "enable_rerank": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Found 5 relevant chunks from equipment_manuals",
  "data": {
    "entities": ["Anti-Surge Valve", "Centrifugal Compressor"],
    "chunks": [
      {
        "chunk_id": "chunk-abc123",
        "content": "Anti-Surge Valve failure causes...",
        "file_path": "OEM.001.17066.pdf",
        "graph_id": "equipment_manuals",
        "similarity_score": 0.92,
        "rank": 1
      }
    ]
  },
  "metadata": {
    "graph_id": "equipment_manuals",
    "chunks_returned": 5,
    "reranking_applied": true
  }
}
```

---

### 1.5 Comparar dados entre Graphs

**Workflow (múltiplas requests):**

```bash
# Step 1: Query equipment_manuals
POST /api/query/filter_data?graph_id=equipment_manuals
{
  "query": "Centrifugal Compressor failures",
  "chunk_top_k": 3
}
# Resposta: Dados técnicos de falhas

# Step 2: Query maintenance_logs
POST /api/query/filter_data?graph_id=maintenance_logs
{
  "query": "Centrifugal Compressor failures",
  "chunk_top_k": 3
}
# Resposta: Registros históricos de manutenção

# Step 3: Comparar resultados manualmente ou via frontend
```

---

## 2. EXEMPLOS DE INTERFACE (WebUI)

### 2.1 Seletor de Graphs

```
┌─────────────────────────────────────┐
│ 📊 Knowledge Graphs                  │
├─────────────────────────────────────┤
│                                     │
│ ▼ Equipment Manuals (245 entities) │  ← Selected
│                                     │
│   Maintenance Logs (523 entities)   │
│   Technical Specs (189 entities)    │
│   Supplier Docs (0 entities)        │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ + Create New Graph              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Graph Details]                     │
│ Name: Equipment Manuals             │
│ Docs: 12                            │
│ Updated: Feb 7, 2026                │
└─────────────────────────────────────┘
```

### 2.2 Upload de Documentos com Graph Selector

```
┌────────────────────────────────────────────┐
│ 📁 Insert Documents                        │
├────────────────────────────────────────────┤
│                                            │
│ Target Graph:                              │
│ [▼ Equipment Manuals             ↻ Reload]│
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ Drag files here or click to select   │  │
│ │ Supported: PDF, TXT, MD              │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ [Cancel]                    [Insert Files] │
└────────────────────────────────────────────┘
```

### 2.3 Query Panel com Graph Context

```
┌────────────────────────────────────────────┐
│ 🔍 Search                                  │
├────────────────────────────────────────────┤
│                                            │
│ Graph: [Equipment Manuals     ▼]           │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ Valve failure, valve stick           │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ Filter by entities: [Anti-Surge Valve, ..] │
│ Rerank results: [✓]                       │
│ Top chunks: [5  ▼]                        │
│                                            │
│ [Clear]                         [Search]   │
└────────────────────────────────────────────┘

Results (Equipment Manuals):
─────────────────────────────────
[1] chunk-abc123 | OEM.001.17066.pdf
    Similarity: 0.92
    "Anti-Surge Valve failure causes..."

[2] chunk-def456 | Compressor_Users_Guide.pdf
    Similarity: 0.88
    "Valve sticking mechanisms..."
```

### 2.4 Visualização do Grafo

```
┌────────────────────────────────────────────┐
│ 📈 Knowledge Graph Visualization           │
├────────────────────────────────────────────┤
│                                            │
│ Graph: [Equipment Manuals ▼]               │
│                                            │
│ ┌──────────────────────────────┐           │
│ │                              │           │
│ │    ●─────────●              │           │
│ │   /|\       /|               │           │
│ │  / │ \     / │               │           │
│ │ ●  ●  ──● ●              │           │
│ │ │  │\  /│ │               │           │
│ │ │  │ \/  │ │               │           │
│ │ ●  ●      ●              │           │
│ │                              │           │
│ │ (Only shows entities from     │           │
│ │  Equipment Manuals graph)     │           │
│ │                              │           │
│ └──────────────────────────────┘           │
│                                            │
│ Zoom: [100% ▼]  [Reset View]               │
└────────────────────────────────────────────┘
```

---

## 3. CASOS DE USO REAIS

### Caso 1: Documentação por Fornecedor

```
Graph 1: "Supplier A - Equipment"
├── OEM Manual 1
├── OEM Manual 2
└── Service Bulletins

Graph 2: "Supplier B - Equipment"
├── OEM Manual 1
├── Troubleshooting Guides
└── Parts Lists

Workflow:
- User seleciona "Supplier A - Equipment"
- Busca por "compressor failure"
- Obtém apenas dados do Supplier A
- Depois muda para "Supplier B - Equipment"
- Busca mesma coisa
- Compara resultados entre fornecedores
```

---

### Caso 2: Separação por Departamento

```
Graph 1: "Engineering"
├── Technical Specifications
├── Design Documents
└── Performance Data

Graph 2: "Operations"
├── Operating Procedures
├── Maintenance Logs
└── Safety Guidelines

Graph 3: "Support"
├── Troubleshooting FAQs
├── Product Support Docs
└── Known Issues

Workflow:
- Engineer: Querys em "Engineering"
- Operator: Querys em "Operations"
- Support: Querys em "Support"
```

---

### Caso 3: Histórico Temporal

```
Graph 1: "2024 Documentation"
├── Models released in 2024
├── Fixes for 2024
└── 2024 Service Records

Graph 2: "2025 Documentation"
├── Models released in 2025
├── Fixes for 2025
└── 2025 Service Records

Workflow:
- "Qual era o procedimento em 2024?" → Query Graph 1
- "Qual é o procedimento em 2025?" → Query Graph 2
- Comparar evolução
```

---

## 4. FLUXO COMPLETO DE EXEMPLO

```
1. SETUP INICIAL
   └─ Admin cria 3 graphs:
      • equipment_manuals
      • maintenance_logs
      • technical_specs

2. INGESTÃO
   └─ DocumentA.pdf → equipment_manuals
   └─ DocumentB.pdf → maintenance_logs
   └─ DocumentC.pdf → technical_specs

3. EXPLORAÇÃO
   ┌─ User abre WebUI
   │  └─ Vê 3 graphs no seletor
   │  └─ Seleciona "equipment_manuals"
   │
   ├─ Query: "Valve failure"
   │  └─ API: GET /query/filter_data?graph_id=equipment_manuals
   │  └─ Resultados: 5 chunks relevantes
   │
   ├─ Visualiza grafo
   │  └─ Mostra entidades apenas de equipment_manuals
   │
   └─ Muda para "maintenance_logs"
      └─ Query novamente
      └─ Vê histórico de manutenção (different data source)

4. COMPARAÇÃO
   └─ User pode comparar saídas de diferentes graphs
```

---

## 5. BENEFÍCIOS POR CASO DE USO

### Pesquisador / Engenheiro
✅ Separar documentação por projeto  
✅ Comparar abordagens entre projetos  
✅ Isolar dados confidenciais  

### Operador
✅ Ver apenas procedimentos relevantes  
✅ Não se perder em dados irrelevantes  
✅ Histórico organizado por período  

### Suporte Técnico
✅ Base de conhecimento estruturada  
✅ Problemas específicos isolados  
✅ FAQs separados por produto  

### Administrador
✅ Controlar crescimento do conhecimento  
✅ Facilitar backup/restauração  
✅ Auditar acesso a dados  
