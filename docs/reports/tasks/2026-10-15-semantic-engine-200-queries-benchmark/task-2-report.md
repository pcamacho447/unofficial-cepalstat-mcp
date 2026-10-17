# Task 2 Report: Build the 200-Question Empirical Benchmark Dataset

- **Task ID:** Task 2
- **Developer:** Amelia (Senior Developer)
- **Base Commit:** `d4dcaa0edc25c01cb6cf399ce182952b369f3e5d`
- **Result Commit:** `35a2b6d38c2c1d38e92362ccde17736925180042`
- **Status:** DONE

---

## 1. Summary of Changes

In Task 2, we authored the comprehensive empirical benchmark dataset consisting of exactly 200 test cases distributed across 10 substantive macroeconomic and social clusters (20 cases per cluster), adhering strictly to the **8-4-4-2-2 coverage matrix**:
- **8 Canonical direct queries** across diverse Latin American economies (Chile, Brasil, México, Colombia, Argentina, Perú, Uruguay, Bolivia, Costa Rica).
- **4 Regionalisms / Slang** capturing realistic colloquial queries (chilenismos: *pega*, *lucas*, *cabros*; lunfardo rioplatense: *laburantes*, *guita*, *pibes*, *morfi*, *sope*; mexicanismos: *chamba*, *lana*, *raza*; modismos andinos/colombianos: *camello*, *plata*, *carestía*).
- **4 Dimensional Breakdowns & Indicator Swaps** testing dynamic facet routing (`sexo`, `edad`, `area`, `estrato`, `rubro`, `canasta`).
- **2 Controlled Ambiguities** testing the `ALTERNATIVE_PROPOSED` resolution mechanism without unjustified guessing.
- **2 Hard Abstentions & Survey Gaps** validating rejection of unobserved survey periods (CASEN 2021 with temporal anchors) and impossible facets / out-of-range dates / fictional geographies.

### Artifacts Created:
1. **`tests/test_benchmark_dataset_integrity.py`:**
   - Strict structural validation suite asserting:
     * Exactly 200 entries in root JSON array.
     * Sequential unique IDs from `SE-001` through `SE-200`.
     * Exact 10 clusters of 20 items each.
     * Strict 8-4-4-2-2 distribution of difficulties (`CANONICAL`, `SLANG`, `BREAKDOWN`, `AMBIGUOUS`, `ABSTENTION`) per cluster.
     * Full schema validation (`id`, `cluster`, `difficulty`, `query`, `expected_status`, `expected_indicator_id`, `expected_facets`, `expected_reason`, `expected_alternatives`).
     * Dedicated assertions for Cluster 4 (Income Disambiguation) context modifiers and ambiguous alternatives.
2. **`tests/benchmark/semantic_benchmark_cases_200.json`:**
   - 200 fully annotated cases serialized in UTF-8 JSON format with rich natural language queries and statistical metadata.

---

## 2. The 10 Clusters & 8-4-4-2-2 Coverage Matrix

