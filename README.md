# RAG Knowledge Base - Intelligent Document Search

> **Просто запусти - пользуйся!** 🚀

Agentic RAG система с умным поиском по документам и графом связей.

---

## ⚡ Быстрый старт (Windows)

### 📦 Портабл версия (РЕКОМЕНДУЕТСЯ)

**Всё работает из папки, без установки в систему!**

```
1. Двойной клик на: install_windows_portable.bat
2. Добавь API ключи в .env (откроется блокнот)
3. Двойной клик на: run_web.bat
```

**Что будет в папке проекта:**
```
MongoDB-RAG-Agent/
├── postgres/        ← PostgreSQL + данные (всё тут!)
├── .venv/           ← Виртуальное окружение
├── python/          ← Портабл Python (если нужен)
└── documents/       ← Твои документы
```

**Можно переносить папку на флешку - всё работает!**

---

### 🐳 Docker версия (если Docker установлен)

```
1. Двойной клик на: install_windows.bat
2. Добавь API ключи в .env
3. Двойной клик на: run_web.bat
```

---

## 📖 Для остальных

### Linux/Mac

```bash
# Установка
uv venv && source .venv/bin/activate
uv pip install -e .

# PostgreSQL (Docker)
docker run --name rag-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=rag_db -p 5432:5432 -d pgvector/pgvector:pg16

# Миграция БД
psql -h localhost -U postgres -d rag_db -f src/schema.sql

# Запуск
./run_web.sh
```

---

## Features

- **🌐 Web UI**: Streamlit-based interface with settings management (Windows-ready!)
- **Hybrid Search**: Semantic vector + full-text search with Reciprocal Rank Fusion (RRF)
- **Knowledge Graph**: Entity extraction + document relations (AMENDS, REFERENCES, PARTIES_TO, etc.)
- **Multi-Format Ingestion**: PDF, Word, PowerPoint, Excel, HTML, Markdown, Audio transcription
- **Named Entity Recognition**: Natasha NER for Russian + pattern matching for foreign companies
- **OpenRouter Audio**: Audio transcription via OpenRouter (gpt-4o-audio-mini, gpt-4o-transcribe)
- **Conversational CLI**: Rich-based interface with real-time streaming
- **Flexible Models**: Configure any OpenRouter model (chat, embedding, audio, graph)

---

## Quick Start

### Option 1: Web UI (Recommended for Windows)

```bash
# 1. Install dependencies
pip install -e .

# 2. Run Web UI
streamlit run src/web_ui.py

# Or use the launcher script:
# Windows: run_web.bat
# Linux/Mac: ./run_web.sh
```

The browser will open automatically at `http://localhost:8501`

**Configure settings in the sidebar:**
- OpenRouter API key (one key for all services)
- Chat model (default: `anthropic/claude-haiku-4.5`)
- Embedding model (default: `qwen/qwen3-embedding-8b`)
- Audio model (default: `openai/gpt-4o-audio-mini`)
- Database URL

### Option 2: CLI Interface

```bash
# 1. Install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 2. Setup PostgreSQL
sudo -u postgres psql << 'SQL'
CREATE DATABASE rag_db;
CREATE USER victor WITH PASSWORD '123456';
GRANT ALL PRIVILEGES ON DATABASE rag_db TO victor;
\q
SQL

psql -U victor -h localhost -d rag_db -f src/schema.sql

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run ingestion
python -m src.ingestion.ingest -d ./documents

# 5. Extract relations
python scripts/extract_relations.py

# 6. Run CLI
python -m src.cli
```

---

## Windows Installation

### Windows Installation (Easy - One-Click Installer)

**Option 1: Auto-Installer (Recommended)**

```batch
# Just double-click the installer:
install_windows.bat
```

The installer will:
- Check Python installation
- Create virtual environment
- Install all dependencies
- Create configuration file (.env)
- Launch Web UI in your browser

