# Soporte Multi-Año, Rangos y Series Temporales en el Motor Semántico CEPALSTAT - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dotar al motor semántico de CEPALSTAT (`QueryParser`, `SemanticDataFetcher`, `AppliedFilters` y `cli.py`) de la capacidad de extraer, resolver y consultar series temporales multi-año (años discretos como *"2022 y 2023"*, rangos cerrados como *"del 2018 al 2022"* y ventanas relativas como *"los últimos 4 años"*), devolviendo la serie completa con sus valores empíricos sin romper la retrocompatibilidad con las 212 pruebas existentes.

**Architecture:** 
1. `AppliedFilters` se extiende con `years: list[int] = Field(default_factory=list)`, `time_mode: str = "SINGLE"` (`SINGLE`, `LIST`, `RANGE`, `RELATIVE_WINDOW`) y `relative_window_size: int | None = None`, preservando `year: int | None` como el año representativo/ancla más reciente.
2. `QueryParser` añade un pipeline de normalización temporal con tres extractores especializados: (a) captura de rangos cerrados (`\b(del|desde|entre)\s+(\d{4})\s+(al|a|hasta|y)\s+(\d{4})\b` y `\b(\d{4})\s*-\s*(\d{4})\b`), (b) captura de listas discretas (`\b(\d{4})\s*(?:,|y|e)\s*(\d{4})\b`), (c) captura de ventanas relativas (*"ultimos (\d+) anos"*, *"ultimos anos"*, *"ultima decada"*).
3. `SemanticDataFetcher` adapta el filtrado de `filtered_df`: si hay múltiples años o una ventana relativa, calcula los $N$ años más recientes disponibles para ese país/indicador, extrae la serie ordenada cronológicamente y puebla `empirical_data["series"]`.
4. `cli.py` renderiza la serie temporal en formato tabular ordenado con año, valor y unidad cuando `series` está presente.

**Tech Stack:** Python 3.10+, Pandas, Pydantic v2, pytest, uv, CEPALSTAT REST API.

