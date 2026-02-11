#!/usr/bin/env python3
"""
Streamlit Web UI for PostgreSQL RAG Agent

Features:
- Project management (create, list, delete)
- Chat sessions with persistence
- Rich HTML chat rendering
- Drag & drop file upload
- Document management per project
"""

import os
import asyncio
import hashlib
import tempfile
import logging
import traceback
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st
from streamlit_chat import message as st_message
from streamlit.components.v1 import html as st_html

from src.db_sync import (
    sync_create_project,
    sync_list_projects,
    sync_get_project,
    sync_update_project,
    sync_delete_project,
    sync_create_session,
    sync_list_sessions,
    sync_get_session,
    sync_update_session,
    sync_delete_session,
    sync_clear_session_messages,
    sync_add_message,
    sync_get_session_messages,
    sync_get_project_documents,
    sync_check_table_exists,
    sync_delete_document,
    sync_apply_schema,
)
from src.dependencies import calculate_file_hash
from src.settings import Settings, load_settings
from src.agent import rag_agent
from src.ingestion.ingest import (
    DocumentIngestionPipeline,
    IngestionConfig,
    IngestionResult,
)

# Setup logging to see errors in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("=" * 50)
logger.info("Starting RAG Knowledge Base Web UI")
logger.info("=" * 50)


