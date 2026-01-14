"""User profile configuration for personalized announcements.

Stores user preferences like name for countdown announcements.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .loader import get_user_profile_path

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalized announcements.

    Attributes:
        version: Schema version for future migrations.
        name: User's name for personalized announcements. None if not configured.
        preferences: Reserved for future settings.
    """

    version: int = 1
    name: str | None = None
    preferences: dict = field(default_factory=dict)


def load_user_profile(path: Path | None = None) -> UserProfile:
    """Load user profile from JSON file.

    Args:
        path: Optional path to profile file. Defaults to ~/.ara/user_profile.json

    Returns:
        UserProfile with loaded data or defaults if file doesn't exist.
    """
    if path is None:
        path = get_user_profile_path()

    if not path.exists():
        logger.debug(f"User profile not found at {path}, using defaults")
        return UserProfile()

    try:
        with open(path) as f:
            data = json.load(f)

        # Validate and extract name
        name = data.get("name")
        if name is not None:
            name = str(name).strip()
            if not name:
                name = None

        return UserProfile(
            version=data.get("version", 1),
            name=name,
            preferences=data.get("preferences", {}),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in user profile: {e}")
        return UserProfile()
    except Exception as e:
        logger.error(f"Failed to load user profile: {e}")
        return UserProfile()


def save_user_profile(profile: UserProfile, path: Path | None = None) -> bool:
    """Save user profile to JSON file.

    Args:
        profile: UserProfile to save.
        path: Optional path to profile file. Defaults to ~/.ara/user_profile.json

    Returns:
        True if saved successfully, False otherwise.
    """
    if path is None:
        path = get_user_profile_path()

    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": profile.version,
            "name": profile.name,
            "preferences": profile.preferences,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved user profile to {path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save user profile: {e}")
        return False


__all__ = [
    "UserProfile",
    "load_user_profile",
    "save_user_profile",
]
