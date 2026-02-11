@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Update ^& Build
echo ==================================================
echo.

REM Backup .env
if exist .env (
    echo Backing up .env...
    copy .env .env.backup >nul
)

echo Pulling from GitHub...
git pull

REM Restore .env
if exist .env.backup (
    copy /Y .env.backup .env >nul
    del .env.backup
)

echo.
echo ==================================================
echo Installing dependencies...
echo ==================================================

uv pip install -r requirements.txt --upgrade

if exist frontend (
    cd frontend
    call npm install
    cd ..
)

echo.
echo ==================================================
echo Building frontend...
echo ==================================================
cd frontend
call npm run build
cd ..

echo.
echo ==================================================
echo Update Complete!
echo ==================================================
echo.
echo Now run: run.bat
echo.
pause
