@echo off
chcp 65001 >nul 2>&1

echo ==================================================
echo   Создание релиза RAG Agent
echo ==================================================
echo.

echo Этот скрипт создаст готовый дистрибутив для распространения.
echo.
pause

REM Настройки
set "VERSION=1.0.0"
set "BUILD_DIR=release"

REM Очистка
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

REM Создаём структуру
mkdir "%BUILD_DIR%\RAG-Agent"

REM Копируем нужные файлы
echo [1/4] Копирование файлов...
xcopy "src" "%BUILD_DIR%\RAG-Agent\src\" /E /I /Y >nul
xcopy "scripts" "%BUILD_DIR%\RAG-Agent\scripts\" /E /I /Y >nul
copy /y "pyproject.toml" "%BUILD_DIR%\RAG-Agent\" >nul
copy /y ".env.example" "%BUILD_DIR%\RAG-Agent\" >nul
copy /y "run_web.bat" "%BUILD_DIR%\RAG-Agent\" >nul
copy /y "stop_postgres.bat" "%BUILD_DIR%\RAG-Agent\" >nul
copy /y "fix_venv.bat" "%BUILD_DIR%\RAG-Agent\" >nul
copy /y "README.md" "%BUILD_DIR%\RAG-Agent\" >nul

REM Создаём установщик
echo [2/4] Создание установщика...
copy /y "install_from_git.bat" "%BUILD_DIR%\RAG-Agent-install.bat" >nul

REM Создаём архив
echo [3/4] Создание архива...
powershell -Command "Compress-Archive -Path '%BUILD_DIR%\RAG-Agent' -DestinationPath 'RAG-Agent-v%VERSION%.zip' -Force"

REM Копируем установщик отдельно (для быстрого доступа)
copy /y "install_from_git.bat" "RAG-Agent-Installer.bat" >nul

echo.
echo [4/4] Готово!
echo.
echo ==================================================
echo   Релиз создан!
echo ==================================================
echo.
echo Файлы:
echo   - RAG-Agent-v%VERSION%.zip    (полный дистрибутив)
echo   - RAG-Agent-Installer.bat     (быстрый установщик с GitHub)
echo.
echo Для распространения:
echo   1. Загрузите RAG-Agent-v%VERSION%.zip на GitHub Releases
echo   2. Пользователи скачивают и запускают RAG-Agent-Installer.bat
echo.
pause