| Cluster Code | Substantive Domain | ID Range | Canonical (8) | Slang (4) | Breakdown (4) | Ambiguous (2) | Abstention (2) | Total |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C1_POBREZA` | Pobreza total, extrema y brecha | `SE-001`–`SE-020` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C2_DESIGUALDAD` | Distribución del ingreso, quintiles y deciles | `SE-021`–`SE-040` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C3_MERCADO_LABORAL` | Desocupación general y desempleo juvenil | `SE-041`–`SE-060` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C4_SALARIOS_E_INGRESOS` | Salario medio, salario mínimo e ingreso per cápita | `SE-061`–`SE-080` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C5_CUENTAS_NACIONALES` | PIB total, per cápita y trimestral constante | `SE-081`–`SE-100` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C6_PRECIOS_E_INFLACION` | IPC general, alimentos y transporte/energía | `SE-101`–`SE-120` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C7_FINANZAS_PUBLICAS` | Deuda pública, balance primario e ingresos tributarios | `SE-121`–`SE-140` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C8_SECTOR_EXTERNO` | Balanza en cuenta corriente y términos de intercambio | `SE-141`–`SE-160` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C9_MEDIO_AMBIENTE` | Emisiones GEI (con/sin LULUCF) y energías renovables | `SE-161`–`SE-180` | 8 | 4 | 4 | 2 | 2 | **20** |
| `C10_ADVERSARIOS_Y_ABSTENCIONES` | Vacíos CASEN, periodicidad horaria/diaria, facetas inválidas | `SE-181`–`SE-200` | 8 | 4 | 4 | 2 | 2 | **20** |
| **Total** | | | **80** | **40** | **40** | **20** | **20** | **200** |

---

## 3. Detailed Specifications for Cluster 4 (Income Disambiguation)

Cluster 4 (`SE-061` to `SE-080`) satisfies all disambiguation scenarios for ambiguous colloquial terms (*"guita"*, *"plata"*, *"lana"*, *"sueldo"*, *"billete"*):

1. **Salario mínimo real (ID 3337):**
   - Context modifiers: *"mínimo"*, *"de ley"*, *"básico"*.
   - Example (`SE-070`): *"Cuál fue la guita mínima por ley en Chile en 2022"* $\to$ Status `RESOLVED`, ID `3337`.
2. **Salario medio real (ID 128):**
   - Context modifiers: *"medio"*, *"promedio"*, *"laburantes"*, *"trabajadores"*.
   - Example (`SE-069`): *"La guita de los laburantes en Argentina en 2021"* $\to$ Status `RESOLVED`, ID `128`.
3. **Ingreso laboral medio (ID 3339):**
   - Breakdowns: *"mujeres"*, *"hombres"*, *"campo/rural"*.
   - Example (`SE-073`): *"Ingreso laboral medio de las mujeres en México en 2020"* $\to$ Status `RESOLVED`, ID `3339`, facets: `{"sexo": "FEMENINO"}`.
   - Example (`SE-074`): *"Ingreso laboral medio en el campo en Brasil en 2021"* $\to$ Status `RESOLVED`, ID `3339`, facets: `{"area": "RURAL"}`.
4. **Ingreso per cápita del hogar (ID 3345):**
   - Context modifiers: *"hogares"*, *"familias"*, *"por cabeza"*.
   - Example (`SE-071`): *"Cuál es la plata de los hogares por cabeza en Colombia en 2020"* $\to$ Status `RESOLVED`, ID `3345`.
5. **Unmodified Slang ($\to$ `ALTERNATIVE_PROPOSED`):**
   - Example (`SE-077`): *"Cómo estuvo la guita en Chile en 2021"* $\to$ Status `ALTERNATIVE_PROPOSED`, Candidate `128`, Alternatives: `[3337, 3345]`.
   - Example (`SE-078`): *"Cuánta plata en Colombia en 2020"* $\to$ Status `ALTERNATIVE_PROPOSED`, Candidate `128`, Alternatives: `[3337, 3345]`.

---

## 4. TDD Verification and Test Evidence

### Step 1 & 2: RED Phase (Integrity Test Failure)
```
AssertionError: Benchmark file C:\papx\statscepal\tests\benchmark\semantic_benchmark_cases_200.json does not exist
============================== 5 errors in 0.19s ==============================
```

### Step 3 & 4: GREEN Phase (Integrity Test Success)
```
tests\test_benchmark_dataset_integrity.py .....                          [100%]
============================== 5 passed in 0.06s ==============================
```

### Step 5: Regression Verification (Full Non-Integration Suite)
```
===================== 174 passed, 2 deselected in 34.70s ======================
```
Zero regressions across existing 169 tests + 5 new integrity tests = 174 tests passing.

---

## 5. Commits Created

- Commit: `35a2b6d`
  - Message: `test(semantic): author complete 200-case empirical benchmark dataset`
  - Files:
    - `tests/benchmark/semantic_benchmark_cases_200.json` (200 test cases)
    - `tests/test_benchmark_dataset_integrity.py` (integrity validation suite)

---

## 6. Verification of Clean Workspace

- `git status` reports working tree clean.
- No temporary scripts or stray files remain in `tests/` or `tests/benchmark/`.
