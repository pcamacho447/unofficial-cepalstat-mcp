# Contributing to unofficial-cepalstat-mcp

Thank you for your interest in contributing to `unofficial-cepalstat-mcp`! This project provides an open-source semantic resolution engine, client, and Model Context Protocol (MCP) server for the UN CEPALSTAT Open Data API.

---

## 🛠️ Development Environment Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for high-speed package management and virtual environment orchestration.

1. **Prerequisites**: Python 3.10 or higher.
2. **Clone the repository**:
   ```bash
   git clone https://github.com/pcamacho447/unofficial-cepalstat-mcp.git
   cd unofficial-cepalstat-mcp
   ```
3. **Synchronize environment and development dependencies**:
   ```bash
   uv sync --extra dev
   ```

---

## 📐 Code Style & Architecture Guidelines

1. **Modern Typing (Python 3.10+)**:
   - Use built-in union syntax (`X | None` instead of `Optional[X]`, `str | int` instead of `Union[str, int]`).
   - Use built-in generics (`list[str]`, `dict[str, Any]`, `tuple[int, ...]`).
   - Maintain strict typing across all public interfaces and internal engines.
2. **Clean Library Code**:
   - Never commit stray `print()` statements in library code (`src/unofficial_cepalstat_mcp/`).
   - CLI modules must output cleanly structured text or JSON.
3. **Encoding & Portability**:
   - Always specify `encoding="utf-8"` when reading or writing files.
   - Use `Path` objects from `pathlib` for all file path operations. Ensure cross-platform compatibility across Linux, macOS, and Windows.

---

## 🧪 Testing Protocol & Invariants

All changes must pass our rigorous test and benchmark suites before being merged.

### 1. Non-Integration Test Suite
Run the full offline test suite:
```bash
uv run pytest -m "not integration"
```
All tests must pass without warnings or regressions.

### 2. Canonical & Adversarial Benchmarks
Verify semantic resolution accuracy and adversarial robustness:
```bash
# Canonical 200-question benchmark
uv run pytest tests/test_semantic_benchmark_200.py -v

# Adversarial 40-question trap benchmark
uv run pytest tests/test_adversarial_benchmark_40.py -v
```

### 3. Non-Negotiable Core Invariants
- **Zero False Substitution Rate (0.00% FSR)**: Pull requests that introduce false substitutions—substituting requested specificities with different indicators at full confidence—will be rejected immediately. If an indicator does not match the exact requested specificity or granularity, the engine must return `ALTERNATIVE_PROPOSED` (with confidence degradation to 0.65 and an explanatory hint) or `ABSTAINED` (`UNRESOLVED_SPECIFICITY`).
- **Strict Offline Hermeticity**: Test suites must NEVER perform live network calls to the CEPALSTAT API. Use mocked transports, pre-cached SQLite fixtures, or `respx`.
- **Latency Budget**: Local SQLite and in-memory resolution latency must maintain median latency $p50 < 0.5\text{ ms}$.

---

## 📋 Pull Request Checklist

Before submitting a pull request, verify:
- [ ] `uv run pytest -m "not integration"` passes completely.
- [ ] `uv run pytest tests/test_semantic_benchmark_200.py -v` achieves 100.0% Top-1 Accuracy and 0.00% FSR.
- [ ] `uv run pytest tests/test_adversarial_benchmark_40.py -v` achieves 100.0% accuracy and 0.00% FSR.
- [ ] New features or bug fixes include corresponding unit tests under `tests/`.
- [ ] Governance and documentation standards are preserved.
