"""Contract: Query Router Interface

This file defines the interface contract for the QueryRouter module.
Implementation must adhere to this interface.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class QueryType(Enum):
    """Classification of query based on data source requirements."""

    PERSONAL_DATA = "personal_data"  # User's history, activities, notes
    FACTUAL_CURRENT = "factual_current"  # Time-sensitive or verifiable facts
    GENERAL_KNOWLEDGE = "general_knowledge"  # Static knowledge, definitions
    AMBIGUOUS = "ambiguous"  # Cannot determine with confidence


class DataSource(Enum):
    """Available sources for answering queries."""

    DATABASE = "database"  # MongoDB
    WEB_SEARCH = "web_search"  # Tavily
    LLM = "llm"  # Ollama


@dataclass
class RoutingDecision:
    """Result of query classification with routing information.

    Attributes:
        query_type: Classified type of query
        primary_source: First source to try
        fallback_source: Source to try if primary fails (None for personal data)
        confidence: Confidence in classification (0.0-1.0)
        indicators_matched: Keywords/patterns that matched
        should_caveat: Whether response should include uncertainty caveat
    """

    query_type: QueryType
    primary_source: DataSource
    fallback_source: DataSource | None = None
    confidence: float = 0.5
    indicators_matched: list[str] = field(default_factory=list)
    should_caveat: bool = False


class QueryRouterProtocol(Protocol):
    """Protocol defining the QueryRouter interface.

    The QueryRouter is responsible for analyzing queries and determining
    which data source should be used to answer them.
    """

    def classify(self, query: str, context: dict | None = None) -> RoutingDecision:
        """Classify a query and determine routing.

        Args:
            query: The user's query text
            context: Optional conversation context for disambiguation

        Returns:
            RoutingDecision with query type and source routing
        """
        ...

    def is_personal_query(self, query: str) -> bool:
        """Check if query is about personal data.

        Args:
            query: The user's query text

        Returns:
            True if query contains personal indicators
        """
        ...

    def is_factual_query(self, query: str) -> bool:
        """Check if query requires factual/current data.

        Args:
            query: The user's query text

        Returns:
            True if query contains factual indicators
        """
        ...


# Response message templates
NOT_FOUND_MESSAGES = {
    "exercise": "I don't have any exercise records.",
    "meeting": "I don't have any meeting records.",
    "activity": "I don't have any records of that activity.",
    "mention": "I don't see that in your recent history.",
    "default": "I don't have any records of that.",
}

FALLBACK_CAVEAT = "I couldn't verify this online, but "
DATABASE_ERROR = "I couldn't access your history right now."
WEB_SEARCH_ERROR = "I couldn't search the web right now."
