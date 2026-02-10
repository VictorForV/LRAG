@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==================================================
echo   RAG Knowledge Base - Установщик
echo ==================================================
echo.
echo Этот скрипт скачает проект с GitHub и установит его.
echo.
pause

REM === НАСТРОЙКИ ===
set "GITHUB_REPO=https://github.com/VictorForV/LRAG.git"
set "PROJECT_DIR=LRAG"

REM Проверяем git
git --version >nul 2>&1
if errorlevel 1 (
    echo [!] Git не установлен. Установка...
    powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/git-for-windows/git/main/release/win64/installer/installer.bat | iex"
    if errorlevel 1 (
        echo.
        echo [!] Не удалось установить Git автоматически.
        echo     Скачайте с https://git-scm.com/download/win
        pause
        exit /b 1
    )
)

echo.
echo [1/6] Клонирование проекта с GitHub...
echo.

REM Если папка существует - спрашиваем
if exist "%PROJECT_DIR%" (
    echo [!] Папка %PROJECT_DIR% уже существует
    echo     1 - Удалить и скачать заново
    echo     2 - Использовать существующую
    echo     3 - Отмена
    choice /c 123 /n /m "Ваш выбор: "
    if errorlevel 3 exit /b 0
    if errorlevel 2 goto :SKIP_CLONE
    if errorlevel 1 (
        echo [*] Удаление старой версии...
        rmdir /s /q "%PROJECT_DIR%"
    )
)

git clone "%GITHUB_REPO%" "%PROJECT_DIR%"
if errorlevel 1 (
    echo [!] Ошибка клонирования! Проверьте подключение к интернету.
    pause
    exit /b 1
)
echo [+] Проект скачан

:SKIP_CLONE
cd "%PROJECT_DIR%"

echo.
echo [2/6] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не установлен.
    echo     Скачайте с https://www.python.org/downloads/
    echo     При установке отметьте "Add Python to PATH"
    pause
    exit /b 1
)
echo [+] Python установлен

echo.
echo [3/6] Проверка UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [*] Установка UV (менеджер пакетов)...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo [!] Ошибка установки UV
        pause
        exit /b 1
    )
    echo [*] Закройте это окно и запустите install.bat заново
    pause
    exit /b 0
)
echo [+] UV установлен

echo.
echo [4/6] Создание виртуального окружения...
if not exist ".venv" (
    uv venv
    echo [+] Виртуальное окружение создано
) else (
    echo [+] Виртуальное окружение уже существует
)

echo.
echo [5/6] Установка зависимостей...
call .venv\Scripts\activate.bat
uv pip install -e .
echo [+] Зависимости установлены

echo.
echo [6/6] Настройка...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
    )
    echo.
    echo [!] Настройте API ключи в .env файле
    notepad .env
)

echo.
echo ==================================================
echo   Установка завершена!
echo ==================================================
echo.
echo Для запуска: run.bat
echo.
pause
