"""Safety — tiered guardrail system for autonomous self-modification.

Three-tier safety architecture:
  Tier 0 (AUTOMATED) - Safe mutations pass without human intervention
  Tier 1 (DRY_RUN)   - Requires sandbox testing to pass before promotion
  Tier 2 (HUMAN)     - Requires explicit human approval
  Tier 3 (BLOCKED)   - Never allowed, regardless of context

Modules:
  - policy:       Tier definitions, operator→tier mappings, path rules
  - sandbox:      Fork-test-promote lifecycle for safe mutation testing
  - audit:        Immutable, hash-chained audit log for all mutations
  - safety_validator: Unified facade coordinating all safety components
"""

from safety.safety_validator import SafetyValidator, SafetyVerdict
from safety.policy import MutationPolicy, SafetyTier, SafetyRule
from safety.audit import AuditLog, AuditEntry
from safety.sandbox import Sandbox, SandboxResult

__all__ = [
    "SafetyValidator",
    "SafetyVerdict",
    "MutationPolicy",
    "SafetyTier",
    "SafetyRule",
    "AuditLog",
    "AuditEntry",
    "Sandbox",
    "SandboxResult",
]
