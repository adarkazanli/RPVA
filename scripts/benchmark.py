#!/usr/bin/env python3
"""Benchmark runner for Ara Voice Assistant.

Runs benchmarks and generates reports with P50/P95/P99 latency statistics.

Usage:
    python scripts/benchmark.py              # Run all benchmarks
    python scripts/benchmark.py --quick      # Run quick benchmarks only
    python scripts/benchmark.py --component stt  # Run specific component
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    samples: list[float] = field(default_factory=list)
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    mean: float = 0.0
    min: float = 0.0
    max: float = 0.0

    def calculate_stats(self) -> None:
        """Calculate statistics from samples."""
        if not self.samples:
            return

        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)

        self.min = sorted_samples[0]
        self.max = sorted_samples[-1]
        self.mean = statistics.mean(sorted_samples)

        # Percentiles
        self.p50 = sorted_samples[int(n * 0.5)]
        self.p95 = sorted_samples[int(n * 0.95)]
        self.p99 = sorted_samples[min(int(n * 0.99), n - 1)]


def run_pytest_benchmark(marker: str = "") -> dict:
    """Run pytest benchmarks and return results."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/benchmark/",
        "-v",
        "--benchmark-only",
        "--benchmark-json=benchmark_results.json",
    ]

    if marker:
        cmd.extend(["-m", marker])

    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Load results
    results_file = Path("benchmark_results.json")
    if results_file.exists():
        with open(results_file) as f:
            return json.load(f)

    return {}


def run_manual_benchmarks(component: str | None = None) -> list[BenchmarkResult]:
    """Run manual benchmarks with custom timing."""
    results = []

    # Add project to path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    if component is None or component == "stt":
        results.append(benchmark_stt())

    if component is None or component == "llm":
        results.append(benchmark_llm())

    if component is None or component == "tts":
        results.append(benchmark_tts())

    if component is None or component == "e2e":
        results.append(benchmark_e2e())

    return results


def benchmark_stt() -> BenchmarkResult:
    """Benchmark STT latency."""
    print("\n📊 Benchmarking STT...")

    from ara.stt.mock import MockTranscriber

    transcriber = MockTranscriber()
    transcriber.set_response("what time is it")
    transcriber.set_latency(0)

    audio = bytes(16000 * 2 * 2)  # 2 seconds
    result = BenchmarkResult(name="STT (mock)")

    # Warmup
    for _ in range(5):
        transcriber.transcribe(audio, 16000)

    # Benchmark
    for _ in range(100):
        start = time.perf_counter()
        transcriber.transcribe(audio, 16000)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.samples.append(elapsed_ms)

    result.calculate_stats()
    return result


def benchmark_llm() -> BenchmarkResult:
    """Benchmark LLM latency."""
    print("\n📊 Benchmarking LLM...")

    from ara.llm.mock import MockLanguageModel

    llm = MockLanguageModel()
    llm.set_response("It's 3:30 in the afternoon.")
    llm.set_latency(0)

    result = BenchmarkResult(name="LLM (mock)")

    # Warmup
    for _ in range(5):
        llm.generate("What time is it?")
        llm.clear_context()

    # Benchmark
    for _ in range(100):
        start = time.perf_counter()
        llm.generate("What time is it?")
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.samples.append(elapsed_ms)
        llm.clear_context()

    result.calculate_stats()
    return result


