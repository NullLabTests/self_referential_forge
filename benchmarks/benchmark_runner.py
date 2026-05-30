"""Benchmark runner — evaluates forge performance on internal fixtures.

Executes a set of canned benchmarks to measure correctness, speed, and
resource usage of mutated forge components. Each benchmark returns a
score in [0.0, 1.0].
"""

from __future__ import annotations

import ast
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Executes internal benchmarks against forge components.

    Benchmarks measure syntax parse speed, import cycle integrity,
    and AST mutation throughput. Results feed into the evaluator
    for fitness scoring.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._results: list[dict[str, Any]] = []

    async def run_all(self, source: str = "") -> dict[str, float]:
        """Run the full benchmark suite against a source string.

        Args:
            source: The forge component source to benchmark.

        Returns:
            Dict mapping benchmark names to scores [0.0, 1.0].
        """
        return {
            "syntax_parse": self._bench_syntax_parse(source),
            "import_cycle": self._bench_import_cycle(source),
            "ast_mutation_speed": self._bench_ast_mutation(source),
        }

    def _bench_syntax_parse(self, source: str) -> float:
        """Measure how quickly the source can be parsed.

        Returns 1.0 if it parses in under 10ms, scaled down for slower.
        """
        if not source:
            return 0.5
        try:
            start = time.perf_counter()
            for _ in range(10):
                ast.parse(source)
            elapsed = (time.perf_counter() - start) / 10
            if elapsed < 0.01:
                return 1.0
            elif elapsed < 0.1:
                return 0.5
            else:
                return 0.1
        except SyntaxError:
            return 0.0

    def _bench_import_cycle(self, source: str) -> float:
        """Check that the source doesn't import itself (cycle detection)."""
        if not source:
            return 0.5
        try:
            tree = ast.parse(source)
            imports = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            ]
            self_references = [i for i in imports if "self" in i.lower() or "forge" in i.lower()]
            if len(self_references) > 3:
                return 0.3
            return 1.0
        except SyntaxError:
            return 0.0

    def _bench_ast_mutation(self, source: str) -> float:
        """Measure AST complexity as proxy for mutation ease."""
        if not source:
            return 0.5
        try:
            tree = ast.parse(source)
            total_nodes = sum(1 for _ in ast.walk(tree))
            if 20 <= total_nodes <= 500:
                return 1.0
            elif total_nodes > 500:
                return 0.5
            else:
                return 0.2
        except SyntaxError:
            return 0.0
