# Requisitos Finais Confirmados: Multi-Graph V1

## Requisitos Ajustados

### 1️⃣ Graph ID - OBRIGATÓRIO em TODAS as Queries

```python
# ANTES (graph_id opcional):
POST /query/filter_data {
  "query": "Valve failure"
  # graph_id opcional → usa default
}

# DEPOIS (graph_id OBRIGATÓRIO):
POST /query/filter_data {
  "query": "Valve failure",
  "graph_id": "equipment_manuals"  # ← OBRIGATÓRIO
}
# Se não fornecido → Erro 400 Bad Request
```

**Aplicar em TODAS:**
- /query/filter_data
- /query/graph/label/list
- /query/graph/visual
- /query/search
- /query/traverse
- /query/global
- /query/hybrid
- /query/llm
- (todas que consultam dados)

---

### 2️⃣ Insert API - Lógica de create

**Novo comportamento:**

```python
# Cenário 1: Ambos fornecidos (VÁLIDO)
POST /insert {
  "graph_id": "equipment_manuals",
  "create": false
}
# ✅ OK: Usa graph existente ou erro 404

# Cenário 2: graph_id fornecido, create=true (VÁLIDO)
POST /insert {
  "graph_id": "new_graph",
  "create": true
}
# ✅ OK: Cria novo graph + ingere

# Cenário 3: graph_id fornecido, create=false (VÁLIDO)
POST /insert {
  "graph_id": "existing_graph",
  "create": false
}
# ✅ OK: Usa graph existente

# Cenário 4: graph_id NÃO fornecido, create=true (INVÁLIDO)
POST /insert {
  "create": true
  # Sem graph_id
}
# ❌ ERRO 400: "graph_id required when create=true"

# Cenário 5: graph_id NÃO fornecido, create=false (INVÁLIDO)
POST /insert {
  "create": false
  # Sem graph_id
}
# ❌ ERRO 400: "graph_id is required"

# Cenário 6: Só graph_id, sem create (VÁLIDO)
POST /insert {
  "graph_id": "equipment_manuals"
  # create default: false
}
# ✅ OK: Usa graph, erro se não existir
```

---

### 3️⃣ Parâmetro Renomeado

```
create_if_not_exists  →  create
```

---

## Ordem de Implementação

### ✅ Fase 1: GraphManager (Base)
- [ ] Criar `lightrag/graph_manager.py`
- [ ] Endpoints GET/POST/DELETE /graphs
- [ ] Testes

### ✅ Fase 2: Insert API com graph_id
- [ ] Modificar POST /insert
- [ ] Validação de graph_id (obrigatório)
- [ ] Lógica de create flag
- [ ] Testes

### ✅ Fase 3: Queries com graph_id obrigatório
- [ ] Adicionar graph_id OBRIGATÓRIO a TODAS queries
- [ ] Validação
- [ ] Modificar 8+ endpoints
- [ ] Testes

### ✅ Fase 4: WebUI (passar graph_id automaticamente)

### ✅ Fase 5: Export/Import

---

## Começando Agora 🚀

Próximo passo: Implementar Fase 1 (GraphManager)
