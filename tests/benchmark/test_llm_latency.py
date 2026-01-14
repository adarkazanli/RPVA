"""LLM latency benchmarks.

Measures language model inference performance.
Target: <4s on Raspberry Pi 4, <1s on laptop.
"""

import pytest

from ara.llm.mock import MockLanguageModel


class TestLLMLatency:
    """Benchmark tests for LLM latency."""

    @pytest.fixture
    def mock_llm(self) -> MockLanguageModel:
        """Create mock LLM for baseline tests."""
        llm = MockLanguageModel()
        llm.set_response("It's 3:30 in the afternoon.")
        return llm

    @pytest.mark.benchmark
    def test_mock_generation_latency(self, benchmark, mock_llm: MockLanguageModel) -> None:
        """Benchmark mock generation (baseline)."""
        mock_llm.set_latency(0)  # Remove artificial latency

        result = benchmark(mock_llm.generate, "What time is it?")

        assert "3:30" in result.text

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_ollama_generation_latency(self, benchmark) -> None:
        """Benchmark real Ollama generation.

        This test requires Ollama to be running with a model loaded.
        """
        try:
            from ara.llm.ollama import OllamaLanguageModel

            llm = OllamaLanguageModel(
                model="llama3.2:3b",
                max_tokens=50,  # Short responses for benchmarking
            )

            # Check if Ollama is available
            if not llm.is_available:
                pytest.skip("Ollama not running")

        except RuntimeError:
            pytest.skip("Ollama client not available")

        # Set system prompt for consistent responses
        llm.set_system_prompt("You are a helpful assistant. Keep responses brief (1 sentence).")

        # Warm up
        llm.generate("Hello")
        llm.clear_context()

        # Benchmark
        result = benchmark(llm.generate, "What is 2+2?")

        assert len(result.text) > 0
        assert result.latency_ms > 0

    @pytest.mark.benchmark
    def test_generation_with_context(self, benchmark, mock_llm: MockLanguageModel) -> None:
        """Benchmark generation with conversation context."""
        mock_llm.set_latency(0)

        # Build up context
        mock_llm.generate("Hello")
        mock_llm.generate("How are you?")
        mock_llm.generate("What's the weather like?")

        # Benchmark with context
        result = benchmark(mock_llm.generate, "What time is it?")

        assert result.text != ""

    @pytest.mark.benchmark
    def test_streaming_generation_latency(self, benchmark, mock_llm: MockLanguageModel) -> None:
        """Benchmark time to first token in streaming mode."""
        mock_llm.set_latency(0)

        def get_first_token():
            stream = mock_llm.generate_stream("What time is it?")
            return next(stream)

        result = benchmark(get_first_token)

        assert result.token != ""
