"""
Document embedding generation for vector search.
Supports OpenRouter embeddings via direct HTTP requests.
"""

import logging
from typing import List, Optional
from datetime import datetime
import httpx

from dotenv import load_dotenv
import openai

from src.ingestion.chunker import DocumentChunk
from src.settings import load_settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize client with settings
settings = load_settings()

# OpenAI client for LLM (not embeddings)
openai_client = openai.AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url
)

EMBEDDING_MODEL = settings.embedding_model
EMBEDDING_API_KEY = settings.embedding_api_key
EMBEDDING_BASE_URL = settings.embedding_base_url


class EmbeddingGenerator:
    """Generates embeddings for document chunks."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        batch_size: int = 100
    ):
        """
        Initialize embedding generator.

        Args:
            model: Embedding model to use
            batch_size: Number of texts to process in parallel
        """
        self.model = model
        self.batch_size = batch_size
        self.api_key = EMBEDDING_API_KEY
        self.base_url = EMBEDDING_BASE_URL

        # Model-specific configurations
        self.model_configs = {
            "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
            "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
            "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
            "openai/text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
        }

        self.config = self.model_configs.get(
            model,
            {"dimensions": 1536, "max_tokens": 8191}
        )

    async def _call_openrouter_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Call OpenRouter embeddings API directly via HTTP.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                }
            )
            response.raise_for_status()
            data = response.json()

            # OpenRouter format: { "data": [ { "embedding": [...] }, ... ] }
            if "data" not in data:
                raise ValueError(f"Unexpected response format: {data}")

            embeddings = [item["embedding"] for item in data["data"]]

            if not embeddings:
                raise ValueError(f"No embeddings in response: {data}")

            return embeddings

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Truncate text if too long
        if len(text) > self.config["max_tokens"] * 4:
            text = text[:self.config["max_tokens"] * 4]

        embeddings = await self._call_openrouter_embeddings([text])
        return embeddings[0]

    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Truncate texts if too long
        processed_texts = []
        for text in texts:
            if len(text) > self.config["max_tokens"] * 4:
                text = text[:self.config["max_tokens"] * 4]
            processed_texts.append(text)

        return await self._call_openrouter_embeddings(processed_texts)

    async def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        progress_callback: Optional[callable] = None
    ) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of document chunks
            progress_callback: Optional callback for progress updates

        Returns:
            Chunks with embeddings added
        """
        if not chunks:
            return chunks

        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Process chunks in batches
        embedded_chunks = []
        total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(chunks), self.batch_size):
            batch_chunks = chunks[i:i + self.batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]

            # Generate embeddings for this batch
            embeddings = await self.generate_embeddings_batch(batch_texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(batch_chunks, embeddings):
                embedded_chunk = DocumentChunk(
                    content=chunk.content,
                    index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata={
                        **chunk.metadata,
                        "embedding_model": self.model,
                        "embedding_generated_at": datetime.now().isoformat()
                    },
                    token_count=chunk.token_count,
                    embedding=embedding
                )
                embedded_chunks.append(embedded_chunk)

            if progress_callback:
                progress_callback(i + len(batch_chunks), len(chunks))

        logger.info(f"Generated {len(embedded_chunks)} embeddings")
        return embedded_chunks


# Singleton instance
_embedder: Optional[EmbeddingGenerator] = None


def get_embedder() -> EmbeddingGenerator:
    """Get or create singleton embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingGenerator()
    return _embedder


def create_embedder(**kwargs) -> EmbeddingGenerator:
    """Create a new embedder instance with custom settings."""
    return EmbeddingGenerator(**kwargs)
