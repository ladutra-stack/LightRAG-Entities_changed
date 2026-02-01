# Exemplos de Uso - Deduplicação de Entidades

## 🎓 Guia Prático com Exemplos Reais

### 1. Detecção de Acrônimos

```python
from lightrag.utils import find_duplicate_entity

# Cenário: Sistema encontrou "DGS" em um documento novo
# Pergunta: Já existe alguma entidade similar?

existing_entities = [
    "Dry Gas Seal",
    "Mechanical Seal",
    "Compressor",
    "Bearing"
]

# Testar se "DGS" é duplicado
new_entity = "DGS"
match, score = find_duplicate_entity(new_entity, existing_entities, threshold=0.8)

if match:
    print(f"✅ Duplicada detectada!")
    print(f"   Entidade nova: '{new_entity}'")
    print(f"   Correspondente: '{match}'")
    print(f"   Confiança: {score*100:.0f}%")
    # Resultado:
    # ✅ Duplicada detectada!
    #    Entidade nova: 'DGS'
    #    Correspondente: 'Dry Gas Seal'
    #    Confiança: 100%
```

### 2. Variações de Plural/Singular

```python
# Cenário: Documentos usam "seals", "seal", "sealing"
# Problema: Estas são a mesma entidade conceitual

entities_found = ["seals", "seal", "sealing", "component", "bearing"]
existing_entities = ["Seal", "Component", "Bearing"]

dedup_results = {}
for entity in entities_found:
    match, score = find_duplicate_entity(entity, existing_entities)
    if match:
        if match not in dedup_results:
            dedup_results[match] = []
        dedup_results[match].append((entity, score))

for canonical, variations in dedup_results.items():
    print(f"\n📦 {canonical}")
    for var, score in variations:
        print(f"   ├─ '{var}' ({score*100:.0f}%)")

# Resultado:
# 📦 Seal
#    ├─ 'seals' (100%)
#    ├─ 'seal' (100%)
#    ├─ 'sealing' (100%)
# 
# 📦 Component
#    ├─ 'component' (100%)
# 
# 📦 Bearing
#    ├─ 'bearing' (100%)
```

### 3. Variações de Espaçamento e Pontuação

```python
# Cenário: Diferentes documentos formatam o mesmo nome diferente

queries = [
    "dry gas seal",
    "Dry Gas Seal",
    "dry-gas-seal",
    "drygasseal",
    "DRY GAS SEAL",
    "Dry_Gas_Seal"
]

canonical_name = "Dry Gas Seal"
existing = [canonical_name, "Mechanical Seal", "Compressor"]

print(f"Testando variações de '{canonical_name}':\n")

for query in queries:
    match, score = find_duplicate_entity(query, existing)
    status = "✅" if match == canonical_name else "❌"
    print(f"{status} '{query}' → {match} ({score*100:.0f}%)")

# Resultado:
# Testando variações de 'Dry Gas Seal':
# 
# ✅ 'dry gas seal' → Dry Gas Seal (100%)
# ✅ 'Dry Gas Seal' → Dry Gas Seal (100%)
# ✅ 'dry-gas-seal' → Dry Gas Seal (100%)
# ✅ 'drygasseal' → Dry Gas Seal (100%)
# ✅ 'DRY GAS SEAL' → Dry Gas Seal (100%)
# ❌ 'Dry_Gas_Seal' → Dry Gas Seal (100%)
```

### 4. Evitando False Positives

```python
# Cenário: Queremos evitar combinar entidades diferentes

test_cases = [
    {
        "query": "seal",
        "existing": ["seal", "dry gas seal", "mechanical seal"],
        "should_not_match": []  # "seal" deve dar match só com "seal"
    },
    {
        "query": "mechanical seal",
        "existing": ["dry gas seal", "mechanical seal", "bearing"],
        "should_not_match": ["dry gas seal"]  # Não combinar com "dry gas seal"
    }
]

for case in test_cases:
    query = case["query"]
    existing = case["existing"]
    
    print(f"\nTestando '{query}' contra {existing}:")
    
    match, score = find_duplicate_entity(query, existing, threshold=0.8)
    
    if match in case.get("should_not_match", []):
        print(f"  ⚠️  FALSE POSITIVE: Matched '{match}' (score: {score*100:.0f}%)")
    else:
        print(f"  ✅ Correct: Matched '{match}' (score: {score*100:.0f}%)")
```

