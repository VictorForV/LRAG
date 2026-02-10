#!/usr/bin/env python3
"""
Audio transcription using OpenRouter API with proxy support.

Supports openai/gpt-audio-mini through OpenRouter's proxy.
Falls back to local Whisper if OpenRouter fails.
"""

import os
import base64
import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
from pydub import AudioSegment

from src.settings import Settings


async def transcribe_audio(
    audio_path: str,
    model: str = "openai/gpt-audio-mini",
    api_key: Optional[str] = None,
    proxy_url: Optional[str] = None
) -> str:
    """
    Transcribe audio file using OpenRouter API with proxy support.

    Args:
        audio_path: Path to audio file (mp3, wav, m4a, etc.)
        model: Model name for transcription (default: openai/gpt-audio-mini)
        api_key: OpenRouter API key (optional, uses env if not provided)
        proxy_url: Proxy URL for OpenRouter access (optional, format: http://user:pass@host:port)

    Returns:
        Transcribed text

    Raises:
        ValueError: If audio file doesn't exist
        RuntimeError: If transcription fails
    """
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise ValueError(f"Audio file not found: {audio_path}")

    # Get API key
    if not api_key:
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OpenRouter API key not found. Set LLM_API_KEY in .env")

    # Get proxy URL from parameter or settings
    if not proxy_url:
        proxy_url = os.getenv("OPENROUTER_PROXY_URL")

    # Check file size - if too large, split into chunks
    file_size_mb = audio_file.stat().st_size / 1024 / 1024
    chunk_duration_minutes = 10  # 10 minutes per chunk

    if file_size_mb > 20:  # Split if larger than 20 MB
        print(f"File is large ({file_size_mb:.1f} MB), splitting into {chunk_duration_minutes}-minute chunks...")
        return await _transcribe_audio_chunks(audio_path, model, api_key, proxy_url, chunk_duration_minutes)

    # Read and encode audio
    with open(audio_file, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")

    # Get audio format
    audio_format = audio_file.suffix.lower().lstrip(".")
    if audio_format == "m4a":
        audio_format = "mp4"

    # Determine URL and proxy based on whether proxy_url contains '@'
    if proxy_url and '@' in proxy_url:
        # Using OpenRouter with proxy
        url = "https://openrouter.ai/api/v1/chat/completions"
        proxy = proxy_url
        print(f"Using OpenRouter via proxy")
    else:
        # Direct connection to OpenRouter (no proxy)
        url = "https://openrouter.ai/api/v1/chat/completions"
        proxy = None
        print(f"Using OpenRouter direct (no proxy)")

    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/victorlizard/MongoDB-RAG-Agent",
        "X-Title": "RAG Knowledge Base"
    }

    # Payload for openai/gpt-audio-mini
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this audio recording accurately. Return only the transcribed text in the original language (Russian or English) without any additional commentary or formatting."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": audio_format
                        }
                    }
                ]
            }
        ]
    }

    # Make request with aiohttp
    timeout = aiohttp.ClientTimeout(total=300)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload, proxy=proxy) as response:
                data = await response.json()

                if response.status != 200:
                    error_msg = data.get('error', str(data))
                    raise RuntimeError(f"OpenRouter API error ({response.status}): {error_msg}")

                text = data["choices"][0]["message"]["content"].strip()
                return text

    except aiohttp.ClientError as e:
        raise RuntimeError(f"Audio transcription failed (network error): {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Audio transcription failed (invalid response): {e}")
    except Exception as e:
        raise RuntimeError(f"Audio transcription failed: {e}")


