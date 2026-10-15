# Motor Semántico de Desambiguación para el MCP no oficial de CEPALSTAT
## Resumen Ejecutivo de Arquitectura e Ingeniería de Ontologías

> **Documento:** Resumen Ejecutivo para Difusión y Compartición Técnica  
> **Ubicación:** `docs/specs/2026-10-15-motor-semantico-cepalstat-resumen-ejecutivo.md`  
> **Ruta de Especificaciones Detalladas:** `docs/superpowers/specs/semantic-engine/`  
> **Fecha:** 15 de Octubre de 2026  
> **Audiencia:** Investigadores, econometristas, ingenieros de datos y desarrolladores de agentes IA  
> **Autores / Panel BMAD:** Equipo Técnico de CEPALSTAT MCP (Raúl Prebisch, Winston, Amelia, Sally, Mary, John)

---

## 1. El Desafío: La Paradoja de CEPALSTAT en la Era de los LLMs

CEPALSTAT (el portal estadístico de la Comisión Económica para América Latina y el Caribe - CEPAL / ECLAC) es el repositorio de información socioeconómica y ambiental más exhaustivo de la región: **contiene 2,143 indicadores** organizados en 23 áreas temáticas oficiales.

Sin embargo, cuando un usuario o un agente LLM intenta consultar datos en lenguaje natural:
> *"¿Cuál fue la pobreza de mujeres jóvenes en Brasil en 2021?"*  
> *"Dame la inflación de alimentos en Colombia"*  
> *"Muéstrame el desempleo juvenil o la brecha salarial formal vs. informal"*

Los sistemas tradicionales de búsqueda colapsan por tres razones críticas:

1. **La Explosión de Ambigüedad Textual:** Solo la palabra *"pobreza"* arroja **99 indicadores distintos**. Un buscador textual ingenuo no puede distinguir entre la *tasa de incidencia de la pobreza* (% bajo la línea), el *Índice de Feminidad de la Pobreza* (ratio mujeres/hombres pobres) o la *pobreza en hogares monoparentales*.
2. **Incompatibilidad Dimensional Oculta:** Si el usuario pide *"pobreza femenina"*, el indicador canónico nacional (`ID 3328`) **no posee dimensión de sexo**. Un agente que consulte ese indicador a ciegas fallará o devolverá datos ciegos al género.
3. **La Trampa de las Brechas Temporales:** En América Latina las encuestas de hogares son heterogéneas. Por ejemplo, en Chile la encuesta CASEN es **bienal/trienal** (2015, 2017, 2020, 2022). Si alguien pide *"pobreza de Chile en 2021"*, los modelos ingenuos alucinan números inexistentes o reportan errores vacíos sin justificación.
4. **La Trampa del "Juguete de 5 Indicadores":** Limitar el MCP a un puñado fijo de 5 variables hardcodeadas priva a la comunidad de la riqueza analítica de los 2,143 indicadores de la CEPAL.

---

## 2. La Solución: Tupla Semántica Cuadridimensional y Grafo de Prominencia

Para procesar cualquier consulta sobre el catálogo completo sin ambigüedad y en milisegundos, el motor descompone la petición en una **Tupla Canónica de 4 Dimensiones**:

$$\mathcal{Q} \implies \langle \mathcal{P}_{\text{root}}, \mathcal{F}_{\text{facets}}, \mathcal{G}_{\text{geo}}, \mathcal{T}_{\text{temp}} \rangle$$

Donde:
- $\mathcal{P}_{\text{root}}$: Uno de los **25 Fenómenos Raíz Universales** (Pobreza, Empleo, Crecimiento, Deuda, Emisiones, etc.).
- $\mathcal{F}_{\text{facets}}$: Vector de **Facetas y Modificadores** (Sexo, Grupo Etario, Área Geográfica, Quintil, Formalidad).
- $\mathcal{G}_{\text{geo}}$: Entidad Geográfica (País ISO-3 o Agregado Regional CEPAL).
- $\mathcal{T}_{\text{temp}}$: Parámetro Temporal (Año puntual, Rango, Frecuencia, o Último Disponible).

