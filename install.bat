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

    REM Try curl first (Windows 10+)
    curl --version >nul 2>&1
    if not errorlevel 1 (
        echo [*] Using curl...
        curl -L -k -o pg_portable.zip "https://taskcase.ru/static/downloads/postgresql-16.1-1-windows-x64-full.zip"
    ) else (
        echo [*] Using PowerShell...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls; $ProgressPreference='SilentlyContinue'; [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; Invoke-WebRequest -Uri 'https://taskcase.ru/static/downloads/postgresql-16.1-1-windows-x64-full.zip' -OutFile 'pg_portable.zip'"
    )

    if not exist pg_portable.zip (
        echo [X] Download failed!
        pause
        exit /b 1
    )

    echo [2/3] Extracting...
    powershell -Command "Expand-Archive -Path 'pg_portable.zip' -DestinationPath 'postgres_temp' -Force"
    del pg_portable.zip

    REM Move files to postgres/ folder
    xcopy "postgres_temp\*" "postgres\" /E /I /H /Y
    rmdir /s /q "postgres_temp"

    echo [3/3] Initializing database...
    postgres\bin\initdb.exe -D postgres\data -U postgres -A trust -E utf8 --locale=C

    echo [OK] PostgreSQL ustanovlen
) else (
    echo [OK] PostgreSQL uzhe ustanovlen
)

echo.
echo [8/8] Sozdanie .env...
echo DATABASE_URL=postgresql://postgres@localhost:5432/rag_db > .env
echo LLM_API_KEY=sk-or-v1-your-api-key-here >> .env
echo LLM_MODEL=anthropic/claude-haiku-4.5 >> .env
echo EMBEDDING_API_KEY=sk-or-v1-your-api-key-here >> .env
echo EMBEDDING_MODEL=qwen/qwen3-embedding-8b >> .env
echo LLM_BASE_URL=https://openrouter.ai/api/v1 >> .env
echo EMBEDDING_BASE_URL=https://api.openai.com/v1 >> .env
echo AUDIO_MODEL=openai/whisper-1 >> .env
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
