#!/bin/bash
# Создаёт дистрибутив RAG Agent
# Упаковывает только нужные файлы, исключая лишнее

echo "Создание дистрибутива RAG Agent..."

# Временная папка
DIST_DIR="dist/RAG-Agent"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Файлы для включения
INCLUDE_FILES=(
    "src/"
    "pyproject.toml"
    ".env.example"
    "src/schema.sql"
    "src/migration_add_projects.sql"
    "run_web.bat"
    "stop_postgres.bat"
    "fix_venv.bat"
    "scripts/"
)

# Файлы для исключения
EXCLUDE_PATTERNS=(
    ".venv"
    "__pycache__"
    "*.pyc"
    ".git"
    "documents/"
    "postgres/"
    "python/"
    "*.db"
    "*.log"
)

# Копируем файлы
echo "Копирование файлов..."
for item in "${INCLUDE_FILES[@]}"; do
    if [ -e "$item" ]; then
        cp -r "$item" "$DIST_DIR/"
        echo "  ✓ $item"
    fi
done

# Создаём список файлов для скачивания
cd "$DIST_DIR"
find . -type f > filelist.txt
echo "Создан список файлов"

# Возвращаемся
cd -

echo "Дистрибутив готов в: $DIST_DIR"
echo "Теперь создайте архив и загрузите на GitHub Releases"
