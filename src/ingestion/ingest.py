"""
Main ingestion script for processing documents into PostgreSQL with pgvector.

This pipeline ingests documents into PostgreSQL vector database.
"""

import os
import asyncio
import logging
import glob
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass
import asyncpg

from dotenv import load_dotenv

from src.ingestion.chunker import ChunkingConfig, create_chunker, DocumentChunk
from src.ingestion.embedder import create_embedder
from src.settings import load_settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 2000
    max_tokens: int = 512
    project_id: Optional[str] = None
    incremental: bool = True  # Skip documents that already exist


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    errors: List[str]


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into PostgreSQL with pgvector."""

    def __init__(
        self,
        config: IngestionConfig,
        documents_folder: str = "documents",
        clean_before_ingest: bool = True,
        project_id: Optional[str] = None,
        user_settings: Optional[Any] = None
    ):
        """Initialize ingestion pipeline."""
        self.config = config
        self.documents_folder = documents_folder
        self.clean_before_ingest = clean_before_ingest
        self.project_id = project_id or config.project_id
        self.user_settings = user_settings

        # Load settings
        self.settings = load_settings()

        # Initialize PostgreSQL pool
        self.db_pool: Optional[asyncpg.Pool] = None

        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
            max_tokens=config.max_tokens
        )

        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder(user_settings=user_settings)

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize PostgreSQL connection pool."""
        if self._initialized:
            return

        logger.info("Initializing ingestion pipeline...")

        self.db_pool = await asyncpg.create_pool(
            self.settings.database_url,
            min_size=2,
            max_size=10
        )

        logger.info(f"Connected to PostgreSQL: {self.settings.database_name}")
        self._initialized = True
        logger.info("Ingestion pipeline initialized")

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._initialized and self.db_pool:
            await self.db_pool.close()
            self.db_pool = None
            self._initialized = False
            logger.info("PostgreSQL connection closed")

    def _find_document_files(self) -> List[str]:
        """Find all supported document files in the documents folder."""
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
            return []

        patterns = [
            "*.md", "*.markdown", "*.txt",
            "*.pdf",
            "*.docx", "*.doc",
            "*.pptx", "*.ppt",
            "*.xlsx", "*.xls",
            "*.html", "*.htm",
            "*.mp3", "*.wav", "*.m4a", "*.flac",
            "*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff", "*.tif", "*.gif",
        ]
        files = []

        for pattern in patterns:
            files.extend(
                glob.glob(
                    os.path.join(self.documents_folder, "**", pattern),
                    recursive=True
                )
            )

        return sorted(files)

    def _read_document(self, file_path: str) -> tuple[str, Optional[Any]]:
        """Read document content from file - supports multiple formats via Docling."""
        file_ext = os.path.splitext(file_path)[1].lower()

        # Handle image files with OCR
        image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
        if file_ext in image_formats:
            return self._ocr_image(file_path)

        audio_formats = ['.mp3', '.wav', '.m4a', '.flac']
        if file_ext in audio_formats:
            return self._transcribe_audio(file_path)

        docling_formats = [
            '.pdf', '.docx', '.doc', '.pptx', '.ppt',
            '.xlsx', '.xls', '.html', '.htm',
            '.md', '.markdown'
        ]

        if file_ext in docling_formats:
            # For PDF files, use PaddleOCR directly (faster and more reliable for Russian)
            if file_ext == '.pdf':
                logger.info(f"Processing PDF with PaddleOCR: {os.path.basename(file_path)}")
                return self._paddle_ocr_pdf(file_path)

            # Other formats (DOCX, etc.) - use Docling
            try:
                from docling.document_converter import DocumentConverter

                logger.info(f"Converting {file_ext} file using Docling: {os.path.basename(file_path)}")

                converter = DocumentConverter()
                result = converter.convert(file_path)
                markdown_content = result.document.export_to_markdown()

                logger.info(f"Successfully converted {os.path.basename(file_path)} to markdown")
                return (markdown_content, result.document)

            except Exception as e:
                logger.error(f"Failed to convert {file_path} with Docling: {e}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return (f.read(), None)
                except Exception:
                    return (f"[Error: Could not read file {os.path.basename(file_path)}]", None)

        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return (f.read(), None)
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return (f.read(), None)

    def _transcribe_audio(self, file_path: str) -> tuple[str, Optional[Any]]:
        """Transcribe audio file using OpenRouter API (with Whisper fallback)."""
        try:
            from pathlib import Path
            import asyncio

            audio_path = Path(file_path).resolve()
            logger.info(f"Transcribing audio file using OpenRouter: {audio_path.name}")

            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Try OpenRouter transcription first
            try:
                from src.ingestion.audio_transcriber import transcribe_audio_auto
                from src.settings import Settings

                settings = Settings()
                text = asyncio.run(transcribe_audio_auto(str(audio_path), settings))

                # Create a simple markdown document from transcription
                markdown_content = f"# Audio Transcription\n\n**Source:** {audio_path.name}\n\n{text}\n"
                logger.info(f"Successfully transcribed {os.path.basename(file_path)} via OpenRouter")

                return (markdown_content, None)

            except Exception as openrouter_error:
                logger.warning(f"OpenRouter transcription failed: {openrouter_error}, falling back to Whisper")

                # Fallback to Docling Whisper
                from docling.document_converter import DocumentConverter, AudioFormatOption
                from docling.datamodel.pipeline_options import AsrPipelineOptions
                from docling.datamodel.base_models import InputFormat
                from docling.pipeline.asr_pipeline import AsrPipeline

                logger.info(f"Transcribing with Whisper fallback: {audio_path.name}")

                # Create whisper options with Russian language forced
                from docling.datamodel.pipeline_options_asr_model import InlineAsrNativeWhisperOptions
                whisper_opts = InlineAsrNativeWhisperOptions(
                    repo_id='turbo',
                    language='ru',  # Force Russian language
                    verbose=True,
                    timestamps=True,
                    temperature=0.0,
                )

                pipeline_options = AsrPipelineOptions()
                pipeline_options.asr_options = whisper_opts

                converter = DocumentConverter(
                    format_options={
                        InputFormat.AUDIO: AudioFormatOption(
                            pipeline_cls=AsrPipeline,
                            pipeline_options=pipeline_options,
                        )
                    }
                )

                result = converter.convert(audio_path)
                markdown_content = result.document.export_to_markdown()
                logger.info(f"Successfully transcribed {os.path.basename(file_path)} via Whisper fallback")

                return (markdown_content, result.document)

        except Exception as e:
            logger.error(f"Failed to transcribe {file_path}: {e}")
            return (f"[Error: Could not transcribe audio file {os.path.basename(file_path)}]", None)

    def _paddle_ocr_pdf(self, file_path: str) -> tuple[str, Optional[Any]]:
        """Convert PDF to images and OCR with PaddleOCR for better multilingual text recognition."""
        try:
            from paddleocr import PaddleOCR
            from pdf2image import convert_from_path
            import numpy as np

            logger.info(f"Converting PDF to images for PaddleOCR: {os.path.basename(file_path)}")

            # Initialize PaddleOCR (supports Russian + English)
            # lang='ru' for Russian support
            logger.info("Initializing PaddleOCR...")
            ocr = PaddleOCR(lang='ru')  # Russian + Latin

            # Process PDF page by page to save memory
            from pdf2image.pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(file_path)
            page_count = info["Pages"]
            logger.info(f"PDF has {page_count} pages, processing page by page")

            all_text = []

            for page_num in range(1, page_count + 1):
                logger.info(f"Processing page {page_num} of {page_count}...")

                # Convert one page at a time
                images = convert_from_path(
                    file_path,
                    dpi=200,  # Good quality for OCR
                    first_page=page_num,
                    last_page=page_num
                )

                if not images:
                    continue

                # Convert PIL image to numpy array for PaddleOCR
                img_array = np.array(images[0])

                # Run OCR on this page
                result = ocr.ocr(img_array, cls=True)

                # Extract text from result
                # PaddleOCR returns: [[[box], (text, confidence)], ...]
                page_text_lines = []
                if result and result[0]:
                    for line in result[0]:
                        if line and len(line) >= 2:
                            text = line[1][0] if isinstance(line[1], tuple) else line[1]
                            if text and text.strip():
                                page_text_lines.append(text.strip())

                if page_text_lines:
                    page_text = "\n".join(page_text_lines)
                    all_text.append(f"## Page {page_num}\n\n{page_text}")
                    logger.info(f"Page {page_num}: extracted {len(page_text)} characters")

                # Clear memory
                del images
                del img_array

            if not all_text:
                logger.warning(f"No text found in PDF {os.path.basename(file_path)}")
                return (f"[No text detected in PDF {os.path.basename(file_path)}]", None)

            combined_text = "\n\n".join(all_text)
            logger.info(f"Successfully extracted {len(combined_text)} characters from PDF with PaddleOCR")

            # Return as markdown
            markdown_content = f"# {os.path.splitext(os.path.basename(file_path))[0]}\n\n{combined_text}"
            return (markdown_content, None)

        except ImportError as e:
            logger.error(f"PaddleOCR dependencies not installed: {e}")
            return (f"[Error: PaddleOCR not installed. Run: pip install paddleocr paddlepaddle]", None)
        except Exception as e:
            logger.error(f"Failed to process PDF with PaddleOCR: {e}")
            logger.exception("Full traceback:")
            return (f"[Error: Could not process PDF {os.path.basename(file_path)}]", None)

    def _ocr_image(self, file_path: str) -> tuple[str, Optional[Any]]:
        """OCR image file using PaddleOCR."""
        try:
            from paddleocr import PaddleOCR
            import numpy as np
            from PIL import Image

            logger.info(f"Performing PaddleOCR on image file: {os.path.basename(file_path)}")

            # Initialize PaddleOCR
            ocr = PaddleOCR(lang='ru')

            # Open and convert image to numpy array
            image = Image.open(file_path)
            img_array = np.array(image)

            # Run OCR
            result = ocr.ocr(img_array, cls=True)

            # Extract text
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text = line[1][0] if isinstance(line[1], tuple) else line[1]
                        if text and text.strip():
                            text_lines.append(text.strip())

            text = "\n".join(text_lines)

            if not text.strip():
                logger.warning(f"No text found in image {os.path.basename(file_path)}")
                return (f"[No text detected in image {os.path.basename(file_path)}]", None)

            logger.info(f"Successfully extracted {len(text)} characters from {os.path.basename(file_path)}")

            # Return as markdown
            markdown_content = f"# {os.path.splitext(os.path.basename(file_path))[0]}\n\n{text}"
            return (markdown_content, None)

        except ImportError as e:
            logger.error(f"OCR dependencies not installed: {e}")
            return (f"[Error: PaddleOCR not installed. Install: pip install paddleocr paddlepaddle]", None)
        except Exception as e:
            logger.error(f"Failed to OCR {file_path}: {e}")
            return (f"[Error: Could not read image file {os.path.basename(file_path)}]", None)

    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract title from document content or filename."""
        lines = content.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return os.path.splitext(os.path.basename(file_path))[0]

    def _extract_document_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from document content."""
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "ingestion_date": datetime.now().isoformat()
        }

        if content.startswith('---'):
            try:
                import yaml
                end_marker = content.find('\n---\n', 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict):
                        metadata.update(yaml_metadata)
            except ImportError:
                logger.warning("PyYAML not installed, skipping frontmatter extraction")
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")

        lines = content.split('\n')
        metadata['line_count'] = len(lines)
        metadata['word_count'] = len(content.split())

        return metadata

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file for incremental ingestion.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def _save_to_postgresql(
        self,
        title: str,
        source: str,
        content: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any],
        file_hash: Optional[str] = None
    ) -> str:
        """Save document and chunks to PostgreSQL."""
        async with self.db_pool.acquire() as conn:
            # Insert document with project support
            document_id = await conn.fetchval(
                """INSERT INTO documents (title, source, uri, metadata, project_id, file_hash)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6)
                   RETURNING id""",
                title, source, source, json.dumps(metadata),
                self.project_id, file_hash
            )

            logger.info(f"Inserted document with ID: {document_id}")

            # Insert chunks with embeddings
            for chunk in chunks:
                embedding_str = f"[{','.join(map(str, chunk.embedding))}]"
                await conn.execute(
                    """INSERT INTO chunks (document_id, content, embedding, chunk_index, token_count, metadata)
                       VALUES ($1, $2, $3::vector, $4, $5, $6::jsonb)""",
                    document_id, chunk.content, embedding_str, chunk.index,
                    chunk.token_count, json.dumps(chunk.metadata)
                )

            logger.info(f"Inserted {len(chunks)} chunks")

            # Extract and save entities using NER
            await self._save_entities(conn, document_id, content, chunks)

        return str(document_id)

    async def _save_entities(
        self,
        conn,
        document_id: str,
        content: str,
        chunks: List[DocumentChunk]
    ) -> None:
        """Extract and save entities from document content."""
        try:
            from src.ingestion.entity_extractor import get_entity_extractor

            extractor = get_entity_extractor()

            # Extract entities from full document content
            doc_entities = extractor.extract_entities(content)

            # Extract entities from each chunk and save
            for chunk in chunks:
                chunk_entities = extractor.extract_entities(chunk.content)

                # Save entities for this chunk (chunk_id can be NULL for document-level entities)
                for entity in chunk_entities:
                    entity_dict = entity.to_dict()
                    await conn.execute(
                        """INSERT INTO entities (document_id, entity_type, entity_name, entity_text, metadata)
                           VALUES ($1, $2, $3, $4, $5::jsonb)""",
                        document_id,
                        entity_dict['entity_type'],
                        entity_dict['entity_name'][:1000],  # Limit name length
                        entity_dict['entity_text'][:5000],  # Limit text length
                        json.dumps(entity_dict.get('metadata', {}))
                    )

            logger.info(f"Extracted and saved {sum(len(extractor.extract_entities(c.content)) for c in chunks)} entities from chunks")

        except ImportError as e:
            logger.warning(f"Entity extraction not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to extract entities: {e}")

    async def _infer_relations(self, conn, document_id: str, entities: List) -> None:
        """Infer document relations based on extracted entities."""
        # This is a placeholder for future relation inference
        # For now, relations will be manually created or inferred based on document references
        pass

    async def _clean_databases(self) -> None:
        """Clean existing data from PostgreSQL tables."""
        logger.warning("Cleaning existing data from PostgreSQL...")

        async with self.db_pool.acquire() as conn:
            # Get counts before deletion
            entities_count = await conn.fetchval("SELECT COUNT(*) FROM entities")
            relations_count = await conn.fetchval("SELECT COUNT(*) FROM relations")
            chunks_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
            docs_count = await conn.fetchval("SELECT COUNT(*) FROM documents")

            # Delete relations first (foreign key to documents)
            await conn.execute("DELETE FROM relations")
            logger.info(f"Deleted {relations_count or 0} relations")

            # Delete entities (foreign key to chunks/documents)
            await conn.execute("DELETE FROM entities")
            logger.info(f"Deleted {entities_count or 0} entities")

            # Delete chunks first (foreign key constraint)
            await conn.execute("DELETE FROM chunks")
            logger.info(f"Deleted {chunks_count or 0} chunks")

            # Delete documents
            await conn.execute("DELETE FROM documents")
            logger.info(f"Deleted {docs_count or 0} documents")

    async def _ingest_single_document(self, file_path: str) -> IngestionResult:
        """Ingest a single document."""
        start_time = datetime.now()

        # Calculate file hash for incremental ingestion
        file_hash = None
        file_name = os.path.basename(file_path)
        if self.config.incremental:
            file_hash = self._calculate_file_hash(file_path)

            # Check if document already exists
            async with self.db_pool.acquire() as conn:
                existing_row = await conn.fetchrow(
                    """SELECT id, title, ingestion_count
                       FROM documents
                       WHERE source = $1 AND file_hash = $2
                       AND (project_id = $3 OR ($3 IS NULL AND project_id IS NULL))
                       LIMIT 1""",
                    file_name, file_hash, self.project_id
                )

                if existing_row:
                    logger.info(f"Skipping duplicate document: {file_name} (already exists)")
                    # Update ingestion metadata
                    await conn.execute(
                        "UPDATE documents SET last_ingested = NOW(), ingestion_count = ingestion_count + 1 WHERE id = $1",
                        existing_row["id"]
                    )
                    return IngestionResult(
                        document_id=str(existing_row["id"]),
                        title=existing_row["title"],
                        chunks_created=0,
                        processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        errors=[]
                    )

        document_content, docling_doc = self._read_document(file_path)
        document_title = self._extract_title(document_content, file_path)
        document_source = os.path.relpath(file_path, self.documents_folder)

        document_metadata = self._extract_document_metadata(document_content, file_path)

        logger.info(f"Processing document: {document_title}")

        chunks = await self.chunker.chunk_document(
            content=document_content,
            title=document_title,
            source=document_source,
            metadata=document_metadata,
            docling_doc=docling_doc
        )

        if not chunks:
            logger.warning(f"No chunks created for {document_title}")
            return IngestionResult(
                document_id="",
                title=document_title,
                chunks_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created"]
            )

        logger.info(f"Created {len(chunks)} chunks")

        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        document_id = await self._save_to_postgresql(
            document_title, document_source, document_content,
            embedded_chunks, document_metadata, file_hash
        )

        logger.info(f"Saved document to PostgreSQL with ID: {document_id}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return IngestionResult(
            document_id=document_id,
            title=document_title,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
            errors=[]
        )

    async def ingest_documents(
        self,
        progress_callback: Optional[callable] = None
    ) -> List[IngestionResult]:
        """Ingest all documents from the documents folder."""
        if not self._initialized:
            await self.initialize()

        if self.clean_before_ingest:
            await self._clean_databases()

        document_files = self._find_document_files()

        if not document_files:
            logger.warning(f"No supported document files found in {self.documents_folder}")
            return []

        logger.info(f"Found {len(document_files)} document files to process")

        results = []

        for i, file_path in enumerate(document_files):
            try:
                logger.info(f"Processing file {i+1}/{len(document_files)}: {file_path}")

                result = await self._ingest_single_document(file_path)
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, len(document_files))

            except Exception as e:
                logger.exception(f"Failed to process {file_path}: {e}")
                results.append(IngestionResult(
                    document_id="",
                    title=os.path.basename(file_path),
                    chunks_created=0,
                    processing_time_ms=0,
                    errors=[str(e)]
                ))

        # Log summary
        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)

        logger.info(
            f"Ingestion complete: {len(results)} documents, "
            f"{total_chunks} chunks, {total_errors} errors"
        )

        return results


