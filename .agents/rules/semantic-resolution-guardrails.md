# Guardarraíles de Resolución Semántica y Desglose Multidimensional

Al desarrollar, extender o refactorizar el motor semántico (`statscepal.semantic`), aplican los siguientes invariantes arquitectónicos y de calidad estadística:

## 1. Invariante de Integridad Dimensional y Anti-Degradación
- **Cero Pérdida de Facetas (Zero Facet Loss):** Si una consulta del usuario contiene un calificador dimensional explícito (e.g. etnia, género, quintil, tramo etario, sector geográfico), el motor **NUNCA** debe ignorar la faceta para retornar el indicador agregado canónico.
- **Tasa de Sustitución Falsa Cero (FSR = 0.00%):** Bajo ninguna circunstancia se debe responder a una pregunta dimensional con una cifra agregada simulando que responde a la solicitud.
- **Abstención Explícita:** Si la dimensión solicitada no existe en la base de datos de CEPALSTAT para el dominio (e.g. *"pobreza por coeficiente intelectual"*), el motor debe responder `ABSTAINED` con razón `UNSUPPORTED_FACET_<DIM>` en lugar de inventar filtros por defecto o degradar a nivel nacional agregado.

## 2. Enrutamiento por Conmutación de Grafo (`BREAKDOWN_OF`)
- **Descubrimiento y Procedencia de Relaciones (`BREAKDOWN_OF`):**
  - Las relaciones de desglose se descubren primariamente por **inferencia automática sobre metadatos oficiales cosechados** en SQLite (`indicator_dimensions` y `dimension_members`) cuando un indicador hijo comparte la raíz de concepto y añade dimensiones adicionales respecto a un indicador base.
  - Las aristas curadas manualmente (`provenance='curated'`) en el registro son prioritarias y actúan como semilla o sobreescritura de alta fidelidad, pero **se prohíbe exigir registro manual** como único mecanismo para soportar nuevas familias de desgloses.
- **Enrutamiento Genérico en Stage 4:**
  - El motor debe evaluar la cobertura facetaria de forma paramétrica y desacoplada mediante la ontología facetaria declarativa (`FacetOntology`). Queda **estrictamente prohibido añadir bifurcaciones `if facet == "nombre"` o listas de agregados cableadas en duro** en `engine.py`, `parser.py` o `matcher.py`.
- **Mapeo de Miembros Dinámicos:**
  - Los miembros requeridos (e.g. categorías específicas de etnia, sexo, quintil, educación) deben resolverse contra las dimensiones nativas indexadas en memoria, aplicando el miembro oficial correspondiente o absteniéndose formalmente si no existe.

## 3. Anclaje Temporal Dinámico en Series Relativas
- Las consultas relativas (*"últimos N años"*, *"última década"*) **NO** deben anclarse al año calendario del reloj del sistema ($T_{\text{system\_clock}}$).
- Deben anclarse dinámicamente al año máximo disponible $T_{\max} = \max(\text{observaciones}(\text{país}, \text{indicador}))$, considerando el rezago estadístico de publicación de las encuestas oficiales de hogares y cuentas nacionales.

## 4. Presupuesto de Rendimiento, Regex y Calidad
- **Latencia y Escalabilidad del Catálogo Completo:** El tiempo de resolución semántica local debe mantenerse estrictamente en $p50 < 0.5\text{ ms}$ y $p95 < 2.0\text{ ms}$ incluso con el catálogo completo de ~2,000 indicadores cargado en memoria (vía grafos e índices invertidos construidos al inicializar).
- **Higiene Regex:** Todos los patrones léxicos y de synsets deben usar delimitadores de palabra estrictos (`\b`) para evitar colisiones polisémicas o con modismos regionales (e.g., la jerga *"raza"* en México vs dimensión étnico-racial).
- **Aislamiento de Pruebas e Ingesta:** La suite de pruebas de CI/CD **nunca** debe depender de llamadas vivas a la red durante la ejecución estándar. Las pruebas de cosecha e ingesta deben operar contra fixtures JSON grabados y mocks herméticos.
- **Suite de Regresión:** Cualquier cambio debe certificar el 100.0% de acierto en el benchmark canónico (`tests/test_semantic_benchmark_200.py`) y 0.00% FSR en el benchmark de cobertura multidimensional.

