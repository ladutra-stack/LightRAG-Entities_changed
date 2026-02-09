"""Graph Manager for handling multiple knowledge graphs."""

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
        """Converter para dicionário"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> GraphMetadata:
        """Criar a partir de dicionário"""
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
                with open(self.config_file, 'r', encoding='utf-8') as f:
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
                with open(metadata_path, 'r', encoding='utf-8') as f:
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
            with open(self.config_file, 'w', encoding='utf-8') as f:
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
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            logger.info(f"Metadata saved for graph {metadata.id}")
        except Exception as e:
            logger.error(f"Error saving metadata for graph {metadata.id}: {e}")
    
    def create_graph(
        self,
        name: str,
        description: str = "",
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
        # Gerar ID se não fornecido (slug baseado no nome)
        if graph_id is None:
            # Criar slug a partir do nome
            slug = name.lower().replace(" ", "_").replace("-", "_")
            slug = "".join(c for c in slug if c.isalnum() or c == "_")[:20]
            # Adicionar timestamp para garantir unicidade
            graph_id = f"{slug}_{int(datetime.now(timezone.utc).timestamp())}"
        
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
        return sorted(list(self._graphs_cache.values()), key=lambda g: g.created_at)
    
    def get_graph(self, graph_id: str) -> Optional[GraphMetadata]:
        """
        Obter metadata de um grafo específico
        
        Args:
            graph_id: ID do grafo
        
        Returns:
            GraphMetadata ou None se não encontrado
        """
        return self._graphs_cache.get(graph_id)
    
    def graph_exists(self, graph_id: str) -> bool:
        """
        Verificar se um grafo existe
        
        Args:
            graph_id: ID do grafo
        
        Returns:
            True se existe, False caso contrário
        """
        return graph_id in self._graphs_cache
    
    def get_default_graph(self) -> Optional[GraphMetadata]:
        """
        Obter o grafo padrão
        
        Returns:
            GraphMetadata do grafo padrão ou None
        """
        if self._default_graph_id:
            return self.get_graph(self._default_graph_id)
        return None
    
    def get_default_graph_id(self) -> Optional[str]:
        """
        Obter o ID do grafo padrão
        
        Returns:
            ID do grafo padrão ou None
        """
        return self._default_graph_id
    
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
    
    def delete_graph(self, graph_id: str, force: bool = False) -> bool:
        """
        Deletar um grafo e todos seus dados
        
        Args:
            graph_id: ID do grafo a deletar
            force: Se True, permite deletar grafo padrão
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        if graph_id not in self._graphs_cache:
            logger.error(f"Graph '{graph_id}' not found")
            return False
        
        # Não permitir deletar grafo padrão sem força
        if not force and graph_id == self._default_graph_id:
            logger.error(f"Cannot delete default graph '{graph_id}' without force=True")
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
        
        # Se era default, mudsar para outro
        if graph_id == self._default_graph_id:
            if self._graphs_cache:
                new_default = list(self._graphs_cache.keys())[0]
                self.set_default_graph(new_default)
            else:
                self._default_graph_id = None
        
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
            **kwargs: Campos a atualizar (name, description, entity_count, etc)
        
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
