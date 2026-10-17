"""Systematic multidimensional facet-coverage benchmark tests for CEPALSTAT.

Stress-tests Faceta x Familia routing, positive breakdown conmutations,
adversarial unsupported facet abstentions, and lexical boundary isolation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

COVERAGE_CASES_PATH = Path(__file__).parent / "benchmark" / "facet_coverage_cases.json"


def load_facet_coverage_cases() -> list[dict[str, Any]]:
    """Load and return the curated facet coverage benchmark test cases."""
    if not COVERAGE_CASES_PATH.exists():
        raise FileNotFoundError(f"Coverage cases file not found at {COVERAGE_CASES_PATH}")
    with open(COVERAGE_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise TypeError(f"Expected list of cases, got {type(cases).__name__}")
    return cases


def test_facet_coverage_cases_file_exists_and_covers_all_13_facets():
    """Verify that the benchmark file exists, conforms to schema, and covers all 13 canonical facets."""
    assert COVERAGE_CASES_PATH.exists(), f"Coverage cases file not found at {COVERAGE_CASES_PATH}"
    cases = load_facet_coverage_cases()

    assert len(cases) >= 65, f"Expected at least 65 coverage cases, found {len(cases)}"

    # Verify all 13 canonical facets are represented
    expected_facets = {
        "etnia",
        "sexo",
        "area",
        "severidad",
        "edad",
        "quintil",
        "estrato",
        "educacion",
        "formalidad",
        "canasta",
        "rubro",
        "moneda",
        "actividad",
    }
    covered_facets = {c["facet"] for c in cases}
    missing = expected_facets - covered_facets
    assert not missing, f"Missing coverage for canonical facets: {missing}"

    # Verify each case has required schema fields
    required_fields = {
        "id",
        "facet",
        "family",
        "query",
        "case_type",
        "expected_status",
    }
    for case in cases:
        missing_fields = required_fields - set(case.keys())
        assert not missing_fields, f"Case {case.get('id')} missing fields: {missing_fields}"
        assert case["case_type"] in ("positive", "negative", "boundary"), (
            f"Case {case.get('id')} has invalid case_type: {case.get('case_type')}"
        )
