"""Unit tests for language model module."""


from ara.llm import LLMResponse, create_language_model
from ara.llm.mock import MockLanguageModel


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self) -> None:
        """Test creating an LLM response."""
        response = LLMResponse(
            text="The time is 3:30 PM.",
            tokens_used=15,
            model="llama3.2:3b",
            latency_ms=500,
        )
        assert response.text == "The time is 3:30 PM."
        assert response.tokens_used == 15
        assert response.model == "llama3.2:3b"
        assert response.latency_ms == 500


class TestMockLanguageModel:
    """Tests for MockLanguageModel."""

    def test_generate_returns_preset(self) -> None:
        """Test that generate returns preset response."""
        model = MockLanguageModel()
        model.set_response("I'm doing well, thank you!")

        response = model.generate("How are you?")

        assert response.text == "I'm doing well, thank you!"
        assert response.tokens_used > 0

    def test_generate_default_response(self) -> None:
        """Test default generation response."""
        model = MockLanguageModel()

        response = model.generate("Hello")

        assert "mock" in response.text.lower() or response.text != ""

    def test_set_system_prompt(self) -> None:
        """Test setting system prompt."""
        model = MockLanguageModel()
        model.set_system_prompt("You are a helpful assistant.")
        assert model.system_prompt == "You are a helpful assistant."

    def test_clear_context(self) -> None:
        """Test clearing conversation context."""
        model = MockLanguageModel()
        model.generate("Hello")
        model.generate("How are you?")

        model.clear_context()

        assert model.context_length == 0

    def test_generate_records_calls(self) -> None:
        """Test that generate records call history."""
        model = MockLanguageModel()

        model.generate("Hello")
        model.generate("World")

        assert model.call_count == 2

    def test_generate_with_parameters(self) -> None:
        """Test generation with custom parameters."""
        model = MockLanguageModel()
        model.set_response("Test response")

        response = model.generate(
            prompt="Test",
            max_tokens=50,
            temperature=0.5,
        )

        assert response.text == "Test response"


class TestCreateLanguageModel:
    """Tests for language model factory function."""

    def test_create_mock_model(self) -> None:
        """Test creating mock language model."""
        model = create_language_model(use_mock=True)
        assert isinstance(model, MockLanguageModel)

    def test_create_model_with_config(self) -> None:
        """Test creating model with configuration."""
        from ara.config import LLMConfig

        config = LLMConfig(
            provider="ollama",
            model="llama3.2:3b",
            temperature=0.8,
        )
        model = create_language_model(config=config, use_mock=True)

        assert isinstance(model, MockLanguageModel)
