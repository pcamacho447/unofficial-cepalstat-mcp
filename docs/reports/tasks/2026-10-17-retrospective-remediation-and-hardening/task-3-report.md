# Task 3 Report: Seed Official Dimensions for Vertical Slice Indicators & Safeguard Dimension Breakdowns in Fetcher (`AI-4`)

**Implementer:** Amelia, Senior Developer  
**Plan:** `docs/superpowers/plans/2026-10-17-retrospective-remediation-and-hardening-plan.md`  
**Base Commit:** `c9b5f90`  
**Task 3 Commit:** `403bc8b` (`feat(semantic): seed dimensions for vertical slice indicators and preserve explicit breakdown dimensions`)  
**Date:** 2026-10-17  

---

## 1. Executive Summary

Task 3 implements retrospective remediation item `AI-4` to complete dimension coverage across all vertical slice indicators and ensure breakdown series are preserved during data retrieval:

1. **Seeding Official Dimensions (`registry.py`):**
   Prior to Task 3, 10 indicators in `VERTICAL_SLICE_INDICATORS` that declared non-empty `supported_facets` lacked corresponding entries in `DEFAULT_OFFICIAL_DIMENSIONS` (`127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333`). Dimension definitions were added for all 10 indicators, ensuring structural parity and shared dimension ID consistency (e.g. `Sexo__ESTANDAR` id=144, `Área geográfica` id=326, `Grupo de edad` id=43054, `Canasta de bienes` id=79565, `Rubro` id=29281).
2. **Dimension Safeguard in Fetcher (`fetcher.py`):**
   In `SemanticDataFetcher._filter_unconstrained_dimensions`, columns not listed in `filtered_dim_cols` were previously collapsed to their aggregate/total member (e.g. "Total" or "Nacional"). When an indicator lacked dimensions in `DEFAULT_OFFICIAL_DIMENSIONS`, queries requesting breakdowns (such as `sexo: SEXO_DESGLOSE` on indicator 127) would result in `filtered_dim_cols` being empty, collapsing all breakdown series to the aggregate row. `_filter_unconstrained_dimensions` and `fetch_resolved_data` now identify explicit breakdown facets (`_DESGLOSE`, `ETNICO_TOTAL`, `ETNICO`), prevent collapsing those dimension columns, normalize alternative value column aliases (`valor`, `monto`, `val`, `dato`), and preserve multi-member series in the final payload.
3. **Handling Dimensionless Supported Facets (`engine.py`):**
   In CEPALSTAT, certain indicators declare conceptual support for facets at the indicator level without offering a physical dimension in the API (e.g. indicator 127 declares `formalidad`, indicator 340 declares `edad`). With dimensions seeded, Stage 4 dimensional gating previously flagged these facets in `unhandled_facets`, triggering erroneous abstentions on valid queries (e.g. `SE-044`, `SE-045`, `FC-024`). `SemanticResolutionEngine._has_dimension_for_facet` was introduced: when an indicator explicitly supports a facet conceptually but lacks a physical dimension for it, the engine recognizes it as a supported dimensionless facet and does not abstain.
4. **Member Enrichment & Synthetic Member Registration (`registry.py`):**
   Indicator 365 (`Rubro`) was enriched with `Member(id=29283, name="Salud")` to satisfy CPI health queries (`SE-033`), and synthetic IDs `29282, 29283` were registered in `SYNTHETIC_DIMENSION_MEMBER_IDS`.

All changes were developed under strict TDD. All 310 non-integration tests pass, the 200-question benchmark achieves 100.0% Top-1 Accuracy and 0.00% False Substitution Rate, and the legacy 50-case benchmark and facet coverage suites are 100% green.

---

## 2. Changes Implemented

### A. Seeded `DEFAULT_OFFICIAL_DIMENSIONS` in `src/statscepal/semantic/registry.py`
- Added official dimension and member definitions for the 10 indicators:
  - **127 (Desocupación por sexo):** `Sexo__ESTANDAR` (`id=144`, members: `146 Ambos sexos, 265 Hombres, 266 Mujeres`).
  - **3331 (Desempleo juvenil 15-24 años):** `Sexo__ESTANDAR` (`id=144`), `Grupo de edad` (`id=43054`, member: `43058 15 a 24 años`).
  - **3337 (Salario mínimo real):** `Área geográfica` (`id=326`, members: `327 Nacional, 330 Urbano, 331 Rural`).
  - **5097 (Desempleo sexo y edad CIET-19):** `Sexo__ESTANDAR` (`id=144`), `Grupo de edad` (`id=43054`, members: `43059, 43058, 43060`).
  - **119 (Desocupación urbana por sexo):** `Sexo__ESTANDAR` (`id=144`), `Área geográfica` (`id=326`).
  - **340 (Salario mínimo real base 2018):** `Área geográfica` (`id=326`).
  - **365 (IPC general):** `Rubro` (`id=29281`, members: `29282 General, 29283 Salud`).
  - **1684 (IPC alimentos y bebidas):** `Canasta de bienes` (`id=79565`, member: `79578 Alimentos y bebidas no alcohólicas`).
  - **3344 (Desocupación por sexo y edad):** `Sexo__ESTANDAR` (`id=144`), `Grupo de edad` (`id=43054`).
  - **3333 (Desempleo):** `Sexo__ESTANDAR` (`id=144`).
