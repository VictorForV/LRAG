#!/bin/bash
# RAG Agent - Development Mode (WSL/Linux)
# Запускает backend и frontend для разработки

echo "========================================"
echo "RAG Knowledge Base - Development Mode"
echo "========================================"
echo ""

# Активируем виртуальное окружение
if [ -f .venv/bin/activate ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Проверяем наличие зависимостей frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "========================================"
echo "Starting Development Servers"
echo "========================================"
echo "Backend:  http://localhost:8888"
echo "Frontend: http://localhost:5174"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "========================================"
echo ""

# Функция для очистки при выходе
cleanup() {
    echo ""
    echo "Stopping servers..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

trap cleanup SIGINT SIGTERM

# Запускаем backend в фоне
echo "Starting backend..."
uvicorn src.web_api:app --host 0.0.0.0 --port 8888 --reload > /tmp/rag-backend.log 2>&1 &
BACKEND_PID=$!

# Ждем запуск бэкенда
sleep 3

# Запускаем frontend в фоне
echo "Starting frontend..."
cd frontend
npm run dev > /tmp/rag-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "Servers started!"
echo "Backend log:  tail -f /tmp/rag-backend.log"
echo "Frontend log: tail -f /tmp/rag-frontend.log"
echo ""

# Ждем завершения
wait $BACKEND_PID $FRONTEND_PID
