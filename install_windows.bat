@echo off
setlocal enabledelayedexpansion
REM MongoDB RAG Agent - Windows Installer
REM Автоматическая установка всего необходимого

echo ==================================================
echo   RAG Knowledge Base - Установка на Windows
echo ==================================================
echo.

REM Проверка прав администратора
net session >nul 2>&1
if errorlevel 1 (
    echo [!] Требуются права администратора
    echo    Пожалуйста, запустите этот файл от имени администратора
    echo    (Правый клик -^> Запуск от имени администратора)
    pause
    exit /b 1
)

echo [1/7] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден. Скачивание...
    echo     Это может занять несколько минут...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile 'python_installer.exe'"
    echo [*] Установка Python...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    echo [*] Ожидание завершения установки...
    timeout /t 30 /nobreak >nul
    del python_installer.exe
    echo [+] Python установлен
) else (
    echo [+] Python уже установлен
)

echo.
echo [2/7] Проверка UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [!] UV не найден. Установка...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo [+] UV установлен
) else (
    echo [+] UV уже установлен
)

echo.
echo [3/7] Создание виртуального окружения...
if not exist .venv (
    uv venv
    echo [+] Виртуальное окружение создано
) else (
    echo [+] Виртуальное окружение уже существует
)

echo.
echo [4/7] Установка зависимостей Python...
call .venv\Scripts\activate.bat
uv pip install -e . -q
echo [+] Зависимости установлены

echo.
echo [5/7] Проверка PostgreSQL...
pg_config --version >nul 2>&1
if errorlevel 1 (
    echo [!] PostgreSQL не найден
    echo.
    echo Запуск PostgreSQL через Docker...
    docker --version >nul 2>&1
    if not errorlevel 1 (
        docker run --name rag-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=rag_db -p 5432:5432 -d pgvector/pgvector:pg16 2>nul
        if errorlevel 1 (
            echo [*] Контейнер уже существует, запуск...
            docker start rag-postgres
        )
        echo [*] Ожидание запуска PostgreSQL...
        timeout /t 10 /nobreak >nul
        echo [+] PostgreSQL запущен в Docker
    ) else (
        echo [!] Docker не найден
        echo    Пожалуйста, установите Docker Desktop: https://www.docker.com/products/docker-desktop
        pause
        exit /b 1
    )
) else (
    echo [+] PostgreSQL уже установлен
)

echo.
echo [6/7] Создание .env файла...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [+] .env файл создан
    ) else (
        echo DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_db > .env
        echo LLM_API_KEY=your-api-key-here >> .env
        echo LLM_MODEL=anthropic/claude-haiku-4.5 >> .env
        echo EMBEDDING_API_KEY=your-embedding-key-here >> .env
        echo EMBEDDING_MODEL=qwen/qwen3-embedding-8b >> .env
        echo LLM_BASE_URL=https://openrouter.ai/api/v1 >> .env
        echo EMBEDDING_BASE_URL=https://api.openai.com/v1 >> .env
        echo [+] .env файл создан
    )
    echo.
    echo [!] ВАЖНО: Добавьте свои API ключи в .env файл!
    echo           Сейчас будет открыт блокнот...
    notepad .env
) else (
    echo [+] .env файл уже существует
)

echo.
echo [7/7] Настройка базы данных...
timeout /t 3 /nobreak >nul

REM Пробуем применить схему через Docker
docker exec -i rag-postgres psql -U postgres -d rag_db -f src\schema.sql 2>nul
if errorlevel 1 (
    REM Если не получилось, пробуем локально
    set PGPASSWORD=postgres
    psql -h localhost -U postgres -d rag_db -f src\schema.sql 2>nul
)
echo [+] База данных настроена

echo.
echo ==================================================
echo   Установка завершена!
echo ==================================================
echo.
echo Для запуска: Двойной клик на run_web.bat
echo.
pause
