"""Evaluators — self-referential fitness evaluation.

Scores forge components across multiple dimensions: syntax validity,
code complexity, safety compliance, modular cohesion, style,
runtime behavior, and novelty.
"""

from evaluators.evaluator import SelfEvaluator
from evaluators.novelty import NoveltyArchive

__all__ = ["SelfEvaluator", "NoveltyArchive"]
