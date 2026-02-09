# Proposta: Suporte a Múltiplos Grafos de Conhecimento (Multi-Graph Architecture)

## 1. ARQUITETURA PROPOSTA

### 1.1 Conceito Base: Graph Projects

Ao invés de ter um único grafo global, a aplicação terá múltiplos **"Graph Projects"** independentes:

```
LightRAG (aplicação)
├── Graph Project 1: "EquipmentManuals"
│   ├── KG (Grafo: entidades, relacionamentos)
│   ├── Documentos (PDFs, textos)
│   └── Metadata (nome, descrição, criação)
├── Graph Project 2: "MaintenanceLogs"
│   ├── KG
│   ├── Documentos
│   └── Metadata
└── Graph Project 3: "TechnicalSpecs"
    ├── KG
    ├── Documentos
    └── Metadata
```

### 1.2 Estrutura de Armazenamento

**Atual:** 
```
trabalho_dir/
├── chunk_entity_relation.db
├── entities.db
├── chunks.db
└── ...
```

**Novo:**
```
trabalho_dir/
├── graphs/
│   ├── equipment_manuals/
│   │   ├── chunk_entity_relation.db
│   │   ├── entities.db
│   │   ├── chunks.db
│   │   ├── metadata.json  (nome, descrição, data criação)
│   │   └── documents/  (docs originais)
│   ├── maintenance_logs/
│   │   ├── chunk_entity_relation.db
│   │   ├── entities.db
│   │   ├── chunks.db
│   │   ├── metadata.json
│   │   └── documents/
│   └── technical_specs/
│       ├── ...
├── config.json  (default graph, lista de graphs)
└── ...
```

---

## 2. IMPLEMENTAÇÃO PROPOSTA

### 2.1 Nova Classe: GraphManager

**Arquivo:** `lightrag/graph_manager.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class GraphMetadata:
    """Metadata de um Graph Project"""
    id: str  # Identificador único
    name: str  # Nome exibível
    description: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    entity_count: int = 0
    relation_count: int = 0
    
class GraphManager:
    """Gerencia múltiplos Graph Projects"""
    
    def __init__(self, base_working_dir: str):
        self.base_working_dir = base_working_dir
        self.graphs_dir = f"{base_working_dir}/graphs"
        self._graphs_cache: Dict[str, GraphMetadata] = {}
        self._load_graphs_metadata()
    
    def create_graph(self, graph_id: str, name: str, description: str) -> GraphMetadata:
        """Criar um novo Graph Project"""
        # Validar ID único
        # Criar diretório do grafo
        # Persistir metadata
        # Retornar GraphMetadata
        pass
    
    def list_graphs(self) -> List[GraphMetadata]:
        """Listar todos os graphs disponíveis"""
        return list(self._graphs_cache.values())
    
    def get_graph(self, graph_id: str) -> Optional[GraphMetadata]:
        """Obter metadata de um grafo específico"""
        return self._graphs_cache.get(graph_id)
    
    def delete_graph(self, graph_id: str) -> bool:
        """Deletar um grafo e seus dados"""
        pass
    
    def _load_graphs_metadata(self):
        """Carregar lista de graphs do disco"""
        pass
```

### 2.2 Modificar LightRAG para aceitar graph_id

**Arquivo:** `lightrag/lightrag.py`

```python
class LightRAG:
    def __init__(
        self,
        working_dir: str = "./ragdata",
        llm_model_func: Optional[Callable] = None,
        embedding_func: Optional[EmbeddingFunc] = None,
        graph_id: Optional[str] = None,  # NOVO: ID do grafo
        **kwargs
    ):
        self.graph_id = graph_id or "default"
        self.graph_manager = GraphManager(working_dir)
        
        # Ajustar working_dir para incluir o graph_id
        if graph_id:
            working_dir = f"{working_dir}/graphs/{graph_id}"
        
        # ... resto da inicialização
       
    async def insert_document_to_graph(
        self,
        file_name: str,
        file_path: str,
        graph_id: Optional[str] = None
    ):
        """Ingerir documento a um grafo específico"""
        if graph_id:
            # Verificar se grafo existe
            # Fazer ingestão
            pass
        else:
            # Ingerir ao grafo atual
            await self.insert(file_path)
```

