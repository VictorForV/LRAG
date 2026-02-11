@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   PostgreSQL Archive Structure Checker
echo ==================================================
echo.
echo This script shows what's inside the PostgreSQL ZIP
echo WITHOUT extracting it.
echo.

if not exist pg_portable.zip (
    echo [*] Downloading PostgreSQL archive to inspect...
    curl -L -o pg_portable.zip "http://45.155.207.234:81/postgresql-16.1-1-windows-x64-full.zip"
    if not exist pg_portable.zip (
        echo [ERROR] Download failed!
        pause
        exit /b 1
    )
)

echo.
echo [*] Listing contents of ZIP file...
echo.

REM Use PowerShell to list archive contents
powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; $zip = [System.IO.Compression.ZipFile]::OpenRead('pg_portable.zip'); foreach($entry in $zip.Entries) { Write-Host $entry.FullName }"

echo.
echo ==================================================
echo   If you see the structure above, compare it to what install.bat expects:
echo.
echo   Expected: postgresql-16.1-1-windows-x64-full\pgsql\bin\
echo   Expected: postgresql-16.1-1-windows-x64-full\bin\
echo.
echo Check if the ZIP has these folders/files!
echo ==================================================
echo.
echo Press any key to keep window open...
