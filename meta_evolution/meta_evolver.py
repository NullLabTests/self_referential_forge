"""Meta-evolver for self-tuning evolution strategy adaptation.

Observes fitness deltas across generations and adjusts mutation
operator selection, rates, and novelty injection to escape local
optima — a second-order evolutionary loop.
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class MetaEvolver:
    """Self-tuning strategy adapter for the self-referential forge.

    Tracks per-operator performance and adjusts selection probabilities,
    mutation rates, and crossover rates.  Can inject novelty when
    convergence is detected.
    """

    def __init__(self) -> None:
        self.operator_scores: dict[str, float] = defaultdict(float)
        self.operator_counts: dict[str, int] = defaultdict(int)
        self.fitness_deltas: list[float] = []
        self.base_operators = [
            "insert_code",
            "rewrite_function",
            "add_parameter",
            "swap_condition",
            "duplicate_component",
        ]
        self.weights: dict[str, float] = {op: 1.0 for op in self.base_operators}
        self.mutation_rate: float = 0.8
        self.crossover_rate: float = 0.2
        self._novelty_boost: bool = False

    def select_operator(self) -> str:
        """Select a mutation operator via weighted random choice."""
        total = sum(self.weights.values()) or 1.0
        r = random.uniform(0, total)
        cumulative = 0.0
        for op, weight in self.weights.items():
            cumulative += weight
            if r <= cumulative:
                return op
        return random.choice(self.base_operators)

    def observe_fitness_delta(self, delta: float) -> None:
        """Feed a fitness delta to update operator weights.

        Positive deltas reinforce the last-selected operator;
        negative deltas penalize it.
        """
        self.fitness_deltas.append(delta)
        if not self.operator_counts:
            return

        best_op = max(self.operator_counts, key=self.operator_counts.get)
        inertia = 0.1
        adjustment = delta * inertia

        for op in self.weights:
            if op == best_op:
                self.weights[op] = max(0.1, self.weights[op] + adjustment)
            else:
                self.weights[op] = max(0.1, self.weights[op] - adjustment * 0.1)

        self.mutation_rate = max(
            0.1, min(0.99, self.mutation_rate + delta * 0.05)
        )

    def record_operator_use(self, operator: str, fitness_gain: float) -> None:
        """Record an operator application and its resulting fitness gain."""
        self.operator_counts[operator] += 1
        self.operator_scores[operator] += fitness_gain

    def trigger_novelty_boost(self) -> None:
        """Temporarily boost low-weight operators to escape local optima."""
        self._novelty_boost = True
        for op in self.weights:
            if self.weights[op] < 0.5 / len(self.weights):
                self.weights[op] = 2.0
        logger.info("Novelty boost applied — low-weight operators amplified")

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of meta-evolver state."""
        return {
            "weights": dict(self.weights),
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "operator_counts": dict(self.operator_counts),
            "fitness_deltas_count": len(self.fitness_deltas),
            "novelty_boost_active": self._novelty_boost,
        }