---

## 3. API REST - Novos Endpoints

### 3.1 Gerenciamento de Graphs

**Arquivo:** `lightrag/api/routers/graph_routes.py` (NOVO)

```python
@router.get("/graphs")
async def list_graphs():
    """Listar todos os graphs disponíveis"""
    return {
        "status": "success",
        "graphs": [
            {
                "id": "equipment_manuals",
                "name": "Equipment Manuals",
                "description": "OEM documentation",
                "created_at": "2026-02-01T10:00:00Z",
                "entity_count": 245,
                "relation_count": 1203
            },
            {"id": "maintenance_logs", ...},
        ]
    }

@router.post("/graphs")
async def create_graph(request: CreateGraphRequest):
    """Criar novo graph"""
    # request: {name, description}
    return {
        "status": "success",
        "graph_id": "new_graph_xxx",
        "message": "Graph criado com sucesso"
    }

@router.get("/graphs/{graph_id}")
async def get_graph(graph_id: str):
    """Obter detalhes de um graph específico"""
    return {
        "id": "equipment_manuals",
        "name": "Equipment Manuals",
        "statistics": {...}
    }

@router.delete("/graphs/{graph_id}")
async def delete_graph(graph_id: str):
    """Deletar um graph"""
    return {"status": "success"}
```

### 3.2 Ingestão Multi-Graph

**Modificar:** `lightrag/api/routers/doc_routes.py`

```python
@router.post("/insert")
async def insert_documents(
    files: List[UploadFile],
    graph_id: Optional[str] = Query(None),  # NOVO parâmetro
    doc_id: Optional[str] = Query(None),
):
    """Ingerir documentos a um grafo específico"""
    if graph_id:
        # Ingerir ao graph_id fornecido
        response = await rag.insert_to_graph(
            files,
            graph_id=graph_id
        )
    else:
        # Usar grafo padrão ou atual
        response = await rag.insert(...)
    
    return response
```

### 3.3 Query Multi-Graph

**Modificar:** `lightrag/api/routers/query_routes.py`

```python
@router.post("/query/filter_data")
async def filter_query_data(request: FilterDataRequest):
    """
    Filter data com suporte a múltiplos graphs
    
    Novo parâmetro no request:
    - graph_id: string (opcional - usa padrão se não fornecido)
    """
    # Se graph_id fornecido, usar esse grafo
    # Senão, usar grafo padrão/atual
    
    # Toda a lógica permanece igual
    return response
```

---

## 4. INTERFACE WEB (WebUI)

### 4.1 Novo Componente: GraphSelector

**Arquivo:** `lightrag_webui/src/components/GraphSelector.tsx`

```typescript
import React, { useState, useEffect } from 'react';

interface Graph {
  id: string;
  name: string;
  description: string;
  entity_count: number;
}

const GraphSelector: React.FC = () => {
  const [graphs, setGraphs] = useState<Graph[]>([]);
  const [selectedGraphId, setSelectedGraphId] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchGraphs();
  }, []);

  const fetchGraphs = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/graphs');
      const data = await response.json();
      setGraphs(data.graphs);
      if (data.graphs.length > 0) {
        setSelectedGraphId(data.graphs[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="font-bold mb-3">Knowledge Graphs</h3>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <select
          value={selectedGraphId}
          onChange={(e) => setSelectedGraphId(e.target.value)}
          className="w-full p-2 border rounded"
        >
          {graphs.map(g => (
            <option key={g.id} value={g.id}>
              {g.name} ({g.entity_count} entities)
            </option>
          ))}
        </select>
      )}
      
      {/* Botão para criar novo graph */}
      <button
        className="mt-3 w-full bg-blue-500 text-white p-2 rounded"
        onClick={() => {/* Modal para criar novo */}}
      >
        + New Graph
      </button>
    </div>
  );
};

export default GraphSelector;
```

