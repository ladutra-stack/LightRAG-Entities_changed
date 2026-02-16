#!/usr/bin/env python3
\"\"\"
Example: Using filter_entities in filter_data queries

This demonstrates the new simplified filter_entities parameter
instead of the previous complex filter_config dictionary.
\"\"\"

import asyncio
from lightrag import LightRAG
from lightrag.base import QueryParam

# =============================================================================
# EXAMPLE 1: Simple entity filtering
# =============================================================================
async def example_simple_filter():
    \"\"\"Filter chunks by a list of specific entity IDs.\"\"\"
    rag = LightRAG(working_dir=\"./rag_storage\")
    await rag.initialize_storages()
    
    try:
        # Define which entities to include
        entity_ids = [\"impeller_main\", \"pump_secondary\", \"compressor_01\"]
        
        result = rag.filter_data(
            query=\"What is the operational function?\",
            filter_entities=entity_ids,
            param=QueryParam(top_k=5, enable_rerank=True)
        )
        
        print(f\"Status: {result['status']}\")
        print(f\"Entities found: {result['metadata']['entities_found']}\")
        print(f\"Entities after filter: {result['metadata']['entities_after_filter']}\")
        print(f\"Chunks returned: {len(result['chunks'])}\")
        
        for i, chunk in enumerate(result['chunks'], 1):
            print(f\"\\n{i}. [{chunk['source_entity']}] Score: {chunk['similarity_score']:.3f}\")
            print(f\"   {chunk['content'][:100]}...\")
            
    finally:
        await rag.finalize_storages()


# =============================================================================
# EXAMPLE 2: Async version with multiple queries
# =============================================================================
async def example_async_filter():
    \"\"\"Use afilter_data for asynchronous filtering.\"\"\"
    rag = LightRAG(working_dir=\"./rag_storage\")
    await rag.initialize_storages()
    
    try:
        entity_ids = [\"component_a\", \"component_b\"]
        
        result = await rag.afilter_data(
            query=\"performance specifications\",
            filter_entities=entity_ids
        )
        
        print(f\"Async result status: {result['status']}\")
        print(f\"Chunks: {result['metadata']['chunks_returned']}\")
        
        return result
        
    finally:
        await rag.finalize_storages()


# =============================================================================
# EXAMPLE 3: No filter (all entities)
# =============================================================================
async def example_no_filter():
    \"\"\"Query all entities without filtering.\"\"\"
    rag = LightRAG(working_dir=\"./rag_storage\")
    await rag.initialize_storages()
    
    try:
        result = rag.filter_data(
            query=\"Find relevant information\",
            filter_entities=None,  # None = all entities
            param=QueryParam(top_k=10)
        )
        
        print(f\"Total entities in graph: {result['metadata']['entities_found']}\")
        print(f\"Entities included: {result['metadata']['entities_after_filter']}\")
        
        return result
        
    finally:
        await rag.finalize_storages()


# =============================================================================
# EXAMPLE 4: Retrieving chunks without semantic search
# =============================================================================
async def example_chunks_only():
    \"\"\"Get chunks from specific entities without semantic ranking.\"\"\"
    rag = LightRAG(working_dir=\"./rag_storage\")
    await rag.initialize_storages()
    
    try:
        entity_list = [\"entity_x\", \"entity_y\"]
        
        result = rag.filter_data(
            query=\"\",  # Empty query = no semantic search
            filter_entities=entity_list
        )
        
        # All chunks have similarity_score = 0.0
        for chunk in result['chunks']:
            print(f\"Chunk from {chunk['source_entity']}:\")
            print(f\"  {chunk['content'][:150]}...\")
            print(f\"  Similarity: {chunk['similarity_score']}\")
        
        return result
        
    finally:
        await rag.finalize_storages()


# =============================================================================
# EXAMPLE 5: API Integration (FastAPI)
# =============================================================================
# Example HTTP request for FastAPI endpoint:
\"\"\"
POST /filter_data
Content-Type: application/json

{
    \"query\": \"operational parameters\",
    \"filter_entities\": [\"entity_1\", \"entity_2\", \"entity_3\"],
    \"top_k\": 5,
    \"chunk_top_k\": 10,
    \"enable_rerank\": true,
    \"max_total_tokens\": 30000
}

Response:
{
    \"status\": \"success\",
    \"message\": \"Retrieved 5 filtered chunks\",
    \"chunks\": [
        {
            \"chunk_id\": \"chunk-123\",
            \"content\": \"...\",
            \"file_path\": \"doc.pdf\",
            \"similarity_score\": 0.85,
            \"source_entity\": \"entity_1\",
            \"rank\": 1
        },
        ...
    ],
    \"metadata\": {
        \"query\": \"operational parameters\",
        \"filters_applied\": [\"entity_1\", \"entity_2\", \"entity_3\"],
        \"entities_found\": 100,
        \"entities_after_filter\": 3,
        \"total_chunks_before_filter\": 250,
        \"total_chunks_after_filter\": 15,
        \"chunks_returned\": 5,
        \"reranking_applied\": true,
        \"semantic_search_applied\": true
    }
}
\"\"\"


# =============================================================================
# MAIN
# =============================================================================
if __name__ == \"__main__\":
    print(\"Filter Entities Examples\")\n    print(\"=\"*50)\n    print()\n    print(\"Note: These examples require:\")\n    print(\"  1. A configured LightRAG instance\")\n    print(\"  2. Data already inserted into the knowledge graph\")\n    print(\"  3. Proper LLM and embedding model configuration\")\n    print()\n    print(\"To run individual examples, uncomment them below:\")\n    print()\n    \n    # Uncomment to run examples:\n    # asyncio.run(example_simple_filter())\n    # asyncio.run(example_async_filter())\n    # asyncio.run(example_no_filter())\n    # asyncio.run(example_chunks_only())\n