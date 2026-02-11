@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Ustanovschik
echo ==================================================
echo.
echo Polnostyu portabilnaya ustanovka
echo.
pause

set "GITHUB_USER=VictorForV"
set "GITHUB_REPO=LRAG"
set "PROJECT_DIR=%GITHUB_REPO%"

echo.
echo [1/8] Skachivanie proekta s GitHub...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/main.zip' -OutFile 'repo.zip'"

if not exist repo.zip (
    echo [X] Oshibka skachivaniya!
    pause
    exit /b 1
)
echo [OK] Skachano

echo.
echo [2/8] Raspackovka...
powershell -Command "Expand-Archive -Path 'repo.zip' -DestinationPath '.' -Force"
if exist "%GITHUB_REPO%-main" move "%GITHUB_REPO%-main" "%PROJECT_DIR%" >nul 2>&1
del repo.zip
echo [OK] Raspackovano

cd "%PROJECT_DIR%"

echo.
echo [3/8] Proverka Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [*] Skachivanie portable Python...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-win32.zip' -OutFile 'python_portable.zip'"
    powershell -Command "Expand-Archive -Path 'python_portable.zip' -DestinationPath 'python' -Force"
    del python_portable.zip
    echo import site >> python\python312._pth
    echo. >> python\python312._pth
    set "PATH=%CD%\python;%PATH%"
    echo [OK] Portable Python gotov
) else (
    echo [OK] Python v sisteme
)

echo.
echo [4/8] Ustanovka UV...
uv --version >nul 2>&1
if errorlevel 1 (
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo [*] ZAKROY OKNO I ZAPUSTI INSTALL.BAT ZANOVO
    pause
    exit /b 0
)
echo [OK] UV ustanovlen

echo.
echo [5/8] Sozdanie venv...
if not exist .venv (
    uv venv
    echo [OK] Venv sozdan
) else (
    echo [OK] Venv uzhe est
)

echo.
echo [6/8] Ustanovka zavisimostey...
call .venv\Scripts\activate.bat
uv pip install -e .
echo [OK] Zavisimosti ustanovleny

echo.
echo [7/8] Ustanovka PostgreSQL...
if not exist postgres\bin\psql.exe (
    echo [*] Skachivanie portable PostgreSQL...
    echo     Eto zanymet 5-10 minut...
    echo.
    mkdir postgres\data

    echo [1/3] Downloading PostgreSQL...

    REM Download via HTTP (no SSL issues)
    curl --version >nul 2>&1
    if not errorlevel 1 (
        echo [*] Using curl...
        curl -L -o pg_portable.zip "http://45.155.207.234:81/postgresql-16.1-1-windows-x64-full.zip"
    ) else (
        echo [*] Using PowerShell...
        powershell -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'http://45.155.207.234:81/postgresql-16.1-1-windows-x64-full.zip' -OutFile 'pg_portable.zip'"
    )

    if not exist pg_portable.zip (
        echo.
        echo [!] AVTOMATICHESKAYA ZAGRUZKA NE SRABOTALA
        echo.
        echo    Skachayte v ruchnuyu:
        echo    https://taskcase.ru/static/downloads/postgresql-16.1-1-windows-x64-full.zip
        echo.
        echo    I polozyte fajl v papku s etim install.bat
        echo    i nazovite ego pg_portable.zip
        echo.
        pause

        if not exist pg_portable.zip (
            echo [X] Fajl ne nayden! Ustanovka nevozmozhna.
            pause
            exit /b 1
        )
    )

    echo [2/3] Extracting...
    powershell -Command "Expand-Archive -Path 'pg_portable.zip' -DestinationPath 'postgres_temp' -Force"
    del pg_portable.zip

    REM Move files to postgres/ folder (/S copies subdirectories)
    robocopy "postgres_temp" "postgres" /E /IS /IT /NFL /NP /NDL /NJH /NJS
    if exist postgres_temp rmdir /s /q "postgres_temp"

    echo [3/3] Initializing database...
    postgres\bin\initdb.exe -D postgres\data -U postgres -A trust -E utf8 --locale=C

    echo [*] Starting PostgreSQL temporarily to create database...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 2 /nobreak >nul

    echo [*] Creating database...
    postgres\bin\psql.exe -U postgres -c "CREATE DATABASE rag_kb;"
    postgres\bin\psql.exe -U postgres -d rag_kb -c "CREATE EXTENSION IF NOT EXISTS vector;"

    echo [*] Stopping PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data stop

    echo [OK] PostgreSQL initialized and database created
) else (
    echo [OK] PostgreSQL uzhe ustanovlen
)

echo.
echo [8/8] Sozdanie .env...
echo database_url=postgresql://postgres:postgres@localhost:5432/rag_kb > .env
echo llm_api_key=sk-or-v1-your-api-key-here >> .env
echo llm_model=anthropic/claude-haiku-4.5 >> .env
echo embedding_api_key=sk-or-v1-your-api-key-here >> .env
echo embedding_model=qwen/qwen3-embedding-8b >> .env
echo llm_base_url=https://openrouter.ai/api/v1 >> .env
echo embedding_base_url=https://api.openai.com/v1 >> .env
echo audio_model=openai/whisper-1 >> .env
echo [OK] .env sozdan

echo.
echo ==================================================
echo   USTANOVKA ZAVERSHENA!
echo ==================================================
echo.
echo [X] Vstavte API klyuch v .env!
echo.
pause
notepad .env
