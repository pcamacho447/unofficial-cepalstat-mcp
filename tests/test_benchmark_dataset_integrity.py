"""Integrity and structural validation tests for the 200-question empirical benchmark dataset."""

import json
import re
from pathlib import Path

import pytest

BENCHMARK_PATH = Path(__file__).parent / "benchmark" / "semantic_benchmark_cases_200.json"

EXPECTED_CLUSTERS = [
    "C1_POBREZA",
    "C2_DESIGUALDAD",
    "C3_MERCADO_LABORAL",
    "C4_SALARIOS_E_INGRESOS",
    "C5_CUENTAS_NACIONALES",
    "C6_PRECIOS_E_INFLACION",
    "C7_FINANZAS_PUBLICAS",
    "C8_SECTOR_EXTERNO",
    "C9_MEDIO_AMBIENTE",
    "C10_ADVERSARIOS_Y_ABSTENCIONES",
]

EXPECTED_DIFFICULTIES = {"CANONICAL", "SLANG", "BREAKDOWN", "AMBIGUOUS", "ABSTENTION"}
EXPECTED_STATUSES = {"RESOLVED", "RESOLVED_WITH_ANCHORS", "ALTERNATIVE_PROPOSED", "ABSTAINED"}

REQUIRED_FIELDS = {
    "id",
    "cluster",
    "difficulty",
    "query",
    "expected_status",
    "expected_indicator_id",
    "expected_facets",
    "expected_reason",
    "expected_alternatives",
}


@pytest.fixture(scope="module")
def benchmark_data():
    assert BENCHMARK_PATH.exists(), f"Benchmark file {BENCHMARK_PATH} does not exist"
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "Benchmark dataset root must be a JSON array"
    return data


def test_dataset_count_and_sequential_ids(benchmark_data):
    assert len(benchmark_data) == 200, f"Expected exactly 200 items, got {len(benchmark_data)}"

    expected_ids = [f"SE-{i:03d}" for i in range(1, 201)]
    actual_ids = [item.get("id") for item in benchmark_data]
    assert actual_ids == expected_ids, "Test case IDs must be strictly sequential from SE-001 to SE-200"


def test_clusters_distribution(benchmark_data):
    cluster_counts = {}
    for item in benchmark_data:
        cl = item.get("cluster")
        assert cl in EXPECTED_CLUSTERS, f"Unknown cluster: {cl} in item {item.get('id')}"
        cluster_counts[cl] = cluster_counts.get(cl, 0) + 1

    assert len(cluster_counts) == 10, f"Expected 10 clusters, got {len(cluster_counts)}"
    for cl in EXPECTED_CLUSTERS:
        assert cluster_counts.get(cl) == 20, f"Cluster {cl} must have exactly 20 items, found {cluster_counts.get(cl)}"


def test_coverage_matrix_8_4_4_2_2_per_cluster(benchmark_data):
    clusters_grouped = {}
    for item in benchmark_data:
        cl = item.get("cluster")
        clusters_grouped.setdefault(cl, []).append(item)

    for cl, items in clusters_grouped.items():
        diff_counts = {}
        for item in items:
            diff = item.get("difficulty")
            assert diff in EXPECTED_DIFFICULTIES, f"Invalid difficulty {diff} in item {item.get('id')}"
            diff_counts[diff] = diff_counts.get(diff, 0) + 1

        assert diff_counts.get("CANONICAL") == 8, f"{cl}: expected 8 CANONICAL, got {diff_counts.get('CANONICAL')}"
        assert diff_counts.get("SLANG") == 4, f"{cl}: expected 4 SLANG, got {diff_counts.get('SLANG')}"
        assert diff_counts.get("BREAKDOWN") == 4, f"{cl}: expected 4 BREAKDOWN, got {diff_counts.get('BREAKDOWN')}"
        assert diff_counts.get("AMBIGUOUS") == 2, f"{cl}: expected 2 AMBIGUOUS, got {diff_counts.get('AMBIGUOUS')}"
        assert diff_counts.get("ABSTENTION") == 2, f"{cl}: expected 2 ABSTENTION, got {diff_counts.get('ABSTENTION')}"


def test_item_schema_and_types(benchmark_data):
    for item in benchmark_data:
        item_id = item.get("id")
        # Check required keys
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"Item {item_id} missing keys: {missing}"

        # Check types
        assert isinstance(item["id"], str) and re.match(r"^SE-\d{3}$", item["id"]), f"Invalid ID: {item_id}"
        assert item["cluster"] in EXPECTED_CLUSTERS
        assert item["difficulty"] in EXPECTED_DIFFICULTIES
        assert isinstance(item["query"], str) and len(item["query"].strip()) > 0, f"Empty query in {item_id}"
        assert item["expected_status"] in EXPECTED_STATUSES, f"Invalid expected_status in {item_id}"

        # Status specific validation
        if item["expected_status"] in ("RESOLVED", "RESOLVED_WITH_ANCHORS"):
            assert isinstance(item["expected_indicator_id"], int), f"Indicator ID must be int in {item_id}"
        elif item["expected_status"] == "ABSTAINED":
            assert item["expected_indicator_id"] is None or isinstance(item["expected_indicator_id"], int)
            assert item["expected_reason"] is not None, f"Abstained item {item_id} must have expected_reason"
        elif item["expected_status"] == "ALTERNATIVE_PROPOSED":
            assert len(item["expected_alternatives"]) > 0, f"Alternative item {item_id} must have expected_alternatives"

        assert isinstance(item["expected_facets"], dict), f"expected_facets must be dict in {item_id}"
        assert isinstance(item["expected_alternatives"], list), f"expected_alternatives must be list in {item_id}"


def test_cluster_4_income_disambiguation_coverage(benchmark_data):
    c4_items = [it for it in benchmark_data if it.get("cluster") == "C4_SALARIOS_E_INGRESOS"]
    assert len(c4_items) == 20

    # Ensure indicators 3337 (minimo), 128 (medio real), 3339 (laboral medio), 3345 (hogares pc) are present
    indicator_ids = {it["expected_indicator_id"] for it in c4_items if it["expected_indicator_id"] is not None}
    assert 3337 in indicator_ids, "C4 must include Salario mínimo real (3337)"
    assert 128 in indicator_ids, "C4 must include Salario medio real (128)"
    assert 3339 in indicator_ids, "C4 must include Ingreso laboral medio (3339)"
    assert 3345 in indicator_ids, "C4 must include Ingreso per cápita del hogar (3345)"

    # Check for context modifiers
    c4_queries_lower = [it["query"].lower() for it in c4_items]

    # minimum wage modifiers
    assert any(any(m in q for m in ["mínimo", "minimo", "básico", "basico", "de ley"]) for q in c4_queries_lower)
    # average wage modifiers
    assert any(any(m in q for m in ["medio", "promedio", "laburantes", "trabajadores"]) for q in c4_queries_lower)
    # household per capita modifiers
    assert any(any(m in q for m in ["hogar", "hogares", "familias", "por cabeza", "per cápita", "per capita"]) for q in c4_queries_lower)
    # breakdowns (sexo / area)
    assert any(any(m in q for m in ["campo", "rural", "mujeres", "hombres", "femenino", "masculino"]) for q in c4_queries_lower)
    # unmodified slang proposing alternatives
    c4_ambiguous = [it for it in c4_items if it["difficulty"] == "AMBIGUOUS"]
    assert len(c4_ambiguous) == 2
    for amb in c4_ambiguous:
        assert amb["expected_status"] == "ALTERNATIVE_PROPOSED"
        assert len(amb["expected_alternatives"]) >= 2