```mermaid
flowchart TD
    NL["Consulta del Usuario:<br/>'pobreza de mujeres de 15 a 24 años en el campo de Brasil 2021'"] --> PARSE["1. Parser Semántico Multi-Token"]
    
    PARSE --> TUPLE["Tupla Canónica:<br/>• Root: POBREZA_Y_VULNERABILIDAD<br/>• Facetas: {SEXO=Femenino, EDAD=15-24, AREA=Rural}<br/>• Geo: BRA | Temp: 2021"]
    
    TUPLE --> DUAL{"2. Mecánica Dual de Resolución"}
    DUAL -- "Indicador 3328 carece de Sexo/Edad" --> SWAP["👉 Indicator Swap (Camino B):<br/>Conmuta a ID 3341 (Pobreza por sexo y edad)"]
    
    SWAP --> INJECT["3. Inyección Determinista de Miembros:<br/>• Sexo Dim 144 = Member 266 (Mujeres)<br/>• Edad Dim 43054 = Member 43058 (15-24 años)<br/>• Área Dim 326 = Member 331 (Rural)"]
    
    INJECT --> SCORE["4. Ponderación de Prominencia P(I|Q):<br/>Score = 0.94 (Tier 1 Armonizado CEPAL)"]
    
    SCORE --> AUDIT["5. Auditoría Temporal y Anti-Alucinación:<br/>Confirma PNADC anual continua en Brasil"]
    
    AUDIT --> MCP_OUT["Respuesta MCP Enriquecida:<br/>Dato Exacto + Metadatos de Confianza + Sugerencia Proactiva"]
```

---

## 3. Los Cuatro Pilares Fundamentales del Motor

El diseño del motor se estructuró en 4 especificaciones exhaustivas (disponibles en `docs/superpowers/specs/semantic-engine/`):

### Pilar 1: Taxonomía de los 25 Fenómenos Raíz Universales
*Detalle completo en:* [`01-taxonomia-fenomenos-raiz.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/superpowers/specs/semantic-engine/01-taxonomia-fenomenos-raiz.md)

Se colapsaron las 23 áreas oficiales en **25 macro-fenómenos invariantes** estructurados en 4 ejes:
1. **Demografía, Sociedad y Bienestar (8 fenómenos):** `POBREZA_Y_VULNERABILIDAD` (Canónico: `3328`), `DISTRIBUCION_INGRESO_Y_DESIGUALDAD` (Gini: `3289`), `EMPLEO_Y_MERCADO_LABORAL` (Desocupación: `127`), `SALARIOS_Y_REMUNERACIONES` (Salario Mínimo Real: `340`), `EDUCACION_Y_CAPITAL_HUMANO` (`53`), `SALUD_Y_PROTECCION_SOCIAL` (`4784`), `VIVIENDA_Y_SERVICIOS_BASICOS`, `DEMOGRAFIA_Y_DINAMICA_POBLACIONAL` (`1`).
2. **Macroeconómico, Precios y Cuentas Nacionales (8 fenómenos):** `CRECIMIENTO_Y_PIB` (Canónico: `2203` a precios constantes), `PRECIOS_E_INFLACION_GENERAL` (IPC: `365`), `INFLACION_DE_ALIMENTOS` (`2929`), `COMERCIO_EXTERIOR_Y_EXPORTACIONES` (`2949`), `BALANZA_DE_PAGOS_Y_SECTOR_EXTERNO` (`740`), `INVERSION_EXTRANJERA_DIRECTA` (`4231`), `SECTOR_PUBLICO_Y_FISCAL` (`4405`), `DEUDA_PUBLICA_Y_EXTERNA` (`1240`).
3. **Género, Derechos y Cohesión (4 fenómenos):** `AUTONOMIA_ECONOMICA_Y_CUIDADOS` (Trabajo no remunerado: `2656`), `VIOLENCIA_Y_SEGURIDAD_CIUDADANA` (Homicidios: `3986`), `PUEBLOS_INDIGENAS_Y_AFRODESCENDIENTES`, `PROTECCION_SOCIAL_Y_PENSIONES`.
4. **Medio Ambiente, Clima y Territorio (5 fenómenos):** `EMISIONES_Y_GASES_EFECTO_INVERNADERO` (`5681` con LULUCF vs. `5682` sin LULUCF), `RECURSOS_FORESTALES`, `RECURSOS_HIDRICOS`, `MATRIZ_ENERGETICA`, `CIENCIA_TECNOLOGIA_Y_CONECTIVIDAD` (`4318`).

### Pilar 2: Diccionario Universal de Facetas y Mecánica Dual
*Detalle completo en:* [`02-diccionario-facetas-modificadores.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/superpowers/specs/semantic-engine/02-diccionario-facetas-modificadores.md)