async def _transcribe_audio_chunks(
    audio_path: str,
    model: str,
    api_key: str,
    proxy_url: Optional[str],
    chunk_duration_minutes: int = 10
) -> str:
    """
    Split audio into chunks and transcribe each chunk separately via OpenRouter.

    Args:
        audio_path: Path to audio file
        model: OpenRouter model name
        api_key: OpenRouter API key
        proxy_url: Proxy URL for OpenRouter access
        chunk_duration_minutes: Duration of each chunk in minutes

    Returns:
        Combined transcribed text from all chunks
    """
    import math

    audio_file = Path(audio_path)
    all_text = []

    try:
        # Load audio file
        print(f"Loading audio file: {audio_file.name}")
        audio = AudioSegment.from_file(str(audio_file))

        duration_ms = len(audio)
        chunk_duration_ms = chunk_duration_minutes * 60 * 1000
        total_chunks = math.ceil(duration_ms / chunk_duration_ms)

        print(f"Total duration: {duration_ms / 1000 / 60:.1f} minutes")
        print(f"Splitting into {total_chunks} chunks of {chunk_duration_minutes} minutes each")

        # Determine URL and proxy
        if proxy_url and '@' in proxy_url:
            url = "https://openrouter.ai/api/v1/chat/completions"
            proxy = proxy_url
        else:
            url = "https://openrouter.ai/api/v1/chat/completions"
            proxy = None

        # Headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/victorlizard/MongoDB-RAG-Agent",
            "X-Title": "RAG Knowledge Base"
        }

        # Process each chunk
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i in range(total_chunks):
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, duration_ms)

                chunk = audio[start_ms:end_ms]
                chunk_size_mb = len(chunk) / 1024 / 1024

                print(f"\n[Chunk {i+1}/{total_chunks}] Duration: {len(chunk) / 1000:.1f}s, Size: {chunk_size_mb:.1f} MB")

                # Export chunk to bytes
                import io
                chunk_buffer = io.BytesIO()
                chunk.export(chunk_buffer, format="mp3")
                chunk_data = chunk_buffer.getvalue()

                # Encode to base64
                chunk_base64 = base64.b64encode(chunk_data).decode("utf-8")

                # Prepare payload
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Transcribe this audio recording accurately. Return only the transcribed text in the original language."
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": chunk_base64,
                                        "format": "mp3"
                                    }
                                }
                            ]
                        }
                    ]
                }

                # Send request
                async with session.post(url, headers=headers, json=payload, proxy=proxy) as response:
                    data = await response.json()

                    if response.status != 200:
                        error_msg = data.get('error', str(data))
                        print(f"✗ Chunk {i+1} failed: {error_msg}")
                        all_text.append(f"[Error transcribing chunk {i+1}]")
                        continue

                    chunk_text = data["choices"][0]["message"]["content"].strip()
                    print(f"✓ Got {len(chunk_text)} characters")
                    all_text.append(chunk_text)

        # Combine all chunks with spacing
        combined = " ".join(all_text)
        print(f"\n✓ Total transcribed: {len(combined)} characters")
        return combined

    except ImportError:
        raise RuntimeError("pydub not installed. Install with: pip install pydub")
    except Exception as e:
        raise RuntimeError(f"Chunked transcription failed: {e}")


# === FALLBACK: Local Whisper (if OpenRouter fails) ===
async def transcribe_audio_whisper(audio_path: str) -> str:
    """
    Fallback transcription using local Whisper.
    Only used if OpenRouter transcription fails or is not configured.

    Args:
        audio_path: Path to audio file

    Returns:
        Transcribed text
    """
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result["text"]
    except ImportError:
        raise RuntimeError("Whisper not installed. Run: pip install openai-whisper")
    except Exception as e:
        raise RuntimeError(f"Whisper transcription failed: {e}")


async def transcribe_audio_auto(audio_path: str, settings: Optional[Settings] = None) -> str:
    """
    Transcribe audio using the best available method.

    Tries in order:
    1. OpenRouter with configured audio model (with proxy if configured)
    2. Fallback to local Whisper

    Args:
        audio_path: Path to audio file
        settings: Application settings (optional)

    Returns:
        Transcribed text
    """
    if settings is None:
        from src.settings import Settings
        settings = Settings()

    # Get audio model from settings or use default
    audio_model = getattr(settings, 'audio_model', None) or os.getenv("AUDIO_MODEL", "openai/gpt-audio-mini")

    # Get proxy URL from settings
    proxy_url = getattr(settings, 'openrouter_proxy_url', None) or os.getenv("OPENROUTER_PROXY_URL")

    # Try OpenRouter first
    try:
        return await transcribe_audio(
            audio_path,
            model=audio_model,
            api_key=settings.llm_api_key,
            proxy_url=proxy_url
        )
    except Exception as e:
        print(f"OpenRouter transcription failed: {e}, trying Whisper fallback...")

    # Fallback to Whisper
    return await transcribe_audio_whisper(audio_path)


# === CLI for testing ===
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python audio_transcriber.py <audio_file>")
            print("\nExample:")
            print("  python audio_transcriber.py recording.mp3")
            print("\nEnvironment variables:")
            print("  LLM_API_KEY=sk-or-v1-...")
            print("  OPENROUTER_PROXY_URL=http://user:pass@host:port")
            sys.exit(1)

        audio_file = sys.argv[1]

        print(f"Transcribing: {audio_file}")
        print("-" * 50)

        try:
            text = await transcribe_audio_auto(audio_file)
            print(text)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    asyncio.run(main())
