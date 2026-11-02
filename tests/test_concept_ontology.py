"""Tests for Declarative Concept Models & Ontology Engine (concept_ontology.py)."""

from __future__ import annotations

import time

import pytest

from unofficial_cepalstat_mcp.semantic.concept_ontology import (
    DEFAULT_CONCEPT_DEFINITIONS,
    DEFAULT_CONCEPT_ONTOLOGY,
    ConceptDefinition,
    ConceptMatchResult,
    ConceptOntology,
    ConceptTriggerRule,
    SubConceptRule,
)


def test_concept_models_validation() -> None:
    """Verify frozen models, defaults, and validation."""
    rule = ConceptTriggerRule(patterns=("pib", "producto interno bruto"))
    assert rule.patterns == ("pib", "producto interno bruto")
    assert rule.is_regex is False
    assert rule.exact_word_boundary is True
    assert rule.ambiguous_candidate is None
    assert rule.requires_subterms == ()
    assert rule.excludes_subterms == ()

    sub = SubConceptRule(
        sub_concept_key="PIB_PER_CAPITA",
        triggers=("per capita", "por habitante"),
        facet_updates={"unidad": "PER_CAPITA"},
    )
    assert sub.sub_concept_key == "PIB_PER_CAPITA"
    assert sub.facet_updates == {"unidad": "PER_CAPITA"}
    assert sub.is_ambiguous is False

    cdef = ConceptDefinition(
        concept_key="PIB",
        description="Gross Domestic Product",
        domain="macro",
        priority=100,
        default_indicator_id=2204,
        triggers=(rule,),
        sub_concept_rules=(sub,),
    )
    assert cdef.concept_key == "PIB"
    assert cdef.priority == 100
    assert cdef.default_indicator_id == 2204

    # Test immutability
    with pytest.raises(Exception):
        cdef.priority = 200  # type: ignore[misc]

    res = ConceptMatchResult(
        concept_key="PIB",
        matched_phrase="pib",
        consumed_phrases=["pib"],
    )
    assert res.concept_key == "PIB"
    assert res.is_ambiguous_measure is False

    assert len(DEFAULT_CONCEPT_DEFINITIONS) >= 22
    assert "PIB" in DEFAULT_CONCEPT_ONTOLOGY


def test_major_concept_classifications() -> None:
    """Verify all major socioeconomic concepts resolve correctly."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    cases = [
        # Macro
        ("pib de chile", "PIB"),
        ("producto interno bruto en uruguay", "PIB"),
        # Pobreza
        ("pobreza en argentina", "POBREZA"),
        ("miseria extrema en bolivia", "POBREZA"),
        # Laboral
        ("desempleo en uruguay", "EMPLEO"),
        ("tasa de desocupacion en brasil", "EMPLEO"),
        # Desigualdad
        ("coeficiente de gini en panama", "GINI"),
        ("distribucion del ingreso en paraguay", "DISTRIBUCION_INGRESO"),
        # Precios
        ("inflacion en mexico", "IPC_GENERAL"),
        ("ipc subyacente en costa rica", "IPC_SUBYACENTE"),
        ("alimentos y bebidas en ecuador", "IPC_ALIMENTOS"),
        # Fiscal
        ("deuda publica en argentina", "DEUDA_PUBLICA"),
        ("balance primario fiscal en chile", "BALANCE_PRIMARIO"),
        ("recaudacion tributaria en colombia", "INGRESOS_TRIBUTARIOS"),
        ("gasto social en peru", "GASTO_SOCIAL"),
        ("gasto publico en educacion en honduras", "GASTO_EDUCACION"),
        # Externo
        ("balanza comercial de paraguay", "BALANZA_COMERCIAL"),
        ("cuenta corriente de paraguay", "CUENTA_CORRIENTE"),
        ("inversion extranjera directa en brasil", "INVERSION_EXTRANJERA_DIRECTA"),
        ("terminos de intercambio comercial", "TERMINOS_INTERCAMBIO"),
        # Ambiental
        ("emisiones de gases de efecto invernadero", "EMISIONES_GEI_LULUCF"),
        ("energia limpia y renovable", "ENERGIA_RENOVABLE"),
        ("extraccion de agua dulce", "AGUA_DULCE"),
        # Demografía
        ("poblacion total del pais", "POBLACION"),
    ]

    for query, expected_concept in cases:
        result = ontology.extract_concept(query)
        assert result is not None, f"Expected concept {expected_concept} for '{query}', got None"
        assert result.concept_key == expected_concept, f"Query '{query}': expected {expected_concept}, got {result.concept_key}"


def test_priority_resolution_fiscal_over_macro() -> None:
    """Verify fiscal, external, and educational queries containing 'PIB' are not shadowed."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    cases = [
        ("deuda publica como porcentaje del pib en brasil", "DEUDA_PUBLICA"),
        ("deuda soberana como % del pbi", "DEUDA_PUBLICA"),
        ("balance primario sobre el pib de colombia", "BALANCE_PRIMARIO"),
        ("deficit primario % pib", "BALANCE_PRIMARIO"),
        ("ingresos tributarios como % del pib", "INGRESOS_TRIBUTARIOS"),
        ("carga tributaria como porcentaje del pib", "INGRESOS_TRIBUTARIOS"),
        ("presion fiscal % del pib", "INGRESOS_TRIBUTARIOS"),
        ("gasto publico en educacion como porcentaje del pib", "GASTO_EDUCACION"),
        ("gasto social % pib", "GASTO_SOCIAL"),
        ("deficit en cuenta corriente como porcentaje del pib", "CUENTA_CORRIENTE"),
    ]

    for query, expected_concept in cases:
        result = ontology.extract_concept(query)
        assert result is not None, f"Query '{query}' returned None"
        assert result.concept_key == expected_concept, f"Priority failure for '{query}': expected {expected_concept}, got {result.concept_key}"


