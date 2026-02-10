"""
Document relation extraction using Gemini 2.5 Flash Lite.

Analyzes pairs of documents to determine relationships between them.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import httpx

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RelationExtractor:
    """Extract relations between documents using Gemini Flash Lite."""

    # Relation types
    RELATION_TYPES = {
        "AMENDS": "Дополнительное соглашение к договору",
        "REFERENCES": "Ссылка на документ (спецификация, приложение)",
        "PARTIES_TO": "Общая сделка (обе стороны)",
        "PAYS_FOR": "Платёжный документ за поставку",
        "DELIVERS": "Транспортная накладная за поставку",
        "NONE": "Связи нет"
    }

    def __init__(
        self,
        model: str = "google/gemini-2.5-flash-lite",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.model = model
        if not api_key:
            from src.settings import load_settings
            settings = load_settings()
            self.api_key = settings.embedding_api_key
        else:
            self.api_key = api_key
        self.base_url = base_url

    async def extract_relation(
        self,
        doc1_title: str,
        doc1_entities: List[Dict[str, Any]],
        doc2_title: str,
        doc2_entities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract relation between two documents.

        Args:
            doc1_title: Title of first document
            doc1_entities: Entities from first document
            doc2_title: Title of second document
            doc2_entities: Entities from second document

        Returns:
            Relation dict with relation_type and confidence, or None if no relation
        """
        try:
            # Build prompt
            prompt = self._build_prompt(doc1_title, doc1_entities, doc2_title, doc2_entities)

            # Call Gemini
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a document analysis expert. Determine if two documents are related and what type of relationship exists."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,  # Low temperature for consistent results
                        "max_tokens": 100
                    }
                )
                response.raise_for_status()
                data = response.json()

            # Parse response
            return self._parse_relation(data, doc1_title, doc2_title)

        except Exception as e:
            logger.error(f"Error extracting relation: {e}")
            return None

    def _build_prompt(
        self,
        doc1_title: str,
        doc1_entities: List[Dict[str, Any]],
        doc2_title: str,
        doc2_entities: List[Dict[str, Any]]
    ) -> str:
        """Build analysis prompt for Gemini."""

        # Extract key entities
        doc1_orgs = [e["entity_name"] for e in doc1_entities if e.get("entity_type") == "ORG"][:5]
        doc2_orgs = [e["entity_name"] for e in doc2_entities if e.get("entity_type") == "ORG"][:5]
        doc1_refs = [e["entity_name"] for e in doc1_entities if e.get("entity_type") == "DOC_REF"][:5]
        doc2_refs = [e["entity_name"] for e in doc2_entities if e.get("entity_type") == "DOC_REF"][:5]

        prompt = f"""Анализируй связь между документами:

ДОКУМЕНТ 1: {doc1_title}
Организации: {', '.join(doc1_orgs)}
Ссылки: {', '.join(doc1_refs)}

ДОКУМЕНТ 2: {doc2_title}
Организации: {', '.join(doc2_orgs)}
Ссылки: {', '.join(doc2_refs)}

Возможные типы связей:
- AMENDS: Доп. соглашение к договору
- REFERENCES: Спецификация или ссылка на документ
- PARTIES_TO: Одна и та же сделка (общие стороны)
- PAYS_FOR: Платёжный документ
- DELIVERS: Транспортная накладная
- NONE: Нет связи

Ответь строго в формате JSON:
{{"relation_type": "ТИП", "confidence": 0.0-1.0, "reasoning": "краткое объяснение"}}"""

        return prompt

    def _parse_relation(
        self,
        response_data: Dict[str, Any],
        doc1_title: str,
        doc2_title: str
    ) -> Optional[Dict[str, Any]]:
        """Parse Gemini response and extract relation."""

        try:
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Try to parse JSON
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                result = json.loads(json_match.group())

                relation_type = result.get("relation_type", "").upper()
                if relation_type in self.RELATION_TYPES:
                    return {
                        "relation_type": relation_type,
                        "confidence": float(result.get("confidence", 0.5)),
                        "reasoning": result.get("reasoning", ""),
                        "source_doc": doc1_title,
                        "target_doc": doc2_title
                    }

            # Fallback: check for keywords in response
            content_lower = content.lower()
            for rel_type, description in self.RELATION_TYPES.items():
                if rel_type.lower() in content_lower:
                    return {
                        "relation_type": rel_type,
                        "confidence": 0.6,
                        "reasoning": f"Detected keyword: {rel_type}",
                        "source_doc": doc1_title,
                        "target_doc": doc2_title
                    }

            return None

        except Exception as e:
            logger.error(f"Error parsing relation: {e}")
            return None

    async def extract_relations_batch(
        self,
        documents: List[Dict[str, Any]],
        max_pairs: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Extract relations for multiple document pairs.

        Args:
            documents: List of documents with id, title, and entities
            max_pairs: Maximum number of pairs to analyze

        Returns:
            List of relations between documents
        """
        relations = []
        pairs_analyzed = 0

        for i, doc1 in enumerate(documents):
            for doc2 in documents[i+1:]:
                if pairs_analyzed >= max_pairs:
                    break

                # Skip if no entities
                if not doc1.get("entities") or not doc2.get("entities"):
                    continue

                relation = await self.extract_relation(
                    doc1["title"],
                    doc1["entities"],
                    doc2["title"],
                    doc2["entities"]
                )

                if relation and relation["relation_type"] != "NONE":
                    relations.append({
                        **relation,
                        "source_doc_id": doc1["id"],
                        "target_doc_id": doc2["id"]
                    })

                pairs_analyzed += 1

            if pairs_analyzed >= max_pairs:
                break

        logger.info(f"Analyzed {pairs_analyzed} pairs, found {len(relations)} relations")
        return relations


# Singleton instance
_extractor: Optional[RelationExtractor] = None


def get_relation_extractor() -> RelationExtractor:
    """Get or create singleton RelationExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = RelationExtractor()
    return _extractor


async def extract_document_relations(
    documents: List[Dict[str, Any]],
    max_pairs: int = 50
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract relations from documents.

    Args:
        documents: List of documents with id, title, and entities
        max_pairs: Maximum number of pairs to analyze

    Returns:
        List of relations between documents
    """
    extractor = get_relation_extractor()
    return await extractor.extract_relations_batch(documents, max_pairs)
