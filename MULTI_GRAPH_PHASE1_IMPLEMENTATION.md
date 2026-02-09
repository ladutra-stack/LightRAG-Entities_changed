# Plano de Implementação - Fase 1: Graph Manager

## Objetivo
Implementar a estrutura base para gerenciar múltiplos grafos, permitindo criar, listar e acessar grafos específicos.

---

## 1. ESTRUTURA DE ARQUIVOS A CRIAR

### Novo arquivo: `lightrag/graph_manager.py`

```python
from __future__ import annotations

import os
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path
from lightrag.utils import logger


@dataclass
class GraphMetadata:
    """Metadata de um Graph Project"""
    id: str                    # Identificador único (UUID)
    name: str                  # Nome exibível
    description: str           # Descrição
    created_at: str            # ISO 8601 format
    updated_at: str            # ISO 8601 format
    document_count: int = 0
    entity_count: int = 0
    relation_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> GraphMetadata:
        return cls(**data)


class GraphManager:
    """Gerencia múltiplos Graph Projects"""
    
    GRAPHS_DIR = "graphs"
    CONFIG_FILE = "graphs_config.json"
    METADATA_FILE = "metadata.json"
    
    def __init__(self, base_working_dir: str):
        """
        Inicializa o GraphManager
        
        Args:
            base_working_dir: Diretório raiz onde os graphs serão armazenados
        """
        self.base_working_dir = Path(base_working_dir)
        self.graphs_dir = self.base_working_dir / self.GRAPHS_DIR
        self.config_file = self.base_working_dir / self.CONFIG_FILE
        
        # Criar diretórios se não existirem
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache de metadatas
        self._graphs_cache: Dict[str, GraphMetadata] = {}
        self._default_graph_id: Optional[str] = None
        
        # Carregar dados persistidos
        self._load_configuration()
    
    def _load_configuration(self):
        """Carregar configuração e metadata dos graphs"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self._default_graph_id = config.get("default_graph")
                    
                    # Carregar metadata de cada graph
                    for graph_id in config.get("graphs", []):
                        metadata = self._load_graph_metadata(graph_id)
                        if metadata:
                            self._graphs_cache[graph_id] = metadata
                        else:
                            logger.warning(f"Graph {graph_id} metadata not found")
                
                logger.info(f"Loaded {len(self._graphs_cache)} graphs from config")
            except Exception as e:
                logger.error(f"Error loading graphs configuration: {e}")
                self._initialize_default_graph()
        else:
            self._initialize_default_graph()
    
    def _initialize_default_graph(self):
        """Criar um graph padrão se nenhum existir"""
        if not self._graphs_cache:
            logger.info("No graphs found, creating default graph")
            self.create_graph("default", "Default Graph", "Default knowledge graph")
            self._default_graph_id = "default"
    
    def _load_graph_metadata(self, graph_id: str) -> Optional[GraphMetadata]:
        """Carregar metadata de um graph específico"""
        metadata_path = self.graphs_dir / graph_id / self.METADATA_FILE
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    return GraphMetadata.from_dict(data)
            except Exception as e:
                logger.error(f"Error loading metadata for graph {graph_id}: {e}")
        
        return None
    
    def _save_configuration(self):
        """Persistir configuração de graphs"""
        config = {
            "default_graph": self._default_graph_id or "default",
            "graphs": list(self._graphs_cache.keys())
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Graphs configuration saved")
        except Exception as e:
            logger.error(f"Error saving graphs configuration: {e}")
    
    def _save_graph_metadata(self, metadata: GraphMetadata):
        """Persistir metadata de um graph"""
        graph_dir = self.graphs_dir / metadata.id
        graph_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_path = graph_dir / self.METADATA_FILE
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            logger.info(f"Metadata saved for graph {metadata.id}")
        except Exception as e:
            logger.error(f"Error saving metadata for graph {metadata.id}: {e}")
    
    def create_graph(
        self,
        name: str,
        description: str,
        graph_id: Optional[str] = None
    ) -> GraphMetadata:
        """
        Criar um novo Graph Project
        
        Args:
            name: Nome do grafo (exibível)
            description: Descrição do grafo
            graph_id: ID do grafo (opcional, gerado automaticamente se não fornecido)
        
        Returns:
            GraphMetadata do novo grafo
        
        Raises:
            ValueError: Se graph_id já existe
        """
        # Gerar ID se não fornecido
        graph_id = graph_id or str(uuid.uuid4())[:8]
        
        # Validar unicidade
        if graph_id in self._graphs_cache:
            raise ValueError(f"Graph with ID '{graph_id}' already exists")
        
        # Criar metadata
        now = datetime.now(timezone.utc).isoformat()
        metadata = GraphMetadata(
            id=graph_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            document_count=0,
            entity_count=0,
            relation_count=0
        )
        
        # Criar diretório do grafo
        graph_dir = self.graphs_dir / graph_id
        graph_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar subdiretórios
        (graph_dir / "documents").mkdir(exist_ok=True)
        
        # Salvar metadata
        self._save_graph_metadata(metadata)
        
        # Atualizar cache
        self._graphs_cache[graph_id] = metadata
        
        # Salvar configuração
        self._save_configuration()
        
        logger.info(f"Created graph '{name}' with ID '{graph_id}'")
        
        return metadata
    
    def list_graphs(self) -> List[GraphMetadata]:
        """
        Listar todos os grafos disponíveis
        
        Returns:
            Lista de GraphMetadata
        """
        return list(self._graphs_cache.values())
    
    def get_graph(self, graph_id: str) -> Optional[GraphMetadata]:
        """
        Obter metadata de um grafo específico
        
        Args:
            graph_id: ID do grafo
        
        Returns:
            GraphMetadata ou None se não encontrado
        """
        return self._graphs_cache.get(graph_id)
    
    def get_default_graph(self) -> Optional[GraphMetadata]:
        """
        Obter o grafo padrão
        
        Returns:
            GraphMetadata do grafo padrão ou None
        """
        if self._default_graph_id:
            return self.get_graph(self._default_graph_id)
        return None
    
    def set_default_graph(self, graph_id: str) -> bool:
        """
        Definir o grafo padrão
        
        Args:
            graph_id: ID do grafo a ser definido como padrão
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        if graph_id not in self._graphs_cache:
            logger.error(f"Graph '{graph_id}' not found")
            return False
        
        self._default_graph_id = graph_id
        self._save_configuration()
        logger.info(f"Set default graph to '{graph_id}'")
        return True
    
    def delete_graph(self, graph_id: str) -> bool:
        """
        Deletar um grafo e todos seus dados
        
        Args:
            graph_id: ID do grafo a deletar
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        if graph_id not in self._graphs_cache:
            logger.error(f"Graph '{graph_id}' not found")
            return False
        
        # Não permitir deletar grafo padrão
        if graph_id == self._default_graph_id:
            logger.error(f"Cannot delete default graph '{graph_id}'")
            return False
        
        # Deletar diretório do grafo
        graph_dir = self.graphs_dir / graph_id
        try:
            import shutil
            shutil.rmtree(graph_dir)
            logger.info(f"Deleted graph directory '{graph_dir}'")
        except Exception as e:
            logger.error(f"Error deleting graph directory: {e}")
            return False
        
        # Remover do cache
        del self._graphs_cache[graph_id]
        
        # Salvar configuração
        self._save_configuration()
        
        logger.info(f"Deleted graph '{graph_id}'")
        
        return True
    
    def update_graph_metadata(
        self,
        graph_id: str,
        **kwargs
    ) -> Optional[GraphMetadata]:
        """
        Atualizar metadata de um grafo
        
        Args:
            graph_id: ID do grafo
            **kwargs: Campos a atualizar (name, description, etc)
        
        Returns:
            GraphMetadata atualizado ou None se erro
        """
        metadata = self.get_graph(graph_id)
        if not metadata:
            logger.error(f"Graph '{graph_id}' not found")
            return None
        
        # Atualizar campos
        for key, value in kwargs.items():
            if hasattr(metadata, key) and key not in ['id', 'created_at']:
                setattr(metadata, key, value)
        
        # Atualizar timestamp
        metadata.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Salvar
        self._save_graph_metadata(metadata)
        self._graphs_cache[graph_id] = metadata
        self._save_configuration()
        
        logger.info(f"Updated metadata for graph '{graph_id}'")
        
        return metadata
    
    def get_graph_working_dir(self, graph_id: str) -> Optional[Path]:
        """
        Obter o diretório de trabalho de um grafo
        
        Args:
            graph_id: ID do grafo
        
        Returns:
            Path do diretório do grafo ou None se não encontrado
        """
        if graph_id not in self._graphs_cache:
            return None
        
        return self.graphs_dir / graph_id
```

