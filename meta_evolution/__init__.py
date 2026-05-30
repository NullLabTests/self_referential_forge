"""Meta-evolution — self-tuning strategy adaptation.

Tracks operator performance and adjusts selection probabilities,
mutation rates, and crossover rates for the self-referential forge.
"""

from meta_evolution.meta_evolver import MetaEvolver

__all__ = ["MetaEvolver"]
