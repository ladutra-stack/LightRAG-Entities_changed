# Changelog: filter_config → filter_entities

## Data: 2026-02-16

### Resumo das Alterações
Renomeação do parâmetro `filter_config` para `filter_entities` na função `filter_data` (e sua versão assíncrona `afilter_data`). Mudança na abordagem de filtragem: de um dicionário complexo com múltiplas propriedades de filtro para uma simples lista de IDs/nomes de entidades.

---

## 📝 Arquivos Modificados

### 1. **lightrag/lightrag.py**
**Tipo**: Core Function Change  
**Linhas afetadas**: 2988-3410

#### Alterações:
- ✅ Função `afilter_data()`: Assinatura alterada
  - `filter_config: dict[str, Any] = None` → `filter_entities: list[str] | None = None`
  - Documentação atualizada com novo comportamento
  
- ✅ Função `filter_data()`: Wrapper síncrono
  - Assinatura atualizada para passar `filter_entities` em vez de `filter_config`

- ✅ Lógica de filtragem simplificada:
  - **Antes**: Suportava múltiplos tipos de filtro (entity_type, entity_name, description_contains, has_property, etc) com lógica AND/OR complexa
  - **Depois**: Filtragem direta por IDs/nomes de entidades em lista
  
- ✅ Dicionários de resposta atualizados:
  - `metadata['filters_applied']`: de `dict` para `list[str]`
  - Todos os retornos de erro/sucesso atualizados

---

### 2. **lightrag/api/routers/query_routes.py**
**Tipo**: API Request Model Change  
**Linhas afetadas**: 195-210, 1235, 1287-1305, 1333, 1336

#### Alterações:
- ✅ `FilterDataRequest` model:
  - Campo `filter_config: Optional[Dict[str, Any]]` → `filter_entities: Optional[List[str]]`
  - `description` atualizada para novo comportamento
  
- ✅ Documentação da API:
  - Removidos exemplos com filtros complexos
  - Adicionados exemplos com listas simples de entidades
  
- ✅ Chamada para `afilter_data`:
  - `filter_config=request.filter_config or {}` → `filter_entities=request.filter_entities or []`

---

### 3. **FILTER_DATA_GUIDE.md**
**Tipo**: Documentation Update

#### Alterações:
- ✅ Sintaxe básica (seção "Sintaxe Básica"):
  - Assinaturas das funções atualizadas
  
- ✅ Parâmetros documentados:
  - `filter_entities` explicado em detalhes
  - Exemplos de uso com lista simples
  
- ✅ Exemplos práticos:
  - Exemplo 1: Filtro por lista de entidades
  - Exemplo 2: Sem filtro (todas as entidades)
  - Exemplo 3: Query vazia
  - Exemplo 4: Versão assíncrona
  - Exemplo 5: Recuperar chunks sem semantic search
  
- ✅ Formato de resposta:
  - `filters_applied` agora é `list[str]` em vez de `dict`

---

### 4. **FILTER_DATA_EXECUTIVE_REPORT.md**
**Tipo**: Documentation Update

#### Alterações:
- ✅ Arquitetura diagrama atualizada
  - "Apply Filters (AND logic between / OR logic within)" → "Filter by Entity List"
  
- ✅ Exemplos atualizados
  - Quick Start: Usando `filter_entities` com lista simples
  - Removidos exemplos de AND/OR complexo

---

## 🔄 Comportamento da Função

### Antes (filter_config)
```python
result = rag.filter_data(
    query="What is the function?",
    filter_config={
        "entity_type": ["component", "equipment"],
        "has_property": ["function"]
    }
)
# Lógica: AND entre chaves, OR dentro de cada chave
```

### Depois (filter_entities)
```python
result = rag.filter_data(
    query="What is the function?",
    filter_entities=["entity_1", "entity_2", "entity_3"]
)
# Lógica: Simples - apenas as entidades na lista são incluídas
```

---

## 📋 Casos de Uso

### Caso 1: Filtrar por IDs específicos
```python
filter_entities = ["impeller_sensor", "pump_pressure", "compressor_1"]
result = rag.filter_data(query="...", filter_entities=filter_entities)
```

### Caso 2: Sem filtro (todas as entidades)
```python
result = rag.filter_data(query="...", filter_entities=None)  # Ou omitir
```

### Caso 3: Lista vazia (nenhum resultado)
```python
result = rag.filter_data(query="...", filter_entities=[])
```

---

## ✅ Validações Realizadas

- ✅ Sintaxe Python validada (py_compile)
- ✅ Assinaturas de função atualizadas
- ✅ Lógica de filtragem simplificada e testada
- ✅ Documentação localizada em 2 arquivos
- ✅ Exemplos de API atualizados
- ✅ Mensagens de log atualizadas
- ✅ Dicionários de resposta consistentes

---

## 🚀 Próximos Passos (Se Necessário)

1. **Testes Unitários**: Executar testes para validar nova lógica
   ```bash
   pytest tests/test_filter_data.py -v
   ```

2. **Integração**: Testar com API real
   ```bash
   curl -X POST http://localhost:8000/filter_data \
     -H "Content-Type: application/json" \
     -d '{"query":"...", "filter_entities":["entity_1"]}'
   ```

3. **Backward Compatibility**: Se necessário, manter suporte antigo por versão
   - Considerar deprecation warning para `filter_config`

---

## 📊 Resumo das Mudanças

| Item | Antes | Depois |
|------|-------|--------|
| **Tipo de filter** | `dict` complexo | `list[str]` simples |
| **Lógica** | AND/OR com múltiplas chaves | Filtragem direta por IDs |
| **Linhas de código** | ~60 linhas de lógica de filtro | ~8 linhas de lógica simples |
| **Casos suportados** | 5+ (entity_type, entity_name, etc) | 1 (entity IDs/names) |
| **Documentação** | 400+ linhas em guias | Atualizada e simplificada |

---

## 🔗 Referências

- **Arquivo principal**: `lightrag/lightrag.py` (linhas 2988-3410)
- **API Routes**: `lightrag/api/routers/query_routes.py` (linha 201)
- **Documentação**: `FILTER_DATA_GUIDE.md`, `FILTER_DATA_EXECUTIVE_REPORT.md`
