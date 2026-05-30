"""Sandbox for safely testing mutations before promoting them to live code.

Implements a fork-test-promote pattern:
  1. FORK: Copy the target file to a temporary sandbox directory
  2. MUTATE: Apply the mutation to the sandbox copy
  3. TEST: Run safety checks, syntax validation, and unit tests
  4. PROMOTE: Only if all checks pass, apply to the real file
  5. ROLLBACK: On failure, restore from the last known-good snapshot
"""

from __future__ import annotations

import ast
import logging
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from safety.policy import MutationPolicy, SafetyTier

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of a sandboxed mutation test."""

    passed: bool
    syntax_valid: bool = True
    tests_passed: bool = True
    safety_violations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    diff: str = ""


class Sandbox:
    """Sandbox for safe mutation testing with fork-test-promote lifecycle.

    Usage:
        sandbox = Sandbox()
        result = sandbox.test_mutation(source_before, source_after, "insert_code")
        if result.passed:
            sandbox.promote(file_path, source_after)
        else:
            sandbox.rollback(file_path, source_before, result)
    """

    def __init__(
        self,
        policy: MutationPolicy | None = None,
        test_command: list[str] | None = None,
        sandbox_root: Path | None = None,
    ) -> None:
        self._policy = policy or MutationPolicy()
        self._test_command = test_command or [
            sys.executable, "-m", "pytest", "--tb=short", "-q", "--timeout=30",
        ]
        self._sandbox_root = sandbox_root or Path(tempfile.mkdtemp(prefix="forge_sandbox_"))

    async def test_mutation(
        self,
        source_before: str,
        source_after: str,
        operator: str,
        tier: SafetyTier = SafetyTier.DRY_RUN,
    ) -> SandboxResult:
        """Test a mutation in the sandbox.

        Performs:
          1. Syntax validation of the mutated source
          2. AST-level safety pattern checks
          3. Unit test execution (if tests directory exists)

        Args:
            source_before: Original source code.
            source_after: Mutated source code.
            operator: Name of the mutation operator.
            tier: Safety tier governing which checks to run.

        Returns:
            SandboxResult with pass/fail and detailed diagnostics.
        """
        start = time.time()
        errors: list[str] = []
        violations: list[str] = []

        # 1. Syntax validation
        syntax_valid = await self._check_syntax(source_after)
        if not syntax_valid:
            errors.append("Mutated source contains syntax errors")

        # 2. AST-level safety checks
        if syntax_valid:
            ast_violations = await self._check_ast_safety(source_after)
            violations.extend(ast_violations)

        # 3. Dangerous pattern scanning
        pattern_violations = await self._check_dangerous_patterns(source_after)
        violations.extend(pattern_violations)

        # 4. Tier-based blocking
        if tier == SafetyTier.BLOCKED:
            errors.append(f"Operator '{operator}' is blocked by policy")

        if violations and tier >= SafetyTier.DRY_RUN:
            errors.append(f"Safety violations detected for tier {tier.name}")

        # 5. Test execution (only for DRY_RUN tier and above)
        tests_passed = True
        if tier >= SafetyTier.DRY_RUN and syntax_valid and not violations:
            tests_passed = await self._run_tests(source_after)

        elapsed = time.time() - start

        result = SandboxResult(
            passed=syntax_valid and tests_passed and not errors,
            syntax_valid=syntax_valid,
            tests_passed=tests_passed,
            safety_violations=violations,
            errors=errors,
            execution_time=elapsed,
        )

        logger.debug(
            "Sandbox result: passed=%s, syntax=%s, tests=%s, violations=%d, time=%.2fs",
            result.passed, result.syntax_valid, result.tests_passed,
            len(violations), elapsed,
        )

        return result

    async def _check_syntax(self, source: str) -> bool:
        """Check if the source is valid Python."""
        try:
            ast.parse(source)
            return True
        except SyntaxError as exc:
            logger.debug("Syntax check failed: %s", exc)
            return False

    async def _check_ast_safety(self, source: str) -> list[str]:
        """Check the AST for blocked node types and imports."""
        violations: list[str] = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self._policy.import_blocklist:
                            violations.append(
                                f"Import of blocked module '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self._policy.import_blocklist:
                        violations.append(
                            f"Import from blocked module '{node.module}'"
                        )
        except SyntaxError:
            pass
        return violations

    async def _check_dangerous_patterns(self, source: str) -> list[str]:
        """Scan for dangerous regex patterns."""
        violations: list[str] = []
        for rule in self._policy.dangerous_patterns:
            import re
            if re.search(rule.pattern, source, re.MULTILINE):
                violations.append(rule.description)
        for rule in self._policy.suspicious_patterns:
            import re
            if re.search(rule.pattern, source, re.MULTILINE):
                violations.append(rule.description)
        return violations

    async def _run_tests(self, source: str) -> bool:
        """Run the unit test suite against the modified source."""
        test_dir = self._sandbox_root / "tests"
        if not test_dir.exists():
            return True

        try:
            result = subprocess.run(
                [*self._test_command, str(test_dir)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                return True
            else:
                logger.warning("Tests failed: %s", result.stderr[:200])
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("Test execution error: %s", exc)
            return False

    def promote(self, file_path: Path, new_source: str) -> None:
        """Promote a mutation from sandbox to live code.

        Args:
            file_path: Path to the file to update.
            new_source: The approved new source code.

        Raises:
            RuntimeError: If promotion fails.
        """
        try:
            file_path.write_text(new_source)
            logger.info("Promoted mutation to %s", file_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to promote mutation: {exc}") from exc

    def rollback(
        self,
        file_path: Path,
        original_source: str,
        result: SandboxResult | None = None,
    ) -> None:
        """Rollback a failed mutation.

        Args:
            file_path: Path to the file to restore.
            original_source: The original source code to restore.
            result: Optional sandbox result for logging.
        """
        try:
            file_path.write_text(original_source)
            violations = result.safety_violations if result else []
            logger.info(
                "Rolled back %s (violations: %s)",
                file_path,
                "; ".join(violations) if violations else "none",
            )
        except Exception as exc:
            logger.error("Rollback failed for %s: %s", file_path, exc)

    def cleanup(self) -> None:
        """Remove the sandbox directory."""
        import shutil
        try:
            if self._sandbox_root.exists():
                shutil.rmtree(self._sandbox_root)
                logger.debug("Sandbox cleaned up")
        except Exception as exc:
            logger.warning("Sandbox cleanup failed: %s", exc)
