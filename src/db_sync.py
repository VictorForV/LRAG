"""Synchronous wrappers for database operations in Streamlit."""

import asyncio
from typing import Optional, Dict, Any, List
from src.dependencies import (
    db_pool_context,
    create_project,
    list_projects,
    get_project,
    update_project,
    delete_project,
    create_session,
    list_sessions,
    get_session,
    update_session,
    delete_session,
    clear_session_messages,
    add_message,
    get_session_messages,
    get_project_documents,
    delete_document,
)


def run_async(coro):
    """Run async function in Streamlit sync context."""
    return asyncio.run(coro)


# === PROJECT WRAPPERS ===
def sync_create_project(db_url: str, name: str, description: Optional[str] = None) -> str:
    async def _create():
        async with db_pool_context(db_url) as pool:
            return await create_project(pool, name, description)
    return run_async(_create())


def sync_list_projects(db_url: str, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    async def _list():
        async with db_pool_context(db_url) as pool:
            return await list_projects(pool, search, limit)
    return run_async(_list())


def sync_get_project(db_url: str, project_id: str) -> Optional[Dict[str, Any]]:
    async def _get():
        async with db_pool_context(db_url) as pool:
            return await get_project(pool, project_id)
    return run_async(_get())


def sync_update_project(db_url: str, project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> bool:
    async def _update():
        async with db_pool_context(db_url) as pool:
            return await update_project(pool, project_id, name, description)
    return run_async(_update())


def sync_delete_project(db_url: str, project_id: str) -> bool:
    async def _delete():
        async with db_pool_context(db_url) as pool:
            return await delete_project(pool, project_id)
    return run_async(_delete())


# === SESSION WRAPPERS ===
def sync_create_session(db_url: str, project_id: str, title: str = "New Chat") -> str:
    async def _create():
        async with db_pool_context(db_url) as pool:
            return await create_session(pool, project_id, title)
    return run_async(_create())


def sync_list_sessions(db_url: str, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    async def _list():
        async with db_pool_context(db_url) as pool:
            return await list_sessions(pool, project_id, limit)
    return run_async(_list())


def sync_get_session(db_url: str, session_id: str) -> Optional[Dict[str, Any]]:
    async def _get():
        async with db_pool_context(db_url) as pool:
            return await get_session(pool, session_id)
    return run_async(_get())


def sync_update_session(db_url: str, session_id: str, title: Optional[str] = None) -> bool:
    async def _update():
        async with db_pool_context(db_url) as pool:
            return await update_session(pool, session_id, title)
    return run_async(_update())


def sync_delete_session(db_url: str, session_id: str) -> bool:
    async def _delete():
        async with db_pool_context(db_url) as pool:
            return await delete_session(pool, session_id)
    return run_async(_delete())


def sync_clear_session_messages(db_url: str, session_id: str) -> int:
    async def _clear():
        async with db_pool_context(db_url) as pool:
            return await clear_session_messages(pool, session_id)
    return run_async(_clear())


# === MESSAGE WRAPPERS ===
def sync_add_message(db_url: str, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> str:
    async def _add():
        async with db_pool_context(db_url) as pool:
            return await add_message(pool, session_id, role, content, metadata)
    return run_async(_add())


def sync_get_session_messages(db_url: str, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    async def _get():
        async with db_pool_context(db_url) as pool:
            return await get_session_messages(pool, session_id, limit)
    return run_async(_get())


# === DOCUMENT WRAPPERS ===
def sync_get_project_documents(db_url: str, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    async def _get():
        async with db_pool_context(db_url) as pool:
            return await get_project_documents(pool, project_id, limit)
    return run_async(_get())


# === CHECK TABLE EXISTS ===
def sync_check_table_exists(db_url: str, table_name: str) -> bool:
    async def _check():
        async with db_pool_context(db_url) as pool:
            return await pool.fetchval(
                """SELECT EXISTS (
                   SELECT FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = $1
                )""", table_name
            )
    return run_async(_check())


# === DELETE DOCUMENT ===
def sync_delete_document(db_url: str, document_id: str) -> bool:
    async def _delete():
        async with db_pool_context(db_url) as pool:
            return await delete_document(pool, document_id)
    return run_async(_delete())


# === APPLY SCHEMA ===
def sync_apply_schema(db_url: str, schema_path: str = "src/schema.sql") -> bool:
    """Apply schema.sql to database."""
    from pathlib import Path

    schema_file = Path(schema_path)
    if not schema_file.exists():
        return False

    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    async def _apply():
        async with db_pool_context(db_url) as pool:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for stmt in statements:
                if stmt and not stmt.startswith('--'):
                    try:
                        await pool.execute(stmt)
                    except Exception as e:
                        # Ignore duplicate table errors, log others
                        if "already exists" not in str(e):
                            print(f"Warning: {e}")
            return True
    return run_async(_apply())
