"""Intent classification for voice commands.

Classifies user utterances into specific intent types with extracted entities.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """Types of intents the system can handle."""

    GENERAL_QUESTION = "general_question"
    TIME_QUERY = "time_query"
    DATE_QUERY = "date_query"
    FUTURE_TIME_QUERY = "future_time_query"
    TIMER_SET = "timer_set"
    TIMER_CANCEL = "timer_cancel"
    TIMER_QUERY = "timer_query"
    REMINDER_SET = "reminder_set"
    REMINDER_CANCEL = "reminder_cancel"
    REMINDER_QUERY = "reminder_query"
    REMINDER_CLEAR_ALL = "reminder_clear_all"
    REMINDER_TIME_LEFT = "reminder_time_left"
    HISTORY_QUERY = "history_query"
    WEB_SEARCH = "web_search"
    SYSTEM_COMMAND = "system_command"
    USER_NAME_SET = "user_name_set"
    USER_PASSWORD_SET = "user_password_set"
    # MongoDB time-based query intents
    DURATION_QUERY = "duration_query"  # "how long was I in the shower?"
    ACTIVITY_SEARCH = "activity_search"  # "what was I doing around 10 AM?"
    EVENT_LOG = "event_log"  # "I'm going to the gym" (activity start/end)
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
        # "wake me up" patterns - message defaults to "wake up", time is extracted
        r"wake\s+me\s+(?:up\s+)?(in|at)\s+(.+)",
    ]

    REMINDER_CANCEL_PATTERNS = [
        r"cancel\s+(?:the\s+)?(?:my\s+)?reminder",
        r"delete\s+(?:the\s+)?(?:my\s+)?reminder",
        r"remove\s+(?:the\s+)?(?:my\s+)?reminder",
        # Cancel by ordinal: "cancel the first/second/third reminder"
        r"cancel\s+(?:the\s+)?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+(?:reminder|one)",
        r"delete\s+(?:the\s+)?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+(?:reminder|one)",
        # Cancel by number: "cancel reminder number 3", "cancel reminder 3"
        r"cancel\s+(?:the\s+)?(?:my\s+)?reminders?\s+(?:number\s+)?\d+",
        r"delete\s+(?:the\s+)?(?:my\s+)?reminders?\s+(?:number\s+)?\d+",
        # Cancel multiple by number: "cancel reminders 1, 2, and 3"
        r"cancel\s+(?:the\s+)?(?:my\s+)?reminders?\s+\d+(?:,?\s*(?:and\s+)?\d+)+",
        # Cancel multiple by ordinal: "cancel the first, third, and fifth reminders"
        r"cancel\s+(?:the\s+)?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)(?:,?\s*(?:and\s+)?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth))+\s+reminders?",
    ]

    REMINDER_QUERY_PATTERNS = [
        r"what\s+reminders?\s+(?:do\s+I\s+have|are\s+set)",
        r"(?:list|show|view)\s+(?:my\s+)?reminders?",
        r"check\s+(?:my\s+)?reminders?",
        r"(?:what\s+are\s+)?my\s+reminders?",
    ]

    REMINDER_CLEAR_ALL_PATTERNS = [
        r"(?:clear|delete|remove|cancel)\s+all\s+(?:my\s+)?reminders?",
        r"(?:clear|delete|remove|cancel)\s+(?:my\s+)?reminders?\s+all",
    ]

    # Reminder time remaining patterns - "how much time until my reminder"
    # Also catches timer-style queries about reminders
    REMINDER_TIME_LEFT_PATTERNS = [
        r"how\s+much\s+time\s+(?:is\s+)?(?:left\s+)?(?:until|till|before)\s+(?:my\s+)?(?:reminder|I\s+(?:need\s+to|have\s+to|should))\s*(.+)?",
        r"how\s+(?:much\s+)?(?:longer|long)\s+(?:until|till|before)\s+(?:my\s+)?(?:reminder|I\s+(?:need\s+to|have\s+to|should))\s*(.+)?",
        r"(?:when\s+is|what\s+time\s+is)\s+my\s+(?:next\s+)?reminder",
        r"how\s+much\s+time\s+(?:is\s+)?left\s+(?:on|for)\s+(?:my\s+)?(?:leaving|reminder|.+ing)",
        r"time\s+(?:left|remaining)\s+(?:on|for|until)\s+(?:my\s+)?(?:reminder|leaving)",
    ]

    # History query patterns
    HISTORY_QUERY_PATTERNS = [
        r"what\s+did\s+I\s+(?:ask|say)\s+(?:you\s+)?yesterday",
        r"what\s+(?:were\s+)?(?:my\s+)?(?:last|recent)\s+(?:questions?|queries)",
        r"(?:show|list)\s+(?:my\s+)?(?:conversation\s+)?history",
        r"what\s+have\s+I\s+(?:asked|said)\s+(?:recently|today)",
        # Time-based history queries
        r"how\s+long\s+(?:ago|since)\s+(?:did\s+)?I\s+(?:said?|asked?|mentioned?)\s+(.+)",
        r"when\s+did\s+I\s+(?:say|ask|mention)\s+(.+)",
        r"(?:look(?:ing)?\s+at|check)\s+(?:my\s+)?history.+(?:tell|when|how\s+long)",
        r"(?:look(?:ing)?\s+at|check)\s+(?:my\s+)?(?:history|records?)",
        # Content-based history queries
        r"did\s+I\s+(?:say|ask|mention)\s+(?:anything\s+)?(?:about\s+)?(.+)",
        r"have\s+I\s+(?:said|asked|mentioned)\s+(.+)",
        # "Do you have history" queries
        r"do\s+you\s+(?:have|keep|retain|store)\s+(?:a\s+)?(?:history|record|log)",
        r"(?:is\s+there|have\s+you\s+got)\s+(?:a\s+)?(?:history|record|log)",
        # "How long have I been" queries (waiting, doing something)
        r"how\s+long\s+have\s+I\s+been\s+(?:waiting|doing|here|gone)(?:\s+(?:for|to)\s+)?(.+)?",
        r"how\s+long\s+(?:has\s+it\s+been|is\s+it)\s+since\s+(?:I\s+)?(.+)",
    ]

    # Web search patterns (more specific patterns first)
    WEB_SEARCH_PATTERNS = [
        r"search\s+(?:the\s+)?internet\s+(?:for\s+)?(.+)",
        r"search\s+(?:the\s+)?web\s+(?:for\s+)?(.+)",
        r"search\s+(?:for\s+)?(.+)",
        r"look\s+up\s+(.+)",
        r"check\s+(?:the\s+)?internet\s+(?:to\s+)?(?:see\s+)?(?:for\s+)?(.+)",
        r"check\s+online\s+(?:for\s+)?(.+)",
        r"find\s+out\s+(?:online\s+)?(.+)",
        r"with\s+internet[,\s]+(.+)",
        r"using\s+internet[,\s]+(.+)",
        r"google\s+(.+)",
        # News patterns - capture full query for context
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?(?:latest|top|recent|current|breaking)\s+(?:news|headlines?)(?:\s+(?:about|on|in|from)\s+(.+))?",
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:in\s+)?(?:the\s+)?news(?:\s+(?:today|right\s+now))?(?:\s+(?:about|on|in|from)\s+(.+))?",
        r"(?:any(?:thing)?|what(?:'s|'s|\s+is))\s+happening\s+(?:in\s+)?(.+)",
        r"news\s+(?:about|on|in|from)\s+(.+)",
        # Weather patterns
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?weather\s+(?:like\s+)?(?:in|at|for)\s+(.+)",
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?(?:current\s+)?(?:weather|temperature|forecast)\s+(?:in|at|for)\s+(.+)",
        r"(?:how(?:'s|'s|\s+is)\s+)?(?:the\s+)?weather\s+(?:in|at|for)?\s*(.+)",
        # Sports patterns
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?(?:latest|recent)\s+(?:sports?|scores?)\s+(?:news)?(?:\s+(?:about|on|for)\s+(.+))?",
        r"(?:who\s+won|score\s+of)\s+(?:the\s+)?(.+)\s+game",
        # Stock/finance patterns
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?(?:stock\s+)?price\s+(?:of|for)\s+(.+)",
        r"(?:how(?:'s|'s|\s+is)\s+)?(.+)\s+(?:stock|trading)",
        # Distance/direction patterns
        r"(?:what(?:'s|'s|\s+is)\s+)?(?:the\s+)?distance\s+(?:between|from)\s+(.+)",
        r"how\s+far\s+(?:is\s+it\s+)?(?:from\s+)?(.+?)(?:\s+to\s+.+)?",
        r"how\s+(?:long|far)\s+(?:does\s+it\s+take|is\s+it)\s+(?:to\s+)?(?:drive|get|travel)\s+(?:from\s+)?(.+)",
        r"(?:how\s+)?(?:do\s+I\s+)?(?:get|drive)\s+to\s+(.+?)(?:\s+from\s+.+)?",
        r"directions?\s+(?:to|from)\s+(.+)",
        r"drive\s+(?:from\s+)?(.+?)\s+to\s+(.+)",
    ]

    # System command patterns
    SYSTEM_PATTERNS = [
        (r"go\s+offline", "offline"),
        (r"go\s+online", "online"),
        (r"(?:what\s+)?mode\s+(?:are\s+you\s+in|is\s+this)", "status"),
        (r"status", "status"),
    ]

    # User name set patterns
    # IMPORTANT: Avoid overly broad patterns like "i'm \w+" which match
    # "I'm gonna", "I'm going", etc. Only use explicit name-setting phrases.
    USER_NAME_SET_PATTERNS = [
        r"my\s+name\s+is\s+(\w+)",
        r"call\s+me\s+(\w+)",
        r"(?:set|change|update)\s+my\s+name\s+to\s+(\w+)",
        r"you\s+can\s+call\s+me\s+(\w+)",
        r"i\s+go\s+by\s+(\w+)",
    ]

    # Common words that should NOT be extracted as names
    # Used to filter false positives from pattern matches
    NAME_BLACKLIST = {
        "gonna",
        "going",
        "trying",
        "about",
        "just",
        "here",
        "there",
        "fine",
        "good",
        "okay",
        "ok",
        "back",
        "home",
        "done",
        "ready",
        "sorry",
        "sure",
        "happy",
        "sad",
        "tired",
        "hungry",
        "busy",
        "late",
        "early",
        "leaving",
        "coming",
        "working",
        "looking",
        "thinking",
        "wondering",
        "asking",
        "saying",
        "telling",
    }

    # Password set patterns for profile protection
    USER_PASSWORD_SET_PATTERNS = [
        r"(?:set|change|update)\s+(?:my\s+)?password\s+(?:to\s+)?(\w+)",
        r"(?:my\s+)?password\s+(?:is|should\s+be)\s+(\w+)",
        r"(?:make|use)\s+(\w+)\s+(?:as\s+)?(?:my\s+)?password",
        r"protect\s+(?:my\s+)?(?:name|profile)\s+with\s+(?:password\s+)?(\w+)",
    ]

    # Time query patterns - must be checked before general questions
    TIME_QUERY_PATTERNS = [
        r"what\s+time\s+is\s+it",
        r"what\s+is\s+(?:the\s+)?(?:current\s+)?time",
        r"what'?s\s+the\s+time",
        r"what\s+time\s+do\s+you\s+have",
        r"what\s+time\s+(?:is\s+it\s+)?(?:right\s+)?now",
        r"(?:can\s+you\s+)?tell\s+me\s+(?:the\s+)?time",
        r"(?:do\s+you\s+)?have\s+(?:the\s+)?time",
        r"current\s+time",
        r"time\s+(?:please|now)",
    ]

    # Date query patterns
    DATE_QUERY_PATTERNS = [
        r"what\s+is\s+(?:the\s+)?(?:today'?s\s+)?date",
        r"what'?s\s+the\s+date\s*(?:today)?",
        r"what\s+day\s+is\s+(?:it|today)",
        r"what'?s\s+today",
        r"(?:can\s+you\s+)?tell\s+me\s+(?:the\s+)?date",
        r"today'?s\s+date",
    ]

    # Future time query patterns (what time will it be in X hours/minutes)
    # Supports both numeric (1, 2) and word form (one, two) numbers
    # Supports "in X hours", "after X hours", "X hours from now"
    FUTURE_TIME_QUERY_PATTERNS = [
        r"what\s+time\s+(?:will\s+it\s+be|would\s+it\s+be)\s+(?:in|after)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(hour|hr|minute|min)s?",
        r"what\s+(?:will|would)\s+(?:the\s+)?time\s+be\s+(?:in|after)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(hour|hr|minute|min)s?",
        r"(?:in|after)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(hour|hr|minute|min)s?\s+what\s+time\s+(?:will|would)\s+it\s+be",
        r"time\s+(?:in|after)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(hour|hr|minute|min)s?",
        r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(hour|hr|minute|min)s?\s+from\s+now",
    ]

    # Word number to digit mapping
    WORD_NUMBERS = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }

    # Duration query patterns - "how long was I in the shower?"
    DURATION_QUERY_PATTERNS = [
        r"how\s+long\s+(?:was|were|did)\s+(?:I|we)\s+(?:in|at|doing|on|with|for)\s+(?:the\s+)?(.+)",
        r"how\s+much\s+time\s+(?:did\s+)?(?:I|we)\s+spend\s+(?:in|at|on|with|doing)\s+(?:the\s+)?(.+)",
        r"how\s+long\s+(?:was|were)\s+(?:my|the)\s+(.+)",
        r"what\s+(?:was|is)\s+the\s+duration\s+(?:of\s+)?(?:my\s+)?(.+)",
        r"(?:tell\s+me\s+)?how\s+long\s+(?:I\s+)?(?:spent|took)\s+(?:on|with|doing|in)\s+(?:the\s+)?(.+)",
        r"duration\s+(?:of\s+)?(?:my\s+)?(?:last\s+)?(.+)",
    ]

    # Activity search patterns - "what was I doing around 10 AM?"
    ACTIVITY_SEARCH_PATTERNS = [
        r"what\s+(?:was|were)\s+(?:I|we)\s+doing\s+(?:around|at|near|about)\s+(.+)",
        r"what\s+(?:happened|did\s+I\s+do)\s+(?:around|at|near|about)\s+(.+)",
        r"what\s+(?:happened|activities?|events?)\s+(?:between|from)\s+(.+)\s+(?:and|to|until)\s+(.+)",
        r"(?:show|list|tell\s+me)\s+(?:my\s+)?(?:activities?|events?)\s+(?:around|at|near|about)\s+(.+)",
        r"(?:what\s+)?activities?\s+(?:around|at|near|about)\s+(.+)",
        r"what\s+(?:was|were)\s+(?:going\s+on|happening)\s+(?:around|at|about)\s+(.+)",
    ]

    # Event log patterns - "I'm going to the gym" (activity start/end)
    EVENT_LOG_PATTERNS = [
        # Activity start patterns
        r"(?:i'?m|i\s+am)\s+(?:going|heading|off)\s+to\s+(?:the\s+)?(.+)",
        r"(?:i'?m|i\s+am)\s+(?:starting|beginning)\s+(?:my\s+)?(.+)",
        r"(?:i'?m|i\s+am)\s+about\s+to\s+(?:start\s+)?(.+)",
        r"(?:i'?m|i\s+am)\s+(?:going\s+)?(?:to\s+)?(?:take|have)\s+(?:a\s+)?(.+)",
        r"(?:starting|beginning)\s+(?:my\s+)?(.+?)(?:\s+now)?$",
        # Activity end patterns
        r"(?:i'?m|i\s+am)\s+(?:done|finished|back)\s+(?:with\s+)?(?:my\s+)?(?:the\s+)?(.+)?",
        r"(?:just\s+)?finished\s+(?:my\s+)?(?:the\s+)?(.+)",
        r"(?:just\s+)?(?:got\s+)?(?:done|completed)\s+(?:with\s+)?(?:my\s+)?(?:the\s+)?(.+)",
        r"(?:i'?m|i\s+am)\s+(?:leaving|left)\s+(?:the\s+)?(.+)",
        r"(?:ended|stopped)\s+(?:my\s+)?(.+)",
        # Note/memo patterns
        r"(?:remember|note|memo)[,:\s]+(.+)",
        r"(?:make\s+a\s+)?note[:\s]+(?!of\s+that)(.+)",  # Exclude "of that" back-reference
        r"(?:i\s+)?parked\s+(?:at|in|on)\s+(.+)",
        # Location statements
        r"(?:i'?m|i\s+am)\s+(?:at|in)\s+(.+?)(?:\s+right\s+now)?(?:\.|$)",
        r"(?:i'?m|i\s+am)\s+(?:currently\s+)?(?:at|in)\s+(.+)",
    ]

    def __init__(self) -> None:
        """Initialize the classifier."""
        # Pre-compile patterns for efficiency
        self._timer_set = [re.compile(p, re.IGNORECASE) for p in self.TIMER_SET_PATTERNS]
        self._timer_cancel = [re.compile(p, re.IGNORECASE) for p in self.TIMER_CANCEL_PATTERNS]
        self._timer_query = [re.compile(p, re.IGNORECASE) for p in self.TIMER_QUERY_PATTERNS]
        self._reminder_set = [re.compile(p, re.IGNORECASE) for p in self.REMINDER_SET_PATTERNS]
        self._reminder_cancel = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_CANCEL_PATTERNS
        ]
        self._reminder_query = [re.compile(p, re.IGNORECASE) for p in self.REMINDER_QUERY_PATTERNS]
        self._reminder_clear_all = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_CLEAR_ALL_PATTERNS
        ]
        self._reminder_time_left = [
            re.compile(p, re.IGNORECASE) for p in self.REMINDER_TIME_LEFT_PATTERNS
        ]
        self._history_query = [re.compile(p, re.IGNORECASE) for p in self.HISTORY_QUERY_PATTERNS]
        self._web_search = [re.compile(p, re.IGNORECASE) for p in self.WEB_SEARCH_PATTERNS]
        self._system = [(re.compile(p, re.IGNORECASE), cmd) for p, cmd in self.SYSTEM_PATTERNS]
        self._user_name_set = [re.compile(p, re.IGNORECASE) for p in self.USER_NAME_SET_PATTERNS]
        self._user_password_set = [
            re.compile(p, re.IGNORECASE) for p in self.USER_PASSWORD_SET_PATTERNS
        ]
        self._time_query = [re.compile(p, re.IGNORECASE) for p in self.TIME_QUERY_PATTERNS]
        self._date_query = [re.compile(p, re.IGNORECASE) for p in self.DATE_QUERY_PATTERNS]
        self._future_time_query = [
            re.compile(p, re.IGNORECASE) for p in self.FUTURE_TIME_QUERY_PATTERNS
        ]
        # MongoDB time-based query patterns
        self._duration_query = [
            re.compile(p, re.IGNORECASE) for p in self.DURATION_QUERY_PATTERNS
        ]
        self._activity_search = [
            re.compile(p, re.IGNORECASE) for p in self.ACTIVITY_SEARCH_PATTERNS
        ]
        self._event_log = [re.compile(p, re.IGNORECASE) for p in self.EVENT_LOG_PATTERNS]

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

        # Reminder intents (clear all must come before cancel to avoid false positive)
        if intent := self._try_reminder_set(text):
            return intent
        if intent := self._try_reminder_clear_all(text):
            return intent
        if intent := self._try_reminder_cancel(text):
            return intent
        if intent := self._try_reminder_time_left(text):
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

        # User password set (check before name set)
        if intent := self._try_user_password_set(text):
            return intent

        # User name set
        if intent := self._try_user_name_set(text):
            return intent

        # Future time query - check before time query (more specific)
        if intent := self._try_future_time_query(text):
            return intent

        # Time query - check before general questions
        if intent := self._try_time_query(text):
            return intent

        # Date query - check before general questions
        if intent := self._try_date_query(text):
            return intent

        # MongoDB time-based query intents
        if intent := self._try_duration_query(text):
            return intent
        if intent := self._try_activity_search(text):
            return intent
        if intent := self._try_event_log(text):
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

                # Handle "wake me up" pattern specially
                # Pattern: r"wake\s+me\s+(?:up\s+)?(in|at)\s+(.+)"
                # Group 1 is "in" or "at", Group 2 is the time
                if text.lower().startswith("wake"):
                    entities["message"] = "wake up"
                    if len(groups) >= 2 and groups[1]:
                        entities["time"] = groups[1].strip()
                else:
                    # Standard pattern: Group 1 is message, Group 2 is time
                    if groups and groups[0]:
                        entities["message"] = groups[0].strip()
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

    def _try_reminder_clear_all(self, text: str) -> Intent | None:
        """Try to match clear all reminders patterns."""
        for pattern in self._reminder_clear_all:
            if pattern.search(text):
                return Intent(
                    type=IntentType.REMINDER_CLEAR_ALL,
                    confidence=0.95,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_reminder_time_left(self, text: str) -> Intent | None:
        """Try to match reminder time remaining patterns."""
        for pattern in self._reminder_time_left:
            match = pattern.search(text)
            if match:
                entities = {}
                # Extract search term if present
                groups = match.groups()
                if groups and groups[0]:
                    entities["search"] = groups[0].strip()
                return Intent(
                    type=IntentType.REMINDER_TIME_LEFT,
                    confidence=0.85,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_history_query(self, text: str) -> Intent | None:
        """Try to match history query patterns."""
        for pattern in self._history_query:
            match = pattern.search(text)
            if match:
                entities = {}

                # Extract search content from capture group if present
                groups = match.groups()
                if groups and groups[0]:
                    entities["search_content"] = groups[0].strip()

                # Determine query type
                text_lower = text.lower()
                if "how long" in text_lower or "when did" in text_lower or "since" in text_lower:
                    entities["query_type"] = "time_since"
                elif "did i" in text_lower or "have i" in text_lower:
                    entities["query_type"] = "content_check"
                elif "do you have" in text_lower or "is there" in text_lower:
                    entities["query_type"] = "list"
                else:
                    entities["query_type"] = "list"

                # Try to detect time reference
                if "yesterday" in text_lower:
                    entities["time_ref"] = "yesterday"
                elif "today" in text_lower:
                    entities["time_ref"] = "today"
                elif "recent" in text_lower or "last" in text_lower:
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
                else:
                    # For patterns without capture groups (like "what's the news"),
                    # use the full text as the query
                    entities["query"] = text.strip()

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

    def _try_user_name_set(self, text: str) -> Intent | None:
        """Try to match user name set patterns."""
        for pattern in self._user_name_set:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract the name from the match
                if groups and groups[0]:
                    name = groups[0].strip().lower()

                    # Filter out common words that aren't names
                    if name in self.NAME_BLACKLIST:
                        continue

                    # Capitalize first letter
                    entities["name"] = name.capitalize()

                    # Check if password is mentioned in the text (for name change with password)
                    password_match = re.search(
                        r"(?:password|passcode|code)\s+(?:is\s+)?(\w+)", text, re.IGNORECASE
                    )
                    if password_match:
                        entities["password"] = password_match.group(1)

                    return Intent(
                        type=IntentType.USER_NAME_SET,
                        confidence=0.9,
                        entities=entities,
                        raw_text=text,
                    )
        return None

    def _try_user_password_set(self, text: str) -> Intent | None:
        """Try to match user password set patterns."""
        for pattern in self._user_password_set:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract the password from the match
                if groups and groups[0]:
                    entities["password"] = groups[0].strip()

                    return Intent(
                        type=IntentType.USER_PASSWORD_SET,
                        confidence=0.9,
                        entities=entities,
                        raw_text=text,
                    )
        return None

    def _try_time_query(self, text: str) -> Intent | None:
        """Try to match time query patterns."""
        for pattern in self._time_query:
            if pattern.search(text):
                return Intent(
                    type=IntentType.TIME_QUERY,
                    confidence=0.95,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_date_query(self, text: str) -> Intent | None:
        """Try to match date query patterns."""
        for pattern in self._date_query:
            if pattern.search(text):
                return Intent(
                    type=IntentType.DATE_QUERY,
                    confidence=0.95,
                    entities={},
                    raw_text=text,
                )
        return None

    def _try_future_time_query(self, text: str) -> Intent | None:
        """Try to match future time query patterns."""
        for pattern in self._future_time_query:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract amount and unit
                if groups and len(groups) >= 2:
                    amount_str = groups[0].lower()
                    # Convert word numbers to digits
                    if amount_str in self.WORD_NUMBERS:
                        entities["amount"] = str(self.WORD_NUMBERS[amount_str])
                    else:
                        entities["amount"] = amount_str
                    entities["unit"] = groups[1].lower()

                return Intent(
                    type=IntentType.FUTURE_TIME_QUERY,
                    confidence=0.95,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_duration_query(self, text: str) -> Intent | None:
        """Try to match duration query patterns.

        Examples: "how long was I in the shower?", "how much time did I spend cooking?"
        """
        for pattern in self._duration_query:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract activity from capture group
                if groups and groups[0]:
                    # Strip whitespace and trailing punctuation
                    activity = groups[0].strip().rstrip("?.!,")
                    entities["activity"] = activity

                return Intent(
                    type=IntentType.DURATION_QUERY,
                    confidence=0.85,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_activity_search(self, text: str) -> Intent | None:
        """Try to match activity search patterns.

        Examples: "what was I doing around 10 AM?", "what happened between 2 and 3 PM?"
        """
        for pattern in self._activity_search:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract time reference(s)
                if groups:
                    if len(groups) >= 2 and groups[1]:
                        # Range query: start and end time
                        entities["start_time"] = groups[0].strip()
                        entities["end_time"] = groups[1].strip()
                    elif groups[0]:
                        # Point query: single time reference
                        entities["time_ref"] = groups[0].strip()

                return Intent(
                    type=IntentType.ACTIVITY_SEARCH,
                    confidence=0.85,
                    entities=entities,
                    raw_text=text,
                )
        return None

    def _try_event_log(self, text: str) -> Intent | None:
        """Try to match event log patterns.

        Examples: "I'm going to the gym", "finished my workout", "note: buy milk"
        """
        text_lower = text.lower()

        for pattern in self._event_log:
            match = pattern.search(text)
            if match:
                entities = {}
                groups = match.groups()

                # Extract context/activity from capture group
                if groups and groups[0]:
                    entities["context"] = groups[0].strip()

                # Determine event type based on keywords
                if any(
                    kw in text_lower
                    for kw in ["going", "heading", "starting", "beginning", "about to"]
                ):
                    entities["event_type"] = "activity_start"
                elif any(
                    kw in text_lower
                    for kw in [
                        "done",
                        "finished",
                        "back",
                        "completed",
                        "ended",
                        "stopped",
                        "leaving",
                        "left",
                    ]
                ):
                    entities["event_type"] = "activity_end"
                elif any(kw in text_lower for kw in ["note", "memo", "remember", "parked"]):
                    entities["event_type"] = "note"
                else:
                    entities["event_type"] = "note"

                return Intent(
                    type=IntentType.EVENT_LOG,
                    confidence=0.85,
                    entities=entities,
                    raw_text=text,
                )
        return None
