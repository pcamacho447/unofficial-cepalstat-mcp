import json
import pytest
from statscepal.catalog.store import CatalogStore
from statscepal.cli import main
from statscepal.dimensions import Dimension, Member
from statscepal.semantic.facet_ontology import (
    DEFAULT_FACET_ONTOLOGY,
    FacetOntology,
    get_default_facet_ontology,
)
from statscepal.semantic.matcher import (
    DIMENSION_KEY_PATTERNS,
    MEMBER_VALUE_PATTERNS,
    DynamicMemberMatcher,
)


def test_default_facet_ontology_covers_core_facets():
    ontology = get_default_facet_ontology()
    expected_keys = {
        "sexo",
        "area",
        "edad",
        "etnia",
        "estrato",
        "quintil",
        "educacion",
        "formalidad",
        "severidad",
        "canasta",
        "rubro",
        "moneda",
        "actividad",
    }
    registered_keys = {f.facet_key for f in ontology.all_facets()}
    assert expected_keys.issubset(registered_keys)


def test_facet_ontology_implicit_aggregate_vs_critical_breakdown():
    ontology = DEFAULT_FACET_ONTOLOGY
    # Implicit national/total defaults do NOT force a breakdown swap if canonical indicator is aggregate
    assert not ontology.is_critical_unhandled_facet("area", "NACIONAL")
    assert not ontology.is_critical_unhandled_facet("severidad", "POBREZA_TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "TOTAL")
    assert not ontology.is_critical_unhandled_facet("sexo", "AMBOS_SEXOS")

    # Explicit breakdown values DO require the dimension (including ETNICO_TOTAL and QUINTIL)
    assert ontology.is_critical_unhandled_facet("etnia", "ETNICO_TOTAL")
    assert ontology.is_critical_unhandled_facet("etnia", "INDIGENA")
    assert ontology.is_critical_unhandled_facet("area", "RURAL")
    assert ontology.is_critical_unhandled_facet("sexo", "FEMENINO")
    assert ontology.is_critical_unhandled_facet("edad", "INFANCIA")
    assert ontology.is_critical_unhandled_facet("estrato", "QUINTIL")
    assert ontology.is_critical_unhandled_facet("educacion", "UNIVERSITARIA")


def test_facet_ontology_dimension_classification():
    ontology = DEFAULT_FACET_ONTOLOGY
    assert ontology.classify_dimension(208, "País__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(29117, "Años__ESTANDAR") == "__structural__"
    assert ontology.classify_dimension(144, "Sexo__ESTANDAR") == "sexo"
    assert ontology.classify_dimension(326, "Área geográfica") == "area"
    assert ontology.classify_dimension(43039, "Tipo de etnia") == "etnia"
    assert ontology.classify_dimension(999999, "Dimensión desconocida xyz") is None


def test_matcher_derives_patterns_from_ontology_and_matches_by_dim_id():
    # 1. Asserts DIMENSION_KEY_PATTERNS and MEMBER_VALUE_PATTERNS contain expected facets and members
    expected_facet_keys = {"sexo", "area", "edad", "etnia", "quintil", "moneda", "severidad"}
    assert expected_facet_keys.issubset(set(DIMENSION_KEY_PATTERNS.keys()))

    expected_member_keys = {"FEMENINO", "MASCULINO", "RURAL", "URBANO", "INDIGENA", "AFRODESCENDIENTE", "POBREZA_EXTREMA"}
    assert expected_member_keys.issubset(set(MEMBER_VALUE_PATTERNS.keys()))

    # 2. Check matcher has ontology attribute
    matcher = DynamicMemberMatcher()
    assert matcher.ontology is DEFAULT_FACET_ONTOLOGY

    # Also test custom ontology injection
    custom_matcher = DynamicMemberMatcher(ontology=DEFAULT_FACET_ONTOLOGY)
    assert custom_matcher.ontology is DEFAULT_FACET_ONTOLOGY

    # 3. Tests matching against a dimension that has a non-standard name
    # ("Clasificación oficial CEPAL 43039") but matches known_dimension_ids (43039),
    # verifying that it is placed in Group A and successfully matches member 43041: Indígena.
    dim_non_standard = Dimension(
        id=43039,
        name="Clasificación oficial CEPAL 43039",
        members=[
            Member(id=43041, name="Indígena"),
            Member(id=43042, name="No indígena"),
        ],
    )
    dim_noise = Dimension(
        id=9999,
        name="Variable genérica no relacionada",
        members=[Member(id=1, name="Total")],
    )

    matched, filters, unhandled = matcher.match_facets_to_dimensions(
        indicator_id=3328,
        dimensions=[dim_non_standard, dim_noise],
        facets={"etnia": "INDIGENA"},
    )

    assert matched is True
    assert len(filters) == 1
    assert filters[0].dim_id == 43039
    assert filters[0].member_id == 43041
    assert filters[0].member_name == "Indígena"
    assert len(unhandled) == 0

    # Also verify with low-scoring member (score < 60) which would fail in Group B fallback (min_score=60)
    dim_partial = Dimension(
        id=43039,
        name="Clasificación oficial CEPAL 43039",
        members=[
            Member(id=43050, name="originario"),  # score 37 < 60
        ],
    )
    matched_p, filters_p, unhandled_p = matcher.match_facets_to_dimensions(
        indicator_id=3328,
        dimensions=[dim_partial],
        facets={"etnia": "INDIGENA"},
    )
    assert matched_p is True
    assert len(filters_p) == 1
    assert filters_p[0].member_id == 43050


def test_store_and_ontology_facet_audit(tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "audit_test.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    store.store_indicator_dimensions(
        3328,
        [
            Dimension(id=208, name="País__ESTANDAR", members=[Member(id=1, name="Chile")]),
            Dimension(id=326, name="Área geográfica", members=[Member(id=2, name="Urbana")]),
            Dimension(id=88888, name="Variable Experimental No Mapeada", members=[Member(id=3, name="X")]),
        ],
    )

    distinct_dims = store.get_distinct_harvested_dimensions()
    assert len(distinct_dims) == 3

    report = DEFAULT_FACET_ONTOLOGY.audit_dimensions(distinct_dims)
    assert report.total_distinct_dimensions == 3
    assert len(report.structural_dimensions) == 1
    assert "area" in report.mapped_dimensions
    assert len(report.unmapped_dimensions) == 1
    assert report.unmapped_dimensions[0]["dim_id"] == 88888

    # Test CLI invocation
    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: CatalogStore(db_path=db_path))
    exit_code = main(["catalog", "facet-audit"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "CEPALSTAT Facet Ontology Audit" in out
    assert "area" in out
    assert "Variable Experimental No Mapeada" in out


def test_cli_facet_audit_json(tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "audit_json_test.db"
    store = CatalogStore(db_path=db_path)
    store.init_tables()
    store.init_semantic_tables()

    store.store_indicator_dimensions(
        3328,
        [
            Dimension(id=208, name="País__ESTANDAR", members=[Member(id=1, name="Chile")]),
            Dimension(id=144, name="Sexo__ESTANDAR", members=[Member(id=2, name="Mujeres")]),
            Dimension(id=99999, name="Unclassified Dim", members=[Member(id=3, name="Val")]),
        ],
    )

    monkeypatch.setattr("statscepal.cli.CatalogStore", lambda: CatalogStore(db_path=db_path))
    exit_code = main(["catalog", "facet-audit", "--json"])
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["total_distinct_dimensions"] == 3
    assert len(data["structural_dimensions"]) == 1
    assert "sexo" in data["mapped_dimensions"]
    assert len(data["unmapped_dimensions"]) == 1
    assert data["unmapped_dimensions"][0]["dim_id"] == 99999
    assert 0.0 < data["coverage_ratio"] <= 1.0


