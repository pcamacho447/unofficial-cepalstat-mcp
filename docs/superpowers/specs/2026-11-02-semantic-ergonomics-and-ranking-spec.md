# Semantic Ergonomics, Typo Suggestions & Tier-2 Re-ranking Specification (Phase 4)

**Date:** 2026-11-02  
**Status:** Approved  
**Scope:** `src/unofficial_cepalstat_mcp/semantic/`, `src/unofficial_cepalstat_mcp/cli.py`, `tests/`  

---

## 1. Context & Objectives

Following the completion of Phases 1–3 and the hardening of measure modifiers and non-LAC geography diagnostics, user testing revealed three ergonomic and quality-of-life improvements required in the semantic layer before opening the MCP server surface:

1. **CLI Fetch Table Hygiene (Bug 7):**
   In the CLI output of `semantic resolve ... --fetch`, the table of observations prints numeric foreign key IDs (such as `12080`) under the `Unit` column header next to the actual unit name. This occurs because `fetcher.py` prioritizes `notes_ids` (an integer metadata key) over textual `notes`/`notas`, and `cli.py` concatenates any non-empty string in `item["notes"]` onto the unit column.
   *Requirement:* Prioritize human-readable textual notes, discard purely numeric IDs from descriptive notes, and clean the CLI tabular formatting.

2. **Typo Suggestions ("Did You Mean?") without Silent Substitution (Point 5):**
   When users mistype common terms (e.g. `"pobresa"` instead of `"pobreza"`, or `"desocupasion"` instead of `"desocupacion"`), the engine currently abstains with `LOW_CONCEPTUAL_RELEVANCE` and a generic hint, offering no guidance.
   *Requirement:* Calculate bounded edit distance (Levenshtein / Damerau-Levenshtein $\le 2$) against `Thesaurus` vocabulary terms. If a close match is found, append a helpful conversational hint (e.g., *`"No se identificó un fenómeno socioeconómico cubierto por el catálogo de CEPALSTAT. ¿Quisiste decir 'pobreza'?"`*).
   *Invariant:* The engine must **never** auto-correct or resolve on fuzzy match; it must remain strictly `ABSTAINED` to uphold **0.00% FSR**.

3. **Tier-2 Headline vs. Peripheral Re-Ranking (Point 6):**
   In open natural language queries (e.g. `"como le fue al empleo en ecuador 2021"`), Tier 2 candidate retrieval currently ranks verbose, highly specialized indicators (such as `5531` *"Población de 15 a 64 años fuera del mercado laboral con dedicación exclusiva al trabajo doméstico..."*) above headline macro indicators (such as `127` *"Tasa de desocupación por sexo"* or `5097`). This occurs because the in-memory inverted index accumulates unnormalized stem weights over long titles without length normalization or headline priority.
   *Requirement:* Implement document length normalization (BM25-style damping) and a headline priority boost for core series (`order_num <= 20` or curated canonical defaults) so headline statistics outrank niche subpopulation breakdowns on general queries.

---

## 2. Technical Invariants & Verification

- **0.00% False Substitution Rate (FSR):** Typo suggestions must be purely advisory in conversational hints and never alter the `ABSTAINED` status.
- **Latency Budget:** Levenshtein checking must execute only on abstained queries with small token counts, keeping overall latency strictly at $p50 < 0.5\text{ ms}$.
- **Backward Compatibility:** All existing 390 certified benchmark queries (200 canonical, 40 adversarial, 100 catalog scale, 50 hold-out) and 8 mutation tests must pass without regression.
