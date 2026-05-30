"""Self-referential forge — core evolution modules.

The forge package contains the orchestrator, self-modification engine,
self-writer (disk write-back + module reload), and CLI entry point for
the self-referential evolution loop.
"""

from forge.orchestrator import SelfReferentialOrchestrator, EvolutionConfig, Component
from forge.self_modifier import SelfModifier
from forge.self_writer import SelfWriter, WriteResult, SmokeTestConfig

__all__ = [
    "SelfReferentialOrchestrator",
    "EvolutionConfig",
    "Component",
    "SelfModifier",
    "SelfWriter",
    "WriteResult",
    "SmokeTestConfig",
]
