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
