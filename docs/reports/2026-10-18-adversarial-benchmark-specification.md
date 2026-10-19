# Especificación de Benchmark Adversario y Matriz de Verificación de Catálogo CEPALSTAT

**Fecha:** 2026-10-18  
**Autoría:** Anti-Consensus Club (🪵 Splinter, 📏 Level, 🛑 Killjoy, 🃏 Wildcard)  
**Estado:** Propuesta Técnica y Matriz Documentada para Revisión del Usuario  
**Commit Base:** [`488bd8d`](https://github.com/cepal/statscepal/commit/488bd8d)  
**Documento de Referencia:** [`docs/reports/2026-10-18-adversarial-benchmark-specification.md`](file:///C:/papx/statscepal/docs/reports/2026-10-18-adversarial-benchmark-specification.md)  
**Catálogo Maestro Auditado:** `scratch/catalog.csv` (1,739 series e indicadores oficiales de CEPALSTAT)

---

## 1. Manifiesto del Anti-Consensus Club

> 🪵 **Splinter:** *"El benchmark canónico de 200 preguntas fue un paseo por el parque: consultas diseñadas a medida para el corte vertical de 50 indicadores. Un motor de resolución semántica no demuestra su temple cuando le piden exactamente lo que sabe responder, sino cuando un investigador real le exige granularidad microeconómica, series ausentes o conceptos que CEPAL jamás ha medido. Si el motor inventa sustituciones 'por conveniencia', no es IA: es una máquina de desinformación econométrica."*

> 📏 **Level:** *"Hemos auditado exhaustivamente cada una de las 40 consultas candidatas contra el catálogo maestro oficial de CEPALSTAT (`scratch/catalog.csv`, 1,739 indicadores). Cero especulaciones: discriminamos con precisión quirúrgica qué indicadores existen formalmente en CEPALSTAT (pero fuera del slice de 50), cuáles existen como proxies o desagregaciones parciales, y cuáles están estrictamente fuera del mandato institucional (banca central, mercados cambiarios paralelos o riqueza privada patrimonial)."*

> 🛑 **Killjoy:** *"Las reglas del juego son binarias. Si un usuario pide 'valor agregado manufacturero' y el motor le devuelve 'PIB total per cápita' con score 1.0, eso no es una aproximación: es una Falsa Sustitución Catastrófica (FSR = 100%). En este benchmark adversarial, el único comportamiento admisible ante un desajuste conceptual severo es `ABSTAINED` (con `UNRESOLVED_SPECIFICITY`) o, en casos de fallback agregado legítimo, `ALTERNATIVE_PROPOSED` con score degradado ($\le 0.65$) y advertencia conversacional explícita."*

> 🃏 **Wildcard:** *"Este documento redacta la batería completa de 40 casos dividida en 4 familias de choque, con sus referencias oficiales comprobadas. Pero la puerta queda abierta: entregamos la mesa al usuario para que audite esta matriz y le agregue sus 'cosas picantes' antes de disparar las pruebas automatizadas."*

---

## 2. Clasificación de Resultados y Criterios de Aceptación

Para cada consulta adversarial, el motor semántico de resolución debe clasificarse estrictamente en uno de tres comportamientos evaluables:

1. **`ABSTAINED` (Abstención Rigurosa):**  
   El motor detecta que la consulta exige un concepto o faceta que no puede ser satisfecho sin violar la integridad econométrica (ej. sector manufacturero específico vs PIB agregado, o variables fuera del mandato de CEPAL como tasas de política monetaria o dólar blue). Razón esperada: `UNSUPPORTED_FACET` o `UNRESOLVED_SPECIFICITY`.
2. **`ALTERNATIVE_PROPOSED` (Alternativa Sugerida con Degradación de Confianza):**  
   El motor identifica un concepto aggregate/padre relevante en su base, pero reconoce que quedan modificadores semánticos no resueltos (ej. "salario mínimo agrícola" derivando a "salario mínimo real general"). Debe emitir un `score <= 0.65`, marcar `is_fallback=True` y proporcionar una `conversational_hint` explicativa.
3. **`RESOLVED` (Resolución Exacta):**  
   Aplica únicamente cuando el concepto, sus facetas y sus filtros dimensionales están completamente soportados por la ontología y el catálogo activo del motor (ej. "población afrodescendiente rural en brasil" mapeando a ID 4969 con filtros de área geográfica y etnia).

**Criterio de Violación Crítica (Falsa Sustitución):**  
Cualquier consulta con modificador específico no absorbido que devuelva `RESOLVED` con `score = 1.0` sobre un indicador canónico generalista será contabilizada como **Falla Catastrófica de Sustitución Falsa**.

---

## 3. Matriz Exhaustiva de Pruebas Adversarias (40 Consultas Verificadas)

### Familia A: Trampas de Granularidad Sectorial y Microeconómica (10 Consultas)
*Objetivo: Evaluar si el motor confunde agregados macroeconómicos con ramas específicas de actividad o categorías microeconómicas.*

| # | Consulta Adversaria | Existencia en Catálogo Maestro CEPALSTAT (1,739) | Indicador Canónico en Motor (Slice 50) | Comportamiento Esperado | Justificación Metodológica / Trampa Econométrica |
|---|-------------------|---------------------------------------------------|----------------------------------------|-------------------------|--------------------------------------------------|
| A1 | `valor agregado manufacturero por habitante en mexico` | **Existe en catálogo:** ID `2195` / `2196` (*PIB por actividad económica a precios corrientes/constantes*). Fuera del slice 50. | ID `730` (*PIB per cápita*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | Falsa equivalencia: la manufactura es solo una fracción del PIB (~18% en MEX). Confundir VAM per cápita con PIB per cápita distorsiona la estructura productiva. |
| A2 | `salario minimo agricola en guatemala` | **Existe en catálogo:** ID `3140` (*Salario Mínimo Agrícola*) e ID `2741` (*Poder adquisitivo alimentario del salario mínimo agrícola*). | ID `340` / `3337` (*Salario mínimo real general*) | `ALTERNATIVE_PROPOSED` (score 0.65) | En Guatemala el salario mínimo agrícola y no agrícola tienen comisiones paritarias y decretos legales diferenciados. |
| A3 | `inversion extranjera directa en el sector telecomunicaciones en colombia` | **Existe parcialmente:** ID `1824` (*IED neta total*). No existe desagregación sectorial telecomunicaciones en CEPALSTAT. | ID `1824` (*Inversión extranjera directa*) | `ALTERNATIVE_PROPOSED` (score 0.65) | Sugerir la IED total advirtiendo que no existe apertura por sectores de infraestructura. |
| A4 | `precio de exportacion del litio en chile` | **AUSENTE EN CEPALSTAT.** ID `4452` tiene productos básicos (cobre, petróleo, hierro), pero no litio. | ID `4452` (*Índice de precios de productos básicos*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | El litio no forma parte de la canasta clásica de commodities de CEPAL. Sustituir por el índice general sería espurio. |
| A5 | `precio spot de exportacion del cobre en peru` | **Existe como componente:** ID `4452` contiene la serie de precios de cobre en su desglose dimensional. | ID `4452` (*Índice de precios trimestrales*) | `ALTERNATIVE_PROPOSED` / `RESOLVED` con dimensión | El cobre existe en la tabla 4452; si la dimensión de producto básico no está parametrizada, debe sugerirse el índice general sin resolver 1.0 ciego. |
| A6 | `exportaciones del sector automotriz en mexico` | **Existe parcialmente:** ID `1924` (*Importaciones de vehículos*), exportaciones totales en ID `1819`. No hay serie exclusiva de exportación automotriz en CEPALSTAT. | ID `1819` (*Exportaciones totales*) | `ABSTAINED` / `ALTERNATIVE_PROPOSED` | El sector automotriz representa más del 30% de manufacturas mexicanas; sustituirlo por exportaciones totales sin aviso es inaceptable. |
| A7 | `salario medio en la mineria en chile` | **AUSENTE EN CEPALSTAT.** ID `128` es el salario medio general de la economía. | ID `128` (*Índice de salario medio real*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | La minería en Chile tiene primas salariales de más del 100% sobre el salario medio general. Asignar salario general es engañoso. |
| A8 | `importaciones de fertilizantes en brasil` | **Existe indirectamente:** ID `2022` / `2038` (*Consumo/intensidad de uso de fertilizantes*). No hay serie comercial de importación de insumos agrícolas. | ID `1819` / Ausente | `ABSTAINED` | CEPAL mide uso físico y ambiental de fertilizantes, no la balanza comercial desagregada por insumos agroquímicos. |
| A9 | `gasto publico en medicamentos y salud en argentina` | **Existe en ODS:** ID `3785`–`3787` (vacunación/salud infantil). Gasto social funcional en ID `1246`. | ID `1246` (*Gasto de gobierno*) | `ALTERNATIVE_PROPOSED` | Ofrecer el gasto en funciones sociales del gobierno central con nota de falta de desagregación farmacéutica. |
| A10 | `gasto militar y de defensa como porcentaje del pib en colombia` | **AUSENTE EN CEPALSTAT.** CEPALSTAT excluye explícitamente estadísticas militares/defensa (mandato civil ODS/ECLAC). | Ninguno / ID `1242` | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | El gasto en defensa pertenece al SIPRI o ministerios nacionales, nunca a la base estadística de CEPAL. |

---

### Familia B: Trampas de Alcance Institucional y Contable (10 Consultas)
*Objetivo: Evaluar el rigor en perímetros contables del sector público, nominalidad vs realidad, y mandatos de banca central.*

| # | Consulta Adversaria | Existencia en Catálogo Maestro CEPALSTAT (1,739) | Indicador Canónico en Motor (Slice 50) | Comportamiento Esperado | Justificación Metodológica / Trampa Econométrica |
|---|-------------------|---------------------------------------------------|----------------------------------------|-------------------------|--------------------------------------------------|
| B1 | `deuda del gobierno general en porcentaje del pib en brasil` | **Existe solo Gobierno Central:** ID `1240` (*Saldo deuda pública % PIB*) e ID `4556` son estrictamente **Gobierno Central**. | ID `1240` (*Deuda pública % PIB*) | `ALTERNATIVE_PROPOSED` (score 0.65) | El Gobierno General incluye estados/municipios y seguridad social (en Brasil la diferencia entre GC y GG supera 15 puntos del PIB). Debe advertirse el perímetro. |
| B2 | `deficit fiscal global en porcentaje del pib en uruguay` | **Existe:** ID `1246` (*Operaciones del gobierno: balance financiero/global*). El slice 50 solo tiene balance primario (ID `1241`). | ID `1241` (*Balance primario*) | `ALTERNATIVE_PROPOSED` (score 0.65) | El déficit global incluye el pago de intereses de la deuda; confundir primario con global en economías endeudadas falsea la sostenibilidad fiscal. |
| B3 | `salario minimo nominal en colombia` | **AUSENTE EN CEPALSTAT.** CEPALSTAT publica exclusivamente salario mínimo **real** (índice 2018=100 en ID `340`). | ID `340` (*Salario mínimo real*) | `ALTERNATIVE_PROPOSED` (score 0.65) | La nominalidad (pesos corrientes) no existe en CEPAL para evitar distorsiones por inflación histórica; debe advertirse que la serie entregada es deflactada. |
| B4 | `tasa de interes de politica monetaria en chile` | **Existe serie histórica:** ID `1206` (*Tasa de política monetaria*), pero está descontinuada o fuera del slice 50. | Ninguno | `ABSTAINED` | Las tasas de interés de política monetaria diaria/mensual son competencia de los Bancos Centrales, no del compendio estructural de CEPAL. |
| B5 | `tipo de cambio del dolar blue informal en argentina` | **TOTALMENTE AUSENTE.** CEPALSTAT solo reconoce tipos de cambio oficiales (ID `2179` nominal, ID `1901` TCRE). | ID `2179` (*Tipo de cambio nominal*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | Presentar el tipo de cambio oficial mayorista cuando el usuario solicita la brecha cambiaria informal genera distorsiones severas de valuación. |
| B6 | `recaudacion del iva como porcentaje del pib en peru` | **Existe como agregado:** ID `1242` (*Ingresos tributarios del gobierno central en % del PIB*). No hay desglose de IVA aislado en el slice. | ID `1242` (*Ingresos tributarios % PIB*) | `ALTERNATIVE_PROPOSED` (score 0.65) | Ofrecer la presión tributaria total del gobierno central aclarando que no se dispone del IVA desagregado. |
| B7 | `coeficiente de gini laboral antes de transferencias en chile` | **Existe solo Gini del ingreso disponible:** ID `3289` (*Índice de Gini*), ID `4357` (*Impacto redistributivo*). | ID `3289` (*Índice de Gini*) | `ALTERNATIVE_PROPOSED` (score 0.65) | El Gini oficial de CEPAL mide el ingreso per cápita de los hogares post-transferencias públicas monetarias, no el ingreso primario laboral de mercado. |
| B8 | `tasa de ahorro de los hogares en mexico` | **Existe agregado nacional:** ID `4050` (*Ahorro Total*) e ID `4051` (*Ahorro nacional a precios corrientes*). No existe desglose institucional de hogares. | ID `4050` / Ausente | `ABSTAINED` / `ALTERNATIVE_PROPOSED` | El ahorro de los hogares no se computa en el marco simplificado de CEPALSTAT; solo se publica el ahorro bruto nacional consolidado. |
| B9 | `gasto en consumo final del gobierno en bolivia` | **Existe en cuentas nacionales:** ID `4549` (*Crecimiento del consumo del gobierno*), tablas ID `2195` / `299`. Fuera del slice 50. | ID `729` (*PIB total*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | Falsa sustitución grosera: el consumo de gobierno es solo un componente (~13-16% del PIB). No puede sustituirse por PIB agregado. |
| B10 | `inversion fija privada vs publica en ecuador` | **Existe agregado:** ID `3379` (*Tasa de variación de Formación Bruta de Capital*). No hay división institucional público/privada. | ID `3379` / Ausente | `ABSTAINED` | La FBCF total no permite inferir el esfuerzo inversor del sector privado frente al Estado. |

---

### Familia C: Fronteras Sociales, Demográficas y ODS (10 Consultas)
*Objetivo: Poner a prueba la distinción entre pobreza por ingresos vs multidimensional, expectativas demográficas, indicadores penales y percepciones.*

| # | Consulta Adversaria | Existencia en Catálogo Maestro CEPALSTAT (1,739) | Indicador Canónico en Motor (Slice 50) | Comportamiento Esperado | Justificación Metodológica / Trampa Econométrica |
|---|-------------------|---------------------------------------------------|----------------------------------------|-------------------------|--------------------------------------------------|
| C1 | `pobreza multidimensional en colombia` | **Existe en catálogo:** ID `5595` (*Incidencia pobreza multidimensional*), ID `4079`, ID `4188`. Fuera del slice 50. | ID `3334` / `3340` (*Pobreza monetaria por ingresos*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | Trampa crítica: la pobreza multidimensional mide privaciones en educación, salud y vivienda; no puede resolverse con líneas monetarias de ingreso. |
| C2 | `esperanza de vida al nacer de los hombres en paraguay` | **Existe en catálogo:** ID `38` y ID `4784` (*Esperanza de vida al nacer, según sexo*). Fuera del slice 50. | Ninguno (ausente en slice 50) | `ABSTAINED` | Evita sustituciones espurias por mortalidad general o natalidad. |
| C3 | `tasa de ocupacion carcelaria y hacinamiento en el salvador` | **Existe en catálogo ODS 16:** ID `4143` (*Tasa de ocupación carcelaria basada en capacidad oficial*). | Ninguno | `ABSTAINED` | Muestra conocimiento de la frontera ODS sin generar alucinación en el corte macro actual. |
| C4 | `poblacion que ha pensado en emigrar en honduras` | **Existe en catálogo Social:** ID `3260` (*Población que ha pensado en migrar a otro país, por sexo*). | Ninguno | `ABSTAINED` | Es un indicador de percepciones y expectativas sociales, no de flujos migratorios reales ni demografía censal. |
| C5 | `remesas de trabajadores como porcentaje del pib en guatemala` | **Existe en catálogo:** ID `4016` (*Volumen de remesas en proporción al PIB*) e ID `2743` (*Remesas familiares*). | Ninguno / ID `1819` | `ABSTAINED` | En Guatemala las remesas representan cerca del 19% del PIB; si el motor no tiene cargada la tabla 4016 en su slice, debe abstenerse y no entregar exportaciones. |
| C6 | `empleo informal en el sector manufacturero en mexico` | **Existe en catálogo:** ID `4207` (*Proporción de empleo informal desglosada por sector y sexo*). | ID `2963` (*Población ocupada en sector informal*) | `ALTERNATIVE_PROPOSED` (score 0.65) | Ofrecer la tasa global de informalidad advirtiendo que no se desagrega el sector industrial. |
| C7 | `tasa de graduacion o finalizacion de la educacion secundaria en uruguay` | **Existe en catálogo ODS 4:** ID `4196` (*Tasa de finalización por nivel educativo y quintil*). | Ninguno | `ABSTAINED` | Medición educativa ODS; no debe aproximarse por tasa de analfabetismo o asistencia escolar general. |
| C8 | `superficie de agricultura organica certificada en argentina` | **Existe en catálogo Ambiental:** ID `4049` (*Proporción de la superficie agrícola con agricultura orgánica*). | Ninguno | `ABSTAINED` | Indicador agroambiental altamente especializado; no confundir con producción agrícola total. |
| C9 | `indice de percepcion de corrupcion en venezuela` | **Existe en ODS 16 / Sociales:** ID `5548` (*Población que cree que la corrupción de funcionarios públicos es generalizada*). | Ninguno | `ABSTAINED` | CEPAL mide encuestas de percepción ciudadana del Latinobarómetro, no el ranking de Transparencia Internacional. |
| C10 | `concentracion de la riqueza del 1 por ciento mas rico forbes en chile` | **TOTALMENTE AUSENTE.** CEPAL mide flujos de ingresos en encuestas de hogares, no stocks de riqueza patrimonial. | ID `3289` (*Gini*) / ID `3324` (*Decil 10*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | Los balances patrimoniales de multimillonarios no son capturados por encuestas de hogares (CASEN). Sustituir por el décimo decil de ingreso falsea la concentración extrema. |

---

### Familia D: Dinámica Temporal, Filtros y Desestacionalización (10 Consultas)
*Objetivo: Evaluar la precisión ante desgloses por componentes de demanda, ajustes estacionales, brechas estructurales y frecuencias.*

| # | Consulta Adversaria | Existencia en Catálogo Maestro CEPALSTAT (1,739) | Indicador Canónico en Motor (Slice 50) | Comportamiento Esperado | Justificación Metodológica / Trampa Econométrica |
|---|-------------------|---------------------------------------------------|----------------------------------------|-------------------------|--------------------------------------------------|
| D1 | `pib trimestral por componente del gasto en brasil` | **Existe en catálogo:** ID `286` (*PIB trimestral por tipo de gasto a precios constantes*) e ID `294` (*precios corrientes*). | ID `731` (*PIB trimestral a precios constantes total*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | La consulta pide el desglose de componentes (consumo, inversión, exportaciones netas). Devolver la serie agregada total como 1.0 es una falsa resolución. |
| D2 | `pib trimestral desestacionalizado en mexico` | **AUSENTE EN CEPALSTAT.** Las series trimestrales publicadas por CEPAL son tasas brutas de variación interanual. | ID `731` (*PIB trimestral variación interanual*) | `ALTERNATIVE_PROPOSED` (score 0.65) | CEPAL no publica series ajustadas por estacionalidad (X-13ARIMA-SEATS); debe aclararse que la serie es variación interanual original. |
| D3 | `pib potencial y brecha del producto en chile` | **TOTALMENTE AUSENTE.** CEPAL no publica estimaciones oficiales de PIB potencial ni filtros de Hodrick-Prescott. | ID `729` / `731` (*PIB real*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | El PIB potencial es una variable latente inobservable de modelado econométrico, no una serie estadística observada. |
| D4 | `precio del petroleo brent spot mensual en ecuador` | **AUSENTE EN CEPALSTAT.** ID `4452` tiene precios trimestrales de canasta de commodities, no cotización spot Brent mensual. | ID `4452` (*Índice de precios de commodities*) | `ABSTAINED` / `ALTERNATIVE_PROPOSED` | El marcador de Ecuador suele ser WTI u Oriente; Brent spot mensual no es publicado por CEPAL. |
| D5 | `volumen de exportaciones fisicas de petroleo en venezuela` | **Existe parcialmente:** ID `1665` (*Producción de petróleo crudo en barriles*). No hay serie de barriles exportados netos. | ID `1665` / ID `1819` | `ALTERNATIVE_PROPOSED` | Ofrecer producción física de crudo o valor monetario de exportaciones advirtiendo el cambio de unidad física a valor. |
| D6 | `variacion trimestral del salario real en uruguay` | **Existe solo anual:** ID `128` y ID `340` son índices de frecuencia **ANUAL**. | ID `128` (*Índice de salario medio real anual*) | `ALTERNATIVE_PROPOSED` (score 0.65) | El usuario pide frecuencia trimestral para análisis de ciclo de corto plazo; si solo hay frecuencia anual, debe rebajarse el score. |
| D7 | `desempleo abierto trimestral en argentina` | **Existe solo anual:** ID `3331` (*Tasa de desocupación*) se publica con periodicidad anual en CEPALSTAT. | ID `3331` (*Tasa de desocupación anual*) | `ALTERNATIVE_PROPOSED` (score 0.65) | Informar la disponibilidad exclusiva de datos anuales en el compendio CEPALSTAT. |
| D8 | `inflacion subyacente sin alimentos y energia en brasil` | **Existe en catálogo:** ID `764` (*Índice de precios subyacente*) e ID `4145` (*Crecimiento del IPC subyacente*). Fuera del slice 50. | ID `2439` (*Inflación general al consumidor IPC*) | `ABSTAINED` (`UNRESOLVED_SPECIFICITY`) | La inflación subyacente (core inflation) excluye componentes volátiles; resolver con IPC general falsea el diagnóstico de presiones de demanda. |
| D9 | `terminos de intercambio mensuales en peru` | **Existe solo anual:** ID `4719` (*Términos de intercambio de bienes FOB/CIF*) es estrictamente anual. | ID `4719` (*Términos de intercambio anuales*) | `ALTERNATIVE_PROPOSED` (score 0.65) | Ofrecer la serie anual indicando la inexistencia de mediciones mensuales de términos de intercambio en CEPAL. |
| D10 | `indice de tipo de cambio real bilateral con estados unidos en colombia` | **Existe solo multilateral:** ID `1901` (*Tipo de cambio real efectivo multilateral TCRE*). | ID `1901` (*TCRE multilateral*) | `ALTERNATIVE_PROPOSED` (score 0.65) | El TCRE de CEPAL pondera los socios comerciales clave de la región; debe advertirse que no es la paridad bilateral exclusiva con EE.UU. |

---

## 4. Arquitectura de Ejecución y Métricas de Validación

Cuando el usuario apruebe esta especificación e incorpore sus casos picantes adicionales, la batería se ejecutará bajo el runner automatizado:

```bash
uv run pytest tests/test_adversarial_benchmark_40.py -v
```

### Métricas de Evaluación Obligatorias:
1. **Top-1 Resolution Accuracy:** $\ge 95\%$ sobre consultas legítimas soportadas.
2. **False Substitution Rate (FSR):** **Estrictamente $0.00\%$** (Cero asignaciones erróneas con score 1.0 cuando existen tokens de granularidad no resueltos).
3. **Abstention Precision:** $100\%$ de abstenciones justificadas ante conceptos fuera de mandato o con discrepancia categorial severa.
4. **Latency Budget:** $p50 < 0.5\text{ ms}$, $p95 < 2.0\text{ ms}$ (resolución local en memoria sin llamadas a red).

---

## 5. Espacio para Cosas Picantes del Usuario 🌶️

Este espacio está reservado para que el usuario inserte o modifique consultas de máxima dificultad antes de la ejecución definitiva:

- [ ] *Espacio para caso picante 1:* __________________________________________________
- [ ] *Espacio para caso picante 2:* __________________________________________________
- [ ] *Espacio para caso picante 3:* __________________________________________________
- [ ] *Espacio para caso picante 4:* __________________________________________________
- [ ] *Espacio para caso picante 5:* __________________________________________________

*Esperando revisión y luz verde del usuario.*
