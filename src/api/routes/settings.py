"""Settings management routes."""

import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.models.requests import SettingsUpdate
from src.api.models.responses import SettingsResponse
from src.api.dependencies import get_settings
from src.settings import Settings, load_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["settings"])


# ============================================================================
# GET SETTINGS
# ============================================================================

@router.get("/settings", response_model=SettingsResponse)
async def get_app_settings(
    settings: Settings = Depends(get_settings)
) -> SettingsResponse:
    """
    Get current application settings.

    Args:
        settings: Application settings

    Returns:
        Current settings (without sensitive data)
    """
    return SettingsResponse(
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        audio_model=getattr(settings, 'audio_model', 'openai/gpt-audio-mini'),
        database_name=settings.database_name,
        llm_api_key_configured=bool(settings.llm_api_key),
        embedding_api_key_configured=bool(settings.embedding_api_key),
        llm_provider=settings.llm_provider,
        embedding_dimension=settings.embedding_dimension
    )


# ============================================================================
# UPDATE SETTINGS
# ============================================================================

@router.put("/settings", response_model=SettingsResponse)
async def update_app_settings(
    settings_data: SettingsUpdate,
    current_settings: Settings = Depends(get_settings)
) -> SettingsResponse:
    """
    Update application settings and save to .env file.

    Args:
        settings_data: Settings to update
        current_settings: Current application settings

    Returns:
        Updated settings

    Raises:
        HTTPException: If update fails
    """
    try:
        env_path = Path(".env")
        lines = []
        existing_keys = set()

        # Build settings dict with all values (new + existing)
        settings_dict = {}

        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key = line.split("=")[0].strip()
                        existing_keys.add(key)

                        # Update with new value if provided, otherwise keep existing
                        if key == "LLM_API_KEY" and settings_data.llm_api_key is not None:
                            line = f"LLM_API_KEY={settings_data.llm_api_key}\n"
                            settings_dict["llm_api_key"] = settings_data.llm_api_key
                        elif key == "LLM_MODEL" and settings_data.llm_model is not None:
                            line = f"LLM_MODEL={settings_data.llm_model}\n"
                            settings_dict["llm_model"] = settings_data.llm_model
                        elif key == "EMBEDDING_API_KEY" and settings_data.embedding_api_key is not None:
                            line = f"EMBEDDING_API_KEY={settings_data.embedding_api_key}\n"
                            settings_dict["embedding_api_key"] = settings_data.embedding_api_key
                        elif key == "EMBEDDING_MODEL" and settings_data.embedding_model is not None:
                            line = f"EMBEDDING_MODEL={settings_data.embedding_model}\n"
                            settings_dict["embedding_model"] = settings_data.embedding_model
                        elif key == "AUDIO_MODEL" and settings_data.audio_model is not None:
                            line = f"AUDIO_MODEL={settings_data.audio_model}\n"
                            settings_dict["audio_model"] = settings_data.audio_model
                        elif key == "DATABASE_URL" and settings_data.database_url is not None:
                            line = f"DATABASE_URL={settings_data.database_url}\n"
                            settings_dict["database_url"] = settings_data.database_url
                        else:
                            # Keep existing value
                            if key == "LLM_API_KEY":
                                settings_dict["llm_api_key"] = line.split("=")[1].strip()
                            elif key == "LLM_MODEL":
                                settings_dict["llm_model"] = line.split("=")[1].strip()
                            elif key == "EMBEDDING_API_KEY":
                                settings_dict["embedding_api_key"] = line.split("=")[1].strip()
                            elif key == "EMBEDDING_MODEL":
                                settings_dict["embedding_model"] = line.split("=")[1].strip()
                            elif key == "AUDIO_MODEL":
                                settings_dict["audio_model"] = line.split("=")[1].strip()
                            elif key == "DATABASE_URL":
                                settings_dict["database_url"] = line.split("=")[1].strip()

                        lines.append(line)
                    else:
                        lines.append(line)

        # Add new keys that weren't in the file
        if settings_data.llm_api_key is not None and "LLM_API_KEY" not in existing_keys:
            lines.append(f"LLM_API_KEY={settings_data.llm_api_key}\n")
        if settings_data.llm_model is not None and "LLM_MODEL" not in existing_keys:
            lines.append(f"LLM_MODEL={settings_data.llm_model}\n")
        if settings_data.embedding_api_key is not None and "EMBEDDING_API_KEY" not in existing_keys:
            lines.append(f"EMBEDDING_API_KEY={settings_data.embedding_api_key}\n")
        if settings_data.embedding_model is not None and "EMBEDDING_MODEL" not in existing_keys:
            lines.append(f"EMBEDDING_MODEL={settings_data.embedding_model}\n")
        if settings_data.audio_model is not None and "AUDIO_MODEL" not in existing_keys:
            lines.append(f"AUDIO_MODEL={settings_data.audio_model}\n")
        if settings_data.database_url is not None and "DATABASE_URL" not in existing_keys:
            lines.append(f"DATABASE_URL={settings_data.database_url}\n")

        # Write updated .env file
        with open(env_path, "w") as f:
            f.writelines(lines)

        logger.info("Settings saved to .env file")

        # Reload and return updated settings
        updated_settings = load_settings()

        return SettingsResponse(
            llm_model=updated_settings.llm_model,
            embedding_model=updated_settings.embedding_model,
            audio_model=getattr(updated_settings, 'audio_model', 'openai/gpt-audio-mini'),
            database_name=updated_settings.database_name,
            llm_api_key_configured=bool(updated_settings.llm_api_key),
            embedding_api_key_configured=bool(updated_settings.embedding_api_key),
            llm_provider=updated_settings.llm_provider,
            embedding_dimension=updated_settings.embedding_dimension
        )

    except Exception as e:
        logger.exception(f"Error updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {e}"
        )
