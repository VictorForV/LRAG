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

REM Kopiruem fajly MINUYA papku LRAG-main
xcopy ".update_temp\%GITHUB_REPO%-main\src" ".\src" /E /I /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\*.bat" ".\" /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\*.sh" ".\" /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\*.toml" ".\" /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\*.md" ".\" /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\.env.example" ".\" /Y /H /R /Q 2>nul
xcopy ".update_temp\%GITHUB_REPO%-main\.gitignore" ".\" /Y /H /R /Q 2>nul

REM Kopiruem frontend build (production)
if exist ".update_temp\%GITHUB_REPO%-main\frontend\dist" (
    xcopy ".update_temp\%GITHUB_REPO%-main\frontend\dist" ".\frontend\dist" /E /I /Y /H /R /Q 2>nul
    echo [OK] Frontend obnovlen
)

REM Ochischaem
rmdir /s /q ".update_temp" 2>nul
del update.zip 2>nul

echo.
echo [+] Update gotov!
echo.
pause
