# Task 2 Report: Wire DynamicMemberMatcher to FacetOntology

## Summary
- **Task**: Wire `DynamicMemberMatcher` to declarative `FacetOntology`.
- **Status**: DONE
- **Commit**: `27dada98885a37a57409c1f598b9d0061969d9e3`
- **Engineer**: Amelia (Senior Developer)

## Changes Implemented
1. **Derived Patterns from `DEFAULT_FACET_ONTOLOGY` in `src/statscepal/semantic/matcher.py`**:
   - Imported `DEFAULT_FACET_ONTOLOGY`, `FacetOntology`, and `strip_accents` from `statscepal.semantic.facet_ontology`.
   - Populated module-level `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` directly from `DEFAULT_FACET_ONTOLOGY.build_dimension_key_patterns()` and `DEFAULT_FACET_ONTOLOGY.build_member_value_patterns()`, maintaining full backwards compatibility for any external callers.
2. **Upgraded `DynamicMemberMatcher`**:
   - Added `__init__(self, ontology: FacetOntology | None = None)` supporting ontology dependency injection and defaulting to `DEFAULT_FACET_ONTOLOGY`.
   - Updated `match_facets_to_dimensions` to look up `facet_def = self.ontology.get_facet(facet_key)`.
   - Upgraded candidate dimension partitioning: dimensions are placed into Group A (`candidate_dims_a`) if `d.id in facet_def.known_dimension_ids` OR if any key pattern matches `strip_accents(d.name)`.
3. **Comprehensive TDD Test Added in `tests/test_semantic_facet_ontology.py`**:
   - `test_matcher_derives_patterns_from_ontology_and_matches_by_dim_id`:
     - Verifies `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` contain expected core facets and members.
     - Verifies `DynamicMemberMatcher` stores `ontology` and supports custom ontology injection.
     - Tests matching against a dimension that has a non-standard name (`"Clasificación oficial CEPAL 43039"`) but matches `known_dimension_ids` (`43039`), verifying that it is placed in Group A and successfully matches member `43041: Indígena`.
     - Tests low-scoring member matching (score < 60) that would fail under Group B fallback (`min_score=60`), proving placement into Group A.

## Verification & Invariants
- **TDD Red Phase**: `uv run pytest tests/test_semantic_facet_ontology.py -k test_matcher` failed with `AttributeError: 'DynamicMemberMatcher' object has no attribute 'ontology'`.
- **TDD Green Phase**: `uv run pytest tests/test_semantic_facet_ontology.py` passed (4/4 passed).
- **200-Case Benchmark**: `uv run pytest tests/test_semantic_benchmark_200.py -v` passed (100% Top-1 accuracy, 0.00% False Substitution Rate across all 10 thematic clusters).
- **Full Non-Integration Suite**: `uv run pytest -m "not integration"` passed (250 passed, 3 deselected in 32.71s).
- **Offline Hermeticity**: 100% preserved; no external network calls made.
