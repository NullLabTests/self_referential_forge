"""Safety policy definitions with tiered approval gates.

Defines the rules and tiers that govern when and how the forge is
allowed to modify its own source code. Three tiers of approval:
  - Tier 0 (Automated): Safe, well-understood mutations
  - Tier 1 (Dry-Run): Requires sandbox tests to pass
  - Tier 2 (Human): Requires explicit human approval
  - Tier 3 (Blocked): Never allowed, regardless of context
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any


class SafetyTier(IntEnum):
    """Approval tier for a mutation operator or pattern.

    Higher values = stricter gate.
    """

    AUTOMATED = 0
    DRY_RUN = 1
    HUMAN_APPROVAL = 2
    BLOCKED = 3


@dataclass(frozen=True)
class SafetyRule:
    """A single safety rule binding a pattern to a tier."""

    tier: SafetyTier
    pattern: str
    description: str


@dataclass
class MutationPolicy:
    """Complete safety policy governing which operator → tier mappings are allowed."""

    operator_tiers: dict[str, SafetyTier] = field(default_factory=lambda: {
        "insert_code": SafetyTier.AUTOMATED,
        "rewrite_function": SafetyTier.DRY_RUN,
        "add_parameter": SafetyTier.DRY_RUN,
        "swap_condition": SafetyTier.HUMAN_APPROVAL,
        "duplicate_component": SafetyTier.DRY_RUN,
    })

    ast_blocklist: set[str] = field(default_factory=lambda: {
        "Exec", "Eval", "Call",
    })

    import_blocklist: set[str] = field(default_factory=lambda: {
        "os", "subprocess", "shutil", "signal", "ctypes",
        "socket", "http.server", "multiprocessing",
    })

    dangerous_patterns: list[SafetyRule] = field(default_factory=lambda: [
        SafetyRule(SafetyTier.BLOCKED, r"\beval\s*\(", "eval() execution"),
        SafetyRule(SafetyTier.BLOCKED, r"\bexec\s*\(", "exec() execution"),
        SafetyRule(SafetyTier.BLOCKED, r"\b__import__\s*\(", "__import__() call"),
        SafetyRule(SafetyTier.BLOCKED, r"\bcompile\s*\(", "compile() call"),
        SafetyRule(SafetyTier.BLOCKED, r"\bos\.system\s*\(", "os.system() execution"),
        SafetyRule(SafetyTier.BLOCKED, r"\bos\.popen\s*\(", "os.popen() execution"),
        SafetyRule(SafetyTier.BLOCKED, r"\bsubprocess\.(call|Popen|run|check_output)\s*\(", "subprocess execution"),
        SafetyRule(SafetyTier.BLOCKED, r"\bshutil\.rmtree\s*\(", "shutil.rmtree() deletion"),
        SafetyRule(SafetyTier.BLOCKED, r"\bPath\(.*?\)\.unlink\b", "Path.unlink() deletion"),
        SafetyRule(SafetyTier.BLOCKED, r"\bgc\.collect\b", "gc.collect() forced GC"),
    ])

    suspicious_patterns: list[SafetyRule] = field(default_factory=lambda: [
        SafetyRule(SafetyTier.HUMAN_APPROVAL, r"except\s*:\s*$", "Bare except: clause"),
        SafetyRule(SafetyTier.HUMAN_APPROVAL, r"except\s+Exception\s*:", "Broad except Exception:"),
        SafetyRule(SafetyTier.HUMAN_APPROVAL, r"\bopen\s*\(.*['\"][wWabx]['\"]", "File write mode"),
        SafetyRule(SafetyTier.HUMAN_APPROVAL, r"\btry\s*:", "Unnecessary try block (heuristic)"),
    ])

    protected_modules: set[str] = field(default_factory=lambda: {
        "safety",
        "archive",
    })

    max_source_size: int = 100_000
    allowed_extensions: set[str] = field(default_factory=lambda: {
        ".py", ".toml", ".cfg", ".ini", ".md", ".txt",
        ".yaml", ".yml", ".json", ".env.example", ".sh",
    })
    blocked_directories: set[str] = field(default_factory=lambda: {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
    })

    def tier_for_operator(self, operator: str) -> SafetyTier:
        """Return the approval tier for a given mutation operator."""
        return self.operator_tiers.get(operator, SafetyTier.HUMAN_APPROVAL)

    def is_protected_module(self, filepath: Path) -> bool:
        """Check if a file belongs to a protected module (immune to mutation)."""
        for part in filepath.parts:
            if part in self.protected_modules:
                return True
        return False

    def check_path(self, path: Path, forge_root: Path) -> tuple[bool, str]:
        """Validate a file path against path-based safety rules.

        Returns:
            Tuple of (is_safe, reason).
        """
        try:
            resolved = path.resolve()
            root_resolved = forge_root.resolve()

            if not str(resolved).startswith(str(root_resolved)):
                return False, f"Path {resolved} is outside forge root {root_resolved}"

            if resolved.suffix not in self.allowed_extensions:
                return False, f"Extension '{resolved.suffix}' not in allowed set"

            if any(blocked in resolved.parts for blocked in self.blocked_directories):
                block_match = next(b for b in self.blocked_directories if b in resolved.parts)
                return False, f"Path contains blocked directory '{block_match}'"

            if self.is_protected_module(resolved):
                return False, f"Path belongs to protected module '{resolved.stem}'"

            return True, ""
        except Exception as exc:
            return False, f"Path resolution error: {exc}"
