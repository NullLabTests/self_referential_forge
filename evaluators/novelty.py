"""Novelty archive for curiosity-driven exploration.

Maintains a structural fingerprint archive of previously seen code
and rewards mutations that produce novel AST topologies.  This
implements a form of novelty search (Lehman & Stanley 2011) within
the self-referential forge's code space, preventing premature
convergence on a single genetic lineage.
"""

from __future__ import annotations

import ast
import hashlib
import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class NoveltyArchive:
    """Archive of AST fingerprints used to score code novelty.

    Each evaluated source contributes a structural fingerprint.  The
    novelty score for a new source is the mean hamming distance to
    its k nearest neighbors in fingerprint space.
    """

    def __init__(self, k: int = 5, max_archive_size: int = 1000) -> None:
        self.k = k
        self.max_archive_size = max_archive_size
        self.archive: list[bytes] = []
        self._threshold: float = 0.3

    def score(self, source: str) -> float:
        """Compute a novelty score for *source* in [0.0, 1.0].

        Updates the archive with the source's fingerprint.
        """
        fingerprint = self._ast_fingerprint(source)

        if not self.archive:
            self.archive.append(fingerprint)
            return 1.0

        distances = sorted(
            self._hamming_distance(fingerprint, archived)
            for archived in self.archive
        )

        k = min(self.k, len(distances))
        sparseness = sum(distances[:k]) / k

        self.archive.append(fingerprint)
        if len(self.archive) > self.max_archive_size:
            self.archive = self.archive[-self.max_archive_size:]

        score = min(1.0, sparseness / 64.0)
        return score

    def _ast_fingerprint(self, source: str) -> bytes:
        """Produce a structural hash of a source file.

        The fingerprint captures which AST node types appear and in
        what proportion, so it is robust against identifier renaming
        and whitespace changes.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return b"\x00" * 16

        counts: Counter[str] = Counter(
            type(node).__name__ for node in ast.walk(tree)
        )
        normalised = {
            k: v / max(1, sum(counts.values()))
            for k, v in sorted(counts.items())
        }
        raw = str(sorted(normalised.items())).encode()
        return hashlib.md5(raw).digest()

    @staticmethod
    def _hamming_distance(a: bytes, b: bytes) -> float:
        """Bitwise hamming distance normalised to [0, 1]."""
        if len(a) != len(b):
            return 1.0
        xor = int.from_bytes(a, "big") ^ int.from_bytes(b, "big")
        return xor.bit_count() / (len(a) * 8)

    def get_summary(self) -> dict[str, Any]:
        return {
            "archive_size": len(self.archive),
            "k": self.k,
            "max_archive_size": self.max_archive_size,
            "threshold": self._threshold,
        }
