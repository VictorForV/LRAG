# RAG Knowledge Base

Agentic RAG система с PostgreSQL + pgvector. Документы загружаются, векторизуются и доступны для поиска через AI-агента.

**Tech Stack:**
- Backend: Python, FastAPI, PostgreSQL + pgvector, Pydantic AI
- Frontend: React, Vite, Tailwind CSS, shadcn/ui
- AI: OpenAI-compatible API (OpenRouter, OpenAI, и т.д.)

---

## Установка

### Windows (Портабл версия)

1. **Клонируй репозиторий**
   ```bash
   git clone <repo-url>
   cd MongoDB-RAG-Agent
   ```

2. **Запусти установку**
   ```bash
   install.bat
   ```
   
   Это создаст виртуальное окружение, установит Python и Node.js зависимости, и соберёт фронтенд.

3. **Настрой `.env`**
   ```bash
   copy .env.example .env
   # Отредактируй .env с твоими API ключами
   ```

4. **Запуск**
   ```bash
   run.bat
   ```
   
   Приложение будет доступно на: http://localhost:8888

---

## Флоу разработки

### Дев режим (WSL/Linux)

Для разработки используем горячую перезагрузку без сборки:

```bash
./run.sh
```

Запускает:
- Backend на http://localhost:8888 (с auto-reload)
- Frontend на http://localhost:5174 (с HMR)

Изменения в коде применяются мгновенно.

### Публикация релиза

Когда готова новая версия:

1. **Собери фронтенд**
   ```bash
   cd frontend && npm run build && cd ..
   ```
   
   Создаётся `frontend/dist/` с собранным фронтендом.

2. **Закоммить в гит**
   ```bash
   git add .
   git commit -m "Release v1.X.X"
   git push
   ```
   
   В гит уходит исходники + `frontend/dist/`.

### Обновление на другом компе (Windows)

**Первичная установка:**
```bash
git clone <repo-url>
cd MongoDB-RAG-Agent
install.bat
```

**Обновление до новой версии:**
```bash
update.bat
```

Скрипт:
- Стянет последние изменения с гита
- Обновит зависимости
- Соберёт фронтенд
- Предложит запустить `run.bat`

---

## Структура проекта

```
MongoDB-RAG-Agent/
├── src/
│   ├── api/              # FastAPI backend (новый)
│   │   ├── routes/       # API endpoints
│   │   ├── models/       # Pydantic модели
│   │   └── dependencies.py
│   ├── web_api.py        # FastAPI приложение
│   ├── web_ui.py         # Streamlit UI (старый, можно удалить)
│   ├── db_sync.py        # Обёртки для БД
│   ├── agent.py          # Pydantic AI агент
│   ├── dependencies.py   # Зависимости агента
│   └── ingestion/        # Загрузка документов
├── frontend/
│   ├── src/              # React исходники
│   ├── dist/             # Собранный фронтенд (коммитится в гит)
│   └── package.json
├── run.sh                # Дев режим (WSL/Linux)
├── run.bat               # Прод режим (Windows)
├── update.bat            # Обновление (Windows)
└── install.bat           # Установка (Windows)
```

---

## API Endpoints

### Projects
- `GET /api/projects` - Список проектов
- `POST /api/projects` - Создать проект
- `GET /api/projects/{id}` - Детали проекта
- `PUT /api/projects/{id}` - Обновить проект
- `DELETE /api/projects/{id}` - Удалить проект

### Sessions
- `GET /api/projects/{pid}/sessions` - Список сессий
- `POST /api/projects/{pid}/sessions` - Создать сессию
- `PUT /api/sessions/{id}` - Переименовать
- `DELETE /api/sessions/{id}` - Удалить

### Messages
- `GET /api/sessions/{sid}/messages` - История чата
- `POST /api/sessions/{sid}/messages` - Добавить сообщение

### Documents
- `GET /api/projects/{pid}/documents` - Список документов
- `POST /api/projects/{pid}/upload` - Загрузить файлы
- `DELETE /api/documents/{id}` - Удалить документ

### Chat
- `POST /api/chat/stream` - SSE стриминг чата

### Settings
- `GET /api/settings` - Получить настройки
- `PUT /api/settings` - Обновить настройки

---

## Переменные окружения (.env)

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/rag_kb

# LLM API
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=anthropic/claude-haiku-4.5
LLM_BASE_URL=https://openrouter.ai/api/v1

# Embeddings
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Audio transcription
AUDIO_MODEL=openai/gpt-audio-mini
```

---

## Поддерживаемые форматы документов

- **Документы:** PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, TXT, MD, HTML
- **Изображения:** JPG, PNG, BMP, TIFF (с OCR)
- **Аудио:** MP3, WAV, M4A, FLAC (транскрибация)

---

## Портбили

- Backend API: **8888**
- Frontend dev: **5174**

(Порты изменены с 8000/5173 чтобы избежать конфликтов)

---

## Лицензия

MIT
