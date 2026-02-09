"""RAG Pool for managing multiple per-graph RAG instances.

This module provides utilities for managing a pool of LightRAG instances,
one for each knowledge graph in the multi-graph system.

Phase 4 (LightRAG Integration): Enables actual data isolation between graphs
by using separate RAG instances with graph-specific working directories.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Dict, Optional, Any
from lightrag import LightRAG
from lightrag.graph_manager import GraphManager
from lightrag.utils import logger


class RAGPool:
    """
    Manages a pool of LightRAG instances for multi-graph support.
    
    Each graph gets its own RAG instance with isolated working directories,
    storage backends, and data.
    
    Phase 4 Implementation:
    - Creates per-graph RAG instances on-demand
    - Caches instances for reuse
    - Handles lifecycle management (initialization, finalization)
    """
    
    def __init__(
        self,
        base_rag_config: Dict[str, Any],
        graph_manager: GraphManager,
    ):
        """
        Initialize RAG Pool.
        
        Args:
            base_rag_config: Base configuration dict for LightRAG instances.
                            Must NOT include 'working_dir', 'graph_id', or 'graph_manager'.
            graph_manager: GraphManager instance for graph lifecycle management
        """
        self.base_rag_config = base_rag_config
        self.graph_manager = graph_manager
        self._rag_instances: Dict[str, LightRAG] = {}
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()  # For thread-safe sync access
        
        logger.info("RAGPool initialized")
    
    async def get_or_create_rag(self, graph_id: str) -> LightRAG:
        """
        Get or create a RAG instance for the specified graph.
        
        If the instance already exists in the pool, return it.
        Otherwise, create a new instance with graph-specific configuration.
        
        Args:
            graph_id: ID of the graph
            
        Returns:
            LightRAG instance for the graph
            
        Raises:
            ValueError: If graph_id is invalid or graph not found
        """
        # Validate graph_id
        if not graph_id or not graph_id.strip():
            raise ValueError("graph_id cannot be empty or whitespace-only")
        
        graph_id = graph_id.strip()
        
        # Return cached instance if available
        if graph_id in self._rag_instances:
            logger.debug(f"Returning cached RAG instance for graph '{graph_id}'")
            return self._rag_instances[graph_id]
        
        # Thread-safe instance creation
        async with self._async_lock:
            # Double-check pattern to avoid race conditions
            if graph_id in self._rag_instances:
                return self._rag_instances[graph_id]
            
            logger.info(f"Creating new RAG instance for graph '{graph_id}'")
            
            # Create new RAG instance with graph-specific context
            rag = LightRAG(
                **self.base_rag_config,
                graph_id=graph_id,
                graph_manager=self.graph_manager,
            )
            
            # Cache the instance
            self._rag_instances[graph_id] = rag
            logger.info(f"RAG instance created and cached for graph '{graph_id}'")
            
            return rag
    
    def get_rag_sync(self, graph_id: str) -> LightRAG:
        """
        Synchronous wrapper for getting RAG instance (when async not available).
        
        WARNING: This method is thread-safe but not fully async-safe.
        Use only in synchronous contexts (background tasks, etc.)
        
        Args:
            graph_id: ID of the graph
            
        Returns:
            LightRAG instance for the graph
            
        Raises:
            ValueError: If graph_id is invalid or empty
        """
        # Validate graph_id
        if not graph_id or not graph_id.strip():
            raise ValueError("graph_id cannot be empty or whitespace-only")
        
        graph_id = graph_id.strip()
        
        if graph_id in self._rag_instances:
            return self._rag_instances[graph_id]
        
        # Thread-safe sync context using threading.Lock
        with self._sync_lock:
            # Double-check pattern
            if graph_id in self._rag_instances:
                return self._rag_instances[graph_id]
            
            logger.info(f"Creating new RAG instance (sync) for graph '{graph_id}'")
            
            # Create new RAG instance with graph-specific context
            rag = LightRAG(
                **self.base_rag_config,
                graph_id=graph_id,
                graph_manager=self.graph_manager,
            )
            self._rag_instances[graph_id] = rag
            logger.info(f"RAG instance created and cached (sync) for graph '{graph_id}'")
            return rag
    
    async def initialize_all_storages(self):
        """Initialize storages for all cached RAG instances."""
        for graph_id, rag in self._rag_instances.items():
            try:
                await rag.initialize_storages()
                logger.info(f"Storages initialized for graph '{graph_id}'")
            except Exception as e:
                logger.error(f"Failed to initialize storages for graph '{graph_id}': {e}")
                raise
    
    async def finalize_all_storages(self):
        """Finalize storages for all cached RAG instances."""
        for graph_id, rag in self._rag_instances.items():
            try:
                await rag.finalize_storages()
                logger.info(f"Storages finalized for graph '{graph_id}'")
            except Exception as e:
                logger.error(f"Failed to finalize storages for graph '{graph_id}': {e}")
    
    def clear_cache(self):
        """Clear all cached RAG instances."""
        self._rag_instances.clear()
        logger.info("RAG pool cache cleared")
    
    def list_cached_graphs(self) -> list[str]:
        """Get list of graphs with cached RAG instances."""
        return list(self._rag_instances.keys())
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG pool."""
        return {
            "total_graphs": len(self.graph_manager.list_graphs()),
            "cached_instances": len(self._rag_instances),
            "cached_graph_ids": self.list_cached_graphs(),
        }
