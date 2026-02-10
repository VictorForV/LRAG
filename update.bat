@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   RAG Knowledge Base - Обновление
echo ==================================================
echo.

REM Проверяем, что мы в папке проекта
if not exist ".git" (
    echo [!] Это не папка проекта Git
    echo     Запустите этот скрипт из папки LRAG
    pause
    exit /b 1
)

echo [*] Сохранение текущих изменений...
git stash

echo.
echo [*] Загрузка обновлений с GitHub...
git pull origin main
if errorlevel 1 (
    echo [!] Ошибка обновления! Проверьте подключение к интернету.
    pause
    exit /b 1
)

echo.
echo [*] Обновление зависимостей...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    uv pip install -e . -q
)

echo.
echo [+] Обновление завершено!
echo.
echo Для запуска: run.bat
echo.
pause