# === PAGE CONFIG ===
st.set_page_config(
    page_title="RAG Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CONTAINER STYLES FOR MAX WIDTH ===
st.markdown("""
<style>
/* Limit main content width for better readability */
.stApp main {
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* Remove excessive padding */
.stApp > div {
    padding-top: 1rem;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
    max-width: 1200px !important;
}
</style>
""", unsafe_allow_html=True)

# === THEME SELECTION ===
def get_theme_colors() -> dict:
    """Get current theme colors based on user preference."""
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"

    is_dark = st.session_state.theme_mode == "dark"

    if is_dark:
        return {
            "bg_primary": "#0f1419",
            "bg_secondary": "#1a1f2e",
            "bg_card": "#1e2433",
            "bg_hover": "#2a3142",
            "text_primary": "#e2e8f0",
            "text_secondary": "#94a3b8",
            "accent": "#6366f1",
            "accent_hover": "#818cf8",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "border": "#2d3748",
            "shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
            "chat_user": "#1e3a5f",
            "chat_assistant": "#1e2433",
        }
    else:
        return {
            "bg_primary": "#f8fafc",
            "bg_secondary": "#ffffff",
            "bg_card": "#ffffff",
            "bg_hover": "#f1f5f9",
            "text_primary": "#1e293b",
            "text_secondary": "#64748b",
            "accent": "#6366f1",
            "accent_hover": "#4f46e5",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "border": "#e2e8f0",
            "shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
            "chat_user": "#e0e7ff",
            "chat_assistant": "#f8fafc",
        }

colors = get_theme_colors()


# === CUSTOM CSS FOR MODERN UI ===
st.markdown(f"""
<style>
/* === RESET & BASE STYLES === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}}

/* Hide Streamlit default elements */
.stApp header {{visibility: hidden;}}
.stApp header {{padding: 0;}}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
.stHeader {{display: none;}}
.stDeployButton {{display: none;}}

/* === MAIN CONTAINER STYLES === */
.stApp main {{
    padding-top: 1rem;
    background-color: {colors['bg_primary']};
}}

/* === SIDEBAR STYLES === */
.css-1d391kg {{
    background: {colors['bg_secondary']} !important;
}}

.css-1d391kg .css-18ni7ap {{
    background-color: {colors['bg_hover']};
    border-radius: 8px;
}}

/* Remove all top padding/margin from sidebar and children */
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] section,
[data-testid="stSidebar"] > div > div > div {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}

/* Remove top spacing from sidebar elements */
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stButton,
[data-testid="stSidebar"] hr {{
    margin-top: 0 !important;
}}

/* === BUTTON STYLES === */
.stButton > button {{
    border-radius: 8px !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    box-shadow: {colors['shadow']} !important;
}}

.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {colors['accent']} 0%, {colors['accent_hover']} 100%) !important;
    color: white !important;
}}

.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, {colors['accent_hover']} 0%, {colors['accent']} 100%) !important;
}}

/* === INPUT STYLES === */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {{
    border-radius: 8px !important;
    border: 1px solid {colors['border']} !important;
    background-color: {colors['bg_card']} !important;
    color: {colors['text_primary']} !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.2s ease !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {colors['accent']} !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    outline: none !important;
}}

/* === CHAT MESSAGE STYLES === */
.chat-message-user {{
    background: linear-gradient(135deg, {colors['chat_user']} 0%, #c7d2fe 100%);
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin-bottom: 12px;
    margin-left: auto;
    margin-right: 0;
    max-width: 75%;
    box-shadow: {colors['shadow']};
    animation: slideInRight 0.3s ease;
}}

.chat-message-assistant {{
    background-color: {colors['chat_assistant']};
    border: 1px solid {colors['border']};
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px;
    margin-bottom: 12px;
    margin-left: 0;
    margin-right: auto;
    max-width: 75%;
    box-shadow: {colors['shadow']};
    animation: slideInLeft 0.3s ease;
}}

@keyframes slideInRight {{
    from {{
        opacity: 0;
        transform: translateX(20px);
    }}
    to {{
        opacity: 1;
        transform: translateX(0);
    }}
}}

@keyframes slideInLeft {{
    from {{
        opacity: 0;
        transform: translateX(-20px);
    }}
    to {{
        opacity: 1;
        transform: translateX(0);
    }}
}}

/* === HTML CONTENT STYLING === */
.chat-message-assistant table {{
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    border-radius: 8px;
    overflow: hidden;
}}

.chat-message-assistant th,
.chat-message-assistant td {{
    border: 1px solid {colors['border']};
    padding: 10px 12px;
    text-align: left;
}}

.chat-message-assistant th {{
    background: linear-gradient(135deg, {colors['bg_hover']} 0%, {colors['bg_secondary']} 100%);
    font-weight: 600;
    color: {colors['text_primary']};
}}

.chat-message-assistant pre {{
    background-color: {colors['bg_secondary']};
    border: 1px solid {colors['border']};
    border-radius: 8px;
    padding: 14px;
    overflow-x: auto;
    margin: 12px 0;
}}

.chat-message-assistant code {{
    background-color: {colors['bg_hover']};
    color: {colors['accent']};
    padding: 3px 6px;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9em;
}}

.chat-message-assistant ul,
.chat-message-assistant ol {{
    margin: 10px 0;
    padding-left: 24px;
}}

.chat-message-assistant li {{
    margin: 6px 0;
    line-height: 1.6;
}}

/* === METRIC CARD STYLES === -->
.stMetric {{
    background-color: {colors['bg_card']};
    border-radius: 12px;
    padding: 1rem;
    border: 1px solid {colors['border']};
    box-shadow: {colors['shadow']};
    transition: all 0.2s ease;
}}

.stMetric:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}}

/* === EXPANDER STYLES === */
.streamlit-expanderHeader {{
    background-color: {colors['bg_card']} !important;
    border-radius: 12px !important;
    border: 1px solid {colors['border']} !important;
    padding: 12px 16px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}}

.streamlit-expanderHeader:hover {{
    background-color: {colors['bg_hover']} !important;
}}

/* === TAB STYLES === */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    background-color: {colors['bg_card']};
    border-radius: 12px;
    padding: 6px;
    border: 1px solid {colors['border']};
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    transition: all 0.2s ease;
}}

.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {colors['accent']} 0%, {colors['accent_hover']} 100%);
    color: white !important;
}}

/* === FILE UPLOADER STYLES === */
.stFileUploader {{
    border: 2px dashed {colors['accent']} !important;
    border-radius: 16px !important;
    background: linear-gradient(135deg, {colors['bg_secondary']} 0%, {colors['bg_hover']} 100%);
    padding: 40px;
    text-align: center;
    transition: all 0.3s ease;
}}

.stFileUploader:hover {{
    border-color: {colors['accent_hover']} !important;
    background: linear-gradient(135deg, {colors['bg_hover']} 0%, {colors['bg_secondary']} 100%);
    transform: scale(1.01);
}}

/* === DIVIDER STYLES === */
.stDivider {{
    border-color: {colors['border']};
    opacity: 0.5;
}}

/* === INFO/SUCCESS/WARNING/ERROR BOXES === */
.stAlert {{
    border-radius: 12px;
    border: none;
    box-shadow: {colors['shadow']};
    padding: 16px 20px;
}}

/* === SPINNER STYLES === */
.stSpinner {{
    border-color: {colors['accent']} !important;
    border-top-color: transparent !important;
}}

/* === CHAT INPUT STYLES === */
.stChatInputContainer {{
    border-radius: 24px;
    border: 2px solid {colors['border']};
    background-color: {colors['bg_card']};
    padding: 8px 16px;
    transition: all 0.2s ease;
}}

.stChatInputContainer:focus-within {{
    border-color: {colors['accent']};
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}}

/* === SCROLLBAR STYLES === */
::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}

::-webkit-scrollbar-track {{
    background: {colors['bg_secondary']};
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb {{
    background: {colors['border']};
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: {colors['accent']};
}}
</style>
""", unsafe_allow_html=True)


# === SESSION STATE INITIALIZATION ===
def init_session_state():
    """Initialize session state variables."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "projects"
    if "current_project" not in st.session_state:
        st.session_state.current_project = None
    if "current_session" not in st.session_state:
        st.session_state.current_session = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


init_session_state()


# === SETTINGS MANAGEMENT ===
def load_app_settings() -> Optional[Settings]:
    """Load settings from .env file."""
    try:
        return load_settings()
    except Exception as e:
        st.error(f"⚠️ Settings error: {e}")
        return None


def save_app_settings(settings: dict) -> None:
    """Save settings to .env file."""
    env_path = Path(".env")
    lines = []
    existing_keys = set()

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key = line.split("=")[0].strip()
                    existing_keys.add(key)
                    if key in settings:
                        lines.append(f"{key}={settings[key]}\n")
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

    for key, value in settings.items():
        if key not in existing_keys:
            lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    st.success("✅ Settings saved! Please restart the application.")


# === HTML RENDERING ===
def render_html_message(content: str, role: str) -> None:
    """
    Render message as rich HTML.

    Args:
        content: Message content (may contain HTML or markdown)
        role: Message role ('user' or 'assistant')
    """
    if role == "user":
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
            <div class="chat-message-user">
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # For assistant, check if content is HTML
        if "<" in content and ">" in content:
            # Content is already HTML
            st.markdown(f"""
            <div class="chat-message-assistant">
                {content}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Content is markdown, render as-is
            st.markdown(content)


# === PROJECTS PAGE ===
def render_projects_page(settings: Settings) -> None:
    """
    Render main projects page with project listing.

    Args:
        settings: Application settings
    """
    # Header row
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown("### 📁 Ваши проекты")
    with col2:
        if st.button("+ Новый", use_container_width=True, type="primary"):
            st.session_state.show_new_project_dialog = True
    with col3:
        if st.button("🔄", use_container_width=True, help="Обновить"):
            st.rerun()
    with col4:
        current_theme = st.session_state.get("theme_mode", "light")
        theme_icon = "🌙" if current_theme == "light" else "☀️"
        if st.button(theme_icon, use_container_width=True, key="theme_projects", help="Переключить тему"):
            st.session_state.theme_mode = "dark" if current_theme == "light" else "light"
            st.rerun()

    # Search bar
    search = st.text_input("🔍", placeholder="Поиск по названию или описанию...", label_visibility="collapsed")

    st.write("")  # Small spacer

    # New project dialog
    if st.session_state.get("show_new_project_dialog", False):
        with st.expander("Создать новый проект", expanded=True):
            name = st.text_input("Название проекта*", placeholder="Мой исследовательский проект")
            description = st.text_area("Описание (необязательно)", placeholder="Опишите ваш проект...")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Создать", type="primary", use_container_width=True):
                    if name:
                        try:
                            project_id = sync_create_project(settings.database_url, name, description)
                            st.success(f"✅ Проект '{name}' создан!")
                            st.session_state.show_new_project_dialog = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Не удалось создать проект: {e}")
                    else:
                        st.warning("Пожалуйста, введите название проекта")
            with col2:
                if st.button("Отмена", use_container_width=True):
                    st.session_state.show_new_project_dialog = False
                    st.rerun()

    # Edit project dialog
    if st.session_state.get("show_edit_project", False):
        project = st.session_state.show_edit_project
        with st.expander("Редактировать проект", expanded=True):
            name = st.text_input("Название", value=project['name'])
            description = st.text_area("Описание", value=project.get('description', '') or '')

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Сохранить", type="primary", use_container_width=True):
                    if name:
                        try:
                            sync_update_project(settings.database_url, project['id'], name, description)
                            st.success(f"✅ Проект '{name}' обновлён!")
                            st.session_state.show_edit_project = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Не удалось обновить: {e}")
            with col2:
                if st.button("Отмена", use_container_width=True):
                    st.session_state.show_edit_project = False
                    st.rerun()

    # Load and display projects
    try:
        projects = sync_list_projects(settings.database_url, search if search else None)

        if not projects:
            st.info("📭 Проекты не найдены. Создайте свой первый проект!")
            return

        # Display project count
        st.caption(f"📊 {len(projects)} {'проект' if len(projects) == 1 else 'проекта' if len(projects) < 5 else 'проектов'}")

        # Project cards as list
        for project in projects:
            # Use panel-like container with st.container
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([4, 1, 1, 1.2, 0.8, 0.8])

                with col1:
                    st.markdown(f"**📂 {project['name']}**")
                    if project['description']:
                        st.caption(project['description'])
                    st.caption(f"🕒 {project['created_at'].strftime('%d %b %Y')}")

                with col2:
                    st.metric("📄", project['doc_count'], help="Документов")

                with col3:
                    st.metric("💬", project['session_count'], help="Чатов")

                with col4:
                    if st.button("Открыть", key=f"open_{project['id']}", use_container_width=True, type="primary"):
                        st.session_state.current_project = project
                        st.session_state.current_page = "workspace"
                        st.rerun()

                with col5:
                    if st.button("✏️", key=f"edit_{project['id']}", use_container_width=True, help="Редактировать"):
                        st.session_state.show_edit_project = project
                        st.rerun()

                with col6:
                    if st.button("🗑️", key=f"del_{project['id']}", use_container_width=True, help="Удалить"):
                        try:
                            sync_delete_project(settings.database_url, project['id'])
                            st.success(f"✅ Проект '{project['name']}' удалён")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Не удалось удалить: {e}")

                st.markdown("---")

    except Exception as e:
        st.error(f"❌ Ошибка загрузки проектов: {e}")


# === PROJECT WORKSPACE ===
def render_project_workspace(settings: Settings) -> None:
    """
    Render project workspace with chat, documents, and upload.

    Args:
        settings: Application settings
    """
    project = st.session_state.current_project
    if not project:
        st.session_state.current_page = "projects"
        st.rerun()
        return

    # Sidebar with project info and sessions
    with st.sidebar:
        # Compact header with no extra spacing
        st.markdown(f"**📂 {project['name']}**")
        if project.get('description'):
            st.caption(project['description'])

        st.markdown("<br style='line-height: 8px;'>", unsafe_allow_html=True)

        # Sessions list
        try:
            sessions = sync_list_sessions(settings.database_url, project['id'])
            logger.info(f"Loaded {len(sessions)} sessions for project {project['id']}")

            if st.button("+ Новый чат", use_container_width=True, key="new_chat_sidebar"):
                # Create new session
                session_id = sync_create_session(settings.database_url, project['id'], "Новый чат")
                st.session_state.current_session = {
                    "id": session_id,
                    "project_id": project['id'],
                    "title": "Новый чат"
                }
                st.session_state.chat_history = []
                st.rerun()

            for idx, session in enumerate(sessions):
                try:
                    # Safely get all session values with defaults
                    session_id = session.get('id')
                    session_title = session.get('title', 'Без названия')
                    message_count = session.get('message_count', 0) or 0

                    # Skip if session_id is missing
                    if not session_id:
                        logger.warning(f"Session {idx} missing id: {session}")
                        continue

                    # Debug logging
                    logger.info(f"Session {idx}: id={session_id}, title={session_title}, msg_count={message_count}, type={type(message_count)}")

                    # Check if this session is active
                    current_session_id = st.session_state.current_session.get('id') if st.session_state.current_session else None
                    is_active = current_session_id == session_id

                    # Truncate title like ChatGPT
                    max_title_length = 30
                    display_title = session_title[:max_title_length] + "..." if len(session_title) > max_title_length else session_title

                    # Two columns: session name and delete button
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        # Build label with truncated title
                        icon = "💬 " if is_active else ""
                        label = f"{icon}{display_title}"

                        if st.button(
                            label,
                            key=f"session_{session_id}",
                            use_container_width=True,
                            disabled=bool(is_active)
                        ):
                            st.session_state.current_session = session
                            # Load messages
                            messages = sync_get_session_messages(settings.database_url, session_id)
                            st.session_state.chat_history = messages
                            st.rerun()

                    with col2:
                        if st.button(
                            "🗑️",
                            key=f"delete_{session_id}",
                            help="Удалить чат",
                            disabled=is_active
                        ):
                            try:
                                sync_delete_session(settings.database_url, session_id)
                                # Clear current session if it was deleted
                                if st.session_state.current_session and st.session_state.current_session.get('id') == session_id:
                                    st.session_state.current_session = None
                                    st.session_state.chat_history = []
                                st.rerun()
                            except Exception as delete_error:
                                st.error(f"❌ Не удалось удалить: {delete_error}")

                except Exception as session_error:
                    error_trace = traceback.format_exc()
                    logger.error(f"Error displaying session {idx}: {session_error}\n{error_trace}")
                    st.error(f"❌ Ошибка отображения чата {idx}: {session_error}")
                    with st.expander("Детали ошибки"):
                        st.code(error_trace)

        except Exception as e:
            logger.exception(f"Error loading sessions: {e}")
            st.error(f"❌ Ошибка загрузки чатов: {e}")

        st.divider()

        # Back button
        if st.button("← Назад к проектам", use_container_width=True):
            st.session_state.current_project = None
            st.session_state.current_session = None
            st.session_state.current_page = "project"
            st.rerun()

        # Project stats
        st.subheader("📊 Статистика")
        try:
            docs = sync_get_project_documents(settings.database_url, project['id'])
            st.metric("Документов", len(docs))
        except:
            pass

    # Main area with tabs
    tab1, tab2, tab3 = st.tabs(["💬 Чат", "📄 Документы", "📤 Загрузить"])

    with tab1:
        render_chat_tab(settings)

    with tab2:
        render_documents_tab(settings)

    with tab3:
        render_upload_tab(settings)


# === CHAT TAB ===
def render_chat_tab(settings: Settings) -> None:
    """
    Render chat interface.

    Args:
        settings: Application settings
    """
    project = st.session_state.current_project
    session = st.session_state.current_session

    # Show message if no session selected
    if not session:
        st.info("💡 Выберите чат из боковой панели или нажмите '+ Новый чат'")
        return

    # Session header
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"### 💬 {session['title']}")

    # Show token count
    estimated_tokens = _estimate_tokens(st.session_state.chat_history)
    max_tokens = 16000  # Typical context limit
    token_percent = min(100, int(estimated_tokens / max_tokens * 100))

    with col2:
        if token_percent > 80:
            st.metric("Токены", f"{estimated_tokens:,}", delta_color="inverse")
            st.caption(f"⚠️ {token_percent}%")
        elif token_percent > 50:
            st.metric("Токены", f"{estimated_tokens:,}")
            st.caption(f"{token_percent}%")
        else:
            st.metric("Токены", f"{estimated_tokens:,}")

    with col3:
        if st.button("✏️ Переименовать", use_container_width=True):
            st.session_state.show_rename_dialog = True

    with col4:
        if st.button("📄 Новый чат", use_container_width=True, help="Сохранить и начать новый чат"):
            st.session_state.show_new_chat_dialog = True

    # Warning for high token usage
    if token_percent > 80:
        st.warning(f"⚠️ Чат становится длинным ({token_percent}% лимита контекста). Рекомендуется начать новый чат.")

    # Rename dialog
    if st.session_state.get("show_rename_dialog", False):
        new_title = st.text_input("Новое название", value=session['title'])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Сохранить", type="primary", key="save_rename"):
                try:
                    sync_update_session(settings.database_url, session['id'], new_title)
                    session['title'] = new_title
                    st.session_state.show_rename_dialog = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        with col2:
            if st.button("Отмена", key="cancel_rename"):
                st.session_state.show_rename_dialog = False
                st.rerun()

    # New chat dialog (save and start new)
    if st.session_state.get("show_new_chat_dialog", False):
        st.info("💡 Текущий чат будет сохранён. Будет создана новая сессия.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Создать новый чат", type="primary", key="confirm_new_chat"):
                try:
                    # Create new session
                    new_session_id = sync_create_session(settings.database_url, project['id'], "Новый чат")
                    # Switch to new session
                    st.session_state.current_session = {
                        "id": new_session_id,
                        "project_id": project['id'],
                        "title": "Новый чат"
                    }
                    st.session_state.chat_history = []
                    st.session_state.show_new_chat_dialog = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        with col2:
            if st.button("Отмена", key="cancel_new_chat"):
                st.session_state.show_new_chat_dialog = False
                st.rerun()

    st.divider()

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            render_html_message(msg['content'], msg['role'])

    # Chat input
    if prompt := st.chat_input("Спросите о ваших документах..."):
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })

        # Save to database
        try:
            sync_add_message(settings.database_url, session['id'], 'user', prompt)
        except:
            pass

        # Get agent response
        with st.spinner("Поиск в документах..."):
            try:
                from src.dependencies import AgentDependencies
                from pydantic_ai.messages import ModelMessage, ModelResponse

                # Create dependencies with project context
                agent_deps = AgentDependencies(
                    project_id=project['id'],
                    session_id=session['id']
                )

                # Build message history from chat_history
                message_history = []
                for msg in st.session_state.chat_history:
                    if msg['role'] == 'user':
                        message_history.append({'role': 'user', 'content': msg['content']})
                    else:
                        message_history.append({'role': 'assistant', 'content': msg['content']})

                async def run_agent():
                    await agent_deps.initialize()
                    result = await rag_agent.run(prompt, deps=agent_deps, message_history=message_history)
                    await agent_deps.cleanup()
                    return result

                # Run agent
                result = asyncio.run(run_agent())
                # Get response text from result
                response = result.output

                # Add assistant message
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response
                })

                # Save to database
                try:
                    sync_add_message(settings.database_url, session['id'], 'assistant', response)
                except:
                    pass

                # Auto-rename session every 3 user messages
                user_message_count = sum(1 for msg in st.session_state.chat_history if msg['role'] == 'user')
                if user_message_count % 3 == 0 and user_message_count > 0:
                    try:
                        new_title = _generate_session_title(st.session_state.chat_history, settings)
                        if new_title and new_title != session['title']:
                            sync_update_session(settings.database_url, session['id'], new_title)
                            session['title'] = new_title
                    except Exception as rename_error:
                        logger.warning(f"Failed to auto-rename session: {rename_error}")

                st.rerun()

            except Exception as e:
                st.error(f"❌ Ошибка: {e}")
                logger.exception("Chat error")


