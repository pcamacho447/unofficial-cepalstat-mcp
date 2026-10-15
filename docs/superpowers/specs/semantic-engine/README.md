# Motor Semántico de Desambiguación para el MCP no oficial de CEPALSTAT

> **Especificación de Arquitectura e Ingeniería de Ontologías para la Desambiguación de Consultas en Lenguaje Natural**  
> **Catálogo de Referencia:** 2,143+ indicadores oficiales de CEPAL / ECLAC (CEPALSTAT)  
> **Metodología de Trabajo:** BMAD Party Mode + Brainstorming + Superpowers Architectural Specs  
> **Ruta del Proyecto:** `docs/superpowers/specs/semantic-engine/`

---

## 1. El Problema Fundamental de Búsqueda en CEPALSTAT

Cuando un usuario interactúa con un agente LLM o un cliente MCP y pregunta:
> *"Dame la pobreza de Brasil en 2021"*  
> *"¿Cuál es la inflación de alimentos en Colombia?"*  
> *"Muéstrame la brecha salarial femenina o el desempleo juvenil"*

El catálogo de CEPALSTAT no tiene una única respuesta trivial. Existen **99 indicadores que contienen la palabra "pobreza"**, docenas de series de precios e inflación, múltiples métricas de balanza de pagos, etc. 

Si un MCP simplemente hace un `LIKE '%pobreza%'` o un vector search naive sobre títulos de indicadores, el modelo o el usuario quedan atrapados en:
1. **Confusión métrica:** Retornar el *Índice de Feminidad de la Pobreza* (ratio mujeres/hombres pobres) en lugar de la *Tasa de Pobreza Total* (% de personas bajo la línea).
2. **Incompatibilidad de dimensiones:** Pedir datos rurales/urbanos para un indicador que solo existe a nivel nacional.
3. **Brechas de periodicidad:** Exigir datos anuales para encuestas de hogares bienales (como CASEN en Chile o ENIGH en México).
4. **Alucinación de IDs:** Hardcodear 5 indicadores arbitrarios como juguete técnico, haciendo al MCP inútil para la riqueza analítica de América Latina y el Caribe.

---

## 2. Formalización del Modelo Semántico (Tupla Canónica)

Para resolver este desafío a escala de todo el catálogo (2,143+ indicadores), el motor descompone toda consulta en una **Tupla Semántica Canónica de 4 Dimensiones**:

$$\mathcal{Q} \implies \langle \mathcal{P}_{\text{root}}, \mathcal{F}_{\text{facets}}, \mathcal{G}_{\text{geo}}, \mathcal{T}_{\text{temp}} \rangle$$

Donde:
- $\mathcal{P}_{\text{root}} \in \mathbf{Roots}$ (~25 Fenómenos Raíz Universales: `POBREZA`, `EMPLEO`, `PIB`, `INFLACION`, etc.).
- $\mathcal{F}_{\text{facets}} \subset \mathbf{Facets}$ (Conjunto de modificadores: sexo, tramo etario, área geográfica, quintil/decil, formalidad, sector).
- $\mathcal{G}_{\text{geo}} \in \mathbf{Geos}$ (País o agregado regional ISO-3 / CEPAL member ID).
- $\mathcal{T}_{\text{temp}} \in \mathbf{Times}$ (Año, rango de años, trimestre o frecuencia requerida).

A partir de esta tupla, un **Grafo de Prominencia Ponderado** selecciona el `indicator_id` canónico óptimo y reporta los indicadores alternativos relacionados sin ambigüedad.

---

## 3. Hoja de Ruta de Especificación (4 Sesiones Secuenciales)

| Sesión | Archivo de Especificación | Eje Central | Estado |
|---|---|---|---|
| **Sesión 1** | [`01-taxonomia-fenomenos-raiz.md`](./01-taxonomia-fenomenos-raiz.md) | **Taxonomía de los ~25 Fenómenos Raíz Universales:** Mapeo exhaustivo de las 23 áreas oficiales de CEPALSTAT a macro-fenómenos económicos, sociales y ambientales invariantes. | 🟢 **Completada** |
| **Sesión 2** | [`02-diccionario-facetas-modificadores.md`](./02-diccionario-facetas-modificadores.md) | **Diccionario Universal de Facetas y Modificadores:** Traducción determinista de lenguaje natural coloquial a dimensiones oficiales CEPAL (`Área`, `Sexo`, `Edad`, `Quintil`). | 🟢 **Completada** |
| **Sesión 3** | [`03-mecanismo-prominencia-enrutamiento.md`](./03-mecanismo-prominencia-enrutamiento.md) | **Mecanismo de Prominencia y Grafo de Enrutamiento:** Función de score $P(I \mid \mathcal{Q})$, backbone de indicadores canónicos por omisión (*default indicators*) y heurísticas de fallback. | 🟢 **Completada** |
| **Sesión 4** | [`04-frecuencia-disponibilidad-temporal.md`](./04-frecuencia-disponibilidad-temporal.md) | **Frecuencia, Periodicidad y Brechas de Disponibilidad:** Manejo de encuestas bienales vs anuales vs trimestrales, metadatos de fuentes oficiales y advertencias de no-cobertura. | 🟢 **Completada** |
| **Normativa v2** | [`05-revision-tecnica-arquitectura-v2.md`](./05-revision-tecnica-arquitectura-v2.md) | **Arquitectura v2 y Rigor Estadístico:** Integración de la revisión técnica, separación de 3 capas, relaciones tipadas, política de abstención, 4 estados temporales y benchmark. | 🟢 **Adoptada** |
| **Resumen** | [`resumen-ejecutivo.md`](./resumen-ejecutivo.md) | **Resumen Ejecutivo y Visión Integral:** Documento condensado para difusión y presentación técnica a colegas y tomadores de decisión. | 🟢 **Disponible** |

---

## 4. Participantes del Panel BMAD (Party Mode)

- 📈 **Raúl Prebisch (Econometrista Macro-estructuralista):** Custodio del rigor metodológico cepalino, consistencia entre encuestas de hogares y cuentas nacionales.
- 🏗️ **Winston (Arquitecto de Sistemas):** Diseñador del grafo de resolución, contratos JSON-RPC del MCP y robustez de esquemas.
- 💻 **Amelia (Senior Software Engineer):** Implementadora de motores de búsqueda, indexación SQLite/FTS5 y rendimiento de consultas.
- 📊 **Mary (Business & Data Analyst):** Mapeo de casos de uso de analistas, periodistas económicos y formuladores de política pública.
- 🎨 **Sally (Diseñadora UX / AI Interaction Specialist):** Claridad conversacional, retroalimentación al usuario y diseño de preguntas de desambiguación.
- 📋 **John (Product Manager):** Gestión de alcance, entregables incrementales y control de versiones de las especificaciones.
