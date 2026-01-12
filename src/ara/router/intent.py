"""Intent classification for voice commands.

Classifies user utterances into specific intent types with extracted entities.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """Types of intents the system can handle."""

    GENERAL_QUESTION = "general_question"
    TIMER_SET = "timer_set"
    TIMER_CANCEL = "timer_cancel"
    TIMER_QUERY = "timer_query"
    REMINDER_SET = "reminder_set"
    REMINDER_CANCEL = "reminder_cancel"
    REMINDER_QUERY = "reminder_query"
    HISTORY_QUERY = "history_query"
    WEB_SEARCH = "web_search"
    SYSTEM_COMMAND = "system_command"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Classified intent with extracted entities."""

    type: IntentType
    confidence: float
    entities: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""


class IntentClassifier:
    """Rule-based intent classifier for voice commands.

    Uses pattern matching to classify intents. This approach is fast and
    works offline, suitable for the limited set of commands we support.
    """

    # Timer patterns
    TIMER_SET_PATTERNS = [
        r"set\s+(?:a\s+)?timer\s+(?:for\s+)?(.+)",
        r"start\s+(?:a\s+)?timer\s+(?:for\s+)?(.+)",
        r"(\d+)\s*(?:minute|min|second|sec|hour|hr)s?\s+timer",
        r"timer\s+(?:for\s+)?(.+)",
    ]

    TIMER_CANCEL_PATTERNS = [
        r"cancel\s+(?:the\s+)?(?:my\s+)?(?:(\w+)\s+)?timer",
        r"stop\s+(?:the\s+)?(?:my\s+)?(?:(\w+)\s+)?timer",
        r"delete\s+(?:the\s+)?(?:my\s+)?(?:(\w+)\s+)?timer",
    ]

    TIMER_QUERY_PATTERNS = [
        r"how\s+much\s+time\s+(?:is\s+)?left",
        r"what\s+timers?\s+(?:do\s+I\s+have|are\s+set|are\s+running)",
        r"check\s+(?:the\s+)?(?:my\s+)?timer",
        r"time\s+left\s+on\s+(?:the\s+)?(?:my\s+)?timer",
    ]

    # Reminder patterns
    REMINDER_SET_PATTERNS = [
        r"remind\s+me\s+(?:to\s+)?(.+?)(?:\s+(?:in|at)\s+(.+))?$",
        r"set\s+(?:a\s+)?reminder\s+(?:to\s+)?(.+?)(?:\s+(?:in|at)\s+(.+))?$",
        r"don'?t\s+let\s+me\s+forget\s+(?:to\s+)?(.+)",
    ]

    REMINDER_CANCEL_PATTERNS = [
        r"cancel\s+(?:the\s+)?(?:my\s+)?reminder",
        r"delete\s+(?:the\s+)?(?:my\s+)?reminder",
        r"remove\s+(?:the\s+)?(?:my\s+)?reminder",
    ]

    REMINDER_QUERY_PATTERNS = [
        r"what\s+reminders?\s+(?:do\s+I\s+have|are\s+set)",
        r"(?:list|show)\s+(?:my\s+)?reminders?",
        r"check\s+(?:my\s+)?reminders?",
    ]

    # History query patterns
    HISTORY_QUERY_PATTERNS = [
        r"what\s+did\s+I\s+(?:ask|say)\s+(?:you\s+)?yesterday",
        r"what\s+(?:were\s+)?(?:my\s+)?(?:last|recent)\s+(?:questions?|queries)",
        r"(?:show|list)\s+(?:my\s+)?(?:conversation\s+)?history",
        r"what\s+have\s+I\s+(?:asked|said)\s+(?:recently|today)",
    ]

    # Web search patterns
    WEB_SEARCH_PATTERNS = [
        r"search\s+(?:for\s+)?(.+)",
        r"look\s+up\s+(.+)",
        r"with\s+internet[,\s]+(.+)",
        r"using\s+internet[,\s]+(.+)",
        r"google\s+(.+)",
        r"find\s+(?:information\s+(?:about|on)\s+)?(.+)",
    ]

    # System command patterns
    SYSTEM_PATTERNS = [
        (r"go\s+offline", "offline"),
        (r"go\s+online", "online"),
        (r"(?:what\s+)?mode\s+(?:are\s+you\s+in|is\s+this)", "status"),
        (r"status", "status"),
    ]

    def __init__(self) -> None:
        """Initialize the classifier."""
        # Pre-compile patterns for efficiency
        self._timer_set = [re.compile(p, re.IGNORECASE) for p in self.TIMER_SET_PATTERNS]
        self._timer_cancel = [
            re.compile(p, re.IGNORECASE) for p in self.TIMER_CANCEL_PATTERNS
        ]
        self._timer_query = [
            re.compile(p, re.IGNORECASE) for p in self.TIMER_QUERY_PATTERNS
        ]
        self._reminder_set = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_SET_PATTERNS
        ]
        self._reminder_cancel = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_CANCEL_PATTERNS
        ]
        self._reminder_query = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_QUERY_PATTERNS
        ]
        self._history_query = [
            re.compile(p, re.IGNORECASE) for p in self.HISTORY_QUERY_PATTERNS
        ]
        self._web_search = [
            re.compile(p, re.IGNORECASE) for p in self.WEB_SEARCH_PATTERNS
        ]
        self._system = [(re.compile(p, re.IGNORECASE), cmd) for p, cmd in self.SYSTEM_PATTERNS]

    def classify(self, text: str) -> Intent:
        """Classify the given text into an intent.

        Args:
            text: The user's utterance to classify.

        Returns:
            An Intent object with type, confidence, and extracted entities.
        """
        text = text.strip()

        if not text:
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw_text=text,
            )

        # Try each intent type in order of specificity
        # Timer intents
        if intent := self._try_timer_set(text):
            return intent
        if intent := self._try_timer_cancel(text):
            return intent
        if intent := self._try_timer_query(text):
            return intent

        # Reminder intents
        if intent := self._try_reminder_set(text):
            return intent
        if intent := self._try_reminder_cancel(text):
            return intent
        if intent := self._try_reminder_query(text):
            return intent

        # History query
        if intent := self._try_history_query(text):
            return intent

        # Web search
        if intent := self._try_web_search(text):
            return intent

        # System commands
        if intent := self._try_system_command(text):
            return intent

        # Default to general question
        return Intent(
            type=IntentType.GENERAL_QUESTION,
            confidence=0.7,
            entities={},
            raw_text=text,
        )

    def _try_timer_set(self, text: str) -> Intent | None:
        """Try to match timer set patterns."""
        for pattern in self._timer_set:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract duration from match
                if groups and groups[0]:
                    entities["duration"] = groups[0].strip()

                # Try to extract timer name
                name_match = re.search(r"(?:called|named)\s+(\w+)", text, re.IGNORECASE)
                if name_match:
                    entities["name"] = name_match.group(1)

                return Intent(
                    type=IntentType.TIMER_SET,
                    confidence=0.9,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_timer_cancel(self, text: str) -> Intent | None:
        """Try to match timer cancel patterns."""
        for pattern in self._timer_cancel:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract timer name if specified
                if groups and groups[0]:
                    entities["name"] = groups[0].strip()

                return Intent(
                    type=IntentType.TIMER_CANCEL,
                    confidence=0.9,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_timer_query(self, text: str) -> Intent | None:
        """Try to match timer query patterns."""
        for pattern in self._timer_query:
            if pattern.search(text):
                return Intent(
                    type=IntentType.TIMER_QUERY,
                    confidence=0.85,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_reminder_set(self, text: str) -> Intent | None:
        """Try to match reminder set patterns."""
        for pattern in self._reminder_set:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract message
                if groups and groups[0]:
                    entities["message"] = groups[0].strip()

                # Extract time if present
                if len(groups) > 1 and groups[1]:
                    entities["time"] = groups[1].strip()

                return Intent(
                    type=IntentType.REMINDER_SET,
                    confidence=0.9,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_reminder_cancel(self, text: str) -> Intent | None:
        """Try to match reminder cancel patterns."""
        for pattern in self._reminder_cancel:
            if pattern.search(text):
                return Intent(
                    type=IntentType.REMINDER_CANCEL,
                    confidence=0.9,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_reminder_query(self, text: str) -> Intent | None:
        """Try to match reminder query patterns."""
        for pattern in self._reminder_query:
            if pattern.search(text):
                return Intent(
                    type=IntentType.REMINDER_QUERY,
                    confidence=0.85,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_history_query(self, text: str) -> Intent | None:
        """Try to match history query patterns."""
        for pattern in self._history_query:
            match = pattern.search(text)
            if match:
                entities = {}
                # Try to detect time reference
                if "yesterday" in text.lower():
                    entities["time_ref"] = "yesterday"
                elif "today" in text.lower():
                    entities["time_ref"] = "today"
                elif "recent" in text.lower() or "last" in text.lower():
                    entities["time_ref"] = "recent"

                return Intent(
                    type=IntentType.HISTORY_QUERY,
                    confidence=0.85,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_web_search(self, text: str) -> Intent | None:
        """Try to match web search patterns."""
        for pattern in self._web_search:
            match = pattern.search(text)
            if match:
                entities = {}
                # Extract the search query from the match
                groups = match.groups()
                if groups and groups[0]:
                    entities["query"] = groups[0].strip()

                return Intent(
                    type=IntentType.WEB_SEARCH,
                    confidence=0.9,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_system_command(self, text: str) -> Intent | None:
        """Try to match system command patterns."""
        for pattern, command in self._system:
            if pattern.search(text):
                return Intent(
                    type=IntentType.SYSTEM_COMMAND,
                    confidence=0.95,
                    entities={"command": command},
                    raw_text=text,
                )
        return None
