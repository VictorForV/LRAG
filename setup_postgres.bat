@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   PostgreSQL Portable - Setup
echo ==================================================
echo.
echo PostgreSQL budet ustanovlen v papku postgres/
echo.

if exist postgres (
    echo [!] Papka postgres uzhe sushchestvuet
    pause
    exit /b 0
)

echo [*] Sozdanie portable PostgreSQL...
echo     Eto zanymet neskolko minut...
echo.

mkdir postgres\data

echo [1/3] Skachivanie PostgreSQL...
powershell -Command "Invoke-WebRequest -Uri 'https://sbp.enterprisedb.com/getfile.jsp?fileid=1259243' -OutFile 'pg_binaries.zip' -UserAgent [Microsoft.PowerShell.Commands.PSUserAgent]::Chrome"

if not exist pg_binaries.zip (
    echo [!] Oshibka skachivaniya!
    echo     Skachayte vrochnuchuyu: https://www.enterprisedb.com/download-postgresql-binaries
    pause
    exit /b 1
)

echo [2/3] Raspakovka...
powershell -Command "Expand-Archive -Path 'pg_binaries.zip' -DestinationPath 'postgres' -Force"
del pg_binaries.zip

REM Nahodim papku s binariami (mozhet byt postgres/postgresql-* или postgres/bin)
for /d %%i in (postgres\postgresql-*) do set "PG_BIN=%%i\bin"
if not exist "!PG_BIN!\psql.exe" set "PG_BIN=postgres\bin"
if not exist "!PG_BIN!\psql.exe" (
    echo [!] Ne nayden PostgreSQL bin!
    pause
    exit /b 1
)

echo [3/3] Inicializatsiya BD...
"!PG_BIN!\initdb.exe" -D postgres\data -U postgres -A trust -E utf8 --locale=C

echo.
echo [OK] PostgreSQL gotov!
echo.
echo Dlya zapuska ispolzuyte run.bat
echo ili vruchnuyu:
echo   "!PG_BIN!\pg_ctl.exe" -D postgres\data -l postgres\log.txt start
echo.
pause
