"""Main self-referential evolution loop coordinator.

The orchestrator manages the complete cycle of self-modification:
  - Load/persist the forge's own component population
  - Select champion component via tournament selection
  - Apply self-mutation operators to forge source code
  - Evaluate the modified forge via internal benchmarks
  - Track fitness and detect convergence
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forge.self_modifier import SelfModifier
from forge.self_writer import SelfWriter, WriteResult
from meta_evolution.meta_evolver import MetaEvolver
from evaluators.evaluator import SelfEvaluator
from archive.archivist import Archivist
from safety import SafetyValidator, SafetyTier

logger = logging.getLogger(__name__)


@dataclass
class Component:
    """An individual forge component in the self-referential evolution population."""

    id: str
    generation: int
    component_type: str
    parent_id: str | None = None
    source: str = ""
    fitness: dict[str, float] = field(default_factory=dict)
    fitness_total: float = 0.0
    created_at: float = 0.0
    mutation_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EvolutionConfig:
    """Configuration for the self-referential evolution loop."""

    population_size: int = 30
    tournament_size: int = 5
    elitism_count: int = 2
    mutation_rate: float = 0.8
    crossover_rate: float = 0.2
    parallel_generations: int = 2
    db_url: str = ""
    sandbox_timeout: int = 300
    convergence_window: int = 15
    convergence_threshold: float = 0.005
    safety_enabled: bool = True
    max_consecutive_failures: int = 5
    auto_commit: bool = False
    human_approval: bool = False
    max_mutation_attempts: int = 3
    audit_chain_verify_interval: int = 20
    rollback_on_violation: bool = True
    apply_mutations: bool = False
    auto_rollback_on_failure: bool = True


class SelfReferentialOrchestrator:
    """Central coordinator for the self-referential evolution loop.

    Manages the complete cycle of loading the forge's own component population,
    selecting champions, applying self-mutation operators to forge source code,
    evaluating modifications via internal benchmarks, and persisting results.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        self_modifier: SelfModifier | None = None,
        self_writer: SelfWriter | None = None,
        evaluator: SelfEvaluator | None = None,
        meta_evolver: MetaEvolver | None = None,
        archivist: Archivist | None = None,
        safety: SafetyValidator | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.self_modifier = self_modifier or SelfModifier()
        self.self_writer = self_writer or SelfWriter()
        self.evaluator = evaluator or SelfEvaluator()
        self.meta_evolver = meta_evolver or MetaEvolver()
        self.archivist = archivist or Archivist()
        self.safety = safety or SafetyValidator() if self.config.safety_enabled else None

        self.population: list[Component] = []
        self.generation: int = 0
        self.best_fitness: float = 0.0
        self.fitness_history: list[float] = []
        self.running: bool = False
        self.consecutive_failures: int = 0
        self._forge_root = Path(__file__).resolve().parent.parent

    async def run(self, cycles: int = -1) -> None:
        """Run the self-referential evolution loop.

        Args:
            cycles: Number of evolution cycles to run. -1 for infinite.
        """
        self.running = True
        cycle_count = 0

        logger.info("Self-referential forge starting (cycles=%s)", "infinite" if cycles < 0 else cycles)

        if not await self._validate_environment():
            logger.error("Environment validation failed. Aborting.")
            self.running = False
            return

        while self.running and (cycles < 0 or cycle_count < cycles):
            cycle_start = time.time()

            champion = self._select_champion()
            component = await self._mutate_component(champion)
            if component is None:
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.config.max_consecutive_failures:
                    logger.error("Too many consecutive mutation failures. Stopping.")
                    break
                continue

            self.consecutive_failures = 0

            fitness = await self._evaluate_component(component)

            if self.config.human_approval:
                if not await self._request_human_approval(component, fitness):
                    logger.info("Human rejected component %s", component.id)
                    continue

            # ── Self-referential write-back ──────────────────────────
            # Write the mutated source to the actual forge .py file and
            # reload the module. This is what makes the loop truly
            # self-referential — the forge modifies its own running code.
            if self.config.apply_mutations and component.parent_id is not None:
                write_ok = await self._apply_self_mutation(component)
                if not write_ok:
                    if self.config.auto_rollback_on_failure:
                        logger.error("Self-modification failed — halting")
                        break
                    continue

            self._update_population(component, fitness)
            self._adjust_strategy()

            await self.archivist.snapshot(self._get_state())

            if self.config.auto_commit:
                await self._auto_commit(component)

            cycle_count += 1
            elapsed = time.time() - cycle_start
            logger.info(
                "Cycle %d | Type: %s | Fitness: %.4f | Best: %.4f | Time: %.1fs",
                cycle_count,
                component.component_type,
                component.fitness_total,
                self.best_fitness,
                elapsed,
            )

            if self._check_convergence():
                logger.info("Convergence detected — injecting novelty")
                self.meta_evolver.trigger_novelty_boost()

            if self.safety and cycle_count > 0 and cycle_count % self.config.audit_chain_verify_interval == 0:
                chain_ok, issues = self.safety.verify_audit_chain()
                if not chain_ok:
                    logger.error("Audit chain integrity violation detected! Issues: %s", issues)

        self.running = False
        total_delta = self.fitness_history[-1] - self.fitness_history[0] if len(self.fitness_history) >= 2 else 0.0
        logger.info(
            "Self-referential evolution completed: %d cycles, delta=%.4f",
            cycle_count,
            total_delta,
        )

    async def _validate_environment(self) -> bool:
        """Validate that the forge environment is properly configured."""
        checks = []

        if self.safety is not None:
            checks.append(self.safety.validate_environment())

        forge_files = list(self._forge_root.rglob("*.py"))
        if not forge_files:
            logger.error("No forge source files found at %s", self._forge_root)
            return False

        logger.info("Environment OK: %d forge source files, %d safety checks", len(forge_files), len(checks))
        return all(checks) if checks else True

    def _select_champion(self) -> Component | None:
        """Select the champion component via tournament selection."""
        if not self.population:
            return None

        tournament = sorted(
            self.population,
            key=lambda c: c.fitness_total,
            reverse=True,
        )
        return tournament[0]

    async def _mutate_component(self, parent: Component | None) -> Component | None:
        """Apply self-mutation to forge source code.

        If no parent exists, generates a baseline component from current forge state.
        All mutations pass through the tiered safety system:
          - Tier 0 (AUTOMATED): Safe mutations pass without human intervention
          - Tier 1 (DRY_RUN):   Requires sandbox testing before promotion
          - Tier 2 (HUMAN):     Requires explicit human approval
          - Tier 3 (BLOCKED):   Never allowed

        Returns:
            A new Component with mutated source, or None on failure.
        """
        operator = self.meta_evolver.select_operator()

        for attempt in range(self.config.max_mutation_attempts):
            try:
                if parent is None:
                    source = await self.self_modifier.snapshot_current()
                    component_type = "baseline"
                else:
                    result = await self.self_modifier.mutate(
                        source=parent.source,
                        operator=operator,
                        component_type=parent.component_type,
                    )
                    source = result["source"]
                    component_type = result["component_type"]
                    operator = result.get("operator", operator)

                if self.safety is not None:
                    safety_result = await self.safety.check_mutation(
                        source=source,
                        component_type=component_type,
                        operator=operator,
                        source_before=parent.source if parent else source,
                    )
                    if not safety_result["safe"]:
                        logger.warning(
                            "Safety check failed (tier=%s): %s",
                            safety_result.get("verdict", {}).get("tier", "unknown"),
                            safety_result["reason"],
                        )
                        if self.config.rollback_on_violation and parent is not None:
                            self.safety._sandbox.rollback(
                                self._forge_root / component_type.replace("_mutated", ".py"),
                                parent.source,
                            )
                        continue

                    tier = safety_result["verdict"].tier
                    if tier >= SafetyTier.HUMAN_APPROVAL or self.config.human_approval:
                        approved = await self._request_human_approval_raw(
                            mutation_id=safety_result["verdict"].mutation_id,
                            component_type=component_type,
                            operator=operator,
                            tier=tier.name,
                            violations=safety_result["violations"],
                        )
                        if not approved:
                            logger.info("Human rejected mutation %s", safety_result["verdict"].mutation_id)
                            continue

                return Component(
                    id=f"{component_type}-gen{self.generation}-{int(time.time())}",
                    generation=self.generation,
                    component_type=component_type,
                    parent_id=parent.id if parent else None,
                    source=source,
                    created_at=time.time(),
                    mutation_log=[{"operator": operator, "attempt": attempt}] if parent else [],
                )

            except Exception as exc:
                logger.warning("Mutation attempt %d failed: %s", attempt + 1, exc)
                continue

        logger.error("All %d mutation attempts failed for operator '%s'", self.config.max_mutation_attempts, operator)
        return None

    async def _evaluate_component(self, component: Component) -> dict[str, float]:
        """Evaluate a forge component's fitness across all dimensions."""
        fitness = await self.evaluator.evaluate(component.source, component.component_type)
        return fitness

    def _update_population(self, component: Component, fitness: dict[str, float]) -> None:
        """Insert the evaluated component into the population."""
        component.fitness = fitness
        component.fitness_total = sum(fitness.values())
        self.population.append(component)
        self.population.sort(key=lambda c: c.fitness_total, reverse=True)
        self.population = self.population[: self.config.population_size]

        if component.fitness_total > self.best_fitness:
            self.best_fitness = component.fitness_total

        self.fitness_history.append(self.best_fitness)
        self.generation += 1

    def _adjust_strategy(self) -> None:
        """Feed fitness deltas to the meta-evolver for strategy adaptation."""
        if len(self.fitness_history) >= 2:
            delta = self.fitness_history[-1] - self.fitness_history[-2]
            self.meta_evolver.observe_fitness_delta(delta)

    def _check_convergence(self) -> bool:
        """Detect if fitness has plateaued."""
        if len(self.fitness_history) < self.config.convergence_window:
            return False
        recent = self.fitness_history[-self.config.convergence_window :]
        return max(recent) - min(recent) < self.config.convergence_threshold

    async def _request_human_approval(self, component: Component, fitness: dict[str, float]) -> bool:
        """Request human approval before accepting a mutation (legacy)."""
        logger.info(
            "Human approval required for %s (fitness: %.4f). Approve? [y/N]",
            component.id,
            sum(fitness.values()),
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, input, "> ")
        return response.strip().lower() in ("y", "yes")

    async def _request_human_approval_raw(
        self,
        mutation_id: str,
        component_type: str,
        operator: str,
        tier: str,
        violations: list[str],
    ) -> bool:
        """Request human approval for a tier-2 mutation.

        Args:
            mutation_id: Unique mutation identifier.
            component_type: Type of component being mutated.
            operator: Mutation operator being applied.
            tier: Safety tier label.
            violations: Safety violations detected.

        Returns:
            True if human approved, False if rejected.
        """
        print("\n" + "=" * 60)
        print(f"  HUMAN APPROVAL REQUIRED — Tier: {tier}")
        print(f"  Mutation:    {mutation_id}")
        print(f"  Component:   {component_type}")
        print(f"  Operator:    {operator}")
        if violations:
            print(f"  Violations:  {'; '.join(violations)}")
        print("=" * 60)
        print("  Approve this self-modification? [y/N] ", end="", flush=True)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, input, "")
        approved = response.strip().lower() in ("y", "yes")
        print()
        return approved

    async def _auto_commit(self, component: Component) -> None:
        """Auto-commit the improved component to git."""
        import subprocess

        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self._forge_root,
                capture_output=True,
                check=False,
            )
            subprocess.run(
                [
                    "git", "commit", "-m",
                    f"auto: self-referential improvement — {component.component_type} "
                    f"fitness={component.fitness_total:.4f} (gen {component.generation})",
                ],
                cwd=self._forge_root,
                capture_output=True,
                check=False,
            )
            logger.info("Auto-committed component %s", component.id)
        except Exception as exc:
            logger.warning("Auto-commit failed: %s", exc)

    def _get_state(self) -> dict[str, Any]:
        """Get the full evolution state for archiving."""
        return {
            "generation": self.generation,
            "best_fitness": self.best_fitness,
            "population_size": len(self.population),
            "fitness_history": self.fitness_history,
            "consecutive_failures": self.consecutive_failures,
            "meta_state": self.meta_evolver.get_summary(),
            "timestamp": time.time(),
        }

    async def _apply_self_mutation(self, component: Component) -> bool:
        """Write a mutated component to disk and reload in the running process.

        This is the core self-referential step: after a mutation is safety-
        approved and fitness-evaluated, we write the new source to the
        forge's own .py file and reload the module so subsequent evolution
        cycles use the modified code.

        Args:
            component: The mutated component to apply.

        Returns:
            True if the write+reload+smoke-test succeeded.
        """
        original_source = component.mutation_log[0].get("_original_source", "") if component.mutation_log else ""

        result: WriteResult = await self.self_writer.apply_mutation(
            source=component.source,
            component_type=component.component_type,
            original_source=original_source,
        )

        if result.success:
            logger.info(
                "Self-mutation applied to disk: %s (module=%s, %.2fs)",
                result.file_path.name,
                result.module_name,
                result.execution_time,
            )
            component.mutation_log.append({
                "event": "self_write",
                "file": str(result.file_path),
                "module": result.module_name,
                "smoke_test": result.smoke_test_passed,
                "reloaded": result.reloaded,
                "time": result.execution_time,
            })
            return True

        logger.error(
            "Self-mutation FAILED for %s: %s",
            component.component_type,
            result.error,
        )

        if self.config.auto_rollback_on_failure and result.backup_path:
            rolled_back = self.self_writer.rollback(result.backup_path, result.file_path)
            logger.info("Rollback %s for %s", "succeeded" if rolled_back else "FAILED", result.file_path)

        return False

    def stop(self) -> None:
        """Gracefully stop the evolution loop."""
        self.running = False
        logger.info("Stop requested — completing current cycle")
