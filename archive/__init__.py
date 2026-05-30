"""Archive — evolution state snapshots and history.

Manages periodic snapshots of the evolution state, enabling rollback,
analysis, and tracking of the forge's evolutionary trajectory.
"""

from archive.archivist import Archivist

__all__ = ["Archivist"]
