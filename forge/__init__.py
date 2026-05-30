"""Self-referential forge — core evolution modules.

The forge package contains the orchestrator, self-modification engine,
and CLI entry point for the self-referential evolution loop.
"""

from forge.orchestrator import SelfReferentialOrchestrator, EvolutionConfig, Component
from forge.self_modifier import SelfModifier

__all__ = [
    "SelfReferentialOrchestrator",
    "EvolutionConfig",
    "Component",
    "SelfModifier",
]