**Spec:** [`docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md`](file:///C:/papx/statscepal/docs/specs/2026-10-15-benchmark-200-preguntas-motor-semantico.md).

## Global Constraints

- Modern typing syntax Python 3.10+ (`list[int]`, `int | None`, `dict[str, Any]`).
- All 212 existing non-integration tests must remain passing without regression.
- False Substitution Rate must strictly equal 0.00% across the 200-question benchmark.
- Top-1 Accuracy across the 200 benchmark test cases must strictly remain 100.0%.
- Local resolution latency over SQLite and in-memory thesaurus must maintain p50 < 0.5 ms.
- Safe UTF-8 encoding for Windows console environments (`cp1252` protection).

---

## File Structure & Responsibilities

| File | Responsibility |
| :--- | :--- |
| `src/statscepal/semantic/models.py` | Extensión de `AppliedFilters` (`years`, `time_mode`, `relative_window_size`) y documentación de payload de series en `empirical_data`. |
| `src/statscepal/semantic/parser.py` | Implementación de extractores para rangos temporales, listas discretas de años y ventanas relativas (*"últimos N años"*). |
| `src/statscepal/semantic/fetcher.py` | Filtrado y extracción de series multi-año y ventanas relativas ancladas al $T_{\max}$ del dataset. |
| `src/statscepal/cli.py` | Renderizado tabular en terminal de la serie cronológica multi-año al usar `--fetch`. |
| `tests/test_semantic_multi_year.py` | Test suite TDD para consultas temporales complejas (listas, rangos, ventanas relativas y fetch multi-año). |

---

### Task 1: Data Model Extensions for Multi-Year & Time Modes

**Files:**
- Modify: `src/statscepal/semantic/models.py:85-95`
- Modify: `src/statscepal/semantic/parser.py:50-70`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: `pydantic.BaseModel`, `Field`
- Produces: `AppliedFilters.years: list[int]`, `AppliedFilters.time_mode: str`, `AppliedFilters.relative_window_size: int | None`, `ParsedIntent.years: list[int]`, `ParsedIntent.time_mode: str`, `ParsedIntent.relative_window_size: int | None`.

- [ ] **Step 1: Write failing test for multi-year fields in models**

```python
# tests/test_semantic_multi_year.py
import pytest
from statscepal.semantic.models import AppliedFilters, ParsedIntent


def test_applied_filters_multi_year_defaults_and_assignment():
    filters = AppliedFilters(country_code="PER", country_name="Perú", year=2023, years=[2022, 2023], time_mode="LIST")
    assert filters.year == 2023
    assert filters.years == [2022, 2023]
    assert filters.time_mode == "LIST"
    assert filters.relative_window_size is None


def test_parsed_intent_multi_year_fields():
    intent = ParsedIntent(
        raw_query="en 2022 y 2023",
        clean_query="en 2022 y 2023",
        years=[2022, 2023],
        time_mode="LIST",
    )
    assert intent.years == [2022, 2023]
    assert intent.time_mode == "LIST"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -v`
Expected: FAIL with ValidationError or unexpected keyword argument `years`

- [ ] **Step 3: Update `models.py` and `parser.py` with multi-year fields**

In `src/statscepal/semantic/models.py`:
```python
class AppliedFilters(BaseModel):
    country_code: str | None = None
    country_name: str | None = None
    year: int | None = None
    years: list[int] = Field(default_factory=list)
    time_mode: str = "SINGLE"  # "SINGLE", "LIST", "RANGE", "RELATIVE_WINDOW"
    relative_window_size: int | None = None
    facets: dict[str, str] = Field(default_factory=dict)
    dimensions: list[AppliedDimensionFilter] = Field(default_factory=list)
```

In `src/statscepal/semantic/parser.py`:
```python
class ParsedIntent(BaseModel):
    ...
    year: int | None = None
    years: list[int] = Field(default_factory=list)
    time_mode: str = "SINGLE"
    relative_window_size: int | None = None
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_multi_year.py -v`
Expected: PASS

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: 212+ tests pass with zero regressions.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/models.py src/statscepal/semantic/parser.py tests/test_semantic_multi_year.py
git commit -m "feat(semantic): add multi-year and time-mode fields to ParsedIntent and AppliedFilters"
```

---

### Task 2: Advanced Temporal Extractor in QueryParser

**Files:**
- Modify: `src/statscepal/semantic/parser.py:150-180`
- Modify: `src/statscepal/semantic/engine.py:80-120`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: Natural language query string
- Produces: Normalized `years`, `time_mode`, `relative_window_size`, and primary `year` (most recent) in `ParsedIntent` and `SemanticResolutionResponse.applied_filters`.

- [ ] **Step 1: Write failing tests for temporal extraction patterns**

```python
# In tests/test_semantic_multi_year.py
def test_parser_extracts_discrete_year_list():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("Cual fue la plata minima real en peru en el 2023 y 2022")
    assert intent.time_mode == "LIST"
    assert sorted(intent.years) == [2022, 2023]
    assert intent.year == 2023  # Primary anchor is latest


def test_parser_extracts_closed_year_range():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("inflacion en chile del 2019 al 2022")
    assert intent.time_mode == "RANGE"
    assert intent.years == [2019, 2020, 2021, 2022]
    assert intent.year == 2022

    intent_dash = parser.parse("PIB de Colombia 2020-2023")
    assert intent_dash.time_mode == "RANGE"
    assert intent_dash.years == [2020, 2021, 2022, 2023]
    assert intent_dash.year == 2023


def test_parser_extracts_relative_time_window():
    from statscepal.semantic.parser import QueryParser

    parser = QueryParser()
    intent = parser.parse("inflacion de alimentos en peru los ultimos 4 anos")
    assert intent.time_mode == "RELATIVE_WINDOW"
    assert intent.relative_window_size == 4
    assert intent.year is None  # Anchored dynamically by fetcher
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -k "test_parser" -v`
Expected: FAIL

- [ ] **Step 3: Implement temporal extractors in `QueryParser.parse()` and propagate in `engine.py`**

In `src/statscepal/semantic/parser.py`:
1. Check relative windows:
   - `re.search(r"\bultimos?\s+(\d+)\s+anos?\b", clean)` -> `time_mode = "RELATIVE_WINDOW"`, `relative_window_size = int(m.group(1))`
   - `re.search(r"\bultima\s+decada\b", clean)` -> `time_mode = "RELATIVE_WINDOW"`, `relative_window_size = 10`
   - `re.search(r"\bultimo\s+quinquenio\b", clean)` -> `time_mode = "RELATIVE_WINDOW"`, `relative_window_size = 5`
   - `re.search(r"\bultimo\s+trienio\b", clean)` -> `time_mode = "RELATIVE_WINDOW"`, `relative_window_size = 3`
2. Check closed ranges:
   - `re.search(r"\b(?:del|desde|entre)\s+(19\d\d|20\d\d)\s+(?:al|a|hasta|y)\s+(19\d\d|20\d\d)\b", clean)`
   - `re.search(r"\b(19\d\d|20\d\d)\s*[-–]\s*(19\d\d|20\d\d)\b", clean)`
   - Generar `range(y1, y2 + 1)`
3. Check discrete lists:
   - `re.findall(r"\b(19\d\d|20\d\d)\b", clean)` -> Si hay $\ge 2$, ordenar únicos, `time_mode = "LIST"`.
4. Si solo hay 1 año:
   - Mantener comportamiento canónico actual (`time_mode = "SINGLE"`, `years = [year]`).

In `src/statscepal/semantic/engine.py`:
- Propagar `applied_filters.years = intent.years`, `applied_filters.time_mode = intent.time_mode`, `applied_filters.relative_window_size = intent.relative_window_size`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_multi_year.py -v`
Expected: PASS

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: 212+ tests pass with zero regressions.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/parser.py src/statscepal/semantic/engine.py tests/test_semantic_multi_year.py
git commit -m "feat(semantic): implement range, list, and relative temporal extractors in QueryParser"
```

---

### Task 3: Multi-Year and Relative Window Data Extraction in SemanticDataFetcher

**Files:**
- Modify: `src/statscepal/semantic/fetcher.py:125-230`
- Test: `tests/test_semantic_multi_year.py`

**Interfaces:**
- Consumes: `SemanticResolutionResponse`, `AppliedFilters.years`, `time_mode`, `relative_window_size`
- Produces: `empirical_data["series"]: list[dict[str, Any]]` donde cada elemento tiene `year`, `value`, `unit`, `notes`.

- [ ] **Step 1: Write failing test with mock dataframe for multi-year fetch**

```python
# In tests/test_semantic_multi_year.py
import pandas as pd
from unittest.mock import patch
from statscepal.semantic.fetcher import SemanticDataFetcher
from statscepal.semantic.models import (
    SemanticResolutionResponse,
    ResolutionStatus,
    SelectedCandidate,
    AppliedFilters,
)


def test_fetcher_extracts_multi_year_series():
    mock_df = pd.DataFrame([
        {"country": "Peru", "year": 2021, "value": 100.0, "notes": ""},
        {"country": "Peru", "year": 2022, "value": 104.2, "notes": ""},
        {"country": "Peru", "year": 2023, "value": 101.8, "notes": ""},
    ])

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="plata minima en peru en 2022 y 2023",
        selected_candidate=SelectedCandidate(indicator_id=3337, name="Salario mínimo real", unit="índice 2018=100"),
        applied_filters=AppliedFilters(country_name="Perú", country_code="PER", year=2023, years=[2022, 2023], time_mode="LIST"),
    )

    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(response)

    assert payload["observation_exists"] is True
    assert "series" in payload
    assert len(payload["series"]) == 2
    assert payload["series"][0]["year"] == 2022
    assert payload["series"][0]["value"] == 104.2
    assert payload["series"][1]["year"] == 2023
    assert payload["series"][1]["value"] == 101.8