### 4.2 Integração no Layout Principal

**Modificar:** `lightrag_webui/src/App.tsx`

```typescript
const App: React.FC = () => {
  const [selectedGraphId, setSelectedGraphId] = useState<string>('');

  return (
    <div className="flex">
      {/* Sidebar com Graph Selector */}
      <aside className="w-1/4 bg-gray-100 p-4">
        <GraphSelector 
          onSelectGraph={setSelectedGraphId}
          currentGraphId={selectedGraphId}
        />
      </aside>

      {/* Main content - atualiza quando graph muda */}
      <main className="w-3/4">
        <QueryPanel graphId={selectedGraphId} />
        <VisualizationPanel graphId={selectedGraphId} />
        <InsertDocumentsPanel graphId={selectedGraphId} />
      </main>
    </div>
  );
};
```

---

## 5. FLUXO DE USO

### 5.1 Criar novo Graph

```
1. User clica em "Create New Graph"
2. Modal aparece: {name, description}
3. POST /graphs → Retorna graph_id
4. Graph aparece na lista e é selecionado
```

### 5.2 Ingerir documento

```
1. User seleciona um graph no selector
2. User faz upload de arquivo
3. POST /insert?graph_id=equipment_manuals
4. Documento é ingerido apenas ao grafo selecionado
```

### 5.3 Fazer query

```
1. User seleciona um graph
2. User escreve query na caixa de busca
3. POST /query/filter_data {query, graph_id: "equipment_manuals", ...}
4. Resultados aparecem (apenas do grafo selecionado)
```

---

## 6. DADOS PERSISTIDOS

### 6.1 Arquivo: `config.json`

```json
{
  "default_graph": "equipment_manuals",
  "graphs": [
    {
      "id": "equipment_manuals",
      "name": "Equipment Manuals",
      "description": "OEM documentation",
      "created_at": "2026-02-01T10:00:00Z"
    },
    {
      "id": "maintenance_logs",
      "name": "Maintenance Logs",
      "created_at": "2026-02-05T08:30:00Z"
    }
  ]
}
```

---

## 7. BENEFÍCIOS

✅ **Isolamento de dados:** Cada graph é independente  
✅ **Escalabilidade:** Pode ter N graphs sem impacto  
✅ **Flexibilidade:** User controla quais dados ver  
✅ **Reutilização:** Mesma infra, múltiplos contextos  
✅ **Backward compatible:** Graph "default" funciona como antes  

---

## 8. ROADMAP DE IMPLEMENTAÇÃO

**Fase 1 (Semana 1):**
- [ ] Implementar GraphManager
- [ ] Modificar LightRAG para aceitar graph_id
- [ ] Criar endpoints /graphs, /graphs/{id}

**Fase 2 (Semana 2):**
- [ ] Modificar inserção de documentos para suportar graph_id
- [ ] Modificar queries para suportar graph_id
- [ ] Testes unitários

**Fase 3 (Semana 3):**
- [ ] Criar interface GraphSelector
- [ ] Integrar ao layout principal
- [ ] Testes E2E

**Fase 4 (Semana 4):**
- [ ] Otimizações
- [ ] Documentação
- [ ] Deploy

---

## 9. PERGUNTAS PARA REFINAMENTO

1. ✅ Suportar compartilhamento de dados entre graphs?
2. ✅ Histórico/versionamento de documents?
3. ✅ Permissões/controle de acesso por graph?
4. ✅ Export/Import de graphs?
5. ✅ Sincronização em tempo real entre múltiplas instâncias?

---

**Esse é o primeiro passo.** Gostaria que eu começasse por qual fase?
