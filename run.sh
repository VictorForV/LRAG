#!/bin/bash
# RAG Agent - Development Mode (WSL/Linux)
# Запускает backend и frontend с hot reload БЕЗ сборки

echo "========================================"
echo "RAG Knowledge Base - Development Mode"
echo "========================================"
echo ""

# Activate venv
if [ -f .venv/bin/activate ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check npm dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "========================================"
echo "Starting Dev Servers (Hot Reload)"
echo "========================================"
echo "Backend:  http://localhost:8888"
echo "Frontend: http://localhost:5174"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "========================================"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend..."
uvicorn src.web_api:app --host 0.0.0.0 --port 8888 --reload > /tmp/rag-backend.log 2>&1 &
BACKEND_PID=$!

sleep 3

# Start frontend (dev mode)
echo "Starting frontend..."
cd frontend
npm run dev > /tmp/rag-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "Servers started! Logs:"
echo "  Backend:  tail -f /tmp/rag-backend.log"
echo "  Frontend: tail -f /tmp/rag-frontend.log"

wait $BACKEND_PID $FRONTEND_PID
