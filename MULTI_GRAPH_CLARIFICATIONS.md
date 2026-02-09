# Esclarecimentos e Refinamento: Multi-Graph Architecture

## Respostas às Perguntas

### 1️⃣ Especificações de Entidades - Compartilhadas ou Isoladas?

**Resposta: COMPARTILHADAS**

Cada graph terá **instâncias diferentes** de entidades, mas as **especificações são globais** (compartilhadas):

```
GLOBAL (Compartilhado por todos os graphs):
├── Entity Types: ["equipment", "component", "failure_mode", "procedure"]
├── Entity Properties: ["name", "description", "function", "location"]
├── Relationship Types: ["has", "affects", "causes", "requires"]
└── Extraction Prompts: Mesmos prompts de IA para todos

Por Graph (Isolado):
├── equipment_manuals/
│   └── Entidades: "Valve#123", "Pump#456" (instances específicas)
├── maintenance_logs/
│   └── Entidades: "Valve#789", "Pump#101" (instances DIFERENTES)
└── technical_specs/
    └── Entidades: "Valve#202", "Pump#303" (instances DIFERENTES)
```

**Implementação:**
- Variáveis de ambiente (entity types, prompts) → Arquivo global `config.ini`
- Instâncias de entidades → Armazenadas por graph

---

### 2️⃣ Todas as Queries Devem Receber graph_id?

**Resposta: SIM, COM FALLBACK**

**Padrão proposto:**

```python
# Opção 1: Especificar graph_id explicitamente
POST /query/filter_data {
  "query": "...",
  "graph_id": "equipment_manuals"  # Explícito
}

# Opção 2: Usar default se não especificado
POST /query/filter_data {
  "query": "..."
  # Sem graph_id → Usa default do config
}

# Opção 3: Usar último graph usado (cookie/session)
POST /query/filter_data {
  "query": "..."
  # WebUI passa graph_id do último selecionado
}
```

**Lista de Queries a Modificar:**
```
Todas as queries devem ter graph_id como parâmetro OPCIONAL:
✅ /query/filter_data
✅ /query/graph/label/list
✅ /query/graph/visual
✅ /query/search
✅ /query/traverse
✅ /query/global
✅ /query/hybrid
✅ (todas que consultam os dados)
```

---

### 3️⃣ API de Inserção de Documentos

**Modificação proposta:**

```python
# ANTES:
POST /insert
{
  "files": [document.pdf],
}

# DEPOIS:
POST /insert
{
  "files": [document.pdf],
  "graph_id": "equipment_manuals",           # NOVO
  "create_if_not_exists": true               # NOVO
}
```

**Lógica:**

```
Se "graph_id" fornecido:
  ✓ Se graph existe → Inserir no graph
  ✓ Se graph NÃO existe:
    - create_if_not_exists = true → Criar novo graph e inserir
    - create_if_not_exists = false → Erro 404

Se "graph_id" NÃO fornecido:
  ✓ Usar graph default (de config)
```

**Exemplos:**

```bash
# Exemplo 1: Inserir em graph existente
POST /insert
{
  "files": [doc1.pdf],
  "graph_id": "equipment_manuals"
}
# Response: Inserido em equipment_manuals

# Exemplo 2: Criar novo graph + inserir
POST /insert
{
  "files": [doc1.pdf],
  "graph_id": "supplier_docs",
  "create_if_not_exists": true
}
# Response: Criado graph 'supplier_docs' + inserido documento

# Exemplo 3: Usar default
POST /insert
{
  "files": [doc1.pdf]
  # Sem graph_id → Usa graph padrão do sistema
}
```

---

### 4️⃣ API para Listar Graphs

**JÁ INCLUÍDA na proposta:**

```bash
GET /api/graphs

Response:
{
  "status": "success",
  "graphs": [
    {
      "id": "equipment_manuals",
      "name": "Equipment Manuals",
      "description": "OEM documentation",
      "created_at": "2026-02-01T10:00:00Z",
      "document_count": 12,
      "entity_count": 245,
      "relation_count": 1203
    },
    {
      "id": "maintenance_logs",
      ...
    }
  ]
}
```

**Também útil:**

```bash
# Obter apenas nomes (leve para dropdown)
GET /api/graphs/names

Response:
{
  "status": "success",
  "graph_names": [
    "equipment_manuals",
    "maintenance_logs",
    "technical_specs"
  ]
}
```

---

### 5️⃣ API/Comando para Deletar Graphs

**JÁ INCLUÍDA na proposta:**

```bash
DELETE /api/graphs/{graph_id}

Response:
{
  "status": "success",
  "message": "Graph 'equipment_manuals' deleted successfully"
}
```