---

## 2. MODIFICAÇÕES EM `lightrag/lightrag.py`

### 2.1 Adicionar import

```python
from lightrag.graph_manager import GraphManager
```

### 2.2 Modificar `__init__`

```python
def __init__(
    self,
    working_dir: str = "./ragdata",
    llm_model_func: Optional[Callable] = None,
    embedding_func: Optional[EmbeddingFunc] = None,
    graph_id: Optional[str] = None,  # NOVO
    **kwargs
):
    """
    Args:
        working_dir: Diretório raiz de trabalho
        llm_model_func: Função para chamar o LLM
        embedding_func: Função para gerar embeddings
        graph_id: ID do grafo a usar (se None, usa default ou cria um novo)
        **kwargs: Argumentos adicionais
    """
    
    # Inicializar GraphManager
    self.graph_manager = GraphManager(working_dir)
    
    # Resolver graph_id
    if graph_id is None:
        default_graph = self.graph_manager.get_default_graph()
        if default_graph:
            graph_id = default_graph.id
        else:
            graph_id = "default"
            self.graph_manager.create_graph("Default", "Default knowledge graph")
    
    self.graph_id = graph_id
    graph_metadata = self.graph_manager.get_graph(graph_id)
    
    if not graph_metadata:
        raise ValueError(f"Graph '{graph_id}' not found")
    
    # Ajustar working_dir para incluir o graph_id
    graph_working_dir = str(self.graph_manager.get_graph_working_dir(graph_id))
    
    # Continuar com inicialização normal usando graph_working_dir
    # ... resto do __init__
```

