# SDD ledger — plan: docs/superpowers/plans/2026-10-17-catalog-alignment-and-empirical-fetch-hardening-plan.md
Base commit: 4ac75d712711be26317233f605917fb8a08d3bdb

## Pre-flight Plan Scan
| Tasks | Shared Interface / File | Findings & Rulings |
|---|---|---|
| Task 1 x Task 2 | `src/statscepal/semantic/fetcher.py` | Clean. Task 1 handles indicator mapping & member ID isolation; Task 2 handles country matching & decade column parsing. Sequential additions to `fetcher.py`. |
| Task 2 x Task 3 | `SemanticDataFetcher` / `Década` | Clean. Task 2 adds decade parsing support to `fetcher.py`, which Task 3 relies on for census/demographic indicators (`4968, 4969`). |
| Task 3 x Task 4 | `SemanticResolutionEngine` / `cli.py` | Clean. Task 3 registers population indicators & demonyms; Task 4 certifies live queries end-to-end and annotates `empirical_indicator_id` in CLI. |

All checks clean. Ready for Task 1 dispatch.

## Task Progress

- [x] Task 1: Empirical Indicator ID Mapping & Synthetic member_id Isolation (commits 4ac75d7..591da03, review clean by Winston)
- [x] Task 2: Robust Country Column Priority, UN Formal Country Name Matching & Decade Period Parsing in `SemanticDataFetcher` (commits 591da03..1b6c651, review clean by Winston)
- [x] Task 3: Latin American Demonyms in `COUNTRY_LEXICON` & Demographic/Ethnic Population Resolution (`4788`, `4968`, `4969`, `4992`, `4639`) (commits 1b6c651..e539d28, review clean by Winston)
- [x] Task 4: End-to-End Certification of Multi-Country Inflation & Ethnic Population Queries (commits e539d28..2bd03e6, review clean by Winston)

All 4 tasks complete and approved.
