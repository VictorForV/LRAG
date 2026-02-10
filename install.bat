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
echo [1/7] Skachivanie proekta s GitHub...
echo     (chtoby git ne nuzhen byl)
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
echo [2/7] Raspackovka...
powershell -Command "Expand-Archive -Path 'repo.zip' -DestinationPath '.' -Force"

REM Pereimenuem papku
if exist "%GITHUB_REPO%-main" (
    move "%GITHUB_REPO%-main" "%PROJECT_DIR%" >nul 2>&1
)

del repo.zip
echo [OK] Raspackovano

cd "%PROJECT_DIR%"

echo.
echo [3/7] Proverka Python...
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
echo [4/7] Ustanovka UV...
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
echo [5/7] Sozdanie virtualnogo okruzheniya...
if not exist .venv (
    uv venv
    echo [OK] Venv sozdan
) else (
    echo [OK] Venv uzhe est
)

echo.
echo [6/7] Ustanovka zavisimostey...
echo     (Eto mozhet zanyat neskolko minut)
echo.
call .venv\Scripts\activate.bat
uv pip install -e .
echo [OK] Zavisimosti ustanovleny

echo.
echo [7/7] Nastroyka...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
    )
    echo.
    echo [X] NASTROYTE API KLYUCHI V .ENV FAILE
    notepad .env
) else (
    echo [OK] .env uzhe est
)

echo.
echo ==================================================
echo   USTANOVKA ZAVERSHENA!
echo ==================================================
echo.
echo Dlya zapuska: run.bat
echo Dlya obnovleniya: update.bat
echo.
pause