def test_fetcher_extracts_relative_window_series():
    mock_df = pd.DataFrame([
        {"country": "Peru", "year": 2019, "value": 95.0},
        {"country": "Peru", "year": 2020, "value": 98.0},
        {"country": "Peru", "year": 2021, "value": 100.0},
        {"country": "Peru", "year": 2022, "value": 104.2},
        {"country": "Peru", "year": 2023, "value": 101.8},
    ])

    response = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="ultimos 3 anos",
        selected_candidate=SelectedCandidate(indicator_id=3337, name="Salario mínimo real", unit="índice 2018=100"),
        applied_filters=AppliedFilters(country_name="Perú", country_code="PER", time_mode="RELATIVE_WINDOW", relative_window_size=3),
    )

    fetcher = SemanticDataFetcher()
    with patch.object(fetcher, "_load_indicator_data", return_value=mock_df):
        payload = fetcher.fetch_resolved_data(response)

    assert len(payload["series"]) == 3
    assert [s["year"] for s in payload["series"]] == [2021, 2022, 2023]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_semantic_multi_year.py -k "test_fetcher" -v`
Expected: FAIL

- [ ] **Step 3: Implement multi-year filtering and series collation in `fetcher.py`**

In `src/statscepal/semantic/fetcher.py`:
- Manejar `target_years = response.applied_filters.years` y `time_mode = response.applied_filters.time_mode`.
- Si `time_mode == "RELATIVE_WINDOW"`:
  - Extraer los $N$ (`relative_window_size`) años máximos no vacíos disponibles en `filtered_df`.
- Si hay múltiples años coincidentes:
  - Generar lista `series = [{"year": int(r[year_col]), "value": float(r["value"]), ...}]` ordenada ascendentemente por año.
  - Asignar `payload["series"] = series`.
  - Asignar `payload["value"] = series[-1]["value"]` y `payload["year"] = series[-1]["year"]` para mantener compatibilidad con consumidores de valor único.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_semantic_multi_year.py -v`
