"""Chat streaming routes with Server-Sent Events."""

import logging
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic_ai.messages import ModelMessage

from src.api.models.requests import ChatRequest
from src.api.models.responses import ChatChunkEvent
from src.api.dependencies import get_agent_dependencies, get_db_pool
from src.agent import rag_agent
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ============================================================================
# STREAM CHAT ENDPOINT
# ============================================================================

@router.post("/chat/stream")
async def stream_chat(
    request_data: ChatRequest,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> StreamingResponse:
    """
    Stream chat response using Server-Sent Events.

    Args:
        request_data: Chat request with session, project, message, and history
        pool: Database connection pool

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If request fails
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for chat streaming."""
        user_message_id = None
        assistant_message_id = None

        try:
            # 1. Save user message
            user_message_id = await pool.fetchval(
                """INSERT INTO chat_messages (session_id, role, content, metadata)
                   VALUES ($1, 'user', $2, '{}'::jsonb) RETURNING id""",
                request_data.session_id,
                request_data.message
            )

            # 2. Send start event
            event = ChatChunkEvent(event="start", session_id=request_data.session_id)
            yield f"event: start\ndata: {event.model_dump_json()}\n\n"

            # 3. Run agent and stream response
            agent_deps = None
            try:
                # Get dependencies
                from src.api.dependencies import get_settings
                from src.settings import Settings

                settings = Settings()
                agent_deps = get_agent_dependencies.__wrapped__(
                    project_id=request_data.project_id,
                    session_id=request_data.session_id,
                    settings=settings
                )
                await agent_deps.initialize()

                # Build message history
                message_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request_data.message_history
                ]

                # Run agent (non-streaming for now - can upgrade to streaming later)
                result = await rag_agent.run(
                    request_data.message,
                    deps=agent_deps,
                    message_history=message_history
                )

                response_text = result.output

                # Send chunk events
                # For now, send full response as one chunk
                # TODO: Upgrade to true streaming when pydantic_ai supports it
                chunk_event = ChatChunkEvent(event="chunk", content=response_text)
                yield f"event: chunk\ndata: {chunk_event.model_dump_json()}\n\n"

                # 4. Save assistant message
                assistant_message_id = await pool.fetchval(
                    """INSERT INTO chat_messages (session_id, role, content, metadata)
                       VALUES ($1, 'assistant', $2, '{}'::jsonb) RETURNING id""",
                    request_data.session_id,
                    response_text
                )

                # 5. Send done event
                done_event = ChatChunkEvent(
                    event="done",
                    content=response_text,
                    session_id=request_data.session_id,
                    message_id=assistant_message_id
                )
                yield f"event: done\ndata: {done_event.model_dump_json()}\n\n"

            finally:
                # Clean up agent dependencies
                if agent_deps:
                    await agent_deps.cleanup()

        except Exception as e:
            logger.exception(f"Error in chat streaming: {e}")
            error_event = ChatChunkEvent(event="error", content=str(e))
            yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# NON-STREAMING CHAT ENDPOINT (fallback)
# ============================================================================

@router.post("/chat")
async def chat(
    request_data: ChatRequest,
    pool: asyncpg.Pool = Depends(get_db_pool)
) -> dict:
    """
    Non-streaming chat endpoint (fallback for clients that don't support SSE).

    Args:
        request_data: Chat request with session, project, message, and history
        pool: Database connection pool

    Returns:
        Dictionary with response content
    """
    try:
        # Save user message
        await pool.fetchval(
            """INSERT INTO chat_messages (session_id, role, content, metadata)
               VALUES ($1, 'user', $2, '{}'::jsonb) RETURNING id""",
            request_data.session_id,
            request_data.message
        )

        # Run agent
        from src.settings import Settings

        settings = Settings()
        agent_deps = get_agent_dependencies.__wrapped__(
            project_id=request_data.project_id,
            session_id=request_data.session_id,
            settings=settings
        )
        await agent_deps.initialize()

        try:
            # Build message history
            message_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request_data.message_history
            ]

            result = await rag_agent.run(
                request_data.message,
                deps=agent_deps,
                message_history=message_history
            )

            response_text = result.output

        finally:
            await agent_deps.cleanup()

        # Save assistant message
        await pool.fetchval(
            """INSERT INTO chat_messages (session_id, role, content, metadata)
               VALUES ($1, 'assistant', $2, '{}'::jsonb) RETURNING id""",
            request_data.session_id,
            response_text
        )

        return {
            "content": response_text,
            "session_id": request_data.session_id
        }

    except Exception as e:
        logger.exception(f"Error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {e}"
        )
