@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Update
echo ==================================================
echo.

set "GITHUB_USER=VictorForV"
set "GITHUB_REPO=LRAG"

echo [*] Skachivanie update...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/main.zip' -OutFile 'update.zip'"

if not exist update.zip (
    echo [X] Oshibka! Proverte internet
    pause
    exit /b 1
)

echo [OK] Skachano

echo.
echo [*] Obnovlenie fajlov...
powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath '.update_temp' -Force"

REM Kopiruem novye fajly (zatem sushchestvuyushchie)
xcopy ".update_temp\%GITHUB_REPO%-main\*" ".\" /E /I /Y /H /R

REM Ochischaem
rmdir /s /q ".update_temp"
del update.zip

echo.
echo [+] Update gotov!
echo.
pause
