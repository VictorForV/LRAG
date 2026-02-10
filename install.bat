@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Ustanovschik
echo ==================================================
echo.
echo Polnostyu portabilnaya ustanovka (bez ustanovki v systemu)
echo.
pause

set "GITHUB_USER=VictorForV"
set "GITHUB_REPO=LRAG"
set "PROJECT_DIR=%GITHUB_REPO%"

echo.
echo [1/9] Skachivanie proekta s GitHub...
echo.

REM Skachivaem arhiv
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/main.zip' -OutFile 'repo.zip'"

if not exist repo.zip (
    echo [X] Oshibka skachivaniya! Proverte internet.
    pause
    exit /b 1
)

echo [OK] Skachano

echo.
echo [2/9] Raspackovka...
powershell -Command "Expand-Archive -Path 'repo.zip' -DestinationPath '.' -Force"

REM Pereimenuem papku
if exist "%GITHUB_REPO%-main" (
    move "%GITHUB_REPO%-main" "%PROJECT_DIR%" >nul 2>&1
)

del repo.zip
echo [OK] Raspackovano

cd "%PROJECT_DIR%"

echo.
echo [3/9] Proverka Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [*] Python ne nayden v sisteme.
    echo     Skachivanie portable Python...
    echo     (Eto zanymet neskolko minut)
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-win32.zip' -OutFile 'python_portable.zip'"
    powershell -Command "Expand-Archive -Path 'python_portable.zip' -DestinationPath 'python' -Force"
    del python_portable.zip

    REM Nuzhno dobavit' import site dlya pip
    echo import site >> python\python312._pth
    echo. >> python\python312._pth

    set "PATH=%CD%\python;%PATH%"
    echo [OK] Portable Python gotov
) else (
    echo [OK] Python ustanovlen v sisteme
)

echo.
echo [4/9] Ustanovka UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [*] Skachivanie UV...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    echo [*] ZAKROYTE OKNO I ZAPUSTITE INSTALL.BAT ZANOVO
    pause
    exit /b 0
)
echo [OK] UV ustanovlen

echo.
echo [5/9] Sozdanie virtualnogo okruzheniya...
if not exist .venv (
    uv venv
    echo [OK] Venv sozdan
) else (
    echo [OK] Venv uzhe est
)

echo.
echo [6/9] Ustanovka zavisimostey...
echo     (Eto mozhet zanyat neskolko minut)
echo.
call .venv\Scripts\activate.bat
uv pip install -e .
echo [OK] Zavisimosti ustanovleny

echo.
echo [7/9] Ustanovka PostgreSQL...
set "PG_OK="
if exist postgres\bin\psql.exe set "PG_OK=1"
for /d %%i in (postgres\postgresql-*) do if exist "%%i\bin\psql.exe" set "PG_OK=1"

if not defined PG_OK (
    echo [*] Skachivanie i ustanovka portable PostgreSQL...
    echo     Eto zanymet neskolko minut...
    echo.
    call setup_postgres.bat
) else (
    echo [OK] PostgreSQL uzhe ustanovlen
)

echo.
echo [8/9] Sozdanie .env fajla...
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
echo [9/9] Sozdanie bazy dannykh...
echo [*] Zapusk PostgreSQL...
if exist postgres\bin\pg_ctl.exe (
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 3 /nobreak >nul
)
if exist postgres\postgresql-*\bin\pg_ctl.exe (
    for /d %%i in (postgres\postgresql-*) do "%%i\bin\pg_ctl.exe" -D postgres\data -l postgres\log.txt start
    timeout /t 3 /nobreak >nul
)

echo [*] Sozdanie BD rag_db...
if exist postgres\bin\psql.exe (
    postgres\bin\psql.exe -U postgres -c "CREATE DATABASE rag_db;" 2>nul
) else if exist postgres\postgresql-*\bin\psql.exe (
    for /d %%i in (postgres\postgresql-*) do "%%i\bin\psql.exe" -U postgres -c "CREATE DATABASE rag_db;" 2>nul
)

echo [*] Ostanovka PostgreSQL...
if exist postgres\bin\pg_ctl.exe (
    postgres\bin\pg_ctl.exe -D postgres\data stop
)
echo [OK] BD gotova

echo.
echo ==================================================
echo   USTANOVKA ZAVERSHENA!
echo ==================================================
echo.
echo [X] DODAYTE VASH API KLUCH V .ENV FAJL!
echo.
echo 1. Poluchite API key: https://openrouter.ai/keys
echo 2. Otkroyte .env i vstavte key vmesto 'sk-or-v1-your-api-key-here'
echo.
echo Dlya zapuska: run.bat
echo.
pause

REM Otkryvaem .env v bloknote
notepad .env
