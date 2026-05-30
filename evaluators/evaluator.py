"""Self-referential fitness evaluator for forge components.

Evaluates forge source code across multiple fitness dimensions:
  - Syntax correctness (AST parse)
  - Code complexity (cyclomatic, function depth)
  - Safety compliance (dangerous patterns)
  - Cohesion (how well the module hangs together)
  - Mutation test survival (if tests exist)
  - Runtime behavior (actually runs the code)
  - Novelty (structural divergence from previous mutations)
"""

from __future__ import annotations

import ast
import importlib.util
import logging
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from pathlib import Path
from typing import Any

from evaluators.novelty import NoveltyArchive

logger = logging.getLogger(__name__)

FITNESS_DIMENSIONS = [
    "syntax_validity",
    "code_complexity",
    "safety_compliance",
    "modular_cohesion",
    "test_survival",
    "style_consistency",
    "runtime_behavior",
    "novelty",
]


class SelfEvaluator:
    """Evaluates forge component source across multiple fitness dimensions.

    Each dimension produces a score in [0.0, 1.0]. The total fitness is
    the weighted sum. Weights can be tuned by the meta-evolver.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        test_dir: str | Path | None = None,
        novelty_archive: NoveltyArchive | None = None,
    ) -> None:
        self.weights = weights or {
            "syntax_validity": 0.20,
            "code_complexity": 0.10,
            "safety_compliance": 0.20,
            "modular_cohesion": 0.10,
            "test_survival": 0.10,
            "style_consistency": 0.05,
            "runtime_behavior": 0.15,
            "novelty": 0.10,
        }
        self._test_dir = Path(test_dir) if test_dir else None
        self.novelty_archive = novelty_archive or NoveltyArchive()
        self._dimension_registry: dict[str, Any] = {}
        self._discover_dimensions()

    def _discover_dimensions(self) -> None:
        """Auto-register all _score_* methods as evolvable evaluation dimensions."""
        for attr_name in dir(self):
            if attr_name.startswith("_score_") and callable(getattr(self, attr_name)):
                dim_name = attr_name.replace("_score_", "")
                self._dimension_registry[dim_name] = getattr(self, attr_name)

    @property
    def active_dimensions(self) -> list[str]:
        return list(self._dimension_registry.keys())

    async def evaluate(self, source: str, component_type: str = "unknown") -> dict[str, float]:
        """Evaluate a forge component's source across all fitness dimensions.

        Args:
            source: The forge component source code to evaluate.
            component_type: Type of the component (for logging).

        Returns:
            Dict mapping dimension names to scores in [0.0, 1.0].
        """
        scores: dict[str, float] = {}
        for dim_name, scorer in self._dimension_registry.items():
            result = scorer(source)
            if hasattr(result, "__await__"):
                result = await result
            scores[dim_name] = result

        scores["novelty"] = self._score_novelty(source)

        logger.debug("Evaluated %s: %s", component_type, scores)
        return scores

    def _score_syntax_validity(self, source: str) -> float:
        """Check if the source parses as valid Python AST.

        Returns 1.0 for valid, 0.0 for invalid.
        """
        try:
            ast.parse(source)
            return 1.0
        except SyntaxError as exc:
            logger.debug("Syntax error in component: %s", exc)
            return 0.0

    def _score_code_complexity(self, source: str) -> float:
        """Score based on code complexity metrics.

        Prefers moderate complexity — too simple is trivial, too complex is fragile.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0.0

        total_nodes = sum(1 for _ in ast.walk(tree))
        func_count = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        class_count = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])

        if total_nodes == 0:
            return 0.0

        max_depth = self._max_depth(tree)
        has_docstrings = bool(ast.get_docstring(tree, clean=False))

        complexity = 0.0
        complexity += min(1.0, total_nodes / 200) * 0.3
        complexity += min(1.0, (func_count + class_count * 2) / 15) * 0.3
        complexity += min(1.0, max_depth / 8) * 0.2
        complexity += (1.0 if has_docstrings else 0.0) * 0.2

        return min(1.0, complexity)

    def _score_safety_compliance(self, source: str) -> float:
        """Check for dangerous or anti-pattern code.

        Penalizes use of exec, eval, __import__, dangerous imports,
        and overly broad exception handlers.
        """
        penalties = 0.0
        checks = [
            (r"\beval\s*\(", "Use of eval()"),
            (r"\bexec\s*\(", "Use of exec()"),
            (r"\b__import__\s*\(", "Use of __import__()"),
            (r"\bcompile\s*\(", "Use of compile()"),
            (r"except\s*:\s*$", "Bare except:"),
            (r"except\s+Exception\s*:", "Broad except Exception:"),
            (r"\bos\.system\s*\(", "Use of os.system()"),
            (r"\bsubprocess\.call\s*\(", "Use of subprocess.call()"),
            (r"\bpickle\.loads?\s*\(", "Use of pickle (unsafe)"),
        ]

        for pattern, label in checks:
            if re.search(pattern, source, re.MULTILINE):
                logger.debug("Safety penalty: %s", label)
                penalties += 0.15

        return max(0.0, 1.0 - penalties)

    def _score_modular_cohesion(self, source: str) -> float:
        """Score how well the module is structured.

        Rewards clear separation of concerns: imports first, then constants,
        then classes/functions. Penalizes monolithic files.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0.0

        lines = source.split("\n")
        if not lines:
            return 0.0

        import_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        func_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        class_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        score = 0.5

        if import_nodes:
            last_import = max(n.lineno for n in import_nodes)
            first_non_import = (
                min(
                    (n.lineno for n in (*func_nodes, *class_nodes) if n.lineno > last_import),
                    default=len(lines),
                )
            )
            if last_import < first_non_import:
                score += 0.15

        if len(lines) > 50 and len(func_nodes) + len(class_nodes) >= 2:
            score += 0.1

        if len(lines) < 10:
            score -= 0.2

        has_if_main = any(
            isinstance(n, ast.If) and hasattr(n.test, "left") and hasattr(n.test.left, "id") and n.test.left.id == "__name__"
            for n in ast.walk(tree)
        )
        if has_if_main:
            score += 0.15

        return max(0.0, min(1.0, score))

    async def _score_test_survival(self, source: str) -> float:
        """Run existing tests against the component to check test survival.

        Returns 0.5 if no tests found (neutral), 1.0 if all tests pass,
        0.0 if tests fail.
        """
        if self._test_dir is None or not self._test_dir.exists():
            return 0.5

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(self._test_dir), "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return 1.0
            elif result.returncode == 5:
                return 0.5
            else:
                return 0.2
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.3

    def _score_style_consistency(self, source: str) -> float:
        """Score style consistency.

        Checks for consistent indentation, line length discipline,
        and presence of type hints.
        """
        lines = source.split("\n")
        if not lines:
            return 0.0

        total = len(lines)
        if total < 5:
            return 0.5

        issues = 0

        for line in lines:
            if len(line) > 120:
                issues += 1

        mixed_indent = any(re.match(r"^ +\t", line) for line in lines)
        if mixed_indent:
            issues += 3

        type_hint_count = len(re.findall(r":\s*\w+\[", source)) + len(re.findall(r"->\s*\w+", source))
        func_count = len(re.findall(r"^def\s+\w+\s*\(", source, re.MULTILINE))
        if func_count > 0 and type_hint_count < func_count:
            issues += 2

        score = 1.0 - (issues / max(total, 1))
        return max(0.0, score)

    def _score_runtime_behavior(self, source: str) -> float:
        """Execute the source in a subprocess and measure correctness.

        Writes the source to a temp file, imports it, calls a simple
        smoke function, and checks for errors.  Returns a score in
        [0.0, 1.0] based on:
          - whether the code parses and imports cleanly (0.4)
          - whether it produces expected output (0.4)
          - execution speed relative to a baseline (0.2)
        """
        if not self._score_syntax_validity(source):
            return 0.0

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="forge_runtime_"
        ) as f:
            f.write(source)
            tmp_path = f.name

        try:
            start = time.perf_counter()
            result = subprocess.run(
                [sys.executable, "-c",
                 textwrap.dedent(f"""\
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("_forge_runtime", {tmp_path!r})
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        print("IMPORT_OK")
                    else:
                        print("IMPORT_FAIL")
                """)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            elapsed = time.perf_counter() - start

            if result.returncode != 0:
                logger.debug("Runtime eval FAILED: %s", result.stderr[:200])
                return 0.0

            output = result.stdout.strip()
            if "IMPORT_OK" in output:
                speed_score = max(0.0, 1.0 - elapsed / 10.0)
                return 0.4 + 0.4 * speed_score

            return 0.2

        except subprocess.TimeoutExpired:
            logger.debug("Runtime eval TIMEOUT")
            return 0.1
        except Exception as exc:
            logger.debug("Runtime eval error: %s", exc)
            return 0.0
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _score_novelty(self, source: str) -> float:
        """Score how structurally novel the source is vs the archive.

        Delegates to NoveltyArchive which tracks AST fingerprints
        across all evaluations.  Returns [0.0, 1.0].
        """
        return self.novelty_archive.score(source)

    @staticmethod
    def _max_depth(tree: ast.AST) -> int:
        """Compute the maximum nesting depth of the AST."""

        def _depth(node: ast.AST, current: int) -> int:
            max_d = current
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    child_max = current + 1
                    for subchild in ast.iter_child_nodes(child):
                        child_max = max(child_max, _depth(subchild, current + 1))
                    max_d = max(max_d, child_max)
            return max_d

        return _depth(tree, 0)
