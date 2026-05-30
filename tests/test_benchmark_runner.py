"""Tests for BenchmarkRunner — internal forge benchmarks."""

from __future__ import annotations

import pytest

from benchmarks.benchmark_runner import BenchmarkRunner


@pytest.fixture
def runner() -> BenchmarkRunner:
    return BenchmarkRunner()


@pytest.fixture
def sample_source() -> str:
    return (
        "import os\n"
        "import logging\n\n"
        "logger = logging.getLogger(__name__)\n\n"
        "def greet(name: str) -> str:\n"
        "    return f'Hello, {name}'\n\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )


@pytest.mark.asyncio
async def test_run_all_returns_three_scores(runner: BenchmarkRunner, sample_source: str) -> None:
    scores = await runner.run_all(sample_source)
    assert isinstance(scores, dict)
    assert set(scores.keys()) == {"syntax_parse", "import_cycle", "ast_mutation_speed"}
    for v in scores.values():
        assert 0.0 <= v <= 1.0


@pytest.mark.asyncio
async def test_run_all_empty_source(runner: BenchmarkRunner) -> None:
    scores = await runner.run_all("")
    assert all(v == 0.5 for v in scores.values())


@pytest.mark.asyncio
async def test_run_all_syntax_error(runner: BenchmarkRunner) -> None:
    scores = await runner.run_all("this is not valid python @@@")
    assert scores["syntax_parse"] == 0.0
    assert scores["import_cycle"] == 0.0
    assert scores["ast_mutation_speed"] == 0.0