---

## 3. NOVOS ENDPOINTS: `lightrag/api/routers/graph_routes.py`

```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from lightrag.utils import logger


class CreateGraphRequest(BaseModel):
    name: str = Field(..., description="Nome do grafo")
    description: str = Field(default="", description="Descrição do grafo")


class UpdateGraphRequest(BaseModel):
    name: Optional[str] = Field(None, description="Novo nome")
    description: Optional[str] = Field(None, description="Nova descrição")


def create_graph_routes(graph_manager):
    router = APIRouter(tags=["graphs"])

    @router.get("/graphs", response_model=Dict[str, Any])
    async def list_graphs():
        """Listar todos os grafos disponíveis"""
        try:
            graphs = graph_manager.list_graphs()
            return {
                "status": "success",
                "graphs": [
                    {
                        "id": g.id,
                        "name": g.name,
                        "description": g.description,
                        "created_at": g.created_at,
                        "updated_at": g.updated_at,
                        "document_count": g.document_count,
                        "entity_count": g.entity_count,
                        "relation_count": g.relation_count,
                    }
                    for g in graphs
                ]
            }
        except Exception as e:
            logger.error(f"Error listing graphs: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/graphs", response_model=Dict[str, Any])
    async def create_graph(request: CreateGraphRequest):
        """Criar novo grafo"""
        try:
            metadata = graph_manager.create_graph(
                name=request.name,
                description=request.description
            )
            return {
                "status": "success",
                "message": f"Graph '{request.name}' created successfully",
                "graph": {
                    "id": metadata.id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "created_at": metadata.created_at,
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating graph: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/graphs/{graph_id}", response_model=Dict[str, Any])
    async def get_graph(graph_id: str):
        """Obter detalhes de um grafo específico"""
        try:
            metadata = graph_manager.get_graph(graph_id)
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")
            
            return {
                "status": "success",
                "graph": {
                    "id": metadata.id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "created_at": metadata.created_at,
                    "updated_at": metadata.updated_at,
                    "document_count": metadata.document_count,
                    "entity_count": metadata.entity_count,
                    "relation_count": metadata.relation_count,
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting graph: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/graphs/{graph_id}", response_model=Dict[str, Any])
    async def delete_graph(graph_id: str):
        """Deletar um grafo"""
        try:
            success = graph_manager.delete_graph(graph_id)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to delete graph '{graph_id}'")
            
            return {
                "status": "success",
                "message": f"Graph '{graph_id}' deleted successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting graph: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.put("/graphs/{graph_id}", response_model=Dict[str, Any])
    async def update_graph(graph_id: str, request: UpdateGraphRequest):
        """Atualizar um grafo"""
        try:
            updates = {k: v for k, v in request.dict().items() if v is not None}
            metadata = graph_manager.update_graph_metadata(graph_id, **updates)
            
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")
            
            return {
                "status": "success",
                "message": f"Graph '{graph_id}' updated successfully",
                "graph": {
                    "id": metadata.id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "updated_at": metadata.updated_at,
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating graph: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
```