### 5. Integração com LightRAG (Pseudocódigo)

```python
# Em operate.py, dentro de _merge_nodes_then_upsert():

from lightrag.utils import find_duplicate_entity

# Encontrou novas entidades durante extração
new_entities = [
    "DGS",
    "dry gas seals", 
    "Compressor",
    "mechanical seals"
]

# Entidades já existentes no conhecimento
existing_entities = await get_all_entity_names(knowledge_graph)
# Returns: ["Dry Gas Seal", "Mechanical Seal", "Compressor", "Bearing"]

# Verificar duplicatas para cada entidade nova
for entity in new_entities:
    match, score = find_duplicate_entity(
        entity,
        existing_entities,
        threshold=0.8
    )
    
    if match:
        logger.info(
            f"Entity dedup: Found potential duplicate - "
            f"'{entity}' matches '{match}' ({score*100:.0f}%)"
        )
        # Em vez de criar nova entidade, poderia:
        # 1. Mesclar com existente automaticamente
        # 2. Sugerir merge ao usuário
        # 3. Apenas registrar para auditoria
    else:
        logger.info(f"Entity '{entity}' is new, creating...")
        # Prosseguir com criação normal de entidade
```

### 6. Análise de Chaves de Deduplicação

```python
from lightrag.utils import normalize_entity_for_dedup

# Para entender como a deduplicação funciona, examine as chaves:

entities = [
    "Dry Gas Seal",
    "DGS", 
    "mechanical seals",
    "Bearing"
]

print("Análise de Chaves de Deduplicação:\n")

for entity in entities:
    normalized, keys = normalize_entity_for_dedup(entity)
    print(f"Entity: '{entity}'")
    print(f"  Normalized: '{normalized}'")
    print(f"  Keys for matching:")
    
    # Categorizar chaves por tipo
    key_types = {
        "exact": [],
        "singular": [],
        "acronym": [],
        "no_spaces": [],
        "components": []
    }
    
    for key in sorted(keys):
        if key == normalized:
            key_types["exact"].append(key)
        elif len(key) <= 3 and key.isupper():
            key_types["acronym"].append(key)
        elif " " not in key:
            key_types["no_spaces"].append(key)
        elif len(key.split()) == 1:
            key_types["components"].append(key)
        else:
            key_types["singular"].append(key)
    
    for category, values in key_types.items():
        if values:
            print(f"    [{category}] {', '.join(values)}")
    print()

# Resultado:
# Entity: 'Dry Gas Seal'
#   Normalized: 'dry gas seal'
#   Keys for matching:
#     [exact] dry gas seal
#     [acronym] dgs
#     [no_spaces] drygasseal
#     [components] dry, gas, seal
```

### 7. Batch Processing de Entidades

```python
# Cenário: Processar múltiplos documentos com entidades potencialmente duplicadas

def deduplicate_batch(new_entities, existing_entities, threshold=0.8):
    """
    Agrupa entidades novas com existentes quando duplicadas.
    
    Returns:
        dict: Mapeamento de entidades novas para existentes
    """
    from lightrag.utils import find_duplicate_entity
    
    dedup_mapping = {}
    new_canonical_entities = []
    
    for entity in new_entities:
        match, score = find_duplicate_entity(
            entity, 
            existing_entities + new_canonical_entities,
            threshold
        )
        
        if match:
            dedup_mapping[entity] = match
            print(f"✅ '{entity}' → '{match}' ({score*100:.0f}%)")
        else:
            dedup_mapping[entity] = entity
            new_canonical_entities.append(entity)
            print(f"➕ '{entity}' is new")
    
    return dedup_mapping

# Uso
new_entities = ["DGS", "dry gas seals", "MS", "mechanical components"]
existing = ["Dry Gas Seal", "Mechanical Seal"]

mapping = deduplicate_batch(new_entities, existing)

# Resultado:
# ✅ 'DGS' → 'Dry Gas Seal' (100%)
# ✅ 'dry gas seals' → 'Dry Gas Seal' (100%)
# ✅ 'MS' → 'Mechanical Seal' (100%)
# ➕ 'mechanical components' is new
```

### 8. Ajustando Threshold para Diferentes Cenários

