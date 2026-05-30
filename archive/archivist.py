"""Evolution state archiving for the self-referential forge.

The archivist manages snapshots of evolution state over time, enabling
rollback, analysis, and tracking of the forge's evolutionary trajectory.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Archivist:
    """Manages snapshots and history of the self-referential evolution process.

    Stores periodic snapshots of the evolution state, maintains a history
    of fitness over time, and provides utility methods for analyzing
    the forge's evolutionary trajectory.
    """

    def __init__(
        self,
        archive_dir: str | Path | None = None,
        max_snapshots: int = 100,
        compress: bool = True,
    ) -> None:
        self._archive_dir = Path(archive_dir or Path(__file__).resolve().parent / "data")
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        self._max_snapshots = max_snapshots
        self._compress = compress
        self._history: list[dict[str, Any]] = []
        self._load_history()

    async def snapshot(self, state: dict[str, Any]) -> None:
        """Take a snapshot of the current evolution state.

        Args:
            state: Evolution state dict to archive.
        """
        timestamp = time.time()
        entry = {
            "timestamp": timestamp,
            "generation": state.get("generation", 0),
            "best_fitness": state.get("best_fitness", 0.0),
            "population_size": state.get("population_size", 0),
            "consecutive_failures": state.get("consecutive_failures", 0),
            "meta_state": state.get("meta_state", {}),
        }

        self._history.append(entry)
        self._trim_history()
        await self._write_snapshot(entry)

    def get_history(self) -> list[dict[str, Any]]:
        """Return the full evolution history."""
        return list(self._history)

    def get_fitness_trajectory(self) -> list[float]:
        """Return the fitness-over-time trajectory."""
        return [e["best_fitness"] for e in self._history]

    def get_generation_count(self) -> int:
        """Return the total number of recorded generations."""
        return len(self._history)

    async def rollback_to(self, generation: int) -> dict[str, Any] | None:
        """Retrieve the state at or before the given generation.

        Args:
            generation: Target generation number.

        Returns:
            The state snapshot, or None if not found.
        """
        snapshots = sorted(
            self._archive_dir.glob("snapshot_*.json*"),
            reverse=True,
        )
        for snap in snapshots:
            try:
                data = self._read_snapshot_file(snap)
                if data.get("generation", 0) <= generation:
                    return data
            except Exception as exc:
                logger.warning("Failed to read snapshot %s: %s", snap.name, exc)
        return None

    def _trim_history(self) -> None:
        """Trim history to the maximum number of snapshots."""
        while len(self._history) > self._max_snapshots:
            self._history.pop(0)

    async def _write_snapshot(self, entry: dict[str, Any]) -> None:
        """Write a snapshot entry to disk."""
        gen = entry["generation"]
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime(entry["timestamp"]))
        filename = f"snapshot_gen{gen:06d}_{timestamp_str}.json"

        if self._compress:
            filename += ".gz"
            path = self._archive_dir / filename
            with gzip.open(path, "wt", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
        else:
            path = self._archive_dir / filename
            with open(path, "w") as f:
                json.dump(entry, f, indent=2)

    def _read_snapshot_file(self, path: Path) -> dict[str, Any]:
        """Read a snapshot file, handling compressed and uncompressed formats."""
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        with open(path) as f:
            return json.load(f)

    def _load_history(self) -> None:
        """Load existing snapshots into the in-memory history."""
        try:
            snapshots = sorted(self._archive_dir.glob("snapshot_*.json*"))
            for snap in snapshots[-self._max_snapshots :]:
                try:
                    data = self._read_snapshot_file(snap)
                    self._history.append(data)
                except Exception:
                    continue
            if self._history:
                logger.info("Loaded %d snapshots from archive", len(self._history))
        except Exception as exc:
            logger.debug("No existing snapshots to load: %s", exc)
