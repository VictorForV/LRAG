#!/bin/bash
# MongoDB RAG Agent - Web UI Launcher
# Opens a browser-based interface for the RAG system

echo "=================================================="
echo "  RAG Knowledge Base - Web UI"
echo "=================================================="
echo ""

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    echo "[OK] Virtual environment activated"
else
    echo "[ERROR] Virtual environment not found!"
    echo "Please run: uv venv"
    echo "Then: uv pip install -e ."
    exit 1
fi

# Set Python path
export PYTHONPATH=$(pwd)

# Check if .env exists
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found - using defaults"
    echo "Please configure settings in the Web UI sidebar"
    echo ""
fi

# Start Streamlit
echo ""
echo "Starting Web UI..."
echo "Browser will open automatically at http://localhost:8501"
echo "Press Ctrl+C to stop"
echo ""
streamlit run src/web_ui.py --server.headless=true
