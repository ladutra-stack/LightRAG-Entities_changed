# Arquitetura: ANTES vs DEPOIS

## Comparação da Estrutura

### ANTES (Atual)

```
LightRAG (1 único grafo)
│
├── working_dir/
│   ├── chunk_entity_relation.db      ← Grafo global
│   ├── entities.db                   ← Entidades globais
│   ├── chunks.db
│   ├── relationships.db
│   └── log files
│
├── Entity Specs (Ambiente):
│   ├── ENTITY_TYPES = [...] (global)
│   ├── RELATION_TYPES = [...] (global)
│   └── Extraction prompts (global)
│
└── API:
    ├── POST /insert → sempre mesmo grafo
    ├── POST /query → sempre mesmo grafo
    └── Sem conceito de "graph selection"
```

---

### DEPOIS (Novo)

```
LightRAG (N grafos)
│
├── working_dir/
│   ├── graphs_config.json            ← Metadata de todos os graphs
│   │
│   └── graphs/
│       ├── equipment_manuals/        ← Graph 1
│       │   ├── chunk_entity_relation.db
│       │   ├── entities.db
│       │   ├── chunks.db
│       │   ├── relationships.db
│       │   ├── metadata.json
│       │   └── documents/
│       │
│       ├── maintenance_logs/         ← Graph 2
│       │   ├── chunk_entity_relation.db
│       │   ├── entities.db
│       │   ├── chunks.db
│       │   ├── relationships.db
│       │   ├── metadata.json
│       │   └── documents/
│       │
│       └── technical_specs/          ← Graph N
│           ├── ...
│
├── Entity Specs (Ambiente - GLOBAL):
│   ├── ENTITY_TYPES = [...] (compartilhado)
│   ├── RELATION_TYPES = [...] (compartilhado)
│   └── Extraction prompts (compartilhado)
│
├── GraphManager:
│   ├── create_graph()
│   ├── list_graphs()
│   ├── get_graph()
│   ├── delete_graph()
│   └── export/import_graph()
│
└── API:
    ├── GET /graphs                  ← NOVO
    ├── POST /graphs                 ← NOVO
    ├── DELETE /graphs/{id}          ← NOVO
    ├── POST /insert?graph_id=X      ← MODIFICADO
    ├── POST /query?graph_id=X       ← MODIFICADO (todas)
    └── POST /graphs/{id}/export     ← NOVO (Fase 5)
```

---

## Comparação: Inserção de Documentos

### ANTES
```bash
POST /insert
Content-Type: multipart/form-data
files: [doc1.pdf, doc2.pdf]

↓ Sistema

✓ Faz ingestão no ÚNICO grafo global
✓ Não há opção de escolher
✓ Tudo vai para o mesmo lugar
```

### DEPOIS
```bash
POST /insert
Content-Type: multipart/form-data
files: [doc1.pdf, doc2.pdf]
graph_id: "supplier_a"              ← NOVO parâmetro
create_if_not_exists: true          ← NOVO parâmetro

↓ Sistema

✓ Se graph_id não fornecido → usa default
✓ Se graph_id fornecido:
  - Se existe → ingere lá
  - Se não existe + create_if_not_exists=true → cria + ingere
  - Se não existe + create_if_not_exists=false → erro
```

---

## Comparação: Queries

### ANTES
```bash
POST /query/filter_data
{
  "query": "Valve failure",
  "filter_config": {...},
  "chunk_top_k": 5
}

↓ Sistema

✓ Busca SEMPRE no único grafo global
✓ Sem opção de escolher
```

### DEPOIS
```bash
POST /query/filter_data
{
  "query": "Valve failure",
  "filter_config": {...},
  "chunk_top_k": 5,
  "graph_id": "equipment_manuals"   ← NOVO (opcional)
}

↓ Sistema

✓ Se graph_id fornecido → busca nesse graph
✓ Se graph_id não fornecido → busca no default
✓ WebUI passa automaticamente o graph selecionado
```

---

## Comparação: Interface Web

### ANTES
```
┌─────────────────────────────────┐
│ 🔍 Search                       │
├─────────────────────────────────┤
│                                 │
│ [Query text here]               │ ← 1 única caixa
│ [Search]      [Clear]           │
│                                 │
└─────────────────────────────────┘

Results (de um único grafo):
─────────────────────────────────
 ✓ Chunk 1
 ✓ Chunk 2
 ✓ Chunk 3
```

### DEPOIS
```
┌──────────────────────────────────┐
│ 📊 Graphs | 🔍 Search             │
├────────────┬──────────────────────┤
│            │                      │
│ ▼ Equipment│ [Query text here]    │
│   Manuals  │ [Search] [Clear]     │
│            │                      │
│ Maintenance│ Filter: [...]        │
│   Logs     │ Rerank: [✓]         │
│            │                      │
│ Technical  │                      │
│   Specs    │ [Results from        │
│            │  Equipment Manuals]  │
│ [+ New]    │                      │
│ [Delete]   └──────────────────────┘
└────────────┘

Results (do graph selecionado):
─────────────────────────────────
 ✓ Chunk 1 (from equipment_manuals)
 ✓ Chunk 2 (from equipment_manuals)
 ✓ Chunk 3 (from equipment_manuals)
```

