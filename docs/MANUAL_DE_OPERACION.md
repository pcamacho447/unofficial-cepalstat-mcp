# Manual de Operación y Metodología: statscepal

## 1. Introducción y Contexto Regional
La Comisión Económica para América Latina y el Caribe (UN CEPAL / ECLAC) es la fuente oficial multilateral de estadísticas económicas, sociales, demográficas y ambientales para los países de América Latina y el Caribe (ALC).

A través del portal CEPALSTAT, se ofrecen cientos de indicadores armonizados. No obstante, al realizar análisis econométricos y consultas mediante modelos de lenguaje (LLM), suelen presentarse dos problemas críticos:
1. **Alucinaciones y Sesgo Metodológico**: Errores al interpretar unidades (ej. confundir miles de personas con personas individuales, pesos corrientes con dólares constantes de un año base particular), mezclar series censales con proyecciones poblacionales, o no advertir quiebres en las metodologías de cuentas nacionales.
2. **Consumo Ineficiente de Tokens**: La estructura dimensional de la CEPAL requiere explorar árboles de categorías y listar miembros dimensionales antes de consultar registros, lo cual puede consumir miles de tokens por cada pregunta.

El ecosistema `statscepal` resuelve estos problemas mediante la arquitectura **"Bitácora Primero"** y el módulo **`AntiBiasValidator`**.

---

## 2. Metodología Anti-Sesgo y Calidad Estadística

### 2.1. Factor de Escala y Unidades de Medida
Todo indicador en CEPALSTAT tiene una unidad oficial registrada en los metadatos. El módulo `AntiBiasValidator` valida la unidad y la categoriza:
- **Población**: Frecuentemente expresada en *"Miles de personas, a mitad del año"*. El validador exige una nota de escala explícita que instruye al usuario o agente a multiplicar por 1,000 para obtener personas individuales.
- **Cuentas Nacionales**: Los agregados macroeconómicos suelen estar en *"Millones de dólares a precios constantes"* o *"Porcentaje del PIB"*.
- **Precios e Inflación**: Variaciones porcentuales anuales o acumuladas respecto a una canasta base.

### 2.2. Manejo de Proyecciones vs. Datos Observados (CELADE)
En las series demográficas elaboradas por el Centro Latinoamericano y Caribeño de Demografía (CELADE) y la División de Población de la ONU:
- El horizonte 1950–2021 corresponde a **estimaciones empíricas** conciliadas con censos y estadísticas vitales.
- El año **2021** es el año base de corte.
- A partir de **2022 y hasta 2100**, los datos son **proyecciones probabilísticas** basadas en el método de componentes por cohorte (sujetas a supuestos de fecundidad, mortalidad y migración).
- **Regla del Validador**: Si la serie solicitada incluye años posteriores a 2021, se marca obligatoriamente `is_projection = true` y se anexa una advertencia metodológica en la ficha de la bitácora.

### 2.3. Detección de Saltos Temporales (Temporal Gaps)
El validador analiza la columna temporal (ej. `Años__ESTANDAR`). Si detecta que faltan años consecutivos (ej. serie 2015, 2016, 2018 sin el año 2017), emite una advertencia de **Discontinuidad Temporal** que previene estimar modelos econométricos lineales sin imputación o tratamiento de datos faltantes.

---

## 3. Arquitectura de las Bitácoras

Las bitácoras funcionan como **recetarios reproducibles y certificados**.

### 3.1. Organización de Carpetas
```
bitacoras/
├── paises/
│   ├── chile/
│   │   ├── 4788_recipe_chl_poblacion_total.md
│   │   └── 415_recipe_chl_pib_anual.md
│   ├── mexico/
│   ├── brasil/
│   └── argentina/
├── temas/
│   ├── demografia/
│   ├── macroeconomia/
│   └── pobreza/
└── modelos/
    └── series_tiempo/
```

