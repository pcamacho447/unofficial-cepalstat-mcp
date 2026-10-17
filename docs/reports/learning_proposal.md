# Propuesta de Aprendizaje: Guardarraíles y Patrones de Resolución Semántica Multidimensional

## 1. Resumen Ejecutivo de Aprendizajes

Durante las sesiones de resolución semántica empírica y soporte a desglose multidimensional, se identificaron y resolvieron tres desafíos arquitectónicos críticos en el análisis de datos de CEPALSTAT:

1. **Riesgo de Degradación Silenciosa y Pérdida de Facetas (Facet Loss & False Substitution):**
   - *Problema:* Cuando una consulta en lenguaje natural incluye un modificador dimensional (e.g. *"pobreza étnica"*, *"pobreza infantil"*, *"por quintil"*), si el parser no reconoce o no enruta la faceta, el motor caía en el indicador canónico agregado (e.g. Indicador `3328` con `area=NACIONAL`), fabricando una respuesta plausible pero estadísticamente falsa.
   - *Solución:* Invariante de **Zero Facet Loss** y enrutamiento conmutable vía grafos (`BREAKDOWN_OF`). Si una consulta pide una dimensión específica no soportada en ningún indicador del grafo, el motor debe **abstenerse** (`UNSUPPORTED_FACET`) en vez de fabricar agregados.

2. **Anclaje Temporal Dinámico a $T_{\max}$ en Series Relativas:**
   - *Problema:* Las encuestas de hogares y cuentas nacionales en América Latina presentan un rezago estadístico intrínseco (publicación a $T - 1$ o $T - 2$). Anclar consultas como *"últimos 4 años"* contra el reloj del sistema ($T_{\text{system\_clock}}$) producía series vacías o truncadas.
   - *Solución:* Las ventanas relativas deben anclarse dinámicamente a $T_{\max} = \max(T_{\text{valid}})$ de las observaciones disponibles para el par (país, indicador).

3. **Higiene Léxica y Delimitadores de Palabra (`\b`):**
   - *Problema:* Términos cortos o polisémicos (e.g. *"raza"*, *"afro"*, *"edad"*, *"salario"*) colisionan con lenguaje coloquial o con otros dominios (e.g., la jerga mexicana *"la raza"* en consultas laborales).
   - *Solución:* Reglas estrictas de límites de palabra (`\b`), contexto de dominio y tests de no-regresión (e.g., SE-190).

---

## 2. Clasificación: Rules vs Skills

| Tipo | Archivo Destino | Justificación |
| :--- | :--- | :--- |
| **Rule** | `.agents/rules/semantic-resolution-guardrails.md` (o `.cursorrules` / `.agents/rules`) | **Obligatorio & No-Negociable:** Define restricciones duras que todo agente o desarrollador que modifique `statscepal.semantic` debe respetar (0.00% FSR, invariante anti-degradación, preservación de latencia $p50 < 0.5\text{ ms}$). |
| **Skill Update** | `.agents/skills/cepalstat-api/SKILL.md` | **Capacidad / Procedimiento Operativo:** Enseña a los agentes cómo invocar, testear y extender el motor de resolución semántica multidimensional (`statscepal.cli semantic resolve`) y cómo mapear indicadores multidimensionales (e.g., `3342`). |

---

## 3. Contenido Propuesto de la Regla

### Archivo: `.agents/rules/semantic-resolution-guardrails.md`

