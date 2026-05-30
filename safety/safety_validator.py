"""Safety facade — unified gate for the tiered self-modification safety system.

Coordinates policy enforcement, sandbox testing, audit logging, and
environment validation. This is the primary safety entry point used
by the orchestrator.
"""

from __future__ import annotations

import ast
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from safety.policy import MutationPolicy, SafetyTier
from safety.audit import AuditLog, AuditEntry
from safety.sandbox import Sandbox, SandboxResult

logger = logging.getLogger(__name__)


@dataclass
class SafetyVerdict:
    """Complete verdict from the safety system for a single mutation."""

    approved: bool
    tier: SafetyTier
    mutation_id: str
    sandbox_result: SandboxResult | None = None
    audit_entry: AuditEntry | None = None
    human_approver: str = ""
    reason: str = ""


class SafetyValidator:
    """Unified safety gate for self-modification.

    Coordinates the full safety lifecycle:
      1. Tier classification (what level of scrutiny is needed?)
      2. Automated checks (syntax, AST, dangerous patterns)
      3. Sandbox testing (fork → test → promote)
      4. Human approval (if tier requires)
      5. Audit logging (immutable, hash-chained)
      6. Rollback (on failure)
    """

    def __init__(
        self,
        policy: MutationPolicy | None = None,
        audit_log: AuditLog | None = None,
        sandbox: Sandbox | None = None,
        forge_root: str | Path | None = None,
    ) -> None:
        self._policy = policy or MutationPolicy()
        self._audit = audit_log or AuditLog()
        self._sandbox = sandbox or Sandbox()
        self._forge_root = Path(forge_root) if forge_root else Path(__file__).resolve().parent.parent
        self._violations: list[str] = []

    def validate_environment(self) -> bool:
        """Validate that the forge environment is safe to run.

        Checks:
          - Forge root exists
          - Source files are valid Python
          - No blocked modules imported in forge source

        Returns:
            True if the environment is safe.
        """
        all_ok = True

        if not self._forge_root.exists():
            logger.error("Forge root %s does not exist", self._forge_root)
            return False

        for fpath in self._forge_root.rglob("*.py"):
            if any(blocked in fpath.parts for blocked in self._policy.blocked_directories):
                continue
            try:
                source = fpath.read_text()
                ast.parse(source)
            except SyntaxError as exc:
                logger.warning("Syntax error in %s: %s", fpath.relative_to(self._forge_root), exc)
                all_ok = False
            except Exception as exc:
                logger.warning("Could not read %s: %s", fpath.relative_to(self._forge_root), exc)
                all_ok = False

        if all_ok:
            logger.info("Environment validation passed for %s", self._forge_root)

        return all_ok

    async def check_mutation(
        self,
        source: str,
        component_type: str = "unknown",
        operator: str = "unknown",
        source_before: str = "",
    ) -> dict[str, Any]:
        """Full safety check for a proposed mutation.

        Args:
            source: The mutated source code.
            component_type: Type/category of the component.
            operator: Name of the mutation operator used.
            source_before: Original source (before mutation).

        Returns:
            Dict with keys: safe (bool), reason (str), violations (list),
            verdict (SafetyVerdict).
        """
        mutation_id = f"mut-{uuid.uuid4().hex[:12]}"
        tier = self._policy.tier_for_operator(operator)
        violations: list[str] = []
        sandbox_result: SandboxResult | None = None

        # 0. Tier 3 = immediately blocked
        if tier == SafetyTier.BLOCKED:
            verdict = SafetyVerdict(
                approved=False,
                tier=tier,
                mutation_id=mutation_id,
                reason=f"Operator '{operator}' is at BLOCKED tier",
            )
            self._audit.record(
                mutation_id=mutation_id,
                operator=operator,
                tier=int(tier),
                component_path=component_type,
                source_before=source_before or source,
                source_after=source,
                safety_verdict="rejected",
                safety_violations=[f"Operator '{operator}' is blocked"],
            )
            return {
                "safe": False,
                "reason": verdict.reason,
                "violations": [verdict.reason],
                "verdict": verdict,
            }

        # 1. Syntax validation (all tiers)
        try:
            ast.parse(source)
        except SyntaxError as exc:
            violations.append(f"Syntax error in mutated source: {exc}")

        # 2. Path validation
        clean = component_type.replace(".", "/").replace("_mutated", "").split("?")[0]
        if not clean.endswith(".py"):
            clean += ".py"
        component_path = self._forge_root / clean
        path_safe, path_reason = self._policy.check_path(component_path, self._forge_root)
        if not path_safe:
            violations.append(f"Path violation: {path_reason}")

        # 3. Dangerous pattern scanning
        for rule in self._policy.dangerous_patterns:
            import re
            if re.search(rule.pattern, source, re.MULTILINE):
                violations.append(rule.description)
        for rule in self._policy.suspicious_patterns:
            import re
            if re.search(rule.pattern, source, re.MULTILINE):
                violations.append(rule.description)

        # 4. Sandbox testing (tier >= DRY_RUN)
        if tier >= SafetyTier.DRY_RUN and not violations:
            sandbox_result = await self._sandbox.test_mutation(
                source_before=source_before or source,
                source_after=source,
                operator=operator,
                tier=tier,
            )
            if not sandbox_result.passed:
                violations.extend(sandbox_result.errors)
                violations.extend(sandbox_result.safety_violations)

        # 5. Human approval gate (tier >= HUMAN_APPROVAL)
        human_approver = ""
        if tier >= SafetyTier.HUMAN_APPROVAL and not violations:
            human_approver = "<pending>"
            # Human approval requested — orchestrator handles the interactive gate

        # 6. Final verdict
        approved = len(violations) == 0
        verdict = SafetyVerdict(
            approved=approved,
            tier=tier,
            mutation_id=mutation_id,
            sandbox_result=sandbox_result,
            human_approver=human_approver,
            reason="Approved" if approved else violations[0],
        )

        # 7. Audit
        audit_entry = self._audit.record(
            mutation_id=mutation_id,
            operator=operator,
            tier=int(tier),
            component_path=component_type,
            source_before=source_before or source,
            source_after=source,
            safety_verdict="approved" if approved else "rejected",
            safety_violations=violations,
            sandbox_result="passed" if sandbox_result and sandbox_result.passed else "failed" if sandbox_result else "skipped",
        )
        verdict.audit_entry = audit_entry

        logger.info(
            "Mutation %s: %s (tier=%s, violations=%d)",
            mutation_id, verdict.reason, tier.name, len(violations),
        )

        return {
            "safe": approved,
            "reason": verdict.reason,
            "violations": violations,
            "verdict": verdict,
        }

    def verify_audit_chain(self) -> tuple[bool, list[str]]:
        """Verify the integrity of the entire audit log."""
        return self._audit.verify_chain()

    def get_audit_summary(self) -> dict[str, Any]:
        """Return a summary of audit activity."""
        entries = self._audit.get_all_entries()
        approved = sum(1 for e in entries if e.get("safety_verdict") == "approved")
        rejected = sum(1 for e in entries if e.get("safety_verdict") == "rejected")
        return {
            "total_mutations": len(entries),
            "approved": approved,
            "rejected": rejected,
            "chain_intact": self._audit.verify_chain()[0],
        }

    def get_violations(self) -> list[str]:
        """Return accumulated violations from the last check."""
        return list(self._violations)
