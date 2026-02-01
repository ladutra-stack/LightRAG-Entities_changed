# 🔧 Deduplicação Inteligente de Entidades - Guia Rápido

## ⚡ Quick Start (5 minutos)

### 1. **Ver Demonstração**

```bash
# Teste a solução
python test_entity_dedup.py
```

### 2. **Usar no Seu Código**

```python
from lightrag.utils import find_duplicate_entity

# Verificar se uma entidade é duplicada
existing_entities = ["Dry Gas Seal", "Mechanical Seal", "Bearing"]

match, score = find_duplicate_entity(
    "DGS",  # Entidade nova
    existing_entities,
    threshold=0.8  # Padrão
)

if match:
    print(f"Encontrado duplicado: '{match}' (confiança: {score*100:.0f}%)")
```

## 🎯 Problemas Resolvidos

| Problema | Antes | Depois | Impacto |
|----------|-------|--------|---------|
| **Plural vs Singular** | `seal`, `seals` → 2 entidades | Consolidadas | ✅ Menos duplicatas |
| **Acrônimos** | `DGS`, `Dry Gas Seal` → 2 entidades | Detectadas | ✅ Menos duplicatas |
| **Espaçamento** | `dry-gas-seal`, `dry gas seal` → 2 entidades | Consolidadas | ✅ Menos duplicatas |
| **Caso** | `SEAL`, `seal` → 2 entidades | Detectadas | ✅ Menos duplicatas |

## 📋 Documentação Disponível

| Documento | Conteúdo | Para Quem |
|-----------|----------|----------|
| [DEDUPLICATION_SUMMARY.md](DEDUPLICATION_SUMMARY.md) | Resumo técnico, arquitetura | Desenvolvedores |
| [ENTITY_DEDUPLICATION_GUIDE.md](ENTITY_DEDUPLICATION_GUIDE.md) | Guia completo com configurações | Técnicos |
| [DEDUP_EXAMPLES.md](DEDUP_EXAMPLES.md) | 8+ exemplos práticos | Todos |
| [test_entity_dedup.py](test_entity_dedup.py) | Código de teste | Validação |

## 🚀 Funcionalidades Principais

### 1. **Normalização Inteligente**
```python
from lightrag.utils import normalize_entity_for_dedup

normalized, keys = normalize_entity_for_dedup("Dry Gas Seals")
# normalized = "dry gas seals"
# keys = {'dgs', 'dry', 'dry gas seal', 'drygasseals', ...}
```

### 2. **Detecção de Duplicatas**
```python
from lightrag.utils import find_duplicate_entity

match, score = find_duplicate_entity("DGS", ["Dry Gas Seal"])
# match = "Dry Gas Seal"
# score = 1.0 (100% confiança)
```

### 3. **Logging Automático**
Ao processar documentos, veja:
```
Entity dedup: Found potential duplicate - 'DGS' vs 'Dry Gas Seal' (similarity: 1.00)
Entity dedup: Found potential duplicate - 'seals' vs 'seal' (similarity: 1.00)
```

## 📊 Resultados de Teste

✅ **Todos os testes passando**

```
✅ TEST 1: normalize_entity_for_dedup() - 8 entidades
✅ TEST 2: find_duplicate_entity() - 7/7 cases
✅ TEST 3: Avoiding False Positives - 2/2 cases
✅ TEST 4: Bulk Entity Deduplication - 7/7 matches
✅ TEST 5: Dedup Keys Analysis - Análise completa
```

## ⚙️ Configuração

### Threshold (Padrão: 0.8)

```python
# Mais permissivo (detecta mais, mas com mais risco de falsos positivos)
find_duplicate_entity(entity, candidates, threshold=0.75)

# Mais rigoroso (menos risco, mas pode perder detecções)
find_duplicate_entity(entity, candidates, threshold=0.95)
```

### Habilitar Logs Detalhados

```bash
# Terminal
export LOG_LEVEL=DEBUG
lightrag-server

# Ou no arquivo .env
LOG_LEVEL=DEBUG
```

## 🔍 Como Funciona

### Fase 1: Chaves Normalizadas (Rápida)
- Converte para minúsculas
- Gera acrônimos
- Trata plural/singular
- Remove espaços/hífens

### Fase 2: Smart Filtering
- Evita false positives
- Valida contexto multiword

### Fase 3: Fuzzy Matching (Fallback)
- Se nenhuma match exata
- SequenceMatcher como último recurso

## 💡 Exemplos Reais

### Exemplo 1: Dados Industriais

```python
# Documento 1: "Maintenance of DGS"
# Documento 2: "Dry Gas Seal inspection"

new_entities = ["DGS", "Dry Gas Seal"]
existing = []

for entity in new_entities:
    match, score = find_duplicate_entity(entity, existing)
    if not match:
        existing.append(entity)

# Result: existing = ["DGS"] 
# (porque "Dry Gas Seal" foi detectado como duplicado de "DGS")
```

### Exemplo 2: Batch Processing

```python
# Processar múltiplas entidades de uma vez
entities_batch = ["seals", "bearing", "compressor"]
existing = ["seal", "Bearing", "Compressor"]

for entity in entities_batch:
    match, score = find_duplicate_entity(entity, existing)
    if match:
        print(f"✅ '{entity}' → '{match}'")
```

## ❓ FAQ

**P: Por que "mechanical seal" não combina com "DGS"?**
R: Porque ambas são multi-word e não compartilham estrutura significativa além de "seal". O smart filtering evita esse false positive.

**P: Como forçar um match?**
R: Reduza o threshold:
```python
find_duplicate_entity("mechanical seal", ["DGS"], threshold=0.7)
```

**P: Qual é o score máximo?**
R: 1.0 = 100% confiança (match perfeito em chaves normalizadas)

**P: Funciona com português/espanhol?**
R: Por enquanto é otimizado para inglês. Extensões são fáceis de adicionar.

## 📈 Impacto Esperado

### Antes
```
100 entidades extraídas
→ 40 duplicatas não detectadas
→ 60 entidades "únicas"
→ Análise manual necessária
```

### Depois
```
100 entidades extraídas
→ Deduplicação automática detém duplicatas conhecidas
→ Relatório de possíveis duplicatas para revisão
→ Consolidação significativa do conhecimento
```

## 🛠️ Troubleshooting

### Problema: Entidade não é detectada como duplicada

**Solução 1**: Reduzir threshold
```python
find_duplicate_entity(entity, candidates, threshold=0.75)
```

**Solução 2**: Verificar chaves
```python
from lightrag.utils import normalize_entity_for_dedup
_, keys = normalize_entity_for_dedup(entity)
print(f"Keys: {keys}")
```

### Problema: Muitos falsos positivos

**Solução**: Aumentar threshold
```python
find_duplicate_entity(entity, candidates, threshold=0.90)
```

## 📞 Suporte

1. **Teste**: `python test_entity_dedup.py`
2. **Logs**: `LOG_LEVEL=DEBUG`
3. **Docs**: Veja [DEDUP_EXAMPLES.md](DEDUP_EXAMPLES.md)
4. **Debug**: Use `normalize_entity_for_dedup()` para ver chaves

## ✨ Próximas Versões

- [ ] Suporte multi-idioma (português, espanhol)
- [ ] Integração com stemming/lemmatization
- [ ] Cache de deduplicações
- [ ] API para merge automático
- [ ] Dashboard de qualidade de entidades

---

**Status**: ✅ Production Ready  
**Versão**: 1.0.0  
**Última Atualização**: 2026-02-01