## 5. Invariante Anti-Colapso en Desagregaciones Críticas
- **Prohibición de Colapso Silencioso a Total/Agregado:** Si la consulta del usuario solicita explícitamente una dimensión de desglose sin acotar un subgrupo específico (e.g. *"pobreza étnica"*, *"desempleo por sexo"*, *"ingreso por área"*), el motor **NUNCA** debe asignar silenciosamente el miembro agregado (`"Total"`, `"Nacional"`, `"Ambos sexos"`), ya que esto anula la intención de la consulta y devuelve el mismo valor agregado del indicador canónico.
- **Enlace de Desglose Completo (`is_breakdown = True`):** Ante solicitudes genéricas de una faceta, el motor debe enlazar la lista completa de miembros oficiales de la dimensión para presentar la serie comparativa de grupos, o bien suspender con `ALTERNATIVE_PROPOSED` solicitando al usuario seleccionar la categoría de interés.

## 6. Preservación Multianual y Extracción de Series Temporales
- **Integridad de Modos Temporales:** El analizador debe preservar la estructura completa de la solicitud temporal:
  - Modos admitidos: `RANGE` (*"de 2019 al 2021"* $\to [2019, 2020, 2021]$), `LIST` (*"2018, 2020 y 2022"*), `RELATIVE_WINDOW` (*"últimos 5 años"*).
- **Prohibición de Truncamiento a Escalar:** Queda estrictamente prohibido truncar una solicitud de rango o lista al último año individual.
- **Auditoría Anual en Stage 5:** Cada año del rango o lista debe ser auditado de forma independiente contra el calendario muestral oficial, particionando los resultados en `observed_years` y `unobserved_years`.
- **Formato Tabular Forzado:** Siempre que `is_multi_year=True`, `SemanticDataFetcher` y el CLI deben estructurar y renderizar los datos como `series` cronológica con columna de año.

## 7. Extracción y Auditoría Multipaís No Destructiva
- **Escaneo Exhaustivo en Orden de Aparición:** Al detectar entidades geográficas, el analizador no debe detenerse (`break`) tras la primera coincidencia del diccionario. Debe escanear todas las menciones, ordenarlas por posición de inicio en el texto (`m.start()`), deduplicar por código ISO-3 y preservar la lista en `country_codes` y `country_names`.
- **Preservación en Filtros y Trazas:** Todos los países solicitados deben fluir hacia `AppliedFilters` y reflejarse de forma transparente en la línea `Geography:` del Stage 1 y en el CLI.
- **Filtrado Multipaís:** En la extracción empírica, el filtrado del DataFrame debe abarcar todos los códigos y nombres de país solicitados, incluyendo la columna `country` en cada fila de la serie resultante.

## 8. Principio Metodológico CEPAL: Estricta No-Interpolación y Puntos Ancla Oficiales
- **Prohibición Absoluta de Interpolación Lineal:** Las encuestas oficiales de hogares en América Latina y el Caribe tienen periodicidades heterogéneas (e.g., CASEN de Chile es bienal/trienal: 2017, 2020, 2022; mientras que ENAHO de Perú y GEIH de Colombia son anuales continuas). Está terminantemente prohibido imputar o promediar linealmente valores para años sin levantamiento muestral oficial (como Chile en 2021).
- **Auditoría Transversal por País en Stage 5:** Cuando una consulta multipaís incluye un año sin medición para alguno de los países solicitados, el motor debe:
  1. Asignar el estado `RESOLVED_WITH_ANCHORS`.
  2. Registrar en `TemporalAnchorInfo.country_anchors` los años sin medición y los puntos ancla adyacentes oficiales (`previous_anchor_year`, `next_anchor_year`) específicos de cada país afectado.
  3. Emitir un `disclaimer` explícito detallando los países con brecha y los puntos ancla disponibles, reiterando la prohibición de interpolación.
