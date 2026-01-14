"""Unit tests for ordinal number generation (T024)."""


from ara.router.orchestrator import _get_ordinal


class TestGetOrdinal:
    """Tests for _get_ordinal function."""

    def test_ordinal_first_through_tenth(self) -> None:
        """Test ordinal words for 1 through 10."""
        expected = {
            1: "first",
            2: "second",
            3: "third",
            4: "fourth",
            5: "fifth",
            6: "sixth",
            7: "seventh",
            8: "eighth",
            9: "ninth",
            10: "tenth",
        }

        for num, word in expected.items():
            assert _get_ordinal(num) == word, f"Expected {word} for {num}"

    def test_ordinal_11th_through_13th(self) -> None:
        """Test special case ordinals 11th, 12th, 13th."""
        assert _get_ordinal(11) == "11th"
        assert _get_ordinal(12) == "12th"
        assert _get_ordinal(13) == "13th"

    def test_ordinal_21st_22nd_23rd(self) -> None:
        """Test ordinals 21st, 22nd, 23rd."""
        assert _get_ordinal(21) == "21st"
        assert _get_ordinal(22) == "22nd"
        assert _get_ordinal(23) == "23rd"

    def test_ordinal_regular_numbers(self) -> None:
        """Test regular ordinal endings."""
        assert _get_ordinal(14) == "14th"
        assert _get_ordinal(15) == "15th"
        assert _get_ordinal(20) == "20th"
        assert _get_ordinal(24) == "24th"
        assert _get_ordinal(25) == "25th"

    def test_ordinal_31st_32nd_33rd(self) -> None:
        """Test ordinals 31st, 32nd, 33rd."""
        assert _get_ordinal(31) == "31st"
        assert _get_ordinal(32) == "32nd"
        assert _get_ordinal(33) == "33rd"

    def test_ordinal_111th_112th_113th(self) -> None:
        """Test special case ordinals 111th, 112th, 113th (not 111st)."""
        assert _get_ordinal(111) == "111th"
        assert _get_ordinal(112) == "112th"
        assert _get_ordinal(113) == "113th"

    def test_ordinal_100th_and_beyond(self) -> None:
        """Test ordinals for 100+."""
        assert _get_ordinal(100) == "100th"
        assert _get_ordinal(101) == "101st"
        assert _get_ordinal(102) == "102nd"
        assert _get_ordinal(103) == "103rd"
        assert _get_ordinal(104) == "104th"

    def test_ordinal_returns_string(self) -> None:
        """Test that _get_ordinal always returns a string."""
        for i in range(1, 50):
            result = _get_ordinal(i)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_ordinal_first_ten_are_words(self) -> None:
        """Test that first 10 ordinals are full words, not numbers."""
        for i in range(1, 11):
            result = _get_ordinal(i)
            # Should not start with a digit
            assert not result[0].isdigit()

    def test_ordinal_above_ten_are_numeric(self) -> None:
        """Test that ordinals above 10 use numeric format."""
        for i in range(11, 20):
            result = _get_ordinal(i)
            # Should start with a digit
            assert result[0].isdigit()

    def test_ordinal_suffix_consistency(self) -> None:
        """Test that suffix endings are consistent."""
        # All numbers ending in 1 (except 11) should end in 'st'
        for n in [1, 21, 31, 41, 51, 101]:
            if n != 11:
                assert _get_ordinal(n).endswith("st") or _get_ordinal(n) == "first"

        # All numbers ending in 2 (except 12) should end in 'nd'
        for n in [2, 22, 32, 42, 52, 102]:
            if n != 12:
                assert _get_ordinal(n).endswith("nd") or _get_ordinal(n) == "second"

        # All numbers ending in 3 (except 13) should end in 'rd'
        for n in [3, 23, 33, 43, 53, 103]:
            if n != 13:
                assert _get_ordinal(n).endswith("rd") or _get_ordinal(n) == "third"