def test_sub_concept_resolution() -> None:
    """Verify sub-concept specialization based on qualifying sub-phrases."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    cases = [
        ("ingresos tributarios en moneda nacional", "INGRESOS_TRIBUTARIOS_CORRIENTES"),
        ("ingresos tributarios a precios corrientes", "INGRESOS_TRIBUTARIOS_CORRIENTES"),
        ("ingresos tributarios", "INGRESOS_TRIBUTARIOS"),
        ("emisiones sin lulucf", "EMISIONES_GEI_SIN_LULUCF"),
        ("emisiones de gei excluyendo utcuts", "EMISIONES_GEI_SIN_LULUCF"),
        ("emisiones de gei", "EMISIONES_GEI_LULUCF"),
        ("salario minimo en colombia", "SALARIO_MINIMO"),
        ("sueldo basico de ley", "SALARIO_MINIMO"),
        ("pib per capita en uruguay", "PIB_PER_CAPITA"),
        ("pbi por habitante en peru", "PIB_PER_CAPITA"),
        ("pib trimestral en mexico", "PIB_TRIMESTRAL"),
        ("crecimiento interanual trimestral", "PIB_TRIMESTRAL"),
        ("brecha de pobreza en chile", "POBREZA_BRECHA"),
        ("cuenta corriente de costa rica", "CUENTA_CORRIENTE_740"),
    ]

    for query, expected_concept in cases:
        result = ontology.extract_concept(query)
        assert result is not None, f"Query '{query}' returned None"
        assert result.concept_key == expected_concept, f"Sub-concept failure for '{query}': expected {expected_concept}, got {result.concept_key}"


def test_controlled_ambiguities() -> None:
    """Verify vague phrases flag is_ambiguous_measure and exact candidate tag."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    cases = [
        ("actividad economica en ecuador", "PIB", "ECONOMIC_ACTIVITY"),
        ("economia de panama", "PIB", "MACRO_ECONOMY"),
        ("situacion laboral en chile", "EMPLEO", "LABOR_SITUATION"),
        ("cuentas fiscales de bolivia", "DEUDA_PUBLICA", "FISCAL_ACCOUNTS"),
        ("privacion y pobreza", "POBREZA", "PRIVATION_GAP"),
        ("sector externo en colombia", "CUENTA_CORRIENTE", "EXTERNAL_SECTOR"),
        ("inflacion sectorial", "IPC_GENERAL", "SECTORAL_INFLATION"),
    ]

    for query, expected_concept, expected_candidate in cases:
        result = ontology.extract_concept(query)
        assert result is not None, f"Query '{query}' returned None"
        assert result.concept_key == expected_concept
        assert result.is_ambiguous_measure is True, f"Query '{query}' should be ambiguous"
        assert result.ambiguous_candidate == expected_candidate, f"Query '{query}': expected {expected_candidate}, got {result.ambiguous_candidate}"


