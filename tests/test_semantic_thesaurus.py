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
