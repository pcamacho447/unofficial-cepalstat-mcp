<!-- bmad:context -->
<!-- Verified 2026-10-30 against 42b170d. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## unofficial-cepalstat-mcp

Cliente Python, catálogo SQLite offline (~2,000 indicadores), recetario anti-sesgo (`bitacora`), analizador econométrico OLS y motor determinista de resolución semántica para la API Open Data de ONU CEPALSTAT (el servidor MCP está especificado pero aún no implementado en código). Stack: Python >=3.10, `uv`, `httpx`, `pydantic` v2, `pandas`, `statsmodels`, SQLite. Diseños y planes viven en `docs/specs/` y `docs/superpowers/`.

## Policy

- Preservar intacto el aviso legal de no-afiliación con ONU/CEPAL en `LICENSE` y `README.md` (`tests/test_governance_and_cleanliness.py` falla si se altera).
- Nunca crear `statscepal.db` en la raíz del repositorio; la caché local autorizada es `.statscepal_cache.db` vía `get_cache_db_path()`.

## Where things are

- Editando `src/unofficial_cepalstat_mcp/semantic/`? Leer `.agents/rules/semantic-resolution-guardrails.md` primero (11 invariantes obligatorios).
- Especificación pendiente del servidor MCP: `docs/specs/2026-10-15-cepalstat-mcp-server-spec.md`.
- Recetas certificadas de indicadores: `bitacoras/paises/`; tras editar un `.md` manualmente, ejecutar `uv run unofficial-cepalstat-mcp bitacora sync`.

## Running and verifying

- Sincronizar entorno completo con `uv sync --all-extras --dev` (instala tanto optional-dependencies como dependency-groups).
- Ejecutar siempre `uv run pytest -m "not integration"`; correr `pytest` sin filtro dispara pruebas `@pytest.mark.integration` contra la API viva de CEPALSTAT.
- Al tocar `semantic/`, certificar `uv run pytest tests/test_semantic_benchmark_200.py tests/test_adversarial_benchmark_40.py -v` (**0.00% FSR**, 40/40 adversarias y p50 < 1.0 ms).
- CI ejecuta `uv run ruff check .` y `uv build`. El código base cuenta con 0 errores de `mypy` en `src/unofficial_cepalstat_mcp/` (verificar cualquier código nuevo o firmas editadas con `uv run mypy src/unofficial_cepalstat_mcp/`).
- Para resolución semántica con extracción empírica por CLI usar `uv run unofficial-cepalstat-mcp semantic resolve "<consulta>" --fetch` (no existe `semantic fetch`).

## Conventions that differ from defaults

- Importar siempre desde `unofficial_cepalstat_mcp` en Python y notebooks; `statscepal` solo persiste como alias de script CLI en `pyproject.toml`.
- Nunca leer las constantes `DEFAULT_DB_PATH` de `catalog/store.py` o `bitacora/store.py` para nuevas rutas; llamar a `get_cache_db_path()` o inyectar `db_path` explícito, abrir SQLite con `timeout=10.0` + `PRAGMA busy_timeout = 10000;` y cerrar en `finally`.
- Nunca enviar miembros de `SYNTHETIC_DIMENSION_MEMBER_IDS` (ej. `79578`) como parámetro `members=` a `/records` (colisionan con IDs de países en otras tablas); todos los indicadores resuelven a IDs canónicos reales de `master_indicators` (`EMPIRICAL_INDICATOR_ID_MAP` permanece `{}` por retrocompatibilidad).
- Prohibido interpolar años sin encuesta en `BADEHOG_SURVEY_INDICATORS`; retornar `RESOLVED_WITH_ANCHORS` con años ancla adyacentes oficiales (`is_anchor=True`).
- Registrar nuevas facetas declarativamente en `FacetOntology` (`semantic/facet_ontology.py`), nunca con condicionales `if facet == "..."` en `engine.py`, `parser.py` o `matcher.py`, y nunca sobrescribir aristas `provenance='curated'` con `inferred`.

## Known pitfalls

- Agentes y recetas antiguas importan `from statscepal import ...`, causando `ModuleNotFoundError`; verificar siempre `from unofficial_cepalstat_mcp import ...`.
- En Linux/POSIX, `Path(str)` no separa barras invertidas de Windows (`\`); normalizar `str.replace("\\", "/")` al parsear rutas multiplataforma (ej. `sys.argv[0]` en `cli.py`).
- `tests/test_skill_structure.py` exige la presencia del comando CLI `statscepal` en `.agents/skills/cepalstat-api/SKILL.md` y `.agents/subagents/cepalstat-analyst.md`; no borrar ese alias CLI al actualizar documentación.

<!-- /bmad:context -->