async def main() -> None:
    """Main function for running ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into PostgreSQL with pgvector"
    )
    parser.add_argument("--documents", "-d", default="documents", help="Documents folder path")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning existing data")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens per chunk")
    parser.add_argument("--project-id", "-p", default=None, help="Project ID for documents")
    parser.add_argument("--no-incremental", action="store_true", help="Disable incremental ingestion (reprocess all files)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        max_tokens=args.max_tokens,
        project_id=args.project_id,
        incremental=not args.no_incremental
    )

    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=not args.no_clean,
        project_id=args.project_id
    )

    def progress_callback(current: int, total: int) -> None:
        print(f"Progress: {current}/{total} documents processed")

    try:
        start_time = datetime.now()
        results = await pipeline.ingest_documents(progress_callback)
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        print("\n" + "="*50)
        print("INGESTION SUMMARY")
        print("="*50)
        print(f"Documents processed: {len(results)}")
        print(f"Total chunks created: {sum(r.chunks_created for r in results)}")
        print(f"Total errors: {sum(len(r.errors) for r in results)}")
        print(f"Total processing time: {total_time:.2f} seconds")
        print()

        for result in results:
            status = "[OK]" if not result.errors else "[FAILED]"
            print(f"{status} {result.title}: {result.chunks_created} chunks")
            if result.errors:
                for error in result.errors:
                    print(f"  Error: {error}")

        print("\n" + "="*50)
        print("NEXT STEPS")
        print("="*50)
        print("PostgreSQL with pgvector is ready!")
        print("Run the agent: uv run python -m src.cli")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user")
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
