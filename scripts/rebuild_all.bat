@echo off
REM Полная пересборка RAG системы (Windows через WSL)

echo =========================================
echo RAG SYSTEM REBUILD
echo =========================================
echo.

echo [1/3] Clearing database...
wsl -u victor psql -h localhost -d rag_db -c "TRUNCATE TABLE relations, entities, chunks, documents CASCADE;"

echo.
echo [2/3] Ingesting documents...
wsl bash -c "cd /home/user/oclw/MongoDB-RAG-Agent && source .venv/bin/activate && PYTHONPATH=/home/user/oclw/MongoDB-RAG-Agent python -m src.ingestion.ingest -d /home/user/oclw/MongoDB-RAG-Agent/documents"

echo.
echo [3/3] Extracting relations...
wsl bash -c "cd /home/user/oclw/MongoDB-RAG-Agent && source .venv/bin/activate && PYTHONPATH=/home/user/oclw/MongoDB-RAG-Agent python scripts/extract_relations.py"

echo.
echo =========================================
echo REBUILD COMPLETE!
echo =========================================
echo.
echo Run the agent: python -m src.cli
echo.
pause
