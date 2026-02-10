"""
Named Entity Recognition for Russian documents using Natasha.

Extracts organizations, people, dates, amounts, and document references.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# Lazy import of Natasha (heavy dependencies)
_nlp_components = None


def _get_nlp_components():
    """Lazy load Natasha NLP components."""
    global _nlp_components
    if _nlp_components is None:
        from natasha import (
            Doc,
            Segmenter,
            NewsEmbedding,
            NewsNERTagger,
            MorphVocab,
            DatesExtractor,
            MoneyExtractor
        )

        segmenter = Segmenter()
        emb = NewsEmbedding()
        ner_tagger = NewsNERTagger(emb)
        morph_vocab = MorphVocab()

        dates_extractor = DatesExtractor(morph_vocab)
        money_extractor = MoneyExtractor(morph_vocab)

        _nlp_components = {
            'Doc': Doc,
            'segmenter': segmenter,
            'ner_tagger': ner_tagger,
            'morph_vocab': morph_vocab,
            'dates_extractor': dates_extractor,
            'money_extractor': money_extractor
        }
        logger.info("Natasha NLP components loaded")

    return _nlp_components


class Entity:
    """Represents a named entity extracted from text."""

    def __init__(
        self,
        entity_type: str,
        name: str,
        text: str,
        start: int,
        end: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.entity_type = entity_type  # ORG, PER, DATE, MONEY, DOC_REF
        self.name = name
        self.text = text
        self.start = start
        self.end = end
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'entity_type': self.entity_type,
            'entity_name': self.name,
            'entity_text': self.text,
            'start_pos': self.start,
            'end_pos': self.end,
            'metadata': self.metadata
        }


class EntityExtractor:
    """Extract entities from Russian text using Natasha."""

    def __init__(self):
        self.components = None

    def initialize(self):
        """Initialize NLP components (lazy loading)."""
        if self.components is None:
            self.components = _get_nlp_components()

    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract all entities from text.

        Args:
            text: Input text in Russian

        Returns:
            List of Entity objects
        """
        if not text or len(text.strip()) < 10:
            return []

        self.initialize()

        entities = []
        Doc = self.components['Doc']
        segmenter = self.components['segmenter']
        ner_tagger = self.components['ner_tagger']
        morph_vocab = self.components['morph_vocab']
        dates_extractor = self.components['dates_extractor']
        money_extractor = self.components['money_extractor']

        # Process document with NER
        doc = Doc(text)
        doc.segment(segmenter)
        doc.tag_ner(ner_tagger)

        # Extract ORG and PER entities
        for span in doc.spans:
            span.normalize(morph_vocab)
            if span.type == 'ORG':
                entities.append(Entity(
                    entity_type='ORG',
                    name=span.normal,
                    text=span.text,
                    start=span.start,
                    end=span.stop,
                    metadata={'span_type': 'ORG'}
                ))
            elif span.type == 'PER':
                entities.append(Entity(
                    entity_type='PER',
                    name=span.normal,
                    text=span.text,
                    start=span.start,
                    end=span.stop,
                    metadata={'span_type': 'PER'}
                ))

        # Extract dates
        for match in dates_extractor(text):
            date_value = match.fact
            # Handle different date types
            if hasattr(date_value, 'isoformat'):
                date_str = date_value.isoformat()
            elif isinstance(date_value, str):
                date_str = date_value
            else:
                date_str = str(match.fact)

            entities.append(Entity(
                entity_type='DATE',
                name=date_str,
                text=text[match.start:match.stop],  # Extract text slice
                start=match.start,
                end=match.stop,
                metadata={
                    'date_type': type(date_value).__name__,
                    'raw_text': text[match.start:match.stop]
                }
            ))

        # Extract money amounts
        for match in money_extractor(text):
            entities.append(Entity(
                entity_type='MONEY',
                name=str(match.fact.amount),
                text=text[match.start:match.stop],  # Extract text slice
                start=match.start,
                end=match.stop,
                metadata={
                    'amount': float(match.fact.amount) if match.fact.amount else None,
                    'currency': match.fact.currency if hasattr(match.fact, 'currency') else None
                }
            ))

        # Extract document references using regex
        doc_refs = self._extract_document_references(text)
        for ref in doc_refs:
            entities.append(Entity(
                entity_type='DOC_REF',
                name=ref['name'],
                text=ref['text'],
                start=ref['start'],
                end=ref['end'],
                metadata={'pattern': ref['pattern']}
            ))

        # Extract foreign/Latin company names
        foreign_orgs = self._extract_foreign_organizations(text)
        for org in foreign_orgs:
            entities.append(Entity(
                entity_type='ORG',
                name=org['name'],
                text=org['text'],
                start=org['start'],
                end=org['end'],
                metadata={'source': 'foreign_org_pattern'}
            ))

        logger.debug(f"Extracted {len(entities)} entities from text")
        return entities

    def _extract_document_references(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract document references using regex patterns.

        Looks for patterns like:
        - Договор №123
        - Доп. соглашение №1
        - Спецификация 4.2
        - Счет-фактура АБВ123
        """
        references = []

        # Document number patterns
        patterns = [
            (r'(?:Договор|Договор\s+поставки|Доп\.?\s*соглашение|Дополнительное\s+соглашение)\s*[№N]?\s*([A-ZА-Яа-яЁё0-9\-/]+)',
             'contract'),
            (r'(?:Спецификация|Спец\.?|Приложение)\s*[№N]?\s*([A-ZА-Яа-яЁё0-9\-/.]+)',
             'specification'),
            (r'(?:Счет[ -]?фактура|ЭСФ|СФ)\s*[№N]?\s*([A-ZА-Яа-яЁё0-9\-/]+)',
             'invoice'),
            (r'(?:CMR|накладная|ТТН)\s*[№N]?\s*([A-ZА-Яа-яЁё0-9\-/]+)',
             'transport'),
            (r'№\s*(\d{6,}\s*[-–]\s*\d+)',  # Pattern: 123456 - 789012
             'number_range'),
        ]

        for pattern, ref_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                references.append({
                    'name': match.group(0),
                    'text': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': ref_type
                })

        return references

    def _extract_foreign_organizations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract foreign/Latin company names using regex patterns.

        Looks for patterns like:
        - Vindasia LLC (or VINDASIALLC from bad OCR)
        - Juki Central Europe Ltd.
        - Fuji Logistics Corp.
        - Amal Group GmbH

        Note: OCR often produces text without spaces, so patterns handle
        both normal and concatenated formats.
        """
        organizations = []

        # Company suffix patterns for foreign companies
        # Matches: Name + LLC/Corp/Ltd/GmbH/Inc/etc (with or without spaces)
        patterns = [
            # Pattern: UAB/LLC/etc + Company name (for concatenated OCR text)
            (r'\b([A-Z]{2,6})(?:[A-Z]{5,30})(?:LLC|CORP|LTD|GMBH|INC|S\.P\.Z\.O\.O\.|SRO|SA|B\.V\.)\b',
             'concatenated_company'),
            # Pattern: Company name + LLC/Corp/Ltd/etc (with optional spaces)
            (r'\b([A-Z][A-Za-z\s&]{2,40}?(?:LLC|LLC\.|Corporation|Corp|Corp\.|Ltd|Ltd\.|Limited|GmbH|GmbH\.|Inc|Inc\.|Incorporated|Group|SA|S\.A\.|B\.V\.|S\.r\.l\.|sp\.z\.o\.o\.|S\.P\.Z\.O\.O\.))',
             'company_suffix'),
            # Pattern: Specific company names we know exist
            (r'\b(VINDASIA|JUKI|FUJI|AMAL|TERMINALITY)(?:\s+[A-Z]{2,20})*\s?(?:LLC|CORP|LTD|GMBH|LOGISTICS|GROUP|INTERNATIONAL|CENTRAL|EUROPE|ASIA)?\b',
             'known_company'),
            # Pattern: Name + Logistics/Trading/Systems/etc
            (r'\b([A-Z][a-z]+(?:Logistics|Trading|Solutions|Services|Systems|International|Global|Export|Import|Supply|Delivery|Central|Europe|Asia|America|Pacific))\b',
             'business_type'),
        ]

        for pattern, org_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                company_name = match.group(0).strip()
                # Filter out short matches and common words
                if len(company_name) >= 4 and company_name.lower() not in ['the', 'and', 'for', 'with', 'from', 'sent']:
                    organizations.append({
                        'name': company_name,
                        'text': match.group(0),
                        'start': match.start(),
                        'end': match.end(),
                        'pattern': org_type
                    })

        return organizations


# Singleton instance
_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Get or create singleton EntityExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor


def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Convenience function to extract entities from text.

    Args:
        text: Input text in Russian

    Returns:
        List of entity dictionaries
    """
    extractor = get_entity_extractor()
    entities = extractor.extract_entities(text)
    return [e.to_dict() for e in entities]