def benchmark_tts() -> BenchmarkResult:
    """Benchmark TTS latency."""
    print("\n📊 Benchmarking TTS...")

    from ara.tts.mock import MockSynthesizer

    synth = MockSynthesizer()
    synth.set_latency(0)

    text = "It's 3:30 in the afternoon."
    result = BenchmarkResult(name="TTS (mock)")

    # Warmup
    for _ in range(5):
        synth.synthesize(text)

    # Benchmark
    for _ in range(100):
        start = time.perf_counter()
        synth.synthesize(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.samples.append(elapsed_ms)

    result.calculate_stats()
    return result


def benchmark_e2e() -> BenchmarkResult:
    """Benchmark end-to-end latency."""
    print("\n📊 Benchmarking E2E pipeline...")

    from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
    from ara.feedback.audio import MockFeedback
    from ara.llm.mock import MockLanguageModel
    from ara.router.orchestrator import Orchestrator
    from ara.stt.mock import MockTranscriber
    from ara.tts.mock import MockSynthesizer
    from ara.wake_word.mock import MockWakeWordDetector

    # Create mock orchestrator
    capture = MockAudioCapture()
    playback = MockAudioPlayback()
    wake_word = MockWakeWordDetector()
    transcriber = MockTranscriber()
    llm = MockLanguageModel()
    synthesizer = MockSynthesizer()
    feedback = MockFeedback()

    wake_word.initialize(keywords=["ara"], sensitivity=0.5)
    transcriber.set_response("what time is it")
    llm.set_response("It's 3:30 in the afternoon.")

    # Remove latencies
    transcriber.set_latency(0)
    llm.set_latency(0)
    synthesizer.set_latency(0)

    orchestrator = Orchestrator(
        audio_capture=capture,
        audio_playback=playback,
        wake_word_detector=wake_word,
        transcriber=transcriber,
        language_model=llm,
        synthesizer=synthesizer,
        feedback=feedback,
    )

    result = BenchmarkResult(name="E2E pipeline (mock)")

    # Warmup
    for _ in range(3):
        wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        capture.set_audio_data(bytes(16000 * 2))
        orchestrator.process_single_interaction()

    # Benchmark
    for _ in range(50):
        wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        capture.set_audio_data(bytes(16000 * 2))

        start = time.perf_counter()
        orchestrator.process_single_interaction()
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.samples.append(elapsed_ms)

    result.calculate_stats()
    return result


def print_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results in a nice table."""
    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print(f"  {'Benchmark':<25} {'P50':>10} {'P95':>10} {'P99':>10} {'Mean':>10}")
    print("  " + "-" * 65)

    for r in results:
        print(
            f"  {r.name:<25} {r.p50:>9.2f}ms {r.p95:>9.2f}ms "
            f"{r.p99:>9.2f}ms {r.mean:>9.2f}ms"
        )

    print()
    print("=" * 70)
    print()

    # Target comparison
    print("  📊 Target Comparison:")
    print("  " + "-" * 40)
    print("  Component    Laptop Target    Pi Target")
    print("  " + "-" * 40)
    print("  STT          <500ms           <1500ms")
    print("  LLM          <1000ms          <4000ms")
    print("  TTS          <200ms           <500ms")
    print("  E2E          <2000ms          <6000ms")
    print()


def save_results(results: list[BenchmarkResult], path: Path) -> None:
    """Save results to JSON file."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "results": [
            {
                "name": r.name,
                "p50": r.p50,
                "p95": r.p95,
                "p99": r.p99,
                "mean": r.mean,
                "min": r.min,
                "max": r.max,
                "samples": len(r.samples),
            }
            for r in results
        ],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Results saved to: {path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Ara Voice Assistant benchmarks"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmarks only (skip slow tests)",
    )
    parser.add_argument(
        "--component",
        choices=["stt", "llm", "tts", "e2e"],
        help="Run benchmarks for specific component only",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Use pytest-benchmark instead of manual benchmarks",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results/latest.json"),
        help="Output file for results",
    )

    args = parser.parse_args()

    print("\n🚀 Ara Voice Assistant - Benchmark Runner")
    print("=" * 50)

    if args.pytest:
        # Run pytest benchmarks
        marker = "benchmark and not slow" if args.quick else "benchmark"
        results = run_pytest_benchmark(marker)
        print(json.dumps(results, indent=2))
    else:
        # Run manual benchmarks
        results = run_manual_benchmarks(args.component)
        print_results(results)
        save_results(results, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