**Com proteção:**
```
- Não permite deletar graph padrão
- Requer confirmação (pode ser um flag)
- Deleta todos os dados (irreversível)
```

**Via UI:** Botão "Delete" no seletor de graph com modal de confirmação

---

## Resumo das Modificações Necessárias

### Escopo Confirmado ✅

| Item | Necessário | Descrito em | Status |
|------|-----------|-------------|--------|
| Compartilhar entity specs | ✅ SIM | Config global | ✅ OK |
| Graph-id em queries | ✅ SIM | Todos endpoints | ⚠️ Todo |
| Insert com graph_id | ✅ SIM | API inserção | ⚠️ Todo |
| Lista de graphs API | ✅ SIM | GET /graphs | ✅ OK |
| Deletar graphs API | ✅ SIM | DELETE /graphs | ✅ OK |
| Export/Import | ✅ SIM | Endpoints novos | ⚠️ Todo |

### Escopo NÃO Incluído ❌

| Item | Motivo |
|------|--------|
| Compartilhar dados entre graphs | Complexo, fazer depois |
| Histórico/versionamento | Fora do escopo V1 |
| Permissões/controle acesso | Fora do escopo V1 |
| Sincronização em tempo real | Não aplicável |

---

## Fluxo Completo Revisado

### Cenário 1: Criar novo graph e ingerir

```
1. User faz upload:
   POST /insert
   {
     "files": [manual.pdf],
     "graph_id": "supplier_a",
     "create_if_not_exists": true
   }

2. Sistema:
   ✓ Verifica se "supplier_a" existe
   ✓ Não existe → Cria novo graph
   ✓ Ingere document em "supplier_a"
   ✓ Responde com sucesso

3. User visualiza:
   GET /graphs
   ✓ Vê "supplier_a" na lista
```

### Cenário 2: Query com graph_id

```
1. User seleciona graph "equipment_manuals" na UI

2. User faz query:
   POST /query/filter_data
   {
     "query": "Valve failure",
     "graph_id": "equipment_manuals"  ← Passado automaticamente
   }

3. Sistema:
   ✓ Usa apenas dados de "equipment_manuals"
   ✓ Retorna chunks desse graph

4. User muda para "maintenance_logs"
   ✓ Todos os calls agora usam "maintenance_logs"
```

### Cenário 3: Deletar graph

```
1. User seleciona graph para deletar
   Click: "Delete Graph"

2. Modal de confirmação:
   "Você tem certeza? Todos os dados serão deletados."

3. DELETE /api/graphs/old_project_id

4. Sistema:
   ✓ Deleta diretório
   ✓ Remove do config
   ✓ Volta para default graph

5. GET /graphs
   ✓ Graph não aparece mais
```

---

## Ordem de Implementação Recomendada

### Fase 1: Base (2-3 dias)
- [x] GraphManager
- [x] GET /graphs
- [x] DELETE /graphs/{id}
- [ ] Testes

### Fase 2: Inserção (2-3 dias)
- [ ] Modificar POST /insert com graph_id
- [ ] Implementar create_if_not_exists
- [ ] Testes

### Fase 3: Queries (3-4 dias)
- [ ] Adicionar graph_id a TODAS as queries
- [ ] Fallback para default
- [ ] Testes

### Fase 4: WebUI (3-4 dias)
- [ ] GraphSelector component
- [ ] Passa graph_id automaticamente
- [ ] Delete UI com confirmação

### Fase 5: Export/Import (2-3 dias)
- [ ] POST /graphs/{id}/export
- [ ] POST /graphs/import

---

## Arquivos a Modificar (Resumido)

```
📝 Criar novos:
  ├─ lightrag/graph_manager.py
  └─ lightrag/api/routers/graph_routes.py

✏️ Modificar (Fase 2+):
  ├─ lightrag/lightrag.py (aceitar graph_id)
  ├─ lightrag/api/routers/doc_routes.py (POST /insert com graph_id)
  └─ lightrag/api/routers/query_routes.py (graph_id em TODAS queries)

🎨 Modificar (Fase 4):
  ├─ lightrag_webui/src/App.tsx
  └─ lightrag_webui/src/components/GraphSelector.tsx (novo)
```

---

## ✅ Confirmação Final

Baseado nas suas respostas:

1. ✅ **Entity specs compartilhadas** → Config global, cada graph tem instâncias diferentes
2. ✅ **Todas queries com graph_id** → Sim, com fallback para default
3. ✅ **Insert API com graph_id** → Sim, com create_if_not_exists
4. ✅ **Lista de graphs** → GET /graphs e GET /graphs/names
5. ✅ **Delete graphs** → DELETE /graphs/{graph_id}
6. ✅ **Export/Import** → Vai incluir nas Fases 5

**Posso começar a implementação das Fases 1-2 imediatamente?**
