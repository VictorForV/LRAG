#!/bin/bash
# Полная пересборка RAG системы: очистка → ингест → графы

set -e  # Остановиться при ошибке

echo "=================================================="
echo "RAG SYSTEM REBUILD"
echo "=================================================="

# Tesseract data for Russian OCR
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Активируем виртуальное окружение
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run: uv venv"
    exit 1
fi

# Устанавливаем PYTHONPATH
export PYTHONPATH=/home/user/oclw/MongoDB-RAG-Agent

echo ""
echo "🗑️  STEP 1: Clearing database..."
PGPASSWORD=123456 psql -U victor -h localhost -d rag_db -c \
    "TRUNCATE TABLE relations, entities, chunks, documents CASCADE;" && \
echo "✅ Database cleared" || echo "❌ Failed to clear database"

echo ""
echo "📄 STEP 2: Ingesting documents..."
python -m src.ingestion.ingest -d /home/user/oclw/MongoDB-RAG-Agent/documents && \
echo "✅ Documents ingested" || echo "❌ Ingestion failed"

echo ""
echo "🔗 STEP 3: Extracting relations..."
python scripts/extract_relations.py && \
echo "✅ Relations extracted" || echo "❌ Relation extraction failed"

echo ""
echo "=================================================="
echo "REBUILD COMPLETE!"
echo "=================================================="
echo ""
echo "Run the agent:"
echo "  python -m src.cli"
echo ""
