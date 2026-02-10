@echo off
chcp 65001 >nul 2>&1

echo Ostanovka portable PostgreSQL...

if exist postgres\bin\pg_ctl.exe (
    echo [*] Ostanovka PostgreSQL...
    postgres\bin\pg_ctl.exe -D postgres\data stop
    echo [+] PostgreSQL ostanovlen
) else (
    echo [!] Portable PostgreSQL ne nayden
    echo    Vozmozhno ispolzuetsya Docker ili sistemnaya ustanovka
)
pause
