"""Evaluators — self-referential fitness evaluation.

Scores forge components across multiple dimensions: syntax validity,
code complexity, safety compliance, modular cohesion, and style.
"""

from evaluators.evaluator import SelfEvaluator

__all__ = ["SelfEvaluator"]
