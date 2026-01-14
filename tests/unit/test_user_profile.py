"""Unit tests for user profile functionality.

Tests user profile load, save, and name handling.
"""

import json
import tempfile
from pathlib import Path

from ara.config.user_profile import UserProfile, load_user_profile, save_user_profile


class TestUserProfileDataclass:
    """Tests for UserProfile dataclass."""

    def test_default_profile_has_no_name(self):
        """Test that default profile has no name."""
        profile = UserProfile()
        assert profile.name is None
        assert profile.version == 1
        assert profile.preferences == {}

    def test_profile_with_name(self):
        """Test profile with name."""
        profile = UserProfile(name="Ammar")
        assert profile.name == "Ammar"

    def test_profile_with_preferences(self):
        """Test profile with preferences."""
        profile = UserProfile(name="Test", preferences={"theme": "dark"})
        assert profile.preferences == {"theme": "dark"}


class TestLoadUserProfile:
    """Tests for load_user_profile function (T018)."""

    def test_load_returns_defaults_when_file_missing(self):
        """Test that missing file returns default profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.json"
            profile = load_user_profile(nonexistent)
            assert profile.name is None
            assert profile.version == 1

    def test_load_parses_valid_json(self):
        """Test loading valid profile JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            data = {
                "version": 1,
                "name": "Ammar",
                "preferences": {"countdown_enabled": True},
            }
            with open(profile_path, "w") as f:
                json.dump(data, f)

            profile = load_user_profile(profile_path)
            assert profile.name == "Ammar"
            assert profile.preferences == {"countdown_enabled": True}

    def test_load_handles_invalid_json(self):
        """Test graceful handling of invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            with open(profile_path, "w") as f:
                f.write("not valid json {")

            profile = load_user_profile(profile_path)
            # Should return default profile on error
            assert profile.name is None
            assert profile.version == 1

    def test_load_trims_whitespace_from_name(self):
        """Test that name whitespace is trimmed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            data = {"version": 1, "name": "  Ammar  ", "preferences": {}}
            with open(profile_path, "w") as f:
                json.dump(data, f)

            profile = load_user_profile(profile_path)
            assert profile.name == "Ammar"

    def test_load_treats_empty_name_as_none(self):
        """Test that empty or whitespace-only name becomes None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            data = {"version": 1, "name": "   ", "preferences": {}}
            with open(profile_path, "w") as f:
                json.dump(data, f)

            profile = load_user_profile(profile_path)
            assert profile.name is None


class TestSaveUserProfile:
    """Tests for save_user_profile function (T018)."""

    def test_save_creates_file(self):
        """Test that save creates the profile file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            profile = UserProfile(name="Test")

            result = save_user_profile(profile, profile_path)
            assert result is True
            assert profile_path.exists()

    def test_save_writes_correct_data(self):
        """Test that saved data is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            profile = UserProfile(name="Ammar", preferences={"test": True})

            save_user_profile(profile, profile_path)

            with open(profile_path) as f:
                data = json.load(f)

            assert data["name"] == "Ammar"
            assert data["version"] == 1
            assert data["preferences"] == {"test": True}

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "subdir" / "profile.json"
            profile = UserProfile(name="Test")

            result = save_user_profile(profile, profile_path)
            assert result is True
            assert profile_path.exists()

    def test_roundtrip_preserves_data(self):
        """Test that save then load preserves all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profile.json"
            original = UserProfile(name="Ammar", preferences={"theme": "dark", "sound": True})

            save_user_profile(original, profile_path)
            loaded = load_user_profile(profile_path)

            assert loaded.name == original.name
            assert loaded.version == original.version
            assert loaded.preferences == original.preferences
