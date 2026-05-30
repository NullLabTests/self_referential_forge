"""Meta-evolver for self-tuning evolution strategy adaptation.

Tracks per-operator performance, adjusts selection weights in real-time,
detects stagnation, and persists state across runs. This is the
second-order evolutionary loop — the evolution strategy itself evolves.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OperatorStats:
    """Per-operator performance statistics."""

    name: str
    weight: float = 1.0
    uses: int = 0
    successes: int = 0
    total_delta: float = 0.0
    avg_delta: float = 0.0
    last_used: float = 0.0


class MetaEvolver:
    """Self-tuning strategy adapter for the self-referential forge.

    Tracks per-operator performance across generations, adjusts
    selection weights based on fitness deltas, detects convergence
    stagnation, and injects novelty boosts. State is persisted to
    a JSON file for continuity across runs.

    The key insight: operators that consistently produce positive
    fitness deltas get higher selection weights. Low-performing
    operators decay. When all operators stagnate, novelty boost
    amplifies the least-used operators.
    """

    def __init__(
        self,
        persistence_path: str | Path = "",
        learning_rate: float = 0.15,
        min_weight: float = 0.05,
        max_weight: float = 5.0,
        stagnation_threshold: int = 10,
        decay_factor: float = 0.98,
    ) -> None:
        self.learning_rate = learning_rate
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.stagnation_threshold = stagnation_threshold
        self.decay_factor = decay_factor

        self._persistence_path = Path(
            persistence_path or os.environ.get("META_EVOLVER_PATH", "meta_state.json")
        )
        self._fitness_history: list[float] = []
        self._generation: int = 0
        self._stagnation_counter: int = 0
        self._last_operator: str = ""
        self._novelty_boost_active: bool = False
        self._novelty_cooldown: int = 0

        from forge.self_modifier import ALL_OPERATORS as _all_ops
        self.operators: dict[str, OperatorStats] = {
            op: OperatorStats(name=op) for op in _all_ops
        }

        self._load_state()

    def select_operator(self) -> str:
        """Select a mutation operator via weighted random selection.

        Returns:
            Name of the selected operator.
        """
        self._decay_weights()
        self._novelty_cooldown = max(0, self._novelty_cooldown - 1)

        names = list(self.operators.keys())
        weights = [max(0.01, self.operators[n].weight) for n in names]
        total = sum(weights)

        if total <= 0:
            selected = random.choice(names)
        else:
            r = random.uniform(0, total)
            cumulative = 0.0
            selected = names[-1]
            for i, op in enumerate(names):
                cumulative += weights[i]
                if r <= cumulative:
                    selected = op
                    break

        self._last_operator = selected
        return selected

    def observe_fitness_delta(self, delta: float) -> None:
        """Record a fitness delta and attribute it to the last operator.

        Args:
            delta: Fitness change from the last evolution cycle.
        """
        self._fitness_history.append(delta)
        self._generation += 1

        if delta > 0:
            self._stagnation_counter = 0
            if self._last_operator:
                self._record_operator_success(self._last_operator, delta)
        elif delta < 0:
            self._stagnation_counter += 1
            if self._last_operator:
                self._record_operator_failure(self._last_operator, delta)
        else:
            self._stagnation_counter += 1

        self._check_stagnation()
        self._persist_state()

    def record_operator_use(self, operator: str, delta: float) -> None:
        """Record an operator use and its resulting delta.

        Called when the orchestrator knows which operator was used
        but the delta is observed separately.
        """
        self._last_operator = operator
        stats = self.operators.setdefault(operator, OperatorStats(name=operator))
        stats.uses += 1
        stats.total_delta += delta
        stats.last_used = time.time()
        stats.avg_delta = stats.total_delta / stats.uses if stats.uses > 0 else 0.0

    def trigger_novelty_boost(self) -> None:
        """Amplify low-weight operators to escape local optima."""
        if self._novelty_cooldown > 0:
            return

        self._novelty_boost_active = True
        self._novelty_cooldown = 5
        min_weight = min(s.weight for s in self.operators.values())
        amplified = 0

        for stats in self.operators.values():
            if stats.weight <= min_weight + 0.1:
                stats.weight = min(self.max_weight, stats.weight * 4.0)
                amplified += 1

        logger.info("Novelty boost: amplified %d low-weight operators", amplified)

    def get_operator_weights(self) -> dict[str, float]:
        """Return current operator weights."""
        return {n: s.weight for n, s in self.operators.items()}

    def get_summary(self) -> dict[str, Any]:
        """Return a complete summary of meta-evolver state."""
        return {
            "generation": self._generation,
            "stagnation_counter": self._stagnation_counter,
            "fitness_history_length": len(self._fitness_history),
            "novelty_boost_active": self._novelty_boost_active,
            "novelty_cooldown": self._novelty_cooldown,
            "operators": {
                name: {
                    "weight": round(stats.weight, 4),
                    "uses": stats.uses,
                    "successes": stats.successes,
                    "avg_delta": round(stats.avg_delta, 6),
                    "total_delta": round(stats.total_delta, 6),
                    "success_rate": round(
                        stats.successes / stats.uses, 4
                    ) if stats.uses > 0 else 0.0,
                    "last_used_ago": round(time.time() - stats.last_used, 1) if stats.last_used else -1,
                }
                for name, stats in sorted(self.operators.items())
            },
        }

    def _record_operator_success(self, operator: str, delta: float) -> None:
        """Record a positive outcome for an operator."""
        stats = self.operators.setdefault(operator, OperatorStats(name=operator))
        stats.uses += 1
        stats.successes += 1
        stats.total_delta += delta
        stats.avg_delta = stats.total_delta / stats.uses
        stats.last_used = time.time()

        adjustment = 1.0 + (self.learning_rate * delta)
        stats.weight = max(self.min_weight, min(self.max_weight, stats.weight * adjustment))
        logger.debug("Operator '%s': success, weight=%.2f", operator, stats.weight)

    def _record_operator_failure(self, operator: str, delta: float) -> None:
        """Record a negative outcome for an operator."""
        stats = self.operators.setdefault(operator, OperatorStats(name=operator))
        stats.uses += 1
        stats.total_delta += delta
        stats.avg_delta = stats.total_delta / stats.uses
        stats.last_used = time.time()

        adjustment = 1.0 + (self.learning_rate * delta / max(abs(delta), 0.01))
        stats.weight = max(self.min_weight, min(self.max_weight, stats.weight * adjustment))
        logger.debug("Operator '%s': failure, weight=%.2f", operator, stats.weight)

    def _decay_weights(self) -> None:
        """Gradually decay all weights toward 1.0.

        Prevents any single operator from dominating permanently.
        """
        for stats in self.operators.values():
            if stats.weight > 1.0:
                stats.weight = max(1.0, stats.weight * self.decay_factor)
            elif stats.weight < 1.0:
                stats.weight = min(1.0, stats.weight / self.decay_factor)

    def _check_stagnation(self) -> None:
        """Check for stagnation and trigger novelty boost if needed."""
        if self._stagnation_counter >= self.stagnation_threshold:
            logger.info(
                "Stagnation: %d cycles without improvement — boosting novelty",
                self._stagnation_counter,
            )
            self.trigger_novelty_boost()
            self._stagnation_counter = 0

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        try:
            if self._persistence_path.exists():
                with open(self._persistence_path) as f:
                    state = json.load(f)

                for name, data in state.get("operators", {}).items():
                    if name in self.operators:
                        self.operators[name].weight = data.get("weight", 1.0)
                        self.operators[name].uses = data.get("uses", 0)
                        self.operators[name].successes = data.get("successes", 0)
                        self.operators[name].total_delta = data.get("total_delta", 0.0)
                        self.operators[name].avg_delta = data.get("avg_delta", 0.0)
                        self.operators[name].last_used = data.get("last_used", 0.0)

                self._generation = state.get("generation", 0)
                self._fitness_history = state.get("fitness_history", [])
                logger.info(
                    "Loaded meta-evolver state: generation=%d, operators=%d",
                    self._generation,
                    len(self.operators),
                )
        except Exception as exc:
            logger.debug("No saved meta-evolver state to load: %s", exc)

    def _persist_state(self) -> None:
        """Persist current state to disk."""
        try:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            state = self.get_summary()
            state["fitness_history"] = self._fitness_history
            with open(self._persistence_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to persist meta-evolver state: %s", exc)
