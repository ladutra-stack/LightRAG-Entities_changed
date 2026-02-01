# 🔧 Como Ativar LOG_LEVEL=DEBUG

## 📍 Onde é Ativado

A variável `LOG_LEVEL` é processada em **2 locais**:

### 1. **Em lightrag/api/config.py** (Linhas 150-160)
```python
parser.add_argument(
    "--log-level",
    default=get_env_value("LOG_LEVEL", "INFO"),  # ← Lê da variável de ambiente
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Logging level (default: from env or INFO)",
)
```

### 2. **Em lightrag/api/lightrag_server.py** (Linha 297)
```python
# Setup logging
logger.setLevel(args.log_level)  # ← Aplica o nível ao logger
```

---

## 🚀 Como Ativar

### Método 1: Variável de Ambiente (Recomendado)

#### Terminal Linux/Mac
```bash
export LOG_LEVEL=DEBUG
lightrag-server
```

Ou em uma única linha:
```bash
LOG_LEVEL=DEBUG lightrag-server
```

#### Terminal Windows (PowerShell)
```powershell
$env:LOG_LEVEL = "DEBUG"
lightrag-server
```

Ou:
```powershell
$env:LOG_LEVEL = "DEBUG"; lightrag-server
```

#### Terminal Windows (CMD)
```cmd
set LOG_LEVEL=DEBUG
lightrag-server
```

### Método 2: Argumento de Linha de Comando

```bash
lightrag-server --log-level DEBUG
```

### Método 3: Arquivo `.env`

Crie ou edite `.env` na raiz do projeto:
```bash
LOG_LEVEL=DEBUG
```

Depois execute:
```bash
lightrag-server
```

---

## 📊 Níveis de Log Disponíveis

| Nível | Descrição | Quando Usar |
|-------|-----------|-----------|
| `DEBUG` | Mensagens de diagnóstico detalhadas | Desenvolvimento, troubleshooting |
| `INFO` | Informações gerais (padrão) | Produção normal |
| `WARNING` | Avisos de potenciais problemas | Produção |
| `ERROR` | Erros que precisam atenção | Produção |
| `CRITICAL` | Erros críticos do sistema | Produção |

---

## 🎯 Ver Logs de Deduplicação

Para ver as mensagens de deduplicação de entidades:

### 1. Ativar DEBUG
```bash
LOG_LEVEL=DEBUG lightrag-server
```

### 2. Processar um Documento
Use a API ou interface web para processar um documento com entidades.

### 3. Ver as Mensagens
Você verá no console:
```
Entity dedup: Found potential duplicate entity names - 'DGS' vs 'Dry Gas Seal' (similarity: 1.00)
Entity dedup: Found potential duplicate entity names - 'seals' vs 'seal' (similarity: 1.00)
```

---

## 💾 Persistir Logs em Arquivo

Se quiser salvar os logs em um arquivo:

### Via Variável de Ambiente
```bash
LOG_LEVEL=DEBUG
LOG_DIR=/path/to/log/directory
lightrag-server
```

### Via .env
```
LOG_LEVEL=DEBUG
LOG_DIR=./logs
```

### Verificar Logs
```bash
tail -f ./logs/lightrag.log
```

---

## 🔍 Filtrar Logs de Deduplicação

### Ver Apenas Mensagens de Dedup
```bash
LOG_LEVEL=DEBUG lightrag-server 2>&1 | grep -i "dedup"
```

### Ver em Tempo Real
```bash
LOG_LEVEL=DEBUG lightrag-server 2>&1 | grep -i "entity dedup"
```

### Salvar em Arquivo com Filtro
```bash
LOG_LEVEL=DEBUG lightrag-server 2>&1 | grep -i "dedup" >> dedup_logs.txt
```

---

## 📋 Padrão de Mensagens de Dedup

Quando `LOG_LEVEL=DEBUG` está ativo, você verá mensagens como:

```
Entity dedup: Found potential duplicate entity names - 'DGS' vs 'Dry Gas Seal' (similarity: 1.00)
Entity dedup: Found potential duplicate entity names - 'seals' vs 'seal' (similarity: 1.00)
Entity dedup: Found potential duplicate entity names - 'Dry Gas Seals' vs 'Dry Gas Seal' (similarity: 1.00)
Entity dedup: Found potential duplicate entity names - 'MS' vs 'Mechanical Seal' (similarity: 1.00)
```

**Formato**: `Entity dedup: Found potential duplicate entity names - '{nova}' vs '{existente}' (similarity: {score})`

---

## ⚙️ Configuração Permanente

### Opção 1: .env Local
Crie/edite `.env` na raiz do projeto:
```bash
LOG_LEVEL=DEBUG
LOG_DIR=./logs
LOG_MAX_BYTES=10485760      # 10MB
LOG_BACKUP_COUNT=5           # Manter 5 backups
```

### Opção 2: Variável Global
```bash
# Linux/Mac - Adicione ao ~/.bashrc ou ~/.zshrc
export LOG_LEVEL=DEBUG

# Windows - Adicione variável de ambiente do sistema
```

### Opção 3: Docker
Se usar Docker:
```dockerfile
ENV LOG_LEVEL=DEBUG
```

---

## 🐛 Troubleshooting

### "LOG_LEVEL não reconhecido"
Certifique-se que está usando uma letra maiúscula e valor válido:
```bash
# ✅ Correto
LOG_LEVEL=DEBUG

# ❌ Incorreto
LOG_LEVEL=debug
log_level=DEBUG
```

### "Logs ainda não aparecem"
1. Verifique se está ativando DEBUG corretamente
2. Certifique-se de processar um documento
3. Procure por "Entity dedup" nos logs
4. Use `grep` para filtrar

### "Muitos logs no console"
Use `grep` para filtrar apenas as mensagens de dedup:
```bash
LOG_LEVEL=DEBUG lightrag-server 2>&1 | grep "dedup"
```

---

## 📚 Configurações Relacionadas

### lightrag/api/config.py (Linha 155)
```python
default=get_env_value("LOG_LEVEL", "INFO"),
```
Define o padrão como "INFO" se não especificado.

### lightrag/api/lightrag_server.py (Linha 297)
```python
logger.setLevel(args.log_level)
```
Aplica o nível ao logger global.

---

## 🎓 Exemplo Completo

```bash
# 1. Criar diretório de logs
mkdir -p logs

# 2. Ativar DEBUG e redirecionar para arquivo
LOG_LEVEL=DEBUG lightrag-server > logs/debug.log 2>&1 &

# 3. Processar um documento (via API ou web UI)
# Exemplo: POST /insert com um documento

# 4. Ver logs de deduplicação
tail -f logs/debug.log | grep "dedup"

# Saída esperada:
# Entity dedup: Found potential duplicate - 'DGS' vs 'Dry Gas Seal' (1.00)
# Entity dedup: Found potential duplicate - 'seals' vs 'seal' (1.00)

# 5. Parar o servidor
kill %1
```

---

## 📝 Resumo Rápido

| Ação | Comando |
|------|---------|
| Ativar DEBUG | `LOG_LEVEL=DEBUG lightrag-server` |
| Debug + Arquivo | `LOG_LEVEL=DEBUG lightrag-server > debug.log 2>&1` |
| Ver apenas Dedup | `LOG_LEVEL=DEBUG lightrag-server 2>&1 \| grep dedup` |
| Debug via .env | Criar `.env` com `LOG_LEVEL=DEBUG` |
| Validar nível | `lightrag-server --log-level DEBUG` |

---

**Próximo passo**: Execute `LOG_LEVEL=DEBUG lightrag-server` e processe um documento para ver as mensagens de deduplicação!
