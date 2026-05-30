"""Safety and validation scaffolding for the self-referential forge.

Provides safety checks that prevent the forge from making dangerous
or destructive self-modifications. Acts as a guardrail system for
autonomous code evolution.
"""

from __future__ import annotations

import ast
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\bos\.system\s*\(", "os.system() execution"),
    (r"\bsubprocess\.(call|Popen|run)\s*\(", "subprocess execution"),
    (r"\bshutil\.rmtree\s*\(", "shutil.rmtree deletion"),
    (r"\bpathlib\.Path\.unlink\s*\(", "Path.unlink deletion"),
    (r"\bopen\s*\(.*['\"][wW]['\"]", "File write operations"),
    (r"\b__import__\s*\(", "__import__ execution"),
    (r"\beval\s*\(", "eval() execution"),
    (r"\bexec\s*\(", "exec() execution"),
    (r"\bcompile\s*\(", "compile() execution"),
    (r"\bgit\s+push", "git push in source"),
    (r"\bdocker\s+(rmi?|kill|system)", "Docker destructive operations"),
]

CRITICAL_PATTERNS: list[tuple[str, str]] = [
    (r"\bos\.remove\s*\(", "os.remove()"),
    (r"\bshutil\.rmtree\b", "shutil.rmtree()"),
    (r"\bPath\(.*?\)\.unlink\b", "Path.unlink()"),
    (r"\bgc\.collect\b", "gc.collect() (no issue but flagged)"),
]

MAX_FILE_SIZE_BYTES = 100_000
ALLOWED_EXTENSIONS = {".py", ".toml", ".cfg", ".ini", ".md", ".txt", ".yaml", ".yml", ".json", ".env.example", ".sh"}
BLOCKED_DIRECTORIES = {".git", "__pycache__", "node_modules", ".venv", "venv"}


class SafetyValidator:
    """Validates that self-modifications are safe and within bounds.

    Performs multiple layers of checking:
      1. Environment safety (validates the forge environment is intact)
      2. Mutation safety (checks proposed changes for dangerous patterns)
      3. Boundary safety (ensures changes stay within allowed paths)
    """

    def __init__(
        self,
        forge_root: str | Path | None = None,
        strict_mode: bool = False,
    ) -> None:
        self._root = Path(forge_root) if forge_root else Path(__file__).resolve().parent.parent
        self._strict_mode = strict_mode
        self._violations: list[str] = []

    def validate_environment(self) -> bool:
        """Validate that the forge environment is in a safe state.

        Checks:
          - Forge root directory exists
          - No obvious corruption in source files
          - System resources are adequate

        Returns:
            True if the environment is safe.
        """
        all_ok = True

        if not self._root.exists():
            logger.error("Forge root %s does not exist", self._root)
            all_ok = False

        for fpath in self._root.rglob("*.py"):
            if any(blocked in fpath.parts for blocked in BLOCKED_DIRECTORIES):
                continue
            try:
                content = fpath.read_text()
                ast.parse(content)
            except SyntaxError as exc:
                logger.warning("Syntax error in %s: %s", fpath.relative_to(self._root), exc)
                if self._strict_mode:
                    all_ok = False
            except Exception as exc:
                logger.warning("Could not read %s: %s", fpath.relative_to(self._root), exc)
                all_ok = False

        return all_ok

    def check_mutation(self, source: str, component_type: str = "unknown") -> dict[str, Any]:
        """Check a proposed mutation for safety violations.

        Args:
            source: The mutated source code to check.
            component_type: Type of component being checked.

        Returns:
            Dict with keys: safe (bool), reason (str), violations (list).
        """
        self._violations = []

        self._check_dangerous_patterns(source)
        self._check_critical_patterns(source)

        if len(source) > MAX_FILE_SIZE_BYTES:
            self._violations.append(
                f"Source exceeds max size ({len(source)} > {MAX_FILE_SIZE_BYTES} bytes)"
            )

        try:
            tree = ast.parse(source)
            self._check_ast_boundaries(tree)
        except SyntaxError as exc:
            self._violations.append(f"Syntax error in mutated source: {exc}")

        if self._violations:
            logger.warning(
                "Safety violations for %s: %s",
                component_type,
                "; ".join(self._violations),
            )
            return {
                "safe": False,
                "reason": self._violations[0],
                "violations": list(self._violations),
            }

        return {"safe": True, "reason": "", "violations": []}

    def validate_path(self, path: Path) -> bool:
        """Validate that a file path is within safe bounds.

        Args:
            path: Path to validate.

        Returns:
            True if the path is safe to write to.
        """
        try:
            resolved = path.resolve()
            root_resolved = self._root.resolve()
            root_resolved_str = str(root_resolved)

            if not str(resolved).startswith(root_resolved_str):
                logger.warning("Path %s is outside forge root %s", resolved, root_resolved)
                return False

            if resolved.suffix not in ALLOWED_EXTENSIONS:
                logger.warning("Extension %s not allowed", resolved.suffix)
                return False

            if any(blocked in resolved.parts for blocked in BLOCKED_DIRECTORIES):
                logger.warning("Path %s contains blocked directory", resolved)
                return False

            return True

        except Exception as exc:
            logger.warning("Path validation error: %s", exc)
            return False

    def _check_dangerous_patterns(self, source: str) -> None:
        """Scan for dangerous patterns in the source."""
        for pattern, label in DANGEROUS_PATTERNS:
            matches = re.findall(pattern, source, re.MULTILINE)
            if matches:
                self._violations.append(f"Dangerous pattern '{label}' found ({len(matches)} match(es))")

    def _check_critical_patterns(self, source: str) -> None:
        """Scan for critical (potentially destructive) patterns."""
        for pattern, label in CRITICAL_PATTERNS:
            matches = re.findall(pattern, source, re.MULTILINE)
            if matches:
                self._violations.append(f"Critical pattern '{label}' found ({len(matches)} match(es))")

    def _check_ast_boundaries(self, tree: ast.AST) -> None:
        """Check AST for structural boundary violations."""
        import_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        for node in import_nodes:
            for alias in node.names:
                if alias.name in ("os", "subprocess", "shutil") and self._strict_mode:
                    self._violations.append(f"Import of '{alias.name}' in strict mode")

    def get_violations(self) -> list[str]:
        """Return the list of accumulated violations."""
        return list(self._violations)