# === DOCUMENTS TAB ===
def render_documents_tab(settings: Settings) -> None:
    """
    Render documents list for current project.

    Args:
        settings: Application settings
    """
    project = st.session_state.current_project

    st.markdown(f"### 📄 Документы в '{project['name']}'")

    try:
        documents = sync_get_project_documents(settings.database_url, project['id'])

        if not documents:
            st.info("📭 В этом проекте нет документов. Загрузите документы для начала работы!")
            return

        st.caption(f"📊 {len(documents)} документов")

        for doc in documents:
            with st.expander(f"📄 {doc['title']}"):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.caption(f"📁 {doc['source']}")
                    st.caption(f"🕒 Первая загрузка: {doc['first_ingested'].strftime('%Y-%m-%d %H:%M')}")
                    if doc['ingestion_count'] > 1:
                        st.caption(f"🔄 Перезагружен {doc['ingestion_count']} раз")

                with col2:
                    st.metric("Чанков", _get_doc_chunk_count(settings, doc['id']))

                with col3:
                    if st.button("🗑️", key=f"delete_doc_{doc['id']}", help="Удалить документ"):
                        try:
                            # Confirm deletion
                            if st.session_state.get(f"confirm_delete_{doc['id']}", False):
                                sync_delete_document(settings.database_url, doc['id'])
                                st.success(f"✅ Документ '{doc['title']}' удалён со всеми связанными данными")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{doc['id']}"] = True
                                st.warning(f"⚠️ Нажмите ещё раз для подтверждения удаления '{doc['title']}'")
                                st.rerun()
                        except Exception as delete_error:
                            st.error(f"❌ Не удалось удалить: {delete_error}")

    except Exception as e:
        st.error(f"❌ Ошибка загрузки документов: {e}")