Expected: PASS

- [ ] **Step 5: Run full non-integration test suite**

Run: `uv run pytest -m "not integration"`
Expected: 212+ tests pass with zero regressions.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/semantic/fetcher.py tests/test_semantic_multi_year.py
git commit -m "feat(semantic): implement multi-year and relative window empirical series extraction"
```

---

### Task 4: CLI Presentation & End-to-End Regression Certification

**Files:**
- Modify: `src/statscepal/cli.py:470-510`
- Test: `tests/test_cli_semantic.py`
- Test: `tests/test_semantic_benchmark_200.py`

**Interfaces:**
- Consumes: `SemanticResolutionResponse.empirical_data["series"]`
- Produces: Formateo tabular ordenado por año en la CLI cuando se ejecuta `semantic resolve ... --fetch`.

- [ ] **Step 1: Write failing CLI test for series display**

```python
# In tests/test_cli_semantic.py
def test_cli_semantic_resolve_multi_year_series_display(capsys):
    from statscepal.cli import main
    from unittest.mock import patch

    mock_payload = {
        "observation_exists": True,
        "indicator_id": 3337,
        "indicator_name": "Salario mínimo real",
        "unit": "índice 2018=100",
        "country": "Perú",
        "year": 2023,
        "value": 101.8,
        "series": [
            {"year": 2022, "value": 104.2, "unit": "índice 2018=100", "notes": ""},
            {"year": 2023, "value": 101.8, "unit": "índice 2018=100", "notes": ""},
        ],
    }

    with patch("statscepal.semantic.fetcher.SemanticDataFetcher.fetch_resolved_data", return_value=mock_payload):
        code = main(["semantic", "resolve", "plata minima en peru en 2022 y 2023", "--fetch"])
    assert code == 0
    captured = capsys.readouterr().out
    assert "Empirical Series (2 observations):" in captured
    assert "2022" in captured and "104.2" in captured
    assert "2023" in captured and "101.8" in captured
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_semantic.py::test_cli_semantic_resolve_multi_year_series_display -v`
Expected: FAIL

- [ ] **Step 3: Update `cli.py` to format series tables**

In `src/statscepal/cli.py`:
- En `resolve`, al imprimir `Empirical Observation:`:
  - Si `emp.get("series")`:
    ```python
    series = emp["series"]
    print(f"Empirical Series ({len(series)} observations):")
    print(f"  {'Year':<8} {'Value':<12} {'Unit'}")
    print(f"  {'-'*6} {'-'*10} {'-'*20}")
    for item in series:
        val_str = f"{item['value']:g}" if isinstance(item['value'], (int, float)) else str(item['value'])
        print(f"  {item['year']:<8} {val_str:<12} {item.get('unit', '')}")
    ```
  - Si no hay `series`, imprimir el formato single-year actual.

- [ ] **Step 4: Run CLI test to verify it passes**

Run: `uv run pytest tests/test_cli_semantic.py -v`
Expected: PASS

- [ ] **Step 5: Run 200-question benchmark and full non-integration suite**

Run: `uv run pytest tests/test_semantic_benchmark_200.py -v`
Run: `uv run pytest -m "not integration"`
Expected: 100.0% pass rate, zero regressions, latency < 0.5 ms.

- [ ] **Step 6: Commit**

```bash
git add src/statscepal/cli.py tests/test_cli_semantic.py
git commit -m "feat(cli): render empirical multi-year time series in semantic resolve output"
```

---

## Self-Review Checklist
- [x] Discrete multi-year list (`2022 y 2023`) handled.
- [x] Closed ranges (`2019 a 2023`, `2020-2023`) handled.
- [x] Relative time windows (`últimos 4 años`, `última década`) dynamically anchored to dataset $T_{\max}$.
- [x] Single-year queries preserve existing `year: int | None` semantics 100%.
- [x] Full test suite (212 tests) and benchmark (200 cases) remain completely green.