- **Rescate Automático de Observaciones Ancla en `--fetch`:**
  - Para los países con cobertura completa en el año solicitado, extraer el dato del año exacto.
  - Para los países con brechas muestrales, rescatar automáticamente del DataFrame las observaciones oficiales correspondientes a sus años ancla adyacentes (e.g., 2020 y 2022 para Chile en 2021).
  - Etiquetar dichas filas en la serie con `is_anchor=True`, `anchor_for_years=[año_solicitado]`, la nota `[Ancla oficial para ...]`, y en el CLI marcarlas visualmente (e.g., `2020*`).

## 9. Aislamiento de Miembros Sintéticos y Mapeo Empírico a Tablas Reales
- **Aislamiento de Miembros Sintéticos (`SYNTHETIC_DIMENSION_MEMBER_IDS`):** Los IDs de miembros creados como mock o placeholders en el slice vertical (e.g. ID `79578`) **NUNCA** deben enviarse como parámetro `members=` a la API viva de CEPALSTAT, pues colisionan con IDs de entidades geográficas (e.g. `79578` en dimensión de países es Chile), destruyendo la extracción multipaís. Dichos miembros se filtran en la frontera del extractor y se evalúan localmente sobre el DataFrame descargado.
- **Mapeo a Tablas Oficiales Publicadas (`EMPIRICAL_INDICATOR_ID_MAP`):** Los indicadores conceptuales del slice vertical que no corresponden directamente al ID de la tabla de la API en vivo deben mapearse de forma transparente y determinista a las tablas reales de CEPALSTAT (e.g., tasa de inflación anual general `2928 -> 2484`, PIB constante `729 -> 2204`), notificando al usuario en el CLI cuando ocurra un mapeo.

## 10. Prioridad de Columnas Legibles, Nombres Formales ONU y Períodos por Décadas
- **Prioridad de Columnas de Nombre sobre Códigos:** Al construir series para presentación o análisis, `SemanticDataFetcher` debe priorizar columnas descriptivas de país (`País__ESTANDAR`, `Países_agregados...`) por sobre columnas de código (`iso3`, `country_code`).
- **Nomenclatura Formal de Naciones Unidas:** El filtrado de países debe reconocer tanto nombres comunes como denominaciones formales de la ONU con calificaciones entre paréntesis (`"Bolivia (Estado Plurinacional de)"`, `"Venezuela (República Bolivariana de)"`), emparejando por prefijo limpio y validando de forma cruzada con la columna `iso3`.
- **Extracción Numérica de Períodos por Décadas:** En indicadores censales o demográficos cuya columna temporal es de tipo texto (e.g., `'Década 2010'`, `'Década 2020'`), el extractor debe extraer el año numérico mediante expresiones regulares `(1\d{3}|20\d{2})`, garantizando el ordenamiento cronológico y la compatibilidad con filtros temporales.

## 11. Léxico de Gentilicios Latinoamericanos y Resolución de Población Étnica
- **Cobertura Exhaustiva de Gentilicios en `COUNTRY_LEXICON`:** Las consultas en lenguaje natural frecuentemente expresan la geografía mediante gentilicios adjetivales (*"población peruana"*, *"inflación argentina"*, *"jóvenes chilenos"*). El diccionario geográfico debe indexar formas masculinas, femeninas, singulares y plurales, con y sin acentos diacríticos, para todos los países de la región.
- **Concepto Raíz `POBLACION` y Desgloses Demográficos:** Consultas sobre demografía o volumen poblacional deben resolver al concepto `POBLACION`, conmutando a indicadores censales específicos (`4788`, `4968`, `4969`, `4992`, `4639`) según las facetas de etnia, área o quintil, y activando desgloses multi-miembro (`ETNICO_TOTAL`) sin colapsar al agregado nacional.