- Registered `29282, 29283` in `SYNTHETIC_DIMENSION_MEMBER_IDS`.

### B. Safeguarded Breakdown Dimensions in `src/statscepal/semantic/fetcher.py`
- Updated `_filter_unconstrained_dimensions` to receive `response` and `breakdown_facets`:
  ```python
  facet_keys_in_breakdown: set[str] = set()
  if response is not None and getattr(response, "applied_filters", None):
      facet_keys_in_breakdown = {
          f_k.lower()
          for f_k, f_v in getattr(response.applied_filters, "facets", {}).items()
          if "_DESGLOSE" in str(f_v) or str(f_v) in ("ETNICO_TOTAL", "ETNICO")
      }
  if breakdown_facets is not None:
      facet_keys_in_breakdown |= {bk.lower() for bk in breakdown_facets}

  for col in list(result.columns):
      ...
      if any(bk in cl for bk in facet_keys_in_breakdown):
          # Explicit breakdown requested -> do not collapse to aggregate
          continue
  ```
- Updated `fetch_resolved_data` to detect `has_breakdown` from `applied_filters.facets`, normalize value column variations (`valor`, `monto`, `val`, `dato`), pass `breakdown_facets` into `_filter_unconstrained_dimensions`, and dynamically append breakdown dimension columns into `breakdown_cols` for series construction.

### C. Dimensionless Supported Facets Architecture in `src/statscepal/semantic/engine.py`
- Added `_has_dimension_for_facet(dims, facet_key)`:
  ```python
  def _has_dimension_for_facet(self, dims: list[Dimension], facet_key: str) -> bool:
      """Check whether any of the indicator's dimensions physically corresponds to facet_key."""
      facet_def = self.ontology.get_facet(facet_key)
      key_norm = strip_accents(facet_key)
      if facet_def and facet_def.dimension_name_patterns:
          key_patterns = list(facet_def.dimension_name_patterns)
      else:
          key_patterns = [key_norm]

      for d in dims:
          if self.ontology.classify_dimension(d.id, d.name) == facet_key:
              return True
          d_name_norm = strip_accents(d.name)
          if facet_def is not None:
              if d.id in facet_def.known_dimension_ids or any(kp in d_name_norm for kp in key_patterns):
                  return True
          else:
              if any(kp in d_name_norm for kp in key_patterns):
                  return True
      return False
  ```
- Hardened Stage 4 Dimensional Gate and Member Matcher to avoid treating conceptual supported facets without physical dimensions as unhandled:
  ```python
  # Stage 4 Gate:
  for fk in def_unhandled:
      if fk in default_supported and not self._has_dimension_for_facet(default_dims, fk):
          continue
      if self.ontology.is_critical_unhandled_facet(fk, intent.facets.get(fk, "")):
          unhandled_facets.add(fk)

  # Stage 4 Candidate Breakdown Swap:
  crit_cand_unhandled = [
      f for f in cand_unhandled
      if not (f in cand_supported and not self._has_dimension_for_facet(cand_dims, f))
      and self.ontology.is_critical_unhandled_facet(f, intent.facets.get(f, ""))
  ]

  # Stage 4 Member Matcher:
  critical_unhandled = [
      f for f in unhandled
      if not (f in selected_meta.supported_facets and not self._has_dimension_for_facet(target_dims, f))
      and self.ontology.is_critical_unhandled_facet(f, intent.facets.get(f, ""))
  ]
  ```

---

## 3. Test Evidence & Verification

### A. TDD Red-Green Verification
1. **Red Stage:**
   - Added `test_vertical_slice_indicators_with_supported_facets_have_default_official_dimensions` to `tests/test_semantic_registry_200.py`. Failed initially with missing indicators: `[127, 3331, 3337, 5097, 119, 340, 365, 1684, 3344, 3333]`.
   - Added `test_fetcher_does_not_collapse_dimension_when_requested_as_breakdown` to `tests/test_semantic_fetcher.py`. Failed initially with `AssertionError: Expected 'series' in payload`.
2. **Green Stage:**
   - Seeded dimensions and implemented fetcher & engine logic.
   - Verified both tests pass cleanly.

### B. Unit & Benchmark Suite Results
- `tests/test_semantic_registry_200.py` and `tests/test_semantic_fetcher.py`: 24 passed.
- `tests/test_semantic_benchmark.py`: 8 passed (all 50 cases pass, 100% Top-1 accuracy).
- `tests/test_semantic_facet_coverage.py`: 17 passed across all 17 facets including `formalidad` (`FC-024`).
- `tests/test_semantic_benchmark_200.py`: 11 passed (100.0% Top-1 accuracy, 0.00% False Substitution Rate).
- Full non-integration suite:
  ```
  uv run pytest -m "not integration"
  ===================== 310 passed, 3 deselected in 45.11s ======================
  ```

---

## 4. Git Commit Details

- **Commit SHA:** `403bc8b`
- **Commit Message:** `feat(semantic): seed dimensions for vertical slice indicators and preserve explicit breakdown dimensions`
- **Files Changed:**
  - `src/statscepal/semantic/engine.py`
  - `src/statscepal/semantic/fetcher.py`
  - `src/statscepal/semantic/registry.py`
  - `tests/test_semantic_fetcher.py`
  - `tests/test_semantic_registry_200.py`
- **Diff Stats:** 5 files changed, 225 insertions(+), 4 deletions(-)
