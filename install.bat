@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Ustanovschik
echo ==================================================
echo.
echo Etot skript skachaet proekt s GitHub i ustanovit ego.
echo.
pause

REM === NASTROYKI ===
set "GITHUB_REPO=https://github.com/VictorForV/LRAG.git"
set "PROJECT_DIR=LRAG"

echo.
echo [1/6] Proverka Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [!] Git ne ustanovlen.
    echo     Skachayte s: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
echo [+] Git ustanovlen

echo.
echo [2/6] Klonirovanie proekta s GitHub...
echo.

REM Esli papka sushchestvuet - sprashivaem
if exist "%PROJECT_DIR%" (
    echo [!] Papka %PROJECT_DIR% uzhe sushchestvuet
    echo.
    echo     1 - Udalit i skachat' zanovo
    echo     2 - Ispol'zovat' sushchestvuyushchuyu
    echo     3 - Otmena
    echo.

    set /p choice="Vash vybor (1-3): "
    if "!choice!"=="3" (
        echo.
        echo Otmeneno.
        pause
        exit /b 0
    )
    if "!choice!"=="2" goto :SKIP_CLONE
    if "!choice!"=="1" (
        echo [*] Udalenie staroy versii...
        rmdir /s /q "%PROJECT_DIR%" 2>nul
    )
)

git clone "%GITHUB_REPO%" "%PROJECT_DIR%"
if errorlevel 1 (
    echo [!] Oshibka klonirovaniya! Proverte podklyuchenie k internetu.
    pause
    exit /b 1
)
echo [+] Proekt skachan

:SKIP_CLONE
cd "%PROJECT_DIR%"

echo.
echo [3/6] Proverka Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python ne ustanovlen.
    echo     Skachayte s: https://www.python.org/downloads/
    echo     Pri ustanovke otmet'te "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [+] Python ustanovlen

echo.
echo [4/6] Proverka UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [*] Ustanovka UV (menedzher paketov)...
    echo     Eto mozhet zanyat' neskol'ko sekund...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo [!] Oshibka ustanovki UV
        pause
        exit /b 1
    )
    echo.
    echo [*] ZAKROYTE ETE OKNO I ZAPUSTITE INSTALL.BAT ZANOVO
    echo     (nuzhno perzagruzit' komandnuyu stroku)
    pause
    exit /b 0
)
echo [+] UV ustanovlen

echo.
echo [5/6] Sozdanie virtual'nogo okruzheniya...
if not exist ".venv" (
    uv venv
    if errorlevel 1 (
        echo [!] Oshibka sozdaniya virtual'nogo okruzheniya
        pause
        exit /b 1
    )
    echo [+] Virtual'noe okruzhenie sozdano
) else (
    echo [+] Virtual'noe okruzhenie uzhe sushchestvuet
)

echo.
echo [6/6] Ustanovka zavisimostey...
echo     Eto mozhet zanyat' neskol'ko minut...
echo.
call .venv\Scripts\activate.bat
uv pip install -e .
if errorlevel 1 (
    echo [!] Oshibka ustanovki zavisimostey
    pause
    exit /b 1
)
echo [+] Zavisimosti ustanovleny

echo.
echo [7/7] Nastroyka...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
    )
    echo.
    echo [!] Nastroyte API klyuchi v .env faile
    notepad .env
) else (
    echo [+] .env uzhe sushchestvuet
)

echo.
echo ==================================================
echo   USTANOVKA ZAVERSHENA!
echo ==================================================
echo.
echo Dlya zapuska: run.bat
echo.
pause
