"""User profile configuration for personalized announcements.

Stores user preferences like name for countdown announcements.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    """Hash a password for storage.

    Args:
        password: Plain text password.

    Returns:
        SHA-256 hash of the password.
    """
    return hashlib.sha256(password.strip().lower().encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash.

    Args:
        password: Plain text password to verify.
        password_hash: Stored hash to compare against.

    Returns:
        True if password matches, False otherwise.
    """
    return _hash_password(password) == password_hash


def _get_user_profile_path() -> Path:
    """Get the path to the user profile file.

    Returns:
        Path to ~/.ara/user_profile.json
    """
    ara_dir = Path.home() / ".ara"
    ara_dir.mkdir(parents=True, exist_ok=True)
    return ara_dir / "user_profile.json"


@dataclass
class UserProfile:
    """User profile for personalized announcements.

    Attributes:
        version: Schema version for future migrations.
        name: User's name for personalized announcements. None if not configured.
        password_hash: Hash of password required to change name. None if not set.
        preferences: Reserved for future settings.
    """

    version: int = 1
    name: str | None = None
    password_hash: str | None = None
    preferences: dict = field(default_factory=dict)

    def set_password(self, password: str) -> None:
        """Set the password for profile protection.

        Args:
            password: Plain text password to set.
        """
        self.password_hash = _hash_password(password)

    def clear_password(self) -> None:
        """Remove password protection from profile."""
        self.password_hash = None

    def verify_password(self, password: str) -> bool:
        """Verify a password matches the stored hash.

        Args:
            password: Plain text password to verify.

        Returns:
            True if password matches or no password set, False otherwise.
        """
        if not self.password_hash:
            return True
        return verify_password(password, self.password_hash)

    @property
    def is_password_protected(self) -> bool:
        """Check if profile has password protection."""
        return self.password_hash is not None


def load_user_profile(path: Path | None = None) -> UserProfile:
    """Load user profile from JSON file.

    Args:
        path: Optional path to profile file. Defaults to ~/.ara/user_profile.json

    Returns:
        UserProfile with loaded data or defaults if file doesn't exist.
    """
    if path is None:
        path = _get_user_profile_path()

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

        # Extract password hash if present
        password_hash = data.get("password_hash")
        if password_hash is not None:
            password_hash = str(password_hash).strip()
            if not password_hash:
                password_hash = None

        return UserProfile(
            version=data.get("version", 1),
            name=name,
            password_hash=password_hash,
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
        path = _get_user_profile_path()

    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": profile.version,
            "name": profile.name,
            "password_hash": profile.password_hash,
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
