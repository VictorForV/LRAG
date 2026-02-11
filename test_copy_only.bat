@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Copy Test - SKIP DOWNLOAD/EXTRACT
echo ==================================================
echo.

REM Check if already extracted
if not exist "postgresql-16.1-1-windows-x64-full" (
    echo [ERROR] Folder postgresql-16.1-1-windows-x64-full NOT found!
    echo Please run test_install.bat first to download and extract.
    pause
    exit /b 1
)

echo [OK] Found extracted folder: postgresql-16.1-1-windows-x64-full
echo.
echo [Step 1] Showing structure of SOURCE...
echo.
dir /b "postgresql-16.1-1-windows-x64-full"
echo.

REM Clean target folder
if exist postgres_test rmdir /s /q postgres_test
mkdir postgres_test

echo.
echo [Step 2] Testing different copy methods...
echo.

REM Method 1: Copy pgsql folder
echo [Method 1] xcopy pgsql folder...
xcopy "postgresql-16.1-1-windows-x64-full\pgsql" "postgres_test\pgsql" /E /I /H /Y /S
if exist "postgres_test\pgsql\bin\initdb.exe" (
    echo [OK] Method 1 SUCCESS - pgsql\bin\initdb.exe exists
    dir /b "postgres_test\pgsql" | head -3
) else (
    echo [FAIL] Method 1 FAILED - pgsql\bin\initdb.exe NOT found
)

REM Method 2: Copy root files (excluding pgsql)
echo [Method 2] xcopy root files excluding pgsql...
xcopy "postgresql-16.1-1-windows-x64-full\*" "postgres_test\" /E /I /H /Y /S /EXCLUDE:pgsql\ 2>nul
if exist "postgres_test\bin\pg_ctl.exe" (
    echo [OK] Method 2 SUCCESS - postgres_test\bin\pg_ctl.exe exists
) else (
    echo [FAIL] Method 2 FAILED - postgres_test\bin\pg_ctl.exe NOT found
)

REM Method 3: Try with PowerShell
echo [Method 3] PowerShell Copy-Item...
powershell -Command "Copy-Item -Path 'postgresql-16.1-1-windows-x64-full\pgsql' -Destination 'postgres_test\psql' -Recurse -Force"
if exist "postgres_test\psql\bin\initdb.exe" (
    echo [OK] Method 3 SUCCESS - psql\bin\initdb.exe exists
) else (
    echo [FAIL] Method 3 FAILED - psql\bin\initdb.exe NOT found
)

echo.
echo [Step 3] Final structure check...
echo === Contents of postgres_test ===
dir /b postgres_test
echo.

echo ==================================================
echo   TEST COMPLETE
echo ==================================================
echo.
echo If all methods show SUCCESS, the copy works.
echo If methods show FAIL, check the source folder structure.
echo.
echo Window will stay open. Close manually with X button or Ctrl+C.
