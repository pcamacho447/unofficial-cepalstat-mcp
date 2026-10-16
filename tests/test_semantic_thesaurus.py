"""Tests for the Semantic Thesaurus architecture, Synsets, Antonyms, and Polarity models."""

import time
import pytest

from statscepal.semantic.thesaurus import (
    AntonymRule,
    ExpectedSign,
    PolarityResolution,
    PolarityType,
    Synset,
    Thesaurus,
)


def test_thesaurus_synset_registration_and_match():
    thesaurus = Thesaurus()
    thesaurus.register_synset(
        Synset(
            canonical_id="CANASTA_ALIMENTOS",
            domain="facet_canasta",
            canonical_term="alimentos y bebidas",
            synonyms=["alimentos", "comida", "morfi", "corrientazo", "carestia de comida"],
            regional_tags={"COL": ["corrientazo"], "ARG": ["morfi"]},
        )
    )

    # Direct match with slang
    match = thesaurus.match_synset("facet_canasta", "cual es el precio del morfi en argentina")
    assert match is not None
    assert match.canonical_id == "CANASTA_ALIMENTOS"
    assert match.matched_term == "morfi"

    # Substring collision protection: 'morfinas' must NOT match 'morfi'
    assert thesaurus.match_synset("facet_canasta", "gasto en morfinas en hospital") is None


def test_thesaurus_antonym_rule_registration_and_polarity():
    thesaurus = Thesaurus()
    thesaurus.register_antonym_rule(
        AntonymRule(
            rule_id="FISCAL_BALANCE_SIGN",
            positive_term="superavit",
            negative_term="deficit",
            polarity_type=PolarityType.ACCOUNTING_SIGN,
            canonical_indicator_id=1241,
            positive_sign=ExpectedSign.POSITIVE,
            negative_sign=ExpectedSign.NEGATIVE,
            explanation="El déficit y superávit corresponden al Balance Primario (1241) con signos opuestos.",
        )
    )

    # With accents in query
    pol = thesaurus.resolve_polarity("cual fue el déficit fiscal en chile 2022")
    assert pol is not None
    assert pol.polarity_type == PolarityType.ACCOUNTING_SIGN
    assert pol.term_detected == "deficit"
    assert pol.canonical_opposite == "superavit"
    assert pol.expected_sign == ExpectedSign.NEGATIVE
    assert pol.canonical_indicator_id == 1241


