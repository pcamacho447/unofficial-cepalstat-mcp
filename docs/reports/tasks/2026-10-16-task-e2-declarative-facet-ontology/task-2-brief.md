# Task 2 Brief: Wire DynamicMemberMatcher to FacetOntology

## Context
- Working Directory: `C:\papx\statscepal`
- Base Commit: `2997146`
- Plan: `docs/superpowers/plans/2026-10-16-task-e2-declarative-facet-ontology-plan.md`

## Objectives
1. Modify `src/statscepal/semantic/matcher.py`:
   - Import `DEFAULT_FACET_ONTOLOGY`, `FacetOntology`, and `strip_accents` from `statscepal.semantic.facet_ontology`.
   - Derive module-level `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` from `DEFAULT_FACET_ONTOLOGY` (keeping them as module-level exports for backwards compatibility with any existing callers).
   - In `DynamicMemberMatcher.__init__(self, ontology: FacetOntology | None = None)`:
     - Store `self.ontology = ontology or DEFAULT_FACET_ONTOLOGY`.
   - In `DynamicMemberMatcher.match_facets_to_dimensions(self, indicator_id, dimensions, facets)`:
     - For each `(facet_key, facet_val)` in `facets.items()`:
       - Look up `facet_def = self.ontology.get_facet(facet_key)`.
       - When partitioning candidate dimensions into `candidate_dims_a` vs `candidate_dims_b`:
         - If `facet_def` exists, place dimension `d` into `candidate_dims_a` if `d.id in facet_def.known_dimension_ids` OR if any `kp` in `key_patterns` matches `strip_accents(d.name)`.
         - Otherwise use default name-pattern matching.
2. Follow strict TDD:
   - In `tests/test_semantic_facet_ontology.py`:
     - Add `test_matcher_derives_patterns_from_ontology_and_matches_by_dim_id`:
       - Asserts `DIMENSION_KEY_PATTERNS` and `MEMBER_VALUE_PATTERNS` contain expected facets and members.
       - Tests matching against a dimension that has a non-standard name (e.g. `"Clasificación oficial CEPAL 43039"`) but matches `known_dimension_ids` (`43039`), verifying that it is placed in Group A and successfully matches member `43041: Indígena`.
   - Run red test: `uv run pytest tests/test_semantic_facet_ontology.py -k test_matcher`
   - Implement changes in `src/statscepal/semantic/matcher.py`.
   - Run green test: `uv run pytest tests/test_semantic_facet_ontology.py`
   - Run benchmark and full non-integration test suite:
     - `uv run pytest tests/test_semantic_benchmark_200.py -v`
     - `uv run pytest -m "not integration"`
3. Commit:
   `git add src/statscepal/semantic/matcher.py tests/test_semantic_facet_ontology.py`
   `git commit -m "refactor(semantic): drive DynamicMemberMatcher from declarative FacetOntology"`
4. Write report to `.superpowers/sdd/2026-10-16-task-e2-declarative-facet-ontology/task-2-report.md`.