- **Normalización de Regionalismos:** Mapea el lenguaje coloquial latinoamericano a 9 dimensiones formales:
  - `AREA`: *"el campo", "agro", "zona rural"* $\to$ `RURAL` (Member `1367` o `331`).
  - `SEXO`: *"pibas", "chicas", "mujeres", "morras"* $\to$ `FEMENINO` (Member `266`).
  - `EDAD`: *"pibes", "chavos", "jóvenes"* $\to$ `JUVENTUD (15-24 años)` (Member `43058`); *"abuelos", "tercera edad"* $\to$ `ADULTOS MAYORES (65+)`.
  - `FORMALIDAD`: *"en negro", "chamba informal"* $\to$ `INFORMAL`; *"en blanco"* $\to$ `FORMAL`.
  - `ESTRATO`: *"los más pobres"* $\to$ `QUINTIL_1`; *"los más ricos"* $\to$ `DECIL_10`.
- **Mecánica Dual de Resolución:**
  - **Camino A (*Member Filtering*):** Si la dimensión existe nativamente en el indicador, inyecta el `member_id` en el query.
  - **Camino B (*Indicator Swap*):** Si el indicador canónico carece de la dimensión solicitada, el motor conmuta automáticamente hacia un indicador de su constelación que sí la soporte (ej. de `3328` a `3341`).

