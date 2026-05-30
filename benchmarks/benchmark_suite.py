"""Benchmark suite for the self-referential forge.

Defines internal benchmarks that evaluate the forge's own components.
Each benchmark tests a specific aspect of evolution quality:
  - Fitness improvement rate
  - Operator diversity
  - Convergence behavior
  - Safety compliance
  - Code quality of generated mutations
"""

from __future__ import annotations

import ast
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

BenchmarkFn = Callable[[dict[str, Any]], float]


@dataclass
class BenchmarkResult:
    """Result of running a single benchmark."""

    name: str
    score: float
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkSuite:
    """Suite of internal benchmarks for the self-referential forge.

    Benchmarks evaluate how well the forge is evolving its own components.
    Results feed into the meta-evolution strategy.
    """

    def __init__(self) -> None:
        self._benchmarks: dict[str, BenchmarkFn] = {
            "fitness_improvement_rate": self._benchmark_fitness_improvement_rate,
            "operator_diversity": self._benchmark_operator_diversity,
            "convergence_resilience": self._benchmark_convergence_resilience,
            "safety_compliance_rate": self._benchmark_safety_compliance_rate,
            "mutation_quality": self._benchmark_mutation_quality,
        }

    async def run_all(self, state: dict[str, Any]) -> list[BenchmarkResult]:
        """Run all benchmarks against the given evolution state.

        Args:
            state: Current evolution state from the orchestrator.

        Returns:
            List of BenchmarkResult objects.
        """
        results: list[BenchmarkResult] = []
        for name, func in self._benchmarks.items():
            try:
                score = func(state)
                results.append(BenchmarkResult(name=name, score=score))
            except Exception as exc:
                logger.warning("Benchmark '%s' failed: %s", name, exc)
                results.append(BenchmarkResult(name=name, score=0.0))
        return results

    def _benchmark_fitness_improvement_rate(self, state: dict[str, Any]) -> float:
        """Score based on rate of fitness improvement over recent history.

        Higher is better — the forge should be consistently improving.
        """
        history = state.get("fitness_history", [])
        if len(history) < 3:
            return 0.5

        recent = history[-10:] if len(history) >= 10 else history
        gains = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        positive_gains = sum(1 for g in gains if g > 0)
        improvement_ratio = positive_gains / len(gains) if gains else 0.0

        total_improvement = recent[-1] - recent[0]
        magnitude_score = min(1.0, total_improvement * 10)

        return 0.6 * improvement_ratio + 0.4 * magnitude_score

    def _benchmark_operator_diversity(self, state: dict[str, Any]) -> float:
        """Score based on diversity of operator usage.

        A healthy evolution uses a variety of operators, not just one.
        """
        meta = state.get("meta_state", {})
        operators = meta.get("operators", {})

        if not operators:
            return 0.5

        total_uses = sum(op.get("uses", 0) for op in operators.values())
        if total_uses == 0:
            return 0.5

        active_operators = sum(1 for op in operators.values() if op.get("uses", 0) > 0)
        active_ratio = active_operators / len(operators)

        uses = [op.get("uses", 0) for op in operators.values()]
        max_uses = max(uses)
        if max_uses == 0:
            return 0.5

        concentration = max_uses / total_uses
        diversity_penalty = max(0.0, concentration - 0.4)

        return max(0.0, min(1.0, active_ratio - diversity_penalty))

    def _benchmark_convergence_resilience(self, state: dict[str, Any]) -> float:
        """Score based on the forge's ability to escape local optima.

        Rewards multiple periods of improvement after stagnation.
        """
        history = state.get("fitness_history", [])
        if len(history) < 10:
            return 0.5

        plateaus = 0
        recoveries = 0
        in_plateau = False

        window = 5
        for i in range(window, len(history)):
            recent = history[i - window : i]
            spread = max(recent) - min(recent)
            if spread < 0.001 and not in_plateau:
                plateaus += 1
                in_plateau = True
            elif spread >= 0.001 and in_plateau and i + 1 < len(history) and history[i + 1] > history[i]:
                recoveries += 1
                in_plateau = False

        if plateaus == 0:
            return 0.7

        recovery_rate = recoveries / plateaus
        return min(1.0, recovery_rate)

    def _benchmark_safety_compliance_rate(self, state: dict[str, Any]) -> float:
        """Score based on the safety compliance of generated mutations."""
        meta = state.get("meta_state", {})
        operators = meta.get("operators", {})

        if not operators:
            return 0.7

        violation_keywords = ["dangerous", "violation", "unsafe", "critical", "penalty"]
        violation_count = 0
        total_checks = 0

        for op_data in operators.values():
            for key, value in op_data.items():
                if isinstance(value, str) and any(kw in value.lower() for kw in violation_keywords):
                    violation_count += 1
                total_checks += 1

        if total_checks == 0:
            return 0.7

        compliance_rate = 1.0 - (violation_count / max(total_checks, 1))
        return max(0.0, min(1.0, compliance_rate))

    def _benchmark_mutation_quality(self, state: dict[str, Any]) -> float:
        """Score based on the quality of mutations produced.

        Evaluates using proxy metrics: average delta per operator,
        success rates, and weight distribution.
        """
        meta = state.get("meta_state", {})
        operators = meta.get("operators", {})

        if not operators:
            return 0.5

        avg_deltas = [abs(op.get("avg_delta", 0)) for op in operators.values()]
        if not avg_deltas:
            return 0.5

        mean_impact = sum(avg_deltas) / len(avg_deltas)
        impact_score = min(1.0, mean_impact * 50)

        success_rates = [
            op.get("success_rate", 0)
            for op in operators.values()
            if op.get("uses", 0) > 0
        ]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.5

        return 0.5 * impact_score + 0.5 * avg_success_rate
