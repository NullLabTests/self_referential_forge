"""Benchmarks — internal evolution quality benchmarks.

Evaluates the forge's own performance: fitness improvement rate,
operator diversity, convergence resilience, and mutation quality.
"""

from benchmarks.benchmark_suite import BenchmarkSuite, BenchmarkResult

__all__ = ["BenchmarkSuite", "BenchmarkResult"]