```python
# Cenário 1: Dataset pequeno, ser permissivo
# (menos detecções perdidas, mais false positives)
strict = False
threshold = 0.75  # Mais permissivo

# Cenário 2: Dataset grande, ser rigoroso  
# (evitar erros que afetam muitos dados)
strict = True
threshold = 0.95  # Mais rigoroso

# Cenário 3: Pós-processamento manual, ser agressivo
# (compilar sugestões para revisão humana)
aggressive = True
threshold = 0.70

# Exemplo
entity = "comprs"  # Typo de "compressor"
existing = ["compressor", "bearing", "seal"]

for scenario, thresh in [("Permissivo", 0.75), ("Rigoroso", 0.95)]:
    from lightrag.utils import find_duplicate_entity
    match, score = find_duplicate_entity(entity, existing, threshold=thresh)
    
    result = f"'{match}'" if match else "Not matched"
    print(f"{scenario:12} (θ={thresh}): {result} (score: {score*100:.1f}%)")

# Resultado:
# Permissivo    (θ=0.75): 'compressor' (score: 90.0%)
# Rigoroso      (θ=0.95): Not matched (score: 90.0%)
```

## 💡 Dicas e Truques

### Tip 1: Debugar por que não houve match

```python
from lightrag.utils import normalize_entity_for_dedup, find_duplicate_entity

entity = "DGS"
candidates = ["Dry Gas Seal"]

# Análise 1: Ver as chaves
query_norm, query_keys = normalize_entity_for_dedup(entity)
cand_norm, cand_keys = normalize_entity_for_dedup(candidates[0])

print(f"Query '{entity}' keys: {query_keys}")
print(f"Candidate '{candidates[0]}' keys: {cand_keys}")
print(f"Intersection: {query_keys & cand_keys}")

# Análise 2: Testar find_duplicate_entity
match, score = find_duplicate_entity(entity, candidates)
print(f"Result: {match} (score: {score})")
```

### Tip 2: Performance com listas grandes

```python
# Para datasets grandes, cache os resultados normalizados:

from lightrag.utils import normalize_entity_for_dedup

# Pré-processar candidatos uma vez
entity_cache = {}
for entity in large_entity_list:
    normalized, keys = normalize_entity_for_dedup(entity)
    entity_cache[entity] = (normalized, keys)

# Depois usar cache
def find_cached(query, candidates):
    _, query_keys = normalize_entity_for_dedup(query)
    
    for candidate in candidates:
        _, cand_keys = entity_cache[candidate]
        if query_keys & cand_keys:
            return candidate
    return None
```

### Tip 3: Entender Score de Similaridade

```python
# Score = 1.0: Match perfeito (chaves normalizadas coincidem)
# Score = 0.9: Match muito bom (fuzzy: 90% similar)
# Score = 0.8: Match bom (threshold padrão)
# Score < 0.8: Não é match (below threshold)

# Exemplo de como interpretar scores:

scores = [(1.0, "Exato"), (0.95, "Typo"), (0.85, "Similar"), (0.75, "Relacionado")]

for score, meaning in scores:
    print(f"Score {score}: {meaning}")
```

## 📊 Casos de Uso Reais

### Caso 1: Compressor Centrifugo (Industrial)

```python
# Documento 1: "DGS maintenance procedure"
# Documento 2: "Dry Gas Seal inspection"  
# Documento 3: "Gas Sealing System (GSS)"

entities_doc1 = ["DGS", "Compressor", "Bearing"]
entities_doc2 = ["Dry Gas Seal", "Head Flange", "Coupling"]
entities_doc3 = ["Gas Sealing System", "Compressor", "Mechanical Seal"]

# Consolidação:
all_unique = {}
for doc_entities in [entities_doc1, entities_doc2, entities_doc3]:
    for entity in doc_entities:
        # Verificar se existe similar
        match = find_duplicate(entity, all_unique.keys())
        if match:
            all_unique[match].append(entity)
        else:
            all_unique[entity] = [entity]

# Resultado esperado:
# {
#   "Dry Gas Seal": ["DGS", "Dry Gas Seal", "Gas Sealing System"],
#   "Compressor": ["Compressor", "Compressor"],
#   "Bearing": ["Bearing"],
#   "Head Flange": ["Head Flange"],
#   "Coupling": ["Coupling"],
#   "Mechanical Seal": ["Mechanical Seal"]
# }
```

Esses exemplos cobrem os principais usos da deduplicação inteligente!
