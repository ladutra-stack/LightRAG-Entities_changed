# Guia de Deduplicação Inteligente de Entidades

## 📋 Resumo das Melhorias

Foram implementadas melhorias no sistema de deduplicação de entidades para detectar e consolidar automaticamente:

1. **Variações de Plural/Singular**: `seal` ↔ `seals`, `component` ↔ `components`
2. **Acrônimos e Expansões**: `DGS` ↔ `Dry Gas Seal`, `dry gas seal`
3. **Variações de Caso**: `SEAL` ↔ `Seal` ↔ `seal`
4. **Espaçamento e Pontuação**: `dry-gas-seal` ↔ `dry gas seal`
5. **Fuzzy Matching**: Detecta similaridades aproximadas entre nomes

## 🔧 Novas Funções Implementadas

### 1. `normalize_entity_for_dedup(entity_name: str)` 
**Localização**: [lightrag/utils.py](lightrag/utils.py#L3357)

Normaliza um nome de entidade para deduplicação inteligente.

**Retorna**: Tupla `(normalized_form, set_of_dedup_keys)`

**Exemplo**:
```python
from lightrag.utils import normalize_entity_for_dedup

# Entrada: "Dry Gas Seals"
normalized, keys = normalize_entity_for_dedup("Dry Gas Seals")

# Saída:
# normalized = "dry gas seals"
# keys = {
#   "dry gas seals",      # lowercase
#   "dry gas seal",       # singular (seals -> seal)
#   "dgs",               # acronym (first letters)
#   "dry",               # componentes individuais
#   "gas",
#   "seal",
#   "drygasseals",       # sem espaços
#   "drygas"            # filtrando palavras comuns
# }
```

**Estratégia de Normalização**:
- Remove artigos comuns: "the", "a", "an", "of", "and", "or"
- Converte para minúsculas e remove espaçamento
- Trata plural/singular automaticamente
- Gera acrônimos a partir de múltiplas palavras
- Cria variações sem espaços/hífens

### 2. `find_duplicate_entity(entity_name, entity_candidates, similarity_threshold=0.8)`
**Localização**: [lightrag/utils.py](lightrag/utils.py#L3416)

Encontra se uma entidade é duplicada em relação a uma lista de candidatos.

**Retorna**: Tupla `(matched_entity_or_None, similarity_score)`

**Exemplo**:
```python
from lightrag.utils import find_duplicate_entity

# Verificar se "DGS" é duplicada
existing_entities = ["Dry Gas Seal", "Compressor", "Bearing"]
match, score = find_duplicate_entity("DGS", existing_entities, threshold=0.8)

# Resultado:
# match = "Dry Gas Seal"
# score = 1.0 (match exato encontrado nas chaves normalizadas)
```

**Algoritmo**:
1. **Fase 1**: Busca exata nas chaves normalizadas (rápida)
2. **Fase 2**: Fuzzy matching com `SequenceMatcher` (fallback)
3. Retorna resultado apenas se acima do limiar de similaridade

## 📊 Integração no Pipeline

### Onde a Deduplicação Ocorre

A detecção agora é acionada em dois pontos críticos:

#### 1. **Durante Extração de Entidades** 
[operate.py](operate.py#L1715-L1750) - Função `_merge_nodes_then_upsert`:

```python
# Nova lógica adicionada:
duplicate_entity_name, dup_score = find_duplicate_entity(
    entity_name, 
    entity_names,
    similarity_threshold=0.8
)
if duplicate_entity_name and duplicate_entity_name != entity_name:
    logger.info(
        f"Entity dedup: Found potential duplicate entity names - "
        f"'{entity_name}' vs '{duplicate_entity_name}' (similarity: {dup_score:.2f})"
    )
```

#### 2. **Logs Informativos**
Quando duplicatas são detectadas, você verá no log:
```
Entity dedup: Found potential duplicate entity names - 'DGS' vs 'Dry Gas Seal' (similarity: 1.00)
Entity dedup: Found potential duplicate entity names - 'seals' vs 'seal' (similarity: 1.00)
```

## 🧪 Como Testar

### Teste 1: Variações de Plural/Singular

```python
from lightrag.utils import normalize_entity_for_dedup, find_duplicate_entity

# Teste plural/singular
entities = ["bearing", "seal"]
result, score = find_duplicate_entity("seals", entities)
print(f"Detectou 'seal' em 'seals'? {result == 'seal'}")  # Deve ser True

# Múltiplas variações
result, score = find_duplicate_entity("Seals", ["Seal", "Bearing"])
print(f"Case-insensitive match: {result == 'Seal'}")  # Deve ser True
```

### Teste 2: Acrônimos

```python
# Teste acrônimos
entities = ["Dry Gas Seal", "Mechanical Component"]
result, score = find_duplicate_entity("DGS", entities)
print(f"DGS encontrado? {result == 'Dry Gas Seal'}")  # Deve ser True

# Reverse: entidade completa vs acrônimo existente
entities = ["DGS", "MC"]
result, score = find_duplicate_entity("Dry Gas Seal", entities)
print(f"Dry Gas Seal encontrado? {result == 'DGS'}")  # Deve ser True
```

### Teste 3: Variações de Espaçamento

```python
# Teste espaçamento e pontuação
entities = ["dry gas seal"]
result, score = find_duplicate_entity("dry-gas-seal", entities)
print(f"Variação com hífen encontrada? {result == 'dry gas seal'}")  # Deve ser True

result, score = find_duplicate_entity("drygasseal", entities)
print(f"Sem espaços encontrada? {result == 'dry gas seal'}")  # Deve ser True
```

### Teste 4: Processamento Completo com LightRAG

```python
from lightrag import LightRAG
import asyncio

async def test_dedup():
    rag = LightRAG()
    
    # Texto com variações de entidades
    text = """
    The Dry Gas Seal (DGS) is critical. The seals must be maintained.
    Dry Gas Seals are common in compressors.
    The compressor has multiple seals for the gas sealing.
    """
    
    # Processar documento
    await rag.ainsert(text, "test_doc.txt")
    
    # Verificar logs para mensagens de deduplicação
    # Você deve ver algo como:
    # "Entity dedup: Found potential duplicate entity names - 'seals' vs 'seal' (similarity: 1.00)"
```

## 📈 Métricas e Ajustes

### Ajustar o Limiar de Similaridade

Para casos mais permissivos (pode gerar false positives):
```python
# No código do operate.py, linha ~1728:
duplicate_entity_name, dup_score = find_duplicate_entity(
    entity_name, 
    entity_names,
    similarity_threshold=0.75  # Reduzir de 0.8 para 0.75
)
```

Para casos mais rigorosos:
```python
duplicate_entity_name, dup_score = find_duplicate_entity(
    entity_name, 
    entity_names,
    similarity_threshold=0.95  # Aumentar para 0.95
)
```

### Adicionar Variações Customizadas

Se você tiver padrões específicos do domínio (ex: termos em português), estenda `normalize_entity_for_dedup`:

```python
def normalize_entity_for_dedup(entity_name: str) -> tuple[str, set[str]]:
    # ... código existente ...
    
    # Adicionar variações customizadas
    custom_variations = {
        "selagem": {"seal", "sealing", "sealant"},
        "compressor": {"compressores", "compressor", "comp"},
        # ... mais variações ...
    }
    
    for key, variations in custom_variations.items():
        if key in normalized:
            dedup_keys.update(variations)
    
    return normalized, dedup_keys
```

## ⚠️ Considerações Importantes

1. **Performance**: A normalização ocorre uma vez por entidade. O fuzzy matching é apenas um fallback.

2. **Preservação de Histórico**: A entidade original é preservada; apenas a detecção é melhorada.

3. **Threshold Padrão**: 0.8 (80%) é conservador para evitar false positives.

4. **Logs Detalhados**: Ative `LOG_LEVEL=DEBUG` para ver todas as operações de deduplicação:
   ```bash
   LOG_LEVEL=DEBUG lightrag-server
   ```

## 🐛 Troubleshooting

### Problema: Entidades ainda aparecem como duplicadas

**Causa**: Threshold muito alto
```python
# Solução: Reduzir threshold em operate.py
similarity_threshold=0.75
```

### Problema: Muitos falsos positivos

**Causa**: Threshold muito baixo
```python
# Solução: Aumentar threshold
similarity_threshold=0.90
```

### Problema: Acrônimos não são detectados

**Causa**: Acrônimo não é reconhecido como variação
```python
# Solução: Adicionar suporte customizado em utils.py
# ou usar a API: find_duplicate_entity(name, existing_names)
```

## 📚 Referências

- [operate.py - Função _merge_nodes_then_upsert](operate.py#L1715)
- [utils.py - normalize_entity_for_dedup](utils.py#L3357)
- [utils.py - find_duplicate_entity](utils.py#L3416)

## ✅ Próximas Melhorias (Futuro)

- [ ] Integração com stemming/lemmatization (NLTK/spaCy)
- [ ] Aprendizado customizado por domínio
- [ ] Cache de deduplicações para performance
- [ ] API para merge automático de entidades detectadas
- [ ] Suporte multi-idioma (português, espanhol, etc.)