```markdown
# Guardarraíles de Resolución Semántica y Desglose Multidimensional

Al desarrollar, extender o refactorizar el motor semántico (`statscepal.semantic`), aplican los siguientes invariantes arquitectónicos obligatorios:

## 1. Invariante de Integridad Dimensional y Anti-Degradación
- **Cero Pérdida de Facetas (Zero Facet Loss):** Si una consulta del usuario contiene un calificador dimensional explícito (e.g. etnia, género, quintil, tramo etario, sector), el motor **NUNCA** debe ignorar la faceta para retornar el indicador agregado canónico.
- **Tasa de Sustitución Falsa Cero (FSR = 0.00%):** Bajo ninguna circunstancia se debe responder a una pregunta dimensional con una cifra agregada simulando que responde a la solicitud.
- **Abstención Explícita:** Si la dimensión solicitada no existe en la base de datos de CEPALSTAT para el dominio (e.g. *"pobreza por coeficiente intelectual"*), el motor debe responder `ABSTAINED` con razón `UNSUPPORTED_FACET_<DIM>` en lugar de inventar filtros por defecto.

## 2. Enrutamiento por Conmutación de Grafo (`BREAKDOWN_OF`)
- Los indicadores multidimensionales deben registrarse con sus dimensiones oficiales y enlazarse bidireccionalmente a su indicador canónico (e.g. `3342` como `BREAKDOWN_OF` `3328`).
- En la etapa de selección dimensional (Stage 4), el motor evalúa si el indicador preliminar soporta la faceta solicitada. Si no la soporta pero tiene un homólogo en el grafo que sí la soporta, conmuta automáticamente hacia el indicador de desglose.

## 3. Anclaje Temporal Dinámico en Series Relativas
- Las consultas relativas (*"últimos N años"*, *"última década"*) **NO** deben anclarse al año calendario del reloj del sistema.
- Deben anclarse dinámicamente al año máximo disponible $T_{\max} = \max(\text{observaciones}(\text{país}, \text{indicador}))$, considerando el rezago estadístico de las encuestas oficiales.

## 4. Presupuesto de Rendimiento y Calidad
- **Latencia:** El tiempo de resolución semántica local (SQLite + Thesauro en memoria) debe mantenerse estrictamente en $p50 < 0.5\text{ ms}$.
- **Higiene Regex:** Todos los patrones léxicos y de synsets deben usar delimitadores de palabra estrictos (`\b`) para evitar colisiones polisémicas o con modismos regionales.
- **Suite de Regresión:** Cualquier cambio debe certificar el 100.0% de acierto en el benchmark de 200 casos de prueba sin regresiones.
```

---

## 4. Actualización Propuesta para la Skill `cepalstat-api`

### Archivo: `.agents/skills/cepalstat-api/SKILL.md`

Se añade una sección dedicada a la interacción con el motor semántico y la CLI:

```markdown
### Motor de Resolución Semántica Multidimensional (CLI & API)

El paquete incorpora un motor determinístico y ultrarrápido ($p50 < 0.5\text{ ms}$) para resolver lenguaje natural a coordenadas formales de CEPALSTAT sin alucinación:

```bash
# Resolución de indicador canónico y filtros
uv run python -m statscepal.cli semantic resolve "cual es la pobreza en el peru en 2020"

# Resolución con desglose multidimensional (etnia, género, etc.)
uv run python -m statscepal.cli semantic resolve "cual es la pobreza etnica en el peru del 2020"

# Resolución con extracción de datos empíricos de la API
uv run python -m statscepal.cli semantic resolve "tasa de pobreza indigena en bolivia 2021" --fetch

# Series temporales multi-anuales y relativas
uv run python -m statscepal.cli semantic resolve "pobreza en chile los ultimos 4 anos" --fetch
```

#### Mapeo de Indicadores Multidimensionales Clave:
- **Pobreza Agregada / Área:** `3328` (*Población en situación de pobreza extrema y pobreza, por área*)
- **Pobreza Étnica / Racial:** `3342` (*Población en situación de pobreza extrema y pobreza, por sexo, autoidentificación étnico-racial y área*)
  - Dimensión `43039` (`Tipo de etnia`): Miembros `43041` (Indígena), `43042` (Afrodescendiente), `43044` (No indígena ni afrodescendiente), `43043` (Total).
```

---

## 5. Preguntas / Decisiones Abiertas

1. ¿Deseas que creemos la regla en `.agents/rules/semantic-resolution-guardrails.md` o prefieres integrarla dentro del archivo de instrucciones existente del proyecto?
2. ¿Aprobamos la actualización de `.agents/skills/cepalstat-api/SKILL.md` con estos parámetros?