def _get_doc_chunk_count(settings: Settings, doc_id: str) -> int:
    """Get chunk count for a document."""
    try:
        async def _get():
            async with db_pool_context(settings.database_url) as pool:
                return await pool.fetchval(
                    "SELECT COUNT(*) FROM chunks WHERE document_id = $1",
                    doc_id
                )
        return asyncio.run(_get())
    except Exception as e:
        logger.exception(f"Error getting chunk count: {e}")
        return 0


def _generate_session_title(chat_history: List[Dict], settings: Settings) -> Optional[str]:
    """
    Generate a session title based on chat history using LLM.

    Args:
        chat_history: List of chat messages
        settings: Application settings

    Returns:
        Generated title or None if generation failed
    """
    try:
        import openai

        # Build conversation summary
        conversation = []
        for msg in chat_history[-6:]:  # Last 6 messages (3 exchanges)
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content'][:200]  # Truncate long messages
            conversation.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation)

        # Generate title using LLM
        client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        async def generate():
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a short, descriptive title (max 5 words) for a chat session based on the conversation. Use the same language as the conversation. Return ONLY the title, no quotes or extra text."
                    },
                    {
                        "role": "user",
                        "content": f"Generate a title for this conversation:\n\n{conversation_text}"
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()

        title = asyncio.run(generate())

        # Clean up the title
        # Remove quotes if present
        title = title.strip('"\'')
        # Truncate if too long
        if len(title) > 50:
            title = title[:47] + "..."

        return title

    except Exception as e:
        logger.exception(f"Error generating session title: {e}")
        return None


def _estimate_tokens(chat_history: List[Dict]) -> int:
    """
    Estimate token count for chat history.

    Args:
        chat_history: List of chat messages

    Returns:
        Estimated token count
    """
    total_chars = 0
    for msg in chat_history:
        total_chars += len(msg.get('content', ''))

    # Rough estimate: ~4 chars per token (conservative for mixed languages)
    # Add overhead for role markers and formatting
    return int(total_chars / 3) + len(chat_history) * 10


# === UPLOAD TAB ===
def render_upload_tab(settings: Settings) -> None:
    """
    Render file upload page with drag & drop.

    Args:
        settings: Application settings
    """
    project = st.session_state.current_project

    st.markdown(f"### 📤 Загрузка документов в '{project['name']}'")
    st.caption("Поддерживаемые форматы: PDF, DOCX, TXT, MD, MP3, WAV, изображения и другие")

    # Upload area
    uploaded_files = st.file_uploader(
        "Перетащите файлы сюда или нажмите для выбора",
        type=[
            'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls',
            'txt', 'md', 'html', 'htm',
            'mp3', 'wav', 'm4a', 'flac',
            'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'gif'
        ],
        accept_multiple_files=True,
        key=f"upload_{project['id']}"
    )

    if uploaded_files:
        st.info(f"📁 Выбрано файлов: {len(uploaded_files)}")

        # Show file info
        for file in uploaded_files:
            st.caption(f"  • {file.name} ({file.size / 1024:.1f} KB)")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Загрузить и обработать", type="primary", use_container_width=True):
                with st.spinner("Обработка файлов..."):
                    results = asyncio.run(process_uploaded_files(
                        uploaded_files,
                        project['id'],
                        settings
                    ))

                # Show results summary
                success_count = sum(1 for r in results if r.get('success'))
                error_count = len(results) - success_count

                if error_count == 0:
                    st.success(f"✅ Все {len(results)} файлов успешно обработаны!")
                else:
                    st.warning(f"⚠️ Обработано {len(results)} файлов: {success_count} успешно, {error_count} с ошибками")

                # Show detailed results
                for result in results:
                    if result.get('success'):
                        chunks = result.get('chunks', 0)
                        if chunks > 0:
                            st.info(f"✅ {result['filename']}: создано {chunks} чанков")
                        else:
                            st.warning(f"⚠️ {result['filename']}: 0 чанков (возможно дубликат или пустой файл)")
                    else:
                        st.error(f"❌ {result['filename']}: {result.get('error', 'Неизвестная ошибка')}")
                        # Show full error in expander
                        with st.expander("Детали ошибки"):
                            st.code(str(result.get('error')))
        with col2:
            if st.button("Отмена", use_container_width=True):
                st.rerun()


async def process_uploaded_files(
    files: List,
    project_id: str,
    settings: Settings
) -> List[Dict[str, Any]]:
    """
    Process uploaded files with incremental ingestion.

    Args:
        files: List of uploaded files from Streamlit
        project_id: Project UUID
        settings: Application settings

    Returns:
        List of processing results
    """
    from src.dependencies import db_pool_context

    results = []
    temp_dir = tempfile.mkdtemp()

    try:
        async with db_pool_context(settings.database_url) as pool:
            for file in files:
                try:
                    logger.info(f"Processing file: {file.name} ({file.size / 1024:.1f} KB)")

                    # Save to temp file
                    temp_path = os.path.join(temp_dir, file.name)
                    with open(temp_path, "wb") as f:
                        f.write(file.getbuffer())

                    logger.info(f"Saved to temp: {temp_path}")

                    # Calculate file hash
                    file_hash = calculate_file_hash(temp_path)
                    logger.info(f"File hash: {file_hash[:16]}...")

                    # Check if already exists
                    existing = await _find_document_by_hash(pool, file.name, file_hash, project_id)

                    if existing:
                        logger.info(f"File {file.name} already exists, skipping")
                        results.append({
                            'filename': file.name,
                            'success': True,
                            'chunks': 0,
                            'status': 'skipped (already exists)'
                        })
                    else:
                        # Process document
                        logger.info(f"Starting ingestion for {file.name}")
                        config = IngestionConfig(
                            project_id=project_id,
                            incremental=True
                        )

                        pipeline = DocumentIngestionPipeline(
                            config=config,
                            documents_folder=temp_dir,
                            clean_before_ingest=False,
                            project_id=project_id
                        )
                        await pipeline.initialize()
                        logger.info(f"Pipeline initialized for {file.name}")

                        # Ingest single file
                        doc_result = await pipeline._ingest_single_document(temp_path)

                        logger.info(f"Ingestion result: {doc_result.chunks_created} chunks, {len(doc_result.errors)} errors")

                        await pipeline.close()

                        results.append({
                            'filename': file.name,
                            'success': len(doc_result.errors) == 0,
                            'chunks': doc_result.chunks_created,
                            'status': 'processed',
                            'error': doc_result.errors[0] if doc_result.errors else None
                        })

                        # Clean up temp file
                        os.remove(temp_path)

                except Exception as e:
                    logger.exception(f"Failed to process {file.name}: {e}")
                    results.append({
                        'filename': file.name,
                        'success': False,
                        'error': str(e)
                    })

    finally:
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass

    return results


async def _find_document_by_hash(
    pool,
    file_name: str,
    file_hash: str,
    project_id: str
) -> Optional[Dict[str, Any]]:
    """Find document by hash (reused from dependencies)."""
    row = await pool.fetchrow(
        """SELECT id, title, source, file_hash, ingestion_count
           FROM documents
           WHERE source = $1 AND file_hash = $2 AND project_id = $3""",
        file_name, file_hash, project_id
    )

    if row:
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "source": row["source"],
            "file_hash": row["file_hash"],
            "ingestion_count": row["ingestion_count"]
        }
    return None