---

## 4. TESTES UNITÁRIOS

### Arquivo: `tests/test_graph_manager.py`

```python
import pytest
import tempfile
from pathlib import Path
from lightrag.graph_manager import GraphManager, GraphMetadata


@pytest.fixture
def temp_dir():
    """Criar diretório temporário para testes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_create_graph(temp_dir):
    """Teste criação de um grafo"""
    manager = GraphManager(temp_dir)
    
    metadata = manager.create_graph(
        name="Test Graph",
        description="A test graph"
    )
    
    assert metadata.name == "Test Graph"
    assert metadata.id in manager._graphs_cache


def test_list_graphs(temp_dir):
    """Teste listagem de grafos"""
    manager = GraphManager(temp_dir)
    manager.create_graph("Graph 1", "Test 1")
    manager.create_graph("Graph 2", "Test 2")
    
    graphs = manager.list_graphs()
    assert len(graphs) >= 2  # default + 2 created


def test_get_graph(temp_dir):
    """Teste obtenção de um grafo"""
    manager = GraphManager(temp_dir)
    metadata = manager.create_graph("Test", "Description")
    
    retrieved = manager.get_graph(metadata.id)
    assert retrieved is not None
    assert retrieved.id == metadata.id


def test_delete_graph(temp_dir):
    """Teste deletação de um grafo"""
    manager = GraphManager(temp_dir)
    metadata = manager.create_graph("Test", "Description")
    
    # Não pode deletar grafo padrão
    assert not manager.delete_graph("default")
    
    # Pode deletar grafo normal
    assert manager.delete_graph(metadata.id)
    assert manager.get_graph(metadata.id) is None


def test_default_graph(temp_dir):
    """Teste grafo padrão"""
    manager = GraphManager(temp_dir)
    
    default = manager.get_default_graph()
    assert default is not None
    assert default.id == "default"
```

---

## 5. MODIFICAR `lightrag_server.py` PARA INCLUIR ROTAS

```python
from lightrag.api.routers.graph_routes import create_graph_routes

# ... resto do código

def create_app(rag, api_key: Optional[str] = None, top_k: int = 60):
    app = FastAPI(...)
    
    # Incluir rotas de graphs
    graph_routes = create_graph_routes(rag.graph_manager)
    app.include_router(graph_routes)
    
    # ... resto das rotas
```

---

## 6. CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Criar `lightrag/graph_manager.py` com `GraphManager` e `GraphMetadata`
- [ ] Modificar `lightrag/lightrag.py` para integrar `GraphManager`
- [ ] Criar `lightrag/api/routers/graph_routes.py` com endpoints
- [ ] Integrar rotas em `lightrag_server.py`
- [ ] Criar testes unitários em `tests/test_graph_manager.py`
- [ ] Testar APIs manualmente com curl/Postman
- [ ] Verificar persistência de dados no disco
- [ ] Documentar em `MULTI_GRAPH_IMPLEMENTATION.md`

---

## 7. PRÓXIMOS PASSOS (Fase 2)

- [ ] Modificar endpoint `/insert` para aceitar `graph_id`
- [ ] Modificar endpoint `/query` para aceitar `graph_id`
- [ ] Testes de integração end-to-end