**Option 2: Manual Setup**

```batch
# 1. Install Python 3.10+ from python.org
#    Make sure to check "Add Python to PATH" during installation

# 2. Install UV package manager
#    Download from: https://github.com/astral-sh/uv/releases

# 3. Clone and setup
git clone <repo_url>
cd MongoDB-RAG-Agent
uv venv
.venv\Scripts\activate
uv pip install -e .

# 4. Run Web UI
streamlit run src/web_ui.py
```

---

## Configuration

### Environment Variables (.env)

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# OpenRouter API (single key for all services)
LLM_API_KEY=sk-or-v1-your-key

# Models (any OpenRouter model format)
LLM_MODEL=anthropic/claude-haiku-4.5
EMBEDDING_MODEL=qwen/qwen3-embedding-8b
AUDIO_MODEL=openai/gpt-audio-mini
GRAPH_MODEL=anthropic/claude-haiku-4.5

# OpenRouter Proxy for Audio API (required for gpt-audio-mini)
# Format: http://username:password@host:port
# Get from: https://openrouter.ai/docs#audio-models
OPENROUTER_PROXY_URL=http://user:pass@proxy-host:port
```

### Supported Model Formats

OpenRouter accepts models in format: `provider/model-name`

**Chat Models:**
- `anthropic/claude-haiku-4.5` - Fast, cheap
- `anthropic/claude-3.5-sonnet` - Balanced
- `openai/gpt-4o-mini` - Fast
- `google/gemini-flash-1.5` - Very fast

**Embedding Models:**
- `qwen/qwen3-embedding-8b` - 4096 dim, good for Russian
- `openai/text-embedding-3-small` - 1536 dim
- `cohere/embed-multilingual-v3.0` - Multilingual

**Audio Models:**
- `openai/gpt-audio-mini` - Fast transcription (requires proxy)
- `openai/gpt-4o-audio-preview` - Higher quality (requires proxy)

**Note:** Audio transcription via OpenRouter requires a proxy URL for OpenAI API access. Get your proxy from OpenRouter documentation.

See all models: [openrouter.ai/models](https://openrouter.ai/models)

---

## Quick Rebuild Script

```bash
# Linux/WSL - clears DB, ingests, extracts relations
./scripts/rebuild_all.sh

# Windows (through WSL)
scripts/rebuild_all.bat
```

---

## How It Works

### Ingestion Pipeline

```
Document (PDF/DOCX/etc.)
    ↓
Docling (OCR + text extraction)
    ↓
HybridChunker (structure-aware chunking)
    ↓
Embedding generation (batch API calls)
    ↓
PostgreSQL (chunks + embeddings via pgvector)
    ↓
Entity extraction (Natasha NER)
    ↓
PostgreSQL (entities table)
```

### Knowledge Graph Pipeline

```
Entities from documents
    ↓
Gemini 2.5 Flash Lite (relation extraction)
    ↓
PostgreSQL (relations table)
    ↓
Graph search tools
```

### Search Pipeline

```
User query
    ↓
Agent (Pydantic AI)
    ↓
Tools:
  ├─ hybrid_search()      # Vector + text with RRF
  ├─ search_by_entity()   # Find by company/person
  ├─ find_related_documents()  # Graph traversal
  └─ find_document_relations()  # Show relations
```

---

## Usage Examples

### Interactive CLI

```bash
python -m src.cli
```

**Example queries:**

```bash
# Semantic search
"Какие есть договоры с Веллес?"

# Entity search
"Найди все документы для Vindasia LLC"

# Graph search
"Покажи связанные документы с Juki Central Europe"
"Какие документы связаны с Амаль Груп?"

