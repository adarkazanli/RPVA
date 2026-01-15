"""Notes module for Ara Voice Assistant.

Provides note capture with entity extraction.
"""

from .categorizer import categorize, categorize_with_confidence
from .extractor import EntityExtractor, ExtractedEntities
from .models import Category, Note
from .service import NoteService

__all__ = [
    "Category",
    "Note",
    "EntityExtractor",
    "ExtractedEntities",
    "NoteService",
    "categorize",
    "categorize_with_confidence",
]
