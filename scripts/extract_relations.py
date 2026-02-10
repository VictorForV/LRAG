"""
Extract and save document relations using Gemini 2.5 Flash Lite.

Run this after document ingestion to build the knowledge graph.
"""

import asyncio
import asyncpg
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from src.ingestion.relation_extractor import get_relation_extractor
from src.settings import load_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_and_save_relations(
    max_pairs: int = 100,
    confidence_threshold: float = 0.5
) -> None:
    """
    Extract relations between documents and save to database.
    """
    settings = load_settings()

    logger.info("Starting relation extraction...")

    # Connect to database
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='victor',
        password='123456',
        database='rag_db'
    )

    try:
        # Get all documents with their entities
        logger.info("Fetching documents and entities...")
        rows = await conn.fetch('''
            SELECT
                d.id,
                d.title,
                d.source
            FROM documents d
            ORDER BY d.title
        ''')

        documents = []

        for row in rows:
            # Get entities for this document
            entities = await conn.fetch('''
                SELECT DISTINCT entity_type, entity_name
                FROM entities
                WHERE document_id = $1
                  AND entity_type IN ('ORG', 'PER', 'DOC_REF', 'DATE', 'MONEY')
                ORDER BY entity_type, entity_name
                LIMIT 100
            ''', row['id'])

            entities_list = [
                {"entity_type": e[0], "entity_name": e[1]}
                for e in entities
            ]

            documents.append({
                "id": str(row["id"]),
                "title": row["title"],
                "source": row["source"],
                "entities": entities_list
            })

        logger.info(f"Loaded {len(documents)} documents")

        # Extract relations
        extractor = get_relation_extractor()

        logger.info(f"Analyzing up to {max_pairs} document pairs...")
        relations = await extractor.extract_relations_batch(documents, max_pairs)

        logger.info(f"Found {len(relations)} relations")

        # Filter by confidence
        high_confidence = [
            r for r in relations
            if r.get("confidence", 0) >= confidence_threshold
            and r["relation_type"] != "NONE"
        ]

        logger.info(f"High-confidence relations: {len(high_confidence)}")

        # Save to database
        saved_count = 0
        for relation in high_confidence:
            try:
                await conn.execute('''
                    INSERT INTO relations (
                        source_document_id,
                        target_document_id,
                        relation_type,
                        confidence,
                        metadata
                    ) VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (source_document_id, target_document_id, relation_type)
                    DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        metadata = EXCLUDED.metadata
                ''',
                    relation["source_doc_id"],
                    relation["target_doc_id"],
                    relation["relation_type"],
                    relation["confidence"],
                    json.dumps({
                        "reasoning": str(relation.get("reasoning", "")),
                        "model": "gemini-2.5-flash-lite",
                        "source_title": relation.get("source_doc", ""),
                        "target_title": relation.get("target_doc", "")
                    })
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save relation: {e}")

        logger.info(f"Saved {saved_count} relations to database")

        # Show summary
        print("\n" + "="*60)
        print("RELATION EXTRACTION SUMMARY")
        print("="*60)
        print(f"Documents analyzed: {len(documents)}")
        print(f"Relations found: {len(relations)}")
        print(f"High-confidence (>={confidence_threshold}): {len(high_confidence)}")
        print(f"Successfully saved: {saved_count}")

        # Group by relation type
        from collections import Counter
        relation_types = Counter([r["relation_type"] for r in high_confidence])

        print("\nRelations by type:")
        for rel_type, count in relation_types.most_common():
            print(f"  {rel_type}: {count}")

        # Show examples
        print("\nExample relations:")
        for i, rel in enumerate(high_confidence[:10], 1):
            print(f"  {i}. {rel['relation_type']}: {rel['source_doc'][:50]}")
            print(f"     -> {rel['target_doc'][:50]}")
            print(f"     (confidence: {rel['confidence']:.2f})")

        print("\n" + "="*60)
        print("Next steps:")
        print("  - Use graph search in CLI: 'Find related documents to [entity_name]'")
        print("  - Or query relations directly in PostgreSQL")
        print("="*60)

    finally:
        await conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    # 23 documents = 23*22/2 = 253 possible pairs, use 300 to be safe
    asyncio.run(extract_and_save_relations(max_pairs=300, confidence_threshold=0.5))