# Combined
"Расскажи про контракт между Веллес и Vindasia"
```

### Graph Search Capabilities

| Search Type | Example | What it finds |
|-------------|---------|---------------|
| **By Entity** | "Vindasia" | All docs mentioning Vindasia |
| **By Relations** | "Juki contracts" | Docs connected via AMENDS, REFERENCES, etc. |
| **Combined** | "Amal Group deliveries" | Entity mentions + related docs |

---

## Project Structure

```
MongoDB-RAG-Agent/
├── src/
│   ├── agent.py              # Pydantic AI agent with tools
│   ├── cli.py                # Rich-based conversational CLI
│   ├── dependencies.py       # PostgreSQL connection management
│   ├── graph_tools.py        # Knowledge graph search tools
│   ├── ingestion/
│   │   ├── entity_extractor.py    # Natasha NER + foreign company patterns
│   │   ├── relation_extractor.py  # Gemini-based relation extraction
│   │   ├── chunker.py             # Docling HybridChunker wrapper
│   │   ├── embedder.py            # Batch embedding generation
│   │   └── ingest.py              # PostgreSQL ingestion pipeline
│   ├── prompts.py            # System prompts
│   ├── providers.py          # LLM/embedding provider configs
│   ├── settings.py           # Pydantic Settings (env vars)
│   ├── schema.sql            # Database schema (pgvector)
│   └── tools.py              # Hybrid search (semantic + text + RRF)
├── scripts/
│   └── extract_relations.py  # Batch relation extraction
├── documents/                # Put your documents here
├── .env                      # Configuration (copy from .env.example)
└── pyproject.toml            # UV package configuration
```

---

## Database Schema

```sql
-- Documents with metadata
documents (id, title, source, content, metadata, created_at)

-- Chunks with embeddings (pgvector)
chunks (id, document_id, content, embedding, metadata)

-- Named entities (ORG, PER, DATE, MONEY, DOC_REF)
entities (id, document_id, chunk_id, entity_type, entity_name, entity_text)

-- Document relations (AMENDS, REFERENCES, PARTIES_TO, PAYS_FOR, DELIVERS)
relations (id, source_document_id, target_document_id, relation_type, confidence, metadata)
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Database** | PostgreSQL 16 + pgvector |
| **Agent** | Pydantic AI 0.1.0+ |
| **Document Processing** | Docling 2.14+ (PDF, DOCX, PPTX, XLSX, Audio) |
| **NER** | Natasha (Russian) + regex (foreign companies) |
| **Relation Extraction** | Gemini 2.5 Flash Lite via OpenRouter |
| **CLI** | Rich 13.9+ |
| **Package Manager** | UV 0.5.0+ |

---

## Costs

| Service | Cost |
|---------|------|
| **PostgreSQL** | $0 (local or self-hosted) |
| **Embeddings** | ~$0.01 per 100K tokens (Qwen via OpenRouter) |
| **LLM (chat)** | ~$0.10 per 1M tokens (Claude Haiku via OpenRouter) |
| **Relation Extraction** | ~$0.002 for 100 document pairs (Gemini Flash) |

**Typical usage**: 23 documents → ~$0.05 total (embeddings + relations)

---

## Troubleshooting

### Database connection error
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Test connection
psql -U victor -h localhost -d rag_db
```

### Vector search not working
```bash
# Check pgvector is installed
psql -U victor -h localhost -d rag_db -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

# Install if missing
psql -U victor -h localhost -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### No relations found
```bash
# Check if relations exist
psql -U victor -h localhost -d rag_db -c "SELECT COUNT(*) FROM relations;"

# Re-extract
python scripts/extract_relations.py
```

### Foreign companies not recognized
```bash
# Check entities table
psql -U victor -h localhost -d rag_db -c "
SELECT entity_name, COUNT(*)
FROM entities
WHERE metadata->>'source' = 'foreign_org_pattern'
GROUP BY entity_name;
"

# Re-ingest with updated patterns
psql -U victor -h localhost -d rag_db -c "TRUNCATE TABLE entities CASCADE;"
python -m src.ingestion.ingest -d ./documents
```

---

## License

MIT