def test_thesaurus_latency_benchmark():
    thesaurus = Thesaurus()
    thesaurus.register_synset(
        Synset(
            canonical_id="CANASTA_ALIMENTOS",
            domain="facet_canasta",
            canonical_term="alimentos y bebidas",
            synonyms=["alimentos", "comida", "morfi", "corrientazo", "carestia de comida"],
            regional_tags={"COL": ["corrientazo"], "ARG": ["morfi"]},
        )
    )
    thesaurus.register_antonym_rule(
        AntonymRule(
            rule_id="FISCAL_BALANCE_SIGN",
            positive_term="superavit",
            negative_term="deficit",
            polarity_type=PolarityType.ACCOUNTING_SIGN,
            canonical_indicator_id=1241,
            positive_sign=ExpectedSign.POSITIVE,
            negative_sign=ExpectedSign.NEGATIVE,
        )
    )

    query = "cual fue el deficit fiscal en chile 2022 y el costo de morfi"
    times = []
    # Warmup
    for _ in range(100):
        thesaurus.match_synset("facet_canasta", query)
        thesaurus.resolve_polarity(query)

    for _ in range(500):
        t0 = time.perf_counter()
        thesaurus.match_synset("facet_canasta", query)
        thesaurus.resolve_polarity(query)
        times.append((time.perf_counter() - t0) * 1000.0)

    times.sort()
    p50 = times[len(times) // 2]
    # Local resolution latency must maintain p50 < 0.5 ms
    assert p50 < 0.5, f"p50 latency {p50:.4f} ms exceeded 0.5 ms target"


def test_default_thesaurus_regionalisms():
    from statscepal.semantic.thesaurus import get_default_thesaurus

    th = get_default_thesaurus()

    # Chilean slang
    assert th.match_synset("facet_canasta", "cual fue el precio de la bencina en chile").canonical_id == "CANASTA_COMBUSTIBLES"
    assert th.match_synset("concept_labor", "busco pega en santiago").canonical_id == "EMPLEO_GENERAL"

    # Argentine/Rioplatense slang
    assert th.match_synset("concept_income", "cuanta guita ganan los laburantes").canonical_id == "SALARIO_MEDIO"
    assert th.match_synset("facet_canasta", "precio de la nafta en buenos aires").canonical_id == "CANASTA_COMBUSTIBLES"

    # Mexican slang
    assert th.match_synset("concept_income", "subio la lana de la gente").canonical_id == "SLANG_INCOME_AMBIGUOUS"
    assert th.match_synset("concept_labor", "conseguir chamba en df").canonical_id == "EMPLEO_GENERAL"

    # Colombian slang
    assert th.match_synset("facet_canasta", "cuanto vale el corrientazo").canonical_id == "CANASTA_ALIMENTOS"
    assert th.match_synset("concept_labor", "duro camello en bogota").canonical_id == "EMPLEO_GENERAL"

    # Safeguards: 'porcelana' must NOT trigger 'lana', 'platanos' must NOT trigger 'plata', 'mediana' must not match
    assert th.match_synset("concept_income", "mercado de porcelana fina") is None
    assert th.match_synset("concept_income", "exportaciones de platanos y frutas") is None


def test_match_all_synsets_multi_facet():
    from statscepal.semantic.thesaurus import get_default_thesaurus

    th = get_default_thesaurus()
    matches = th.match_all_synsets("facet_canasta", "comprar comida y luego cargar bencina")
    assert len(matches) == 2
    canonical_ids = {m.canonical_id for m in matches}
    assert "CANASTA_ALIMENTOS" in canonical_ids
    assert "CANASTA_COMBUSTIBLES" in canonical_ids


def test_default_thesaurus_all_canonical_domains():
    from statscepal.semantic.thesaurus import get_default_thesaurus

    th = get_default_thesaurus()

    # facet_area
    assert th.match_synset("facet_area", "medicion en el campo y zona rural").canonical_id == "RURAL"
    assert th.match_synset("facet_area", "poblacion en ciudades y area urbana").canonical_id == "URBANO"
    assert th.match_synset("facet_area", "estimacion para todo el pais a nivel nacional").canonical_id == "NACIONAL"

    # facet_sexo
    assert th.match_synset("facet_sexo", "tasa de participacion de mujeres y chicas").canonical_id == "FEMENINO"
    assert th.match_synset("facet_sexo", "ingreso de los varones y chicos").canonical_id == "MASCULINO"
    assert th.match_synset("facet_sexo", "cifras para ambos sexos").canonical_id == "AMBOS_SEXOS"

    # facet_edad
    assert th.match_synset("facet_edad", "nutricion de ninos y ninas en la infancia").canonical_id == "INFANCIA"
    assert th.match_synset("facet_edad", "desempleo en jovenes y pibes de 15 a 24").canonical_id == "JUVENTUD"
    assert th.match_synset("facet_edad", "pensiones de adultos mayores y tercera edad").canonical_id == "ADULTOS_MAYORES"

    # facet_severidad
    assert th.match_synset("facet_severidad", "indicador de indigencia y miseria").canonical_id == "POBREZA_EXTREMA"
    assert th.match_synset("facet_severidad", "porcentaje de pobreza total").canonical_id == "POBREZA_TOTAL"

    # facet_formalidad
    assert th.match_synset("facet_formalidad", "trabajadores en negro y rebusque informal").canonical_id == "INFORMAL"
    assert th.match_synset("facet_formalidad", "asalariados en blanco con empleo formal").canonical_id == "FORMAL"

    # concept_macro
    assert th.match_synset("concept_macro", "tasa de crecimiento del producto interno bruto").canonical_id == "PIB_GENERAL"
    assert th.match_synset("concept_macro", "evolucion de la inflacion y costo de vida").canonical_id == "IPC_GENERAL"


def test_econometric_antonym_polarities():
    from statscepal.semantic.thesaurus import get_default_thesaurus, PolarityType, ExpectedSign

    th = get_default_thesaurus()

    # 1. State Inversion: Ocupación vs Desocupación
    pol_desemp = th.resolve_polarity("cual es la tasa de desempleo en colombia 2021")
    assert pol_desemp is not None
    assert pol_desemp.polarity_type == PolarityType.STATE_INVERSION
    assert pol_desemp.canonical_opposite in ["ocupacion", "empleo"]

    # 2. Accounting Sign: Superávit vs Déficit (Indicador 1241)
    pol_def = th.resolve_polarity("deficit primario como porcentaje del pib en brasil 2020")
    assert pol_def is not None
    assert pol_def.polarity_type == PolarityType.ACCOUNTING_SIGN
    assert pol_def.canonical_indicator_id == 1241
    assert pol_def.expected_sign == ExpectedSign.NEGATIVE

    pol_sup = th.resolve_polarity("superavit primario en uruguay 2019")
    assert pol_sup is not None
    assert pol_sup.polarity_type == PolarityType.ACCOUNTING_SIGN
    assert pol_sup.canonical_indicator_id == 1241
    assert pol_sup.expected_sign == ExpectedSign.POSITIVE

    # 3. Inclusion / Exclusion: LULUCF (5681 vs 5682)
    pol_sin_lulucf = th.resolve_polarity("emisiones brutas de gei sin lulucf en argentina")
    assert pol_sin_lulucf is not None
    assert pol_sin_lulucf.polarity_type == PolarityType.INCLUSION_EXCLUSION
    assert pol_sin_lulucf.canonical_indicator_id == 5682

    pol_con_lulucf = th.resolve_polarity("emisiones netas con lulucf en argentina")
    assert pol_con_lulucf is not None
    assert pol_con_lulucf.polarity_type == PolarityType.INCLUSION_EXCLUSION
    assert pol_con_lulucf.canonical_indicator_id == 5681

    # 4. Current Account Sign (1243)
    pol_ca = th.resolve_polarity("deficit en cuenta corriente en peru")
    assert pol_ca is not None
    assert pol_ca.polarity_type == PolarityType.ACCOUNTING_SIGN
    assert pol_ca.canonical_indicator_id == 1243
    assert pol_ca.expected_sign == ExpectedSign.NEGATIVE

    # 5. Facet Complements (Formalidad y Área)
    pol_formal = th.resolve_polarity("tasa de empleo formal en ecuador")
    assert pol_formal is not None
    assert pol_formal.polarity_type == PolarityType.FACET_COMPLEMENT

    pol_rural = th.resolve_polarity("pobreza en zona rural de bolivia")
    assert pol_rural is not None
    assert pol_rural.polarity_type == PolarityType.FACET_COMPLEMENT


def test_semantic_resolution_response_polarity_field():
    from statscepal.semantic.models import SemanticResolutionResponse, ResolutionStatus
    from statscepal.semantic.thesaurus import PolarityResolution, PolarityType

    resp = SemanticResolutionResponse(
        status=ResolutionStatus.RESOLVED,
        query="test query",
        polarity_info=PolarityResolution(
            polarity_type=PolarityType.STATE_INVERSION,
            term_detected="desempleo",
            canonical_opposite="ocupacion",
        ),
    )
    assert resp.polarity_info is not None
    assert resp.polarity_info.polarity_type == PolarityType.STATE_INVERSION


def test_default_thesaurus_latency_benchmark():
    from statscepal.semantic.thesaurus import get_default_thesaurus

    th = get_default_thesaurus()
    query = "deficit primario como porcentaje del pib en brasil 2020 y empleo informal en zona rural"
    times = []
    # Warmup
    for _ in range(100):
        th.match_synset("facet_area", query)
        th.resolve_polarity(query)

    for _ in range(500):
        t0 = time.perf_counter()
        th.match_synset("facet_area", query)
        th.resolve_polarity(query)
        times.append((time.perf_counter() - t0) * 1000.0)

    times.sort()
    p50 = times[len(times) // 2]
    assert p50 < 0.5, f"Default thesaurus p50 latency {p50:.4f} ms exceeded 0.5 ms target"


def test_end_to_end_synonyms_and_antonyms_queries():
    from statscepal.catalog.store import CatalogStore
    from statscepal.semantic.registry import SemanticRegistry
    from statscepal.semantic.engine import SemanticResolutionEngine
    from statscepal.semantic.models import ResolutionStatus

    store = CatalogStore()
    registry = SemanticRegistry(store=store)
    engine = SemanticResolutionEngine(registry=registry)

    # Chilean fuels slang
    res_bencina = engine.resolve_query("cual fue el aumento en bencina en chile 2022")
    assert res_bencina.status == ResolutionStatus.RESOLVED
    assert res_bencina.selected_candidate.indicator_id == 2930

    # Argentine fuels slang
    res_nafta = engine.resolve_query("inflacion de la nafta en argentina 2022")
    assert res_nafta.status == ResolutionStatus.RESOLVED
    assert res_nafta.selected_candidate.indicator_id == 2930

    # Fiscal deficit polarity
    res_def = engine.resolve_query("cual fue el deficit primario en chile 2022")
    assert res_def.status == ResolutionStatus.RESOLVED
    assert res_def.selected_candidate.indicator_id == 1241
    assert res_def.polarity_info is not None
    assert res_def.polarity_info.expected_sign.value == "NEGATIVE"

    # LULUCF exclusion
    res_sin_lulucf = engine.resolve_query("emisiones sin lulucf en colombia 2020")
    assert res_sin_lulucf.status == ResolutionStatus.RESOLVED
    assert res_sin_lulucf.selected_candidate.indicator_id == 5682


