"""Tamper-evident audit trail for every self-modification.

Maintains an append-only, hash-chained log of all mutation events.
Each entry is linked to the previous via SHA-256 hash, providing
tamper evidence. The log is written in a JSON Lines format for
easy programmatic consumption.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_LOG_FILENAME = "mutation_audit.jsonl"


@dataclass
class AuditEntry:
    """A single audit log entry recording one mutation event."""

    timestamp: float
    mutation_id: str
    operator: str
    tier: int
    component_path: str
    source_hash_before: str
    source_hash_after: str
    safety_verdict: str
    safety_violations: list[str] = field(default_factory=list)
    human_approver: str = ""
    sandbox_result: str = ""
    prev_hash: str = ""
    entry_hash: str = ""


class AuditLog:
    """Append-only, hash-chained audit log for self-modifications.

    Each entry is hashed with SHA-256 and linked to the previous entry's
    hash. The log is stored as a JSON Lines file. Tampering with any
    entry breaks the chain for all subsequent entries.
    """

    def __init__(self, log_dir: str | Path | None = None) -> None:
        self._log_dir = Path(log_dir or Path(__file__).resolve().parent / "audit")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / AUDIT_LOG_FILENAME
        self._last_hash: str = self._load_last_hash()

    def record(
        self,
        mutation_id: str,
        operator: str,
        tier: int,
        component_path: str,
        source_before: str,
        source_after: str,
        safety_verdict: str,
        safety_violations: list[str] | None = None,
        human_approver: str = "",
        sandbox_result: str = "",
    ) -> AuditEntry:
        """Record a mutation event in the audit log.

        Args:
            mutation_id: Unique identifier for the mutation.
            operator: Name of the mutation operator applied.
            tier: Safety tier at which the mutation was approved.
            component_path: Path to the mutated component (relative).
            source_before: Source code before mutation.
            source_after: Source code after mutation.
            safety_verdict: 'approved', 'rejected', or 'rolled_back'.
            safety_violations: List of safety violations (if rejected).
            human_approver: Name/ID of human who approved (if applicable).
            sandbox_result: Result of sandbox testing.

        Returns:
            The created AuditEntry.
        """
        entry = AuditEntry(
            timestamp=time.time(),
            mutation_id=mutation_id,
            operator=operator,
            tier=tier,
            component_path=component_path,
            source_hash_before=self._hash_source(source_before),
            source_hash_after=self._hash_source(source_after),
            safety_verdict=safety_verdict,
            safety_violations=safety_violations or [],
            human_approver=human_approver,
            sandbox_result=sandbox_result,
            prev_hash=self._last_hash,
        )

        entry.entry_hash = self._hash_entry(entry)
        self._last_hash = entry.entry_hash
        self._append_entry(entry)
        return entry

    def verify_chain(self) -> tuple[bool, list[str]]:
        """Verify the integrity of the entire audit log hash chain.

        Returns:
            Tuple of (chain_is_intact, list of issues).
        """
        issues: list[str] = []
        entries = self._read_all()

        if not entries:
            return True, []

        prev_hash = ""
        for i, entry in enumerate(entries):
            stored_hash = entry.pop("entry_hash", "")
            computed = self._compute_hash(json.dumps(entry, sort_keys=True, default=str))
            if stored_hash != computed:
                issues.append(f"Entry {i}: hash mismatch (stored={stored_hash}, computed={computed})")
            if prev_hash != entry.get("prev_hash", ""):
                issues.append(f"Entry {i}: chain broken (prev_hash mismatch)")
            prev_hash = stored_hash
            entry["entry_hash"] = stored_hash

        return len(issues) == 0, issues

    def get_all_entries(self) -> list[dict[str, Any]]:
        """Return all audit log entries as dicts."""
        return self._read_all()

    def count(self) -> int:
        """Return the total number of entries in the audit log."""
        return len(self._read_all())

    def _load_last_hash(self) -> str:
        """Load the hash of the last entry in the log."""
        try:
            if self._log_path.exists():
                with open(self._log_path) as f:
                    lines = [line for line in f if line.strip()]
                if lines:
                    last = json.loads(lines[-1])
                    return last.get("entry_hash", "")
        except Exception:
            pass
        return ""

    def _append_entry(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log file."""
        data = asdict(entry)
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(data, sort_keys=True, default=str) + "\n")
        except Exception as exc:
            logger.error("Failed to write audit entry: %s", exc)

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all entries from the audit log file."""
        entries: list[dict[str, Any]] = []
        try:
            if self._log_path.exists():
                with open(self._log_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
        except Exception as exc:
            logger.error("Failed to read audit log: %s", exc)
        return entries

    @staticmethod
    def _hash_source(source: str) -> str:
        """Compute the SHA-256 hash of a source code string."""
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_entry(entry: AuditEntry) -> str:
        """Compute the SHA-256 hash of an audit entry."""
        data = asdict(entry)
        data.pop("entry_hash", None)
        raw = json.dumps(data, sort_keys=True, default=str)
        return AuditLog._compute_hash(raw)

    @staticmethod
    def _compute_hash(raw: str) -> str:
        """Compute SHA-256 hash of a string."""
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
