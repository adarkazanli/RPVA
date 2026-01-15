"""Query Router for intelligent query routing.

Classifies queries and routes them to the most appropriate data source:
- Personal queries → MongoDB (prevents LLM hallucination)
- Factual queries → Web search (prevents LLM guessing)
- General knowledge → LLM (fast responses for static knowledge)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


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


# Query indicator constants for classification
PERSONAL_INDICATORS = {
    "pronouns": ["I", "me", "my", "mine", "I'm", "I've", "I'd"],
    "patterns": [
        r"when did I",
        r"what did I",
        r"did I mention",
        r"how long was I",
        r"my \w+",
        r"have I",
        r"was I",
    ],
    "time_refs": ["last time", "yesterday", "this week", "recently", "earlier"],
}

FACTUAL_INDICATORS = {
    "weather": ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"],
    "prices": ["price", "cost", "stock", "worth", "value"],
    "news": ["news", "headlines", "current events", "latest"],
    "distance": ["how far", "distance", "directions", "drive to", "miles", "kilometers"],
    "time_sensitive": ["right now", "today", "current", "latest", "live"],
    "sports": ["score", "who won", "game", "match"],
}

GENERAL_INDICATORS = {
    "definitions": ["what is", "what does", "define", "meaning of"],
    "static_facts": ["capital of", "invented", "who wrote", "who created"],
    "how_to": ["how do I", "how to", "explain", "tell me about"],
    "math": ["calculate", "plus", "minus", "percent", "divided"],
}

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


class QueryRouter:
    """Routes queries to the most appropriate data source.

    The QueryRouter analyzes query text and determines whether it should
    be routed to MongoDB (personal data), web search (factual/current),
    or directly to the LLM (general knowledge).
    """

    def __init__(self) -> None:
        """Initialize the QueryRouter with compiled patterns."""
        # Compile personal patterns
        self._personal_patterns = [
            re.compile(p, re.IGNORECASE) for p in PERSONAL_INDICATORS["patterns"]
        ]
        self._personal_pronouns = {p.lower() for p in PERSONAL_INDICATORS["pronouns"]}
        self._personal_time_refs = {t.lower() for t in PERSONAL_INDICATORS["time_refs"]}

        # Build factual keyword set
        self._factual_keywords: set[str] = set()
        for keywords in FACTUAL_INDICATORS.values():
            self._factual_keywords.update(k.lower() for k in keywords)

        # Build general keyword set
        self._general_keywords: set[str] = set()
        for keywords in GENERAL_INDICATORS.values():
            self._general_keywords.update(k.lower() for k in keywords)

    def classify(self, query: str, context: dict | None = None) -> RoutingDecision:
        """Classify a query and determine routing.

        Args:
            query: The user's query text
            context: Optional conversation context for disambiguation

        Returns:
            RoutingDecision with query type and source routing
        """
        query_lower = query.lower().strip()
        indicators_matched: list[str] = []

        # Stage 0: Check for explicit general knowledge patterns FIRST
        # These should never be routed to personal data even if they contain "I"
        general_patterns = [
            (r"how do I", "how_to"),
            (r"how can I", "how_to"),
            (r"how should I", "how_to"),
            (r"what is\b", "definition"),
            (r"what does\b", "definition"),
            (r"define\b", "definition"),
            (r"explain\b", "explanation"),
            (r"tell me about", "explanation"),
        ]
        for pattern, indicator in general_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                indicators_matched.append(f"general:{indicator}")
                logger.debug(
                    "Query classified as GENERAL_KNOWLEDGE (explicit): %s (indicators: %s)",
                    query[:50],
                    indicators_matched,
                )
                return RoutingDecision(
                    query_type=QueryType.GENERAL_KNOWLEDGE,
                    primary_source=DataSource.LLM,
                    fallback_source=None,
                    confidence=0.85,
                    indicators_matched=indicators_matched,
                    should_caveat=False,
                )

        # Stage 1: Check for personal indicators
        if self.is_personal_query(query):
            # Collect matched indicators
            for pattern in self._personal_patterns:
                if pattern.search(query):
                    indicators_matched.append(f"pattern:{pattern.pattern}")
            for pronoun in self._personal_pronouns:
                if re.search(rf"\b{pronoun}\b", query_lower):
                    indicators_matched.append(f"pronoun:{pronoun}")
            for time_ref in self._personal_time_refs:
                if time_ref in query_lower:
                    indicators_matched.append(f"time_ref:{time_ref}")

            logger.debug(
                "Query classified as PERSONAL_DATA: %s (indicators: %s)",
                query[:50],
                indicators_matched,
            )
            return RoutingDecision(
                query_type=QueryType.PERSONAL_DATA,
                primary_source=DataSource.DATABASE,
                fallback_source=None,  # Never hallucinate personal data
                confidence=0.9 if len(indicators_matched) > 1 else 0.8,
                indicators_matched=indicators_matched,
                should_caveat=False,
            )

        # Stage 2: Check for factual/time-sensitive indicators
        if self.is_factual_query(query):
            for keyword in self._factual_keywords:
                if keyword in query_lower:
                    indicators_matched.append(f"factual:{keyword}")

            logger.debug(
                "Query classified as FACTUAL_CURRENT: %s (indicators: %s)",
                query[:50],
                indicators_matched,
            )
            return RoutingDecision(
                query_type=QueryType.FACTUAL_CURRENT,
                primary_source=DataSource.WEB_SEARCH,
                fallback_source=DataSource.LLM,  # With caveat
                confidence=0.85 if len(indicators_matched) > 1 else 0.75,
                indicators_matched=indicators_matched,
                should_caveat=True,  # Caveat if falling back to LLM
            )

        # Stage 3: Check for general knowledge indicators
        for keyword in self._general_keywords:
            if keyword in query_lower:
                indicators_matched.append(f"general:{keyword}")

        if indicators_matched:
            logger.debug(
                "Query classified as GENERAL_KNOWLEDGE: %s (indicators: %s)",
                query[:50],
                indicators_matched,
            )
            return RoutingDecision(
                query_type=QueryType.GENERAL_KNOWLEDGE,
                primary_source=DataSource.LLM,
                fallback_source=None,
                confidence=0.8,
                indicators_matched=indicators_matched,
                should_caveat=False,
            )

        # Default: Ambiguous or general knowledge
        # If we have context, try to resolve
        if context and self._can_resolve_from_context(query_lower, context):
            resolved_type = self._resolve_from_context(query_lower, context)
            logger.debug(
                "Query resolved from context as %s: %s", resolved_type.query_type, query[:50]
            )
            return resolved_type

        # Truly ambiguous - default to LLM
        logger.debug("Query classified as GENERAL_KNOWLEDGE (default): %s", query[:50])
        return RoutingDecision(
            query_type=QueryType.GENERAL_KNOWLEDGE,
            primary_source=DataSource.LLM,
            fallback_source=None,
            confidence=0.5,
            indicators_matched=["default"],
            should_caveat=False,
        )

    def is_personal_query(self, query: str) -> bool:
        """Check if query is about personal data.

        Args:
            query: The user's query text

        Returns:
            True if query contains personal indicators
        """
        query_lower = query.lower()

        # Exclude general knowledge patterns that happen to contain "I"
        # "How do I" is a how-to question, not personal data
        general_exclusions = [
            r"how do I",
            r"how can I",
            r"how should I",
            r"what is",
            r"what does",
            r"define",
            r"explain",
            r"tell me about",
        ]
        for exclusion in general_exclusions:
            if re.search(exclusion, query_lower, re.IGNORECASE):
                return False

        # Check for personal patterns (more specific than pronouns)
        for pattern in self._personal_patterns:
            if pattern.search(query):
                return True

        # Check for personal pronouns with personal context
        # Only match pronouns when paired with past tense or possessive patterns
        personal_context_patterns = [
            r"\bmy\s+\w+",  # "my workout", "my meeting"
            r"\bwhen did I\b",
            r"\bwhat did I\b",
            r"\bdid I\b",
            r"\bhave I\b",
            r"\bwas I\b",
            r"\bI\s+(?:went|did|had|said|asked|mentioned|ate|drank|exercised|worked)\b",
        ]
        for pattern in personal_context_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True

        # Check for time references with personal context
        for time_ref in self._personal_time_refs:
            if time_ref in query_lower:
                # Only count time refs if there's also a personal pronoun in a personal context
                for pattern in personal_context_patterns:
                    if re.search(pattern, query, re.IGNORECASE):
                        return True

        return False

    def is_factual_query(self, query: str) -> bool:
        """Check if query requires factual/current data.

        Args:
            query: The user's query text

        Returns:
            True if query contains factual indicators
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self._factual_keywords)

    def _can_resolve_from_context(self, _query: str, context: dict) -> bool:
        """Check if query can be resolved using conversation context."""
        # Check if context has recent queries that inform this one
        recent_queries = context.get("recent_queries", [])
        return len(recent_queries) > 0

    def _resolve_from_context(self, _query: str, context: dict) -> RoutingDecision:
        """Resolve ambiguous query using conversation context."""
        recent_queries = context.get("recent_queries", [])

        # If recent queries were about personal data, assume this continues
        for recent in recent_queries[-3:]:  # Look at last 3 queries
            if recent.get("query_type") == QueryType.PERSONAL_DATA:
                return RoutingDecision(
                    query_type=QueryType.PERSONAL_DATA,
                    primary_source=DataSource.DATABASE,
                    fallback_source=None,
                    confidence=0.6,
                    indicators_matched=["context:follow_up"],
                    should_caveat=False,
                )

        # Default to general knowledge
        return RoutingDecision(
            query_type=QueryType.GENERAL_KNOWLEDGE,
            primary_source=DataSource.LLM,
            fallback_source=None,
            confidence=0.5,
            indicators_matched=["context:default"],
            should_caveat=False,
        )
