# Task 4 Brief: Automated Benchmark Execution & Stress Test (200 Cases)

## Requirements
Working directory: `C:\papx\statscepal`

You are implementing Task 4 of the 200-Question Empirical Benchmark Plan.
You must implement `tests/test_semantic_benchmark_200.py` to run all 200 test cases from `tests/benchmark/semantic_benchmark_cases_200.json` against `SemanticResolutionEngine`, validating:
1. **Top-1 Accuracy:** Must be $\ge 98.0\%$ (target $100.0\%$).
2. **False Substitution Rate (FSR):** Must be strictly $0.0\%$. No untyped swaps allowed.
3. **Local Resolution Latency:** $p50 < 2.0\text{ ms}$.
4. **Cluster-level Health:** Verify each of the 10 clusters individually passes with zero fatal crashes.

## TDD Instructions
1. Author `tests/test_semantic_benchmark_200.py`.
2. Run `uv run pytest tests/test_semantic_benchmark_200.py -v`.
3. If any test case fails or needs registry/parser fine-tuning, address it cleanly.
4. Run full non-integration test suite: `uv run pytest -m "not integration"` (all 168+ tests must pass).
5. Commit:
   `git add tests/test_semantic_benchmark_200.py`
   `git commit -m "test(semantic): implement automated 200-case benchmark runner"`
6. Write full report to:
   `.superpowers/sdd/2026-10-15-semantic-engine-200-queries-benchmark-plan/task-4-report.md`
