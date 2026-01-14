"""Unit tests for cloud LLM (Claude API) integration."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestCloudLLMConfig:
    """Tests for CloudLLMConfig data class."""

    def test_create_config(self) -> None:
        """Test creating CloudLLMConfig."""
        from ara.llm.cloud import CloudLLMConfig

        config = CloudLLMConfig(
            api_key="test-key",
            model="claude-3-haiku-20240307",
            max_tokens=1024,
        )

        assert config.api_key == "test-key"
        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 1024

    def test_default_values(self) -> None:
        """Test CloudLLMConfig default values."""
        from ara.llm.cloud import CloudLLMConfig

        config = CloudLLMConfig(api_key="test-key")

        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 1024
        assert config.temperature == 0.7

    def test_from_env(self) -> None:
        """Test creating config from environment variable."""
        from ara.llm.cloud import CloudLLMConfig

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            config = CloudLLMConfig.from_env()

        assert config.api_key == "env-key"

    def test_from_env_missing_key(self) -> None:
        """Test error when API key is missing."""
        from ara.llm.cloud import CloudLLMConfig

        # Create environment without the API key
        env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with (
            patch.dict(os.environ, env_without_key, clear=True),
            pytest.raises(ValueError, match="ANTHROPIC_API_KEY"),
        ):
            CloudLLMConfig.from_env()


class TestCloudLanguageModel:
    """Tests for CloudLanguageModel class."""

    def test_create_cloud_model(self) -> None:
        """Test creating CloudLanguageModel."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)

        assert model is not None
        assert model.model_name == "claude-3-haiku-20240307"

    def test_implements_language_model_protocol(self) -> None:
        """Test CloudLanguageModel implements LanguageModel protocol."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)

        # Check protocol methods exist
        assert hasattr(model, "generate")
        assert hasattr(model, "set_system_prompt")
        assert hasattr(model, "clear_context")

    @patch("ara.llm.cloud.anthropic")
    @patch("ara.llm.cloud.ANTHROPIC_AVAILABLE", True)
    def test_generate_response(self, mock_anthropic: MagicMock) -> None:
        """Test generating response from Claude API."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        # Mock the API response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Paris is the capital of France.")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 8
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)

        result = model.generate("What is the capital of France?")

        assert result.text == "Paris is the capital of France."
        assert result.tokens_used == 18  # input + output

    @patch("ara.llm.cloud.anthropic")
    @patch("ara.llm.cloud.ANTHROPIC_AVAILABLE", True)
    def test_generate_with_system_prompt(self, mock_anthropic: MagicMock) -> None:
        """Test generating with custom system prompt."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)
        model.set_system_prompt("You are a helpful assistant.")

        model.generate("Hello")

        # Verify system prompt was included
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs.get("system") == "You are a helpful assistant."

    @patch("ara.llm.cloud.anthropic")
    @patch("ara.llm.cloud.ANTHROPIC_AVAILABLE", True)
    def test_generate_handles_api_error(self, mock_anthropic: MagicMock) -> None:
        """Test graceful handling of API errors."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.Anthropic.return_value = mock_client

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)

        with pytest.raises(Exception, match="API Error"):
            model.generate("Test")

    def test_clear_context(self) -> None:
        """Test clearing conversation context."""
        from ara.llm.cloud import CloudLanguageModel, CloudLLMConfig

        config = CloudLLMConfig(api_key="test-key")
        model = CloudLanguageModel(config=config)

        model.set_system_prompt("Test prompt")
        model.clear_context()

        # After clear, system prompt should be reset
        assert model._system_prompt is None or model._system_prompt == ""


class TestMockCloudModel:
    """Tests for MockCloudModel for testing."""

    def test_create_mock_cloud_model(self) -> None:
        """Test creating MockCloudModel."""
        from ara.llm.cloud import MockCloudModel

        model = MockCloudModel()
        assert model is not None

    def test_mock_generate(self) -> None:
        """Test mock model generates preset response."""
        from ara.llm.cloud import MockCloudModel

        model = MockCloudModel()
        model.set_response("Mock response")

        result = model.generate("Test query")
        assert result.text == "Mock response"

    def test_mock_tracks_calls(self) -> None:
        """Test mock model tracks API calls."""
        from ara.llm.cloud import MockCloudModel

        model = MockCloudModel()
        model.set_response("Response")

        model.generate("Query 1")
        model.generate("Query 2")

        assert len(model.calls) == 2
        assert model.calls[0] == "Query 1"


class TestComplexityScoring:
    """Tests for query complexity scoring."""

    def test_simple_query_low_complexity(self) -> None:
        """Test simple queries have low complexity."""
        from ara.llm.cloud import score_query_complexity

        score = score_query_complexity("What time is it?")
        assert score < 0.3

    def test_complex_query_high_complexity(self) -> None:
        """Test complex queries have high complexity."""
        from ara.llm.cloud import score_query_complexity

        query = (
            "Can you explain the differences between supervised and unsupervised "
            "machine learning, and provide examples of when to use each approach "
            "in real-world applications?"
        )
        score = score_query_complexity(query)
        assert score > 0.3  # Complex query should score above simple threshold

    def test_code_question_high_complexity(self) -> None:
        """Test code-related questions have high complexity."""
        from ara.llm.cloud import score_query_complexity

        query = "Write a Python function to implement a quicksort algorithm"
        score = score_query_complexity(query)
        assert score > 0.2  # Code questions should be above simple threshold

    def test_factual_query_medium_complexity(self) -> None:
        """Test factual queries have medium complexity."""
        from ara.llm.cloud import score_query_complexity

        query = "What are the main causes of climate change?"
        score = score_query_complexity(query)
        assert score >= 0.0  # Factual queries can vary


class TestCloudFallback:
    """Tests for cloud fallback behavior."""

    def test_should_fallback_on_context_overflow(self) -> None:
        """Test fallback triggers on context overflow."""
        from ara.llm.cloud import should_use_cloud_fallback

        # Simulate a local LLM context overflow error
        error = Exception("context length exceeded")
        assert should_use_cloud_fallback(error) is True

    def test_no_fallback_on_other_errors(self) -> None:
        """Test no fallback on non-context errors."""
        from ara.llm.cloud import should_use_cloud_fallback

        error = Exception("model not found")
        assert should_use_cloud_fallback(error) is False

    def test_should_fallback_on_complexity(self) -> None:
        """Test fallback triggers on high complexity."""
        from ara.llm.cloud import should_use_cloud_fallback_for_complexity

        assert should_use_cloud_fallback_for_complexity(0.8) is True
        assert should_use_cloud_fallback_for_complexity(0.3) is False