---

## Comparação: Armazenamento em Disco

### ANTES
```
ragdata/
├── chunk_entity_relation/
│   └── data.db
├── entities/
│   └── data.db
├── chunks/
│   └── data.db
├── documents/
│   ├── doc1.pdf
│   └── doc2.pdf
└── logs/
```

**Problema:** Tudo misturado, dificil fazer backup/restore de um subset

---

### DEPOIS
```
ragdata/
├── graphs_config.json           ← Qual é o default, lista de graphs
│
├── graphs/
│   ├── equipment_manuals/
│   │   ├── metadata.json        ← Nome, descrição, stats
│   │   ├── documents/           ← Apenas docs desse graph
│   │   │   ├── doc1.pdf
│   │   │   └── doc2.pdf
│   │   ├── chunk_entity_relation/
│   │   │   └── data.db
│   │   ├── entities/
│   │   │   └── data.db
│   │   └── chunks/
│   │       └── data.db
│   │
│   ├── maintenance_logs/
│   │   ├── metadata.json
│   │   ├── documents/
│   │   │   ├── doc3.pdf
│   │   │   └── doc4.pdf
│   │   ├── chunk_entity_relation/
│   │   │   └── data.db
│   │   ├── entities/
│   │   │   └── data.db
│   │   └── chunks/
│   │       └── data.db
│   │
│   └── technical_specs/
│       └── ...
│
└── logs/                       ← Global
```

**Benefício:** Posso fazer backup/restore de um graph inteiro facilmente

---

## Comparação: Casos de Uso

### ANTES: Caso de Uso Limitante

```
❌ "Preciso trabalhar com documentos de 2 fornecedores diferentes"
   → Tudo vai pro mesmo grafo
   → Dados misturados
   → Queries retornam informações de ambos misturadas
   → Difícil separar depois

❌ "Tenho projeto histórico (2024) e projeto novo (2025)"
   → Tudo no mesmo grafo
   → Não consigo comparar facilmente
   → Documentos antigos "poluem" as buscas

❌ "Quero dar acesso a subconjuntos de dados para diferentes times"
   → Sem isolamento de dados
   → Só posso gerenciar no nível de aplicação
```

### DEPOIS: Casos de Uso Habilitados

```
✅ "Preciso trabalhar com documentos de 2 fornecedores diferentes"
   → Graph: "supplier_a"
   → Graph: "supplier_b"
   → Dados completamente isolados
   → Queries específicas por supplier

✅ "Tenho projeto histórico (2024) e projeto novo (2025)"
   → Graph: "project_2024"
   → Graph: "project_2025"
   → Posso comparar facilmente
   → Documentos antigos não interferem

✅ "Quero dar acesso a subconjuntos de dados para diferentes times"
   → Team A acessa apenas "engineering_docs"
   → Team B acessa apenas "operations_manual"
   → Isolamento natural no storage

✅ "Preciso fazer backup de dados de um cliente específico"
   → Backup apenas da pasta: graphs/client_a/
   → Muito eficiente
```

---

## Resumo de Benefícios

| Aspecto | ANTES | DEPOIS |
|---------|-------|--------|
| **Múltiplos contextos** | ❌ Não | ✅ Sim |
| **Isolamento de dados** | ❌ Não | ✅ Sim |
| **Backup seletivo** | ❌ Difícil | ✅ Fácil |
| **Escalabilidade** | ❌ Limitada | ✅ Linear |
| **Organização** | ❌ Caótica | ✅ Clara |
| **Reuso de specs** | ✅ N/A | ✅ Sim |
| **Complexidade** | ✅ Baixa | ⚠️ Média |

---

## Impacto no Código

### Mudanças Internas (Core)
```
✏️ lightrag.py
  + Aceitar graph_id no __init__
  + Usar GraphManager para resolver qual KG usar
  + Resto da lógica permanece igual (por graph)

✏️ storage/ (KG, KV, Vector)
  + Caminhos de disco ajustados automaticamente
  + Sem mudança na lógica de operações
```

### Mudanças Externas (API)
```
✏️ Todos os routers (doc, query, kg)
  + Adicionar parâmetro graph_id (opcional)
  + Passar graph_id ao LightRAG
  + Resto remains igual
```

### Mudanças UI
```
✏️ App.tsx
  + Adicionar GraphSelector
  + Pass graph_id em todos os calls automaticamente
  + Resto remains igual
```

---

## Dependências Entre Fases

```
Fase 1 (GraphManager)
    ↓ (base para tudo)
Fase 2 (Insert com graph_id)
Fase 3 (Queries com graph_id) ← Pode ser paralelo com Fase 2
    ↓
Fase 4 (WebUI)
    ↓
Fase 5 (Export/Import) ← Pode ser paralelo com Fase 4
```

---

## Próximos Passos

Baseado nesse documento:

1. **Confirme:** A estrutura de disco proposta está OK?
2. **Confirme:** Todos os queries devem receber graph_id (não apenas alguns)?
3. **Confirme:** Posso começar com Fase 1 (GraphManager)?

Pronto, posso começar a codificar? 🚀
