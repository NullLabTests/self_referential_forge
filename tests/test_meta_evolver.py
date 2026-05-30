"""Tests for MetaEvolver — persistence, operator tracking, novelty boost."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from meta_evolution.meta_evolver import MetaEvolver
from forge.self_modifier import ALL_OPERATORS


@pytest.fixture
def meta() -> MetaEvolver:
    return MetaEvolver(
        persistence_path=Path(tempfile.mktemp(suffix=".json")),
        learning_rate=0.15,
        stagnation_threshold=5,
    )


class TestOperatorSelection:
    """Tests for weighted random operator selection."""

    def test_select_operator_returns_valid(self, meta: MetaEvolver) -> None:
        for _ in range(50):
            op = meta.select_operator()
            assert op in ALL_OPERATORS, f"Unknown operator: {op}"

    def test_select_operator_distribution(self, meta: MetaEvolver) -> None:
        selections: dict[str, int] = {}
        for _ in range(500):
            op = meta.select_operator()
            selections[op] = selections.get(op, 0) + 1
        assert len(selections) >= 8
        assert sum(selections.values()) == 500

    def test_weights_affect_selection(self, meta: MetaEvolver) -> None:
        for op in meta.operators:
            meta.operators[op].weight = 0.01
        meta.operators["insert_code"].weight = 100.0

        picks = [meta.select_operator() for _ in range(200)]
        insert_count = picks.count("insert_code")
        assert insert_count > 100


class TestFitnessDeltaTracking:
    """Tests for observe_fitness_delta and operator weight adjustment."""

    def test_positive_delta_increases_weight(self, meta: MetaEvolver) -> None:
        meta._last_operator = "add_type_hints"
        initial_weight = meta.operators["add_type_hints"].weight
        meta.observe_fitness_delta(0.5)
        assert meta.operators["add_type_hints"].weight > initial_weight

    def test_negative_delta_decreases_weight(self, meta: MetaEvolver) -> None:
        meta._last_operator = "rewrite_function"
        initial_weight = meta.operators["rewrite_function"].weight
        meta.observe_fitness_delta(-0.5)
        assert meta.operators["rewrite_function"].weight < initial_weight

    def test_operator_stats_tracked(self, meta: MetaEvolver) -> None:
        meta._last_operator = "add_parameter"
        meta.observe_fitness_delta(0.3)
        stats = meta.operators["add_parameter"]
        assert stats.uses == 1
        assert stats.successes == 1
        assert stats.avg_delta == 0.3

    def test_multiple_deltas_accumulate(self, meta: MetaEvolver) -> None:
        for op in ["add_type_hints", "add_type_hints", "insert_code"]:
            meta._last_operator = op
            meta.observe_fitness_delta(0.1)
        assert meta.operators["add_type_hints"].uses == 2
        assert meta.operators["insert_code"].uses == 1


class TestStagnationAndNovelty:
    """Tests for stagnation detection and novelty boost."""

    def test_stagnation_triggers_novelty(self, meta: MetaEvolver) -> None:
        meta.stagnation_threshold = 3
        meta._last_operator = "insert_code"
        for _ in range(3):
            meta.observe_fitness_delta(0.0)
        assert meta._stagnation_counter == 0
        assert meta._novelty_boost_active

    def test_novelty_boost_amplifies_low_weights(self, meta: MetaEvolver) -> None:
        for op in meta.operators:
            meta.operators[op].weight = 0.1
        meta.operators["insert_code"].weight = 5.0

        meta.trigger_novelty_boost()
        low_ops = [s.weight for s in meta.operators.values() if s.weight > 0.1]
        assert len(low_ops) >= 8

    def test_novelty_cooldown(self, meta: MetaEvolver) -> None:
        meta._novelty_cooldown = 5
        meta.trigger_novelty_boost()
        assert not meta._novelty_boost_active


class TestPersistence:
    """Tests for state persistence across runs."""

    def test_persist_and_reload(self, meta: MetaEvolver) -> None:
        meta._last_operator = "add_docstring"
        meta.observe_fitness_delta(0.5)
        meta.observe_fitness_delta(0.3)
        meta.observe_fitness_delta(-0.1)

        assert meta._persistence_path.exists()
        saved_data = json.loads(meta._persistence_path.read_text())
        assert saved_data["generation"] == 3
        assert "add_docstring" in saved_data["operators"]

    def test_reload_restores_state(self, meta: MetaEvolver) -> None:
        meta._last_operator = "add_type_hints"
        meta.observe_fitness_delta(1.0)
        original_weight = meta.operators["add_type_hints"].weight
        original_gen = meta._generation
        original_path = meta._persistence_path

        meta2 = MetaEvolver(persistence_path=original_path)
        assert meta2._generation == original_gen
        assert meta2.operators["add_type_hints"].weight == original_weight

    def test_persistence_path_default(self) -> None:
        meta = MetaEvolver(persistence_path="")
        assert meta._persistence_path is not None


class TestSummary:
    """Tests for get_summary()."""

    def test_summary_contains_all_keys(self, meta: MetaEvolver) -> None:
        summary = meta.get_summary()
        assert "generation" in summary
        assert "operators" in summary
        assert "stagnation_counter" in summary

    def test_summary_includes_all_operators(self, meta: MetaEvolver) -> None:
        summary = meta.get_summary()
        assert len(summary["operators"]) == len(ALL_OPERATORS)

    def test_summary_operator_data(self, meta: MetaEvolver) -> None:
        meta._last_operator = "extract_constant"
        meta.observe_fitness_delta(0.7)
        summary = meta.get_summary()
        op_data = summary["operators"]["extract_constant"]
        assert op_data["uses"] == 1
        assert op_data["successes"] == 1
        assert op_data["avg_delta"] == 0.7


class TestWeightDecay:
    """Tests for gradual weight decay."""

    def test_high_weight_decays_toward_one(self, meta: MetaEvolver) -> None:
        meta.operators["insert_code"].weight = 3.0
        meta.select_operator()
        assert meta.operators["insert_code"].weight < 3.0
        assert meta.operators["insert_code"].weight >= 1.0

    def test_low_weight_increases_toward_one(self, meta: MetaEvolver) -> None:
        meta.operators["insert_code"].weight = 0.1
        for _ in range(3):
            meta.select_operator()
        assert meta.operators["insert_code"].weight > 0.1
