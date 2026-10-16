# Guardarraíles de Resolución Semántica y Desglose Multidimensional

Al desarrollar, extender o refactorizar el motor semántico (`statscepal.semantic`), aplican los siguientes invariantes arquitectónicos y de calidad estadística:

## 1. Invariante de Integridad Dimensional y Anti-Degradación
- **Cero Pérdida de Facetas (Zero Facet Loss):** Si una consulta del usuario contiene un calificador dimensional explícito (e.g. etnia, género, quintil, tramo etario, sector geográfico), el motor **NUNCA** debe ignorar la faceta para retornar el indicador agregado canónico.
- **Tasa de Sustitución Falsa Cero (FSR = 0.00%):** Bajo ninguna circunstancia se debe responder a una pregunta dimensional con una cifra agregada simulando que responde a la solicitud.
- **Abstención Explícita:** Si la dimensión solicitada no existe en la base de datos de CEPALSTAT para el dominio (e.g. *"pobreza por coeficiente intelectual"*), el motor debe responder `ABSTAINED` con razón `UNSUPPORTED_FACET_<DIM>` en lugar de inventar filtros por defecto o degradar a nivel nacional agregado.

## 2. Enrutamiento por Conmutación de Grafo (`BREAKDOWN_OF`)
- Los indicadores multidimensionales deben registrarse con sus dimensiones oficiales y enlazarse bidireccionalmente a su indicador canónico (e.g. Indicador `3342` como `BREAKDOWN_OF` `3328`).
- En la etapa de selección dimensional (Stage 4 de `SemanticResolutionEngine`), el motor evalúa si el indicador preliminar soporta la faceta solicitada. Si no la soporta pero tiene un homólogo en el grafo que sí la soporta, conmuta automáticamente hacia el indicador de desglose.
- Si se solicitan filtros miembros (e.g. `INDIGENA`, `AFRODESCENDIENTE`), el `DynamicMemberMatcher` debe asociar el ID de miembro exacto a la dimensión oficial (`43039: Tipo de etnia`).

## 3. Anclaje Temporal Dinámico en Series Relativas
- Las consultas relativas (*"últimos N años"*, *"última década"*) **NO** deben anclarse al año calendario del reloj del sistema ($T_{\text{system\_clock}}$).
- Deben anclarse dinámicamente al año máximo disponible $T_{\max} = \max(\text{observaciones}(\text{país}, \text{indicador}))$, considerando el rezago estadístico de publicación de las encuestas oficiales de hogares y cuentas nacionales.

## 4. Presupuesto de Rendimiento, Regex y Calidad
- **Latencia:** El tiempo de resolución semántica local (SQLite + Thesauro en memoria) debe mantenerse estrictamente en $p50 < 0.5\text{ ms}$.
- **Higiene Regex:** Todos los patrones léxicos y de synsets deben usar delimitadores de palabra estrictos (`\b`) para evitar colisiones polisémicas o con modismos regionales (e.g., la jerga *"raza"* en México vs dimensión étnico-racial).
- **Suite de Regresión:** Cualquier cambio debe certificar el 100.0% de acierto en el benchmark de 200 casos de prueba sin regresiones (`tests/test_semantic_benchmark_200.py`).