# === MAIN APP ===
def main():
    """Main application."""
    logger.info("main() started")

    # Initialize settings in session state
    if "app_settings" not in st.session_state:
        logger.info("Loading app settings...")
        try:
            st.session_state.app_settings = load_app_settings()
            logger.info(f"Settings loaded: {st.session_state.app_settings is not None}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            st.session_state.app_settings = None

    settings = st.session_state.app_settings
    logger.info(f"Settings valid: {settings is not None}")

    # === TOP BAR WITH TITLE & SETTINGS ===
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("### 📚 База знаний RAG")
    with col2:
        if st.button("⚙️", help="Настройки", use_container_width=True):
            st.session_state.show_settings = True

    st.divider()

    # === SETTINGS DIALOG ===
    if st.session_state.get("show_settings", False):
        with st.expander("⚙️ Настройки", expanded=True):
            if not settings:
                try:
                    settings = load_app_settings()
                except:
                    settings = None

            if settings:
                # API Keys
                st.subheader("🔑 API ключи")
                api_key = st.text_input(
                    "API ключ",
                    value=settings.llm_api_key or "",
                    type="password",
                    help="Используется для LLM и эмбеддингов"
                )

                # Models
                st.subheader("🤖 Модели")
                chat_model = st.text_input(
                    "Модель чата",
                    value=settings.llm_model or "anthropic/claude-haiku-4.5",
                    help="Основная модель для чата и запросов"
                )

                embedding_model = st.text_input(
                    "Модель эмбеддингов",
                    value=settings.embedding_model or "qwen/qwen3-embedding-8b",
                    help="Модель для векторных представлений"
                )

                audio_model = st.text_input(
                    "Модель аудио",
                    value=getattr(settings, 'audio_model', 'openai/gpt-audio-mini') or "openai/gpt-audio-mini",
                    help="Модель для транскрибации аудио"
                )

                # Database
                st.subheader("🗄️ База данных")
                db_url = st.text_input(
                    "URL базы данных",
                    value=settings.database_url or "",
                    type="password"
                )

                col_save, col_close = st.columns(2)
                with col_save:
                    if st.button("💾 Сохранить", type="primary", use_container_width=True):
                        save_app_settings({
                            "LLM_API_KEY": api_key,
                            "LLM_MODEL": chat_model,
                            "EMBEDDING_API_KEY": api_key,
                            "EMBEDDING_MODEL": embedding_model,
                            "AUDIO_MODEL": audio_model,
                            "DATABASE_URL": db_url
                        })
                        st.session_state.app_settings = load_app_settings()
                        st.success("✅ Настройки сохранены!")
                        st.rerun()
                with col_close:
                    if st.button("Закрыть", use_container_width=True):
                        st.session_state.show_settings = False
                        st.rerun()
            else:
                st.warning("⚠️ Не удалось загрузить настройки. Проверьте ваш .env файл.")
                st.code("""
# Создайте .env файл с:
DATABASE_URL=postgresql://user:pass@localhost:5432/rag_db
LLM_API_KEY=your-api-key
LLM_MODEL=anthropic/claude-haiku-4.5
EMBEDDING_MODEL=qwen/qwen3-embedding-8b
                """)
                if st.button("Закрыть", use_container_width=True):
                    st.session_state.show_settings = False
                    st.rerun()

        st.divider()

    if not settings:
        st.error("❌ Настройте настройки, нажав кнопку ⚙️ Настройки вверху")
        st.stop()

    # Check if projects table exists - auto-apply schema if not
    try:
        if not sync_check_table_exists(settings.database_url, "projects"):
            st.info("📦 Применение схемы базы данных...")
            if sync_apply_schema(settings.database_url):
                st.success("✅ Схема применена!")
                st.rerun()
            else:
                st.error("❌ Не удалось применить схему. Проверьте файл src/schema.sql")
                st.stop()
    except Exception as e:
        st.error(f"❌ Ошибка базы данных: {e}")
        st.info("Убедитесь что PostgreSQL запущен и .env настроен правильно")
        st.stop()

    # Routing
    if st.session_state.current_page == "projects" or not st.session_state.current_project:
        render_projects_page(settings)
    else:
        render_project_workspace(settings)


if __name__ == "__main__":
    try:
        logger.info("Running main()")
        main()
        logger.info("main() completed successfully")
    except Exception as e:
        logger.error(f"Fatal error in main(): {e}", exc_info=True)
        st.error(f"❌ Критическая ошибка: {e}")
        st.code(traceback.format_exc())
        logger.error(traceback.format_exc())
