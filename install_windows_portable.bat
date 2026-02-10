@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Portable (bez ustanovki)
echo ==================================================
echo.
echo Vse budet v papke projekta. Nikakoy ustanovki v systemu!
echo.

echo [1/6] Proverka Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python ne nayden. Skachivanie...
    echo     Eto mozhet zanyat neskolko minut...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-win32.zip' -OutFile 'python_portable.zip'"
    echo [*] Raspakovka...
    powershell -Command "Expand-Archive -Path 'python_portable.zip' -DestinationPath 'python' -Force"
    del python_portable.zip
    echo [*] Nastroyka...
    echo import site >> python\python312._pth
    echo. >> python\python312._pth
    echo [+] Portable Python gotov
) else (
    echo [+] Python ustanovlen v sisteme
)

echo.
echo [2/6] Proverka UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [!] UV ne nayden. Ustanovka...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo [+] UV ustanovlen
) else (
    echo [+] UV uzhe ustanovlen
)

echo.
echo [3/6] Sozdanie virtualnogo okruzheniya...
if not exist .venv (
    uv venv
    echo [+] Virtualnoe okruzhenie sozdano
) else (
    echo [+] Virtualnoe okruzhenie uzhe sushchestvuet
)

echo.
echo [4/6] Ustanovka zavisimostey Python...
call .venv\Scripts\activate.bat
uv pip install -e . -q
echo [+] Zavisimosti ustanovleny

echo.
echo [5/6] PostgreSQL Portable v papke projekta...
if not exist postgres (
    echo [*] Sozdanie portable PostgreSQL...
    
    mkdir postgres\data
    
    echo [*] Skachivanie PostgreSQL (eto zanymet vremya)...
    powershell -Command "Invoke-WebRequest -Uri 'https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64-binaries.zip' -OutFile 'pg_binaries.zip'"
    
    echo [*] Raspakovka PostgreSQL (mozhet zanyat neskolko minut)...
    powershell -Command "Expand-Archive -Path 'pg_binaries.zip' -DestinationPath 'postgres' -Force"
    del pg_binaries.zip
    
    echo [*] Inicializatsiya bazy dannykh...
    postgres\bin\initdb.exe -D postgres\data -U postgres -A trust -E utf8
    
    echo [*] Sozdanie bazy rag_db...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
    timeout /t 5 /nobreak >nul
    postgres\bin\createdb.exe -U postgres rag_db
    
    echo [*] Primenenie skhemy...
    postgres\bin\psql.exe -U postgres -d rag_db -f src\schema.sql
    
    echo [+] PostgreSQL gotov v papke postgres/
) else (
    echo [+] PostgreSQL uzhe sushchestvuet
    echo [*] Zapusk...
    postgres\bin\pg_ctl.exe -D postgres\data -l postgres\log.txt start
)

echo.
echo [6/6] Sozdanie .env fayla...
if not exist .env (
    if exist .env.example (
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
    echo [!] Dobavte svoi API klyuchi v .env fayl
    pause
    notepad .env
) else (
    echo [+] .env uzhe sushchestvuet
)

echo.
echo ==================================================
echo   Gotovo! Vse v papke projekta
echo ==================================================
echo.
echo Dlya zapuska: run_web.bat
echo.
pause