### 3.2. Ciclo de Vida de una Receta
1. **Borrador / Consulta Exploratoria**: Un agente o analista utiliza `statscepal search` o `statscepal fetch` para consultar un indicador nuevo.
2. **Auditoría**: Se ejecuta `AntiBiasValidator.audit()` sobre el DataFrame resultante y los metadatos oficiales.
3. **Certificación**: Si los datos son consistentes y tienen metadatos válidos, se genera la ficha Markdown con frontmatter YAML y estado `status: "certified"`.
4. **Indexación**: La receta se registra en `.statscepal_cache.db` para que las futuras búsquedas de cualquier agente sean instantáneas.

### 3.3. Relación entre Catálogo Maestro y Bitácoras
Es fundamental distinguir las dos capas del sistema:
- **Catálogo Maestro (`statscepal catalog`)**: Contiene el índice de los **2,070 indicadores oficiales** de la CEPAL estructurados en SQLite local (`.statscepal_cache.db`). Sirve para **descubrimiento instantáneo** (en < 2 ms y 0 tokens de red): saber qué indicadores existen, cuál es su `indicator_id`, su tema y su área oficial.
- **Bitácoras (`statscepal bitacora`)**: Contienen las **recetas analíticas certificadas**. No solo guardan el nombre del indicador, sino los códigos de miembros validados (ej. Chile = 224, Año 2020 = 29190), el código Python reproducible, las alertas de escala y la auditoría estadística del `AntiBiasValidator`.

---

## 4. Guía para Incorporar Nuevos Países e Indicadores

### Paso 1: Descubrir Indicadores en el Catálogo Maestro Offline
Antes de consultar la red, busca en el catálogo local de 2,070 indicadores:
```bash
# Ver estadísticas generales
uv run statscepal catalog stats

# Búsqueda filtrada por tema (ej. Mercado Laboral / Desempleo)
uv run statscepal catalog search "desempleo" --theme "Económicos"
# Resultado: Indicador 2427 (Tasa de desocupación abierta)
```

### Paso 2: Consultar los Códigos de País y Año
Consulta la guía de referencia en [`.agents/skills/cepalstat-api/references/dimensions-reference.md`](file:///C:/papx/statscepal/.agents/skills/cepalstat-api/references/dimensions-reference.md):
- **Chile**: `224`
- **México**: `238`
- **Brasil**: `222`
- **Argentina**: `218`
- **Colombia**: `225`
- **Perú**: `242`

### Paso 3: Extraer y Certificar en la Bitácora
```bash
uv run statscepal bitacora add 2427 --country Mexico --members 238 --tags mexico,empleo,mercado_laboral
```
El sistema automáticamente:
- Descarga los datos de la CEPAL.
- Ejecuta la auditoría anti-sesgo.
- Guarda la ficha en `bitacoras/paises/mexico/2427_recipe-mex-2427-desemp.md`.
- Actualiza el índice SQLite local.

---

## 5. Integración con Agentes de IA en Antigravity

El repositorio provee el **Skill `cepalstat-api`** y los subagentes **`cepalstat_analyst`** y **`cepalstat_expert`**.

### Protocolo para Agentes
Cuando un agente reciba una pregunta como:
> *"Dame la población proyectada de Chile para 2025 y el PIB de los últimos 5 años"*

El agente seguirá este flujo determinista:
1. **Ejecuta `statscepal bitacora lookup poblacion --country Chile`**:
   - Encuentra inmediatamente la receta `recipe-chl-4788-pob`.
   - Lee que la unidad es miles de personas y que 2025 es un dato proyectado de CELADE.
   - Gasto de tokens: **~150 tokens** (en lugar de ~3,000 tokens de navegación de árbol).
2. **Ejecuta `statscepal bitacora lookup pib --country Chile`**:
   - Encuentra la receta `recipe-chl-415-pib`.
   - Conoce directamente que el código de país es 224 y la unidad son millones de USD constantes.
3. **Genera la respuesta libre de sesgo y alucinaciones**:
   - Cita la fuente oficial (CEPAL / CELADE).
   - Multiplica correctamente por 1,000 para informar el total de habitantes.
   - Advierte que el dato demográfico de 2025 es una proyección estadística sujeta a supuestos de fecundidad y migración.
