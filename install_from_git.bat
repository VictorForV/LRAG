@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Автоустановщик
echo ==================================================
echo.
echo Этот установщик скачает все необходимые файлы
echo и настроит приложение автоматически.
echo.
pause

# === НАСТРОЙКИ ===
set "GITHUB_USER=victor12345678"
set "GITHUB_REPO=MongoDB-RAG-Agent"
set "GITHUB_BRANCH=main"
set "DIST_URL=https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/%GITHUB_BRANCH%.zip"

REM Создаём временную папку
set "TEMP_DIR=%TEMP%\rag_agent_install"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo.
echo [1/6] Скачивание файлов с GitHub...
echo.

REM Скачиваем архив с GitHub
powershell -Command "Invoke-WebRequest -Uri '%DIST_URL%' -OutFile '%TEMP_DIR%\dist.zip'"

if not exist "%TEMP_DIR%\dist.zip" (
    echo [!] Ошибка скачивания! Проверьте подключение к интернету.
    pause
    exit /b 1
)

echo [+] Файлы скачаны

echo.
echo [2/6] Распаковка файлов...

REM Распаковываем архив
powershell -Command "Expand-Archive -Path '%TEMP_DIR%\dist.zip' -DestinationPath '%TEMP_DIR%' -Force"

echo [+] Файлы распакованы

echo.
echo [3/6] Проверка Python...

REM Переходим в папку с проектом
cd "%TEMP_DIR%\%GITHUB_REPO%-%GITHUB_BRANCH%"

if exist ".venv\Scripts\activate.bat" (
    echo [+] Виртуальное окружение уже существует
) else (
    echo [*] Создание виртуального окружения...
    if exist "python\python.exe" (
        python\python.exe -m venv .venv
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo [!] Python не установлен
            echo.
            echo Установите Python 3.10+ с https://www.python.org/downloads/
            echo И запустите этот установщик снова.
            pause
            exit /b 1
        )
        python -m venv .venv
    )
)

echo [+] Виртуальное окружение готово

echo.
echo [4/6] Установка зависимостей...

call .venv\Scripts\activate.bat
uv pip install -e . -q

echo [+] Зависимости установлены

echo.
echo [5/6] Настройка...

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
    ) else (
        echo DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_db > .env
        echo LLM_API_KEY=your-api-key-here >> .env
        echo LLM_MODEL=anthropic/claude-haiku-4.5 >> .env
        echo EMBEDDING_API_KEY=your-embedding-key-here >> .env
        echo EMBEDDING_MODEL=qwen/qwen3-embedding-8b >> .env
        echo LLM_BASE_URL=https://openrouter.ai/api/v1 >> .env
        echo EMBEDDING_BASE_URL=https://api.openai.com/v1 >> .env
    )
    echo.
    echo [!] Добавьте свои API ключи в .env файл
    notepad .env
    pause
)

REM Запускаем PostgreSQL если есть портабл
if exist "postgres\bin\pg_ctl.exe" (
    echo [*] Запуск PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start 2>nul
    timeout /t 3 /nobreak >nul
)

echo.
echo [6/6] Перемещение в текущую папку...

set "TARGET_DIR=%CD%\RAG-Agent"
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"

mkdir "%TARGET_DIR%"
xcopy "%TEMP_DIR%\%GITHUB_REPO%-%GITHUB_BRANCH%\*" "%TARGET_DIR%\" /E /I /Y /Q

REM Очистка
cd "%TARGET_DIR%"
rmdir /s /q "%TEMP_DIR%"

echo.
echo ==================================================
echo   ✓ Установка завершена!
echo ==================================================
echo.
echo Приложение установлено в: %TARGET_DIR%
echo.
echo Для запуска: run_web.bat
echo.
pause
