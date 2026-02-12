@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   Rebuilding Frontend
echo ==================================================
echo.

cd frontend

echo [*] Installing dependencies (if needed)...
call npm install

echo.
echo [*] Building frontend...
call npm run build

cd ..

echo.
echo ==================================================
echo   Frontend rebuilt!
echo ==================================================
echo.
pause