def test_regionalisms_and_slang() -> None:
    """Verify Latin American regionalisms and colloquialisms resolve correctly."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    cases = [
        ("pbi del peru", "PIB"),
        ("producto bruto interno de argentina", "PIB"),
        ("chamba en mexico", "EMPLEO"),
        ("sin pega en santiago", "EMPLEO"),
        ("sin laburo en buenos aires", "EMPLEO"),
        ("guita de los laburantes", "SALARIO_REAL"),
        ("plata de los asalariados", "SALARIO_REAL"),
        ("morfi en buenos aires", "IPC_ALIMENTOS"),
        ("corrientazo en bogota", "IPC_ALIMENTOS"),
        ("carestia de la comida", "IPC_ALIMENTOS"),
        ("presion fiscal en brasil", "INGRESOS_TRIBUTARIOS"),
        ("enchufes y luz verde", "ENERGIA_RENOVABLE"),
    ]

    for query, expected_concept in cases:
        result = ontology.extract_concept(query)
        assert result is not None, f"Query '{query}' returned None"
        assert result.concept_key == expected_concept, f"Regionalism failure for '{query}': expected {expected_concept}, got {result.concept_key}"


def test_demographic_and_gender_invariants() -> None:
    """Verify gender ratio and demographic query invariants."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    r_brecha = ontology.extract_concept("brecha salarial entre hombres y mujeres")
    assert r_brecha is not None
    assert r_brecha.concept_key == "BRECHA_SALARIAL"

    r_genero = ontology.extract_concept("brecha de genero en chile")
    assert r_genero is not None
    assert r_genero.concept_key == "BRECHA_SALARIAL"

    r_pob_quintil = ontology.extract_concept("poblacion por quintil de ingreso")
    assert r_pob_quintil is not None
    assert r_pob_quintil.concept_key == "POBLACION"


def test_resolution_latency_benchmark() -> None:
    """Verify 1,000 extractions execute with avg latency < 0.05 ms (< 50 microseconds)."""
    ontology = DEFAULT_CONCEPT_ONTOLOGY

    benchmark_queries = [
        "deuda publica como % del pib",
        "tasa de desocupacion juvenil en uruguay",
        "ingresos tributarios en moneda nacional",
        "pobreza extrema y carestia de comida",
        "pbi per capita del peru en 2022",
        "emisiones de gases de efecto invernadero sin lulucf",
        "actividad economica en ecuador",
        "inflacion de alimentos interanual",
        "gasto publico en educacion",
        "balanza comercial y cuenta corriente",
    ] * 100  # 1,000 queries

    start = time.perf_counter()
    for q in benchmark_queries:
        res = ontology.extract_concept(q)
        assert res is not None
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / len(benchmark_queries)) * 1000.0
    print(f"\n[BENCHMARK] 1,000 extractions completed in {elapsed*1000:.2f} ms ({avg_ms:.4f} ms/query)")
    assert avg_ms < 0.05, f"Latency benchmark exceeded budget: {avg_ms:.4f} ms > 0.05 ms"


def test_custom_ontology_override() -> None:
    """Verify ConceptOntology can be configured with custom definitions."""
    custom_def = ConceptDefinition(
        concept_key="CUSTOM_CONCEPT",
        description="A custom concept",
        domain="custom",
        priority=999,
        triggers=(
            ConceptTriggerRule(patterns=("mi concepto personalizado",)),
        ),
    )
    custom_ontology = ConceptOntology(definitions=[custom_def])
    assert "CUSTOM_CONCEPT" in custom_ontology
    assert len(custom_ontology) == 1

    result = custom_ontology.extract_concept("analisis de mi concepto personalizado en 2023")
    assert result is not None
    assert result.concept_key == "CUSTOM_CONCEPT"
    assert result.matched_phrase == "mi concepto personalizado"
