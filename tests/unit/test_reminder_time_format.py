"""Unit tests for time-aware response formatting (T009)."""

from datetime import UTC, datetime, timedelta

from ara.commands.reminder import format_time_local


class TestFormatTimeLocal:
    """Tests for format_time_local function."""

    def test_format_time_local_returns_string(self) -> None:
        """Test that format_time_local returns a string."""
        dt = datetime.now(UTC)
        result = format_time_local(dt)
        assert isinstance(result, str)

    def test_format_time_local_includes_am_pm(self) -> None:
        """Test that format includes AM or PM."""
        dt = datetime.now(UTC)
        result = format_time_local(dt)
        assert "AM" in result or "PM" in result

    def test_format_time_local_includes_colon(self) -> None:
        """Test that format includes time with colon."""
        dt = datetime.now(UTC)
        result = format_time_local(dt)
        assert ":" in result

    def test_format_time_local_morning(self) -> None:
        """Test formatting a morning time."""
        # Create a time known to be AM in UTC
        morning = datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC)
        result = format_time_local(morning)
        # Should include minutes
        assert ":30" in result

    def test_format_time_local_afternoon(self) -> None:
        """Test formatting an afternoon time."""
        afternoon = datetime(2024, 1, 15, 14, 45, 0, tzinfo=UTC)
        result = format_time_local(afternoon)
        # Should include minutes
        assert ":45" in result

    def test_format_time_local_midnight(self) -> None:
        """Test formatting midnight."""
        midnight = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        result = format_time_local(midnight)
        # Should be formatted as a time string
        assert ":" in result
        assert "AM" in result or "PM" in result

    def test_format_time_local_noon(self) -> None:
        """Test formatting noon."""
        noon = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        result = format_time_local(noon)
        assert ":" in result

    def test_format_time_local_different_times(self) -> None:
        """Test that different times produce different outputs."""
        time1 = datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC)
        time2 = datetime(2024, 1, 15, 15, 0, 0, tzinfo=UTC)
        result1 = format_time_local(time1)
        result2 = format_time_local(time2)
        assert result1 != result2


class TestTimeAwareResponseFormat:
    """Tests for time-aware response format in reminder confirmations."""

    def test_response_includes_current_time(self) -> None:
        """Test that reminder response would include current time format."""
        now = datetime.now(UTC)
        current_time = format_time_local(now)
        # Verify the format is suitable for the response
        assert len(current_time) > 0
        assert any(c.isdigit() for c in current_time)

    def test_response_includes_target_time(self) -> None:
        """Test that reminder response would include target time format."""
        target = datetime.now(UTC) + timedelta(hours=1)
        target_time = format_time_local(target)
        # Verify the format is suitable for the response
        assert len(target_time) > 0
        assert any(c.isdigit() for c in target_time)

    def test_both_times_formatted_consistently(self) -> None:
        """Test that current and target times use same format."""
        now = datetime.now(UTC)
        target = now + timedelta(hours=1)

        current = format_time_local(now)
        future = format_time_local(target)

        # Both should have AM/PM
        assert "AM" in current or "PM" in current
        assert "AM" in future or "PM" in future

        # Both should have colon for time
        assert ":" in current
        assert ":" in future