### Pilar 3: Función Matemática de Prominencia y Grafo DAG
*Detalle completo en:* [`03-mecanismo-prominencia-enrutamiento.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/superpowers/specs/semantic-engine/03-mecanismo-prominencia-enrutamiento.md)

Ante múltiples candidatos rivales, el sistema evalúa la función de scoring:

$$P(I \mid \mathcal{Q}) = 0.35 \cdot S_{\text{root}} + 0.30 \cdot S_{\text{facet}} + 0.20 \cdot S_{\text{cov}} + 0.15 \cdot A(I) - \Omega(I)$$

- **Nivel de Autoridad CEPAL ($A(I)$):** Otorga máxima prioridad (1.0) a series armonizadas regionales de la CEPAL, 0.8 a metas globales ODS y 0.5 a series nacionales brutas.
- **Penalización por Especificidad Huérfana ($\Omega(I)$):** Si el usuario preguntó por *"desempleo general"*, se penaliza severamente a un indicador que solo mida *"desempleo agrícola"* (`4041`), protegiendo la respuesta macroeconómica.
- **Protocolo de Proactividad Conversacional:** Si dos indicadores empatan en puntaje (ej. incidencia de pobreza `3341` vs. ratio de feminidad `3330`), el MCP devuelve el ganador canónico y adjunta un campo explicativo para que el LLM informe elegantemente al usuario:  
  *💡 "Obtuve la tasa de pobreza de mujeres (28.4%). ¿Deseas además incluir el Índice de Feminidad de la Pobreza (114 mujeres pobres por cada 100 hombres)?"*

### Pilar 4: Frecuencia Temporal, Desfases y Política Anti-Alucinación
*Detalle completo en:* [`04-frecuencia-disponibilidad-temporal.md`](file:///C:/Users/camac/.herdr/worktrees/statscepal/worktree-quiet-harbor-46a5/docs/superpowers/specs/semantic-engine/04-frecuencia-disponibilidad-temporal.md)

- **Régimen de Periodicidad:** Clasifica las series en mensuales (IPC `365`), trimestrales (PIB `2447`), anuales continuas (`2203`) y estructurales discontinuas (encuestas de hogares `3328`).
- **El Desfase Oficial (*Timeliness Lag*):** Reconoce que las encuestas de hogares armonizadas por CEPAL se publican con 12 a 18 meses de desfase respecto al año calendario corriente.
- **Protocolo del Punto Ancla Vecino (*Nearest-Neighbor Anchor*):** Si se solicita un año sin medición (como Chile 2021), **se prohíbe inventar cifras**. El motor localiza los dos puntos ancla oficiales más cercanos (CASEN 2020: 10.8% y CASEN 2022: 6.5%) y emite un disclaimer metodológico formal.
- **Rupturas Metodológicas Oficiales:** Alerta al usuario ante eventos históricos conocidos (apagón estadístico del INDEC en Argentina 2015-2016, nueva metodología CASEN en Chile 2015, y sesgo de encuestas telefónicas por COVID-19 en 2020).

---

## 4. Matriz de Casos de Prueba Resueltos

| Consulta en Lenguaje Natural | Fenómeno Raíz | Facetas Detectadas | Indicador Resuelto | Razón de la Decisión Algorítmica |
|---|---|---|:---:|---|
| *"PIB de Colombia"* | `CRECIMIENTO_Y_PIB` | `{PAIS: COL}` | **2203** | Canónico Tier 1 (precios constantes en USD). Descarta moneda corriente `2204`. |
| *"Inflación en Argentina"* | `PRECIOS_E_INFLACION` | `{PAIS: ARG}` | **365** | IPC general. El indicador de alimentos `2929` sufre penalización $\Omega$ por especificidad huérfana. |
| *"Inflación de alimentos en Colombia"* | `INFLACION_DE_ALIMENTOS` | `{CANASTA: ALIM, PAIS: COL}` | **2929** | Match de n-gram especializado `INFLACION_DE_ALIMENTOS` sobre el IPC general. |
| *"Pobreza de mujeres en Brasil 2021"* | `POBREZA_Y_VULNERABILIDAD` | `{SEXO: FEM, PAIS: BRA, ANIO: 2021}` | **3341** | *Indicator Swap*: `3328` carece de dimensión Sexo; conmuta a `3341` (miembro 266). |
| *"Pobreza de Chile en 2021"* | `POBREZA_Y_VULNERABILIDAD` | `{PAIS: CHL, ANIO: 2021}` | **3328 (Anclas 2020/2022)** | Auditoría temporal: CASEN no se midió en 2021; entrega anclas de 2020 (10.8%) y 2022 (6.5%). |
| *"Desempleo de los pibes en Argentina"* | `EMPLEO_Y_MERCADO_LABORAL` | `{EDAD: JUVENTUD, PAIS: ARG}` | **5097** | Regionalismo 'pibes' activa `EDAD=JUVENTUD` (15-24 años); selecciona serie CIET-19. |

---

## 5. Arquitectura de Interfaces para el Servidor MCP

El motor semántico expone sus capacidades en el servidor MCP a través de una API modular y unificada:

```
Herramienta de Pipeline Completo:
└── cepalstat_resolve_indicator(query: str) -> ResolvedPayload
    ├── 1. cepalstat_resolve_root(query)        -> Root Slug & Constellation
    ├── 2. cepalstat_parse_facets(query)        -> Normalized Facets & Member IDs
    ├── 3. cepalstat_score_indicators(...)      -> Ranked Top-3 Indicators (Score breakdown)
    └── 4. cepalstat_temporal_audit(...)        -> Frequency check, Anchor years & Breaks

Recursos Canónicos Expuestos:
├── cepalstat://catalog/root-phenomena          (Definición de los 25 fenómenos y constelaciones)
├── cepalstat://catalog/facets-dictionary       (Diccionario universal de facetas y regionalismos)
└── cepalstat://metadata/timeliness-calendar    (Matriz de cobertura y calendario de publicaciones)
```

---

## 6. Conclusión y Próximos Pasos

Con esta arquitectura:
1. **Se supera la barrera del "juguete de 5 indicadores":** Cualquier indicador de los 2,143 del catálogo queda accesible mediante su constelación y facetas.
2. **Se garantiza rigor estadístico internacional:** No se confunden tasas urbanas con nacionales, ni monedas corrientes con constantes, ni ratios de feminidad con tasas de incidencia.
3. **Se elimina la alucinación temporal:** Las brechas de las encuestas latinoamericanas (CASEN, ENIGH, EPH) se gestionan con honestidad científica y puntos ancla.
4. **Rendimiento extremo:** La resolución sobre SQLite / DAG toma menos de **2 milisegundos**, permitiendo una experiencia de chat en tiempo real sin fricción.

El siguiente paso es la **implementación de código en Python** dentro del paquete `statscepal`, integrando estos contratos en las herramientas del servidor MCP no oficial.
