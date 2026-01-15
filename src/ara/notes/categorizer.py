"""Auto-categorization for notes and activities.

Uses keyword-first approach with optional LLM fallback for ambiguous cases.
"""

import logging

from .models import Category

logger = logging.getLogger(__name__)

# Keyword mappings for fast categorization (<10ms)
CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.HEALTH: [
        "workout",
        "exercise",
        "gym",
        "run",
        "running",
        "yoga",
        "meditation",
        "meditate",
        "doctor",
        "health",
        "hospital",
        "clinic",
        "therapy",
        "physical therapy",
        "dentist",
        "checkup",
        "fitness",
        "swim",
        "swimming",
        "bike",
        "biking",
        "cycling",
        "walk",
        "walking",
        "hike",
        "hiking",
        "stretch",
        "stretching",
        "weights",
        "cardio",
    ],
    Category.WORK: [
        "meeting",
        "call",
        "project",
        "deadline",
        "client",
        "sprint",
        "standup",
        "work",
        "office",
        "presentation",
        "report",
        "email",
        "conference",
        "interview",
        "review",
        "coding",
        "programming",
        "development",
        "deploy",
        "release",
        "budget",
        "quarterly",
        "strategy",
        "team",
        "manager",
        "boss",
        "colleague",
        "coworker",
    ],
    Category.ERRANDS: [
        "groceries",
        "grocery",
        "shopping",
        "pickup",
        "pick up",
        "drop off",
        "errand",
        "pharmacy",
        "bank",
        "post office",
        "dry cleaning",
        "laundry",
        "repair",
        "mechanic",
        "car wash",
        "gas station",
        "store",
        "mall",
        "appointment",
        "dmv",
        "license",
        "registration",
    ],
    Category.PERSONAL: [
        "family",
        "friend",
        "dinner",
        "lunch",
        "breakfast",
        "movie",
        "game",
        "hobby",
        "party",
        "birthday",
        "anniversary",
        "date",
        "vacation",
        "travel",
        "trip",
        "read",
        "reading",
        "book",
        "tv",
        "netflix",
        "relax",
        "relaxing",
        "nap",
        "sleep",
        "rest",
        "cook",
        "cooking",
        "bake",
        "baking",
        "garden",
        "gardening",
    ],
}


def categorize(text: str) -> Category:
    """Categorize text using keyword matching.

    Fast path: Uses keyword matching for obvious categories (<10ms).
    Returns UNCATEGORIZED if no match found.

    Args:
        text: Text to categorize (note transcript or activity name)

    Returns:
        Category enum value
    """
    text_lower = text.lower()

    # Check each category's keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                logger.debug(
                    f"Categorized '{text[:50]}...' as {category.value} (keyword: {keyword})"
                )
                return category

    logger.debug(f"No category match for '{text[:50]}...', using UNCATEGORIZED")
    return Category.UNCATEGORIZED


def categorize_with_confidence(text: str) -> tuple[Category, float]:
    """Categorize text and return confidence score.

    Args:
        text: Text to categorize

    Returns:
        Tuple of (Category, confidence) where confidence is 0.0-1.0
    """
    text_lower = text.lower()

    # Count keyword matches per category
    matches: dict[Category, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            matches[category] = count

    if not matches:
        return Category.UNCATEGORIZED, 0.5

    # Return category with most matches
    best_category = max(matches, key=lambda c: matches[c])
    # Confidence based on number of matches (more matches = higher confidence)
    confidence = min(0.95, 0.7 + (matches[best_category] * 0.1))

    return best_category, confidence


# LLM categorization prompt
LLM_CATEGORIZE_PROMPT = """Categorize this text into ONE of these categories:
- work: meetings, calls, projects, deadlines, office tasks
- personal: family, friends, hobbies, entertainment
- health: exercise, medical, wellness, fitness
- errands: shopping, chores, appointments, tasks

Text: "{text}"

Respond with ONLY the category name (work, personal, health, or errands).
If unsure, respond with: uncategorized"""


class LLMCategorizer:
    """LLM-based categorizer for ambiguous cases.

    Uses local LLM when keyword matching has low confidence.
    """

    def __init__(self, llm: object) -> None:
        """Initialize with language model.

        Args:
            llm: Language model with generate() method
        """
        self._llm = llm

    def categorize(self, text: str) -> Category:
        """Categorize text using LLM.

        Args:
            text: Text to categorize

        Returns:
            Category enum value
        """
        prompt = LLM_CATEGORIZE_PROMPT.format(text=text)

        try:
            response = self._llm.generate(prompt, max_tokens=20, temperature=0.1)  # type: ignore
            response_text = response.text if hasattr(response, "text") else str(response)

            # Parse response
            category_str = response_text.strip().lower()
            return Category(category_str)

        except (ValueError, AttributeError) as e:
            logger.warning(f"LLM categorization failed: {e}")
            return Category.UNCATEGORIZED


def categorize_with_llm_fallback(
    text: str,
    llm: object | None = None,
    confidence_threshold: float = 0.7,
) -> Category:
    """Categorize with keyword matching and optional LLM fallback.

    Args:
        text: Text to categorize
        llm: Optional language model for fallback
        confidence_threshold: Minimum confidence for keyword match

    Returns:
        Category enum value
    """
    # Try keyword matching first
    category, confidence = categorize_with_confidence(text)

    # If confident enough or no LLM, return keyword result
    if confidence >= confidence_threshold or llm is None:
        return category

    # Fall back to LLM for low-confidence cases
    logger.debug(f"Low confidence ({confidence:.2f}), falling back to LLM")
    llm_categorizer = LLMCategorizer(llm)
    return llm_categorizer.categorize(text)


__all__ = [
    "categorize",
    "categorize_with_confidence",
    "categorize_with_llm_fallback",
    "LLMCategorizer",
    "CATEGORY_KEYWORDS",
]
