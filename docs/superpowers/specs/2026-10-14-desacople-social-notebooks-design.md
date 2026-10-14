# Especificación de Diseño: Suite de Análisis y Jupyter Notebooks de Desacople Crecimiento-Bienestar

## 1. Problema y Motivación

En América Latina y el Caribe, el crecimiento del Producto Interno Bruto (PIB) per cápita no se traduce de manera automática ni lineal en reducciones equivalentes de la pobreza o la desigualdad. Fenómenos como la inflación de alimentos, la informalidad laboral masiva y la contracción del salario mínimo real pueden esterilizar el impacto del crecimiento económico en los deciles de menores ingresos.

El objetivo de este sistema es dotar a `statscepal` de una **suite analítica e investigativa con soporte nativo para Jupyter Notebooks**, permitiendo a investigadores, analistas y agentes de IA:
1. Extraer y armonizar automáticamente series temporales de PIB per cápita, pobreza, salarios reales, inflación de alimentos e informalidad desde la API de CEPALSTAT.
2. Cuantificar el **Índice de Elasticidad Social del Crecimiento** y clasificar a las economías en cuadrantes de desempeño socioeconómico.
3. Explorar visual e interactivamente los procesos mediante un **Jupyter Notebook guiado y reproducible**.

---

## 2. Definición Teórica y Métricas

### 2.1. Elasticidad Social del Crecimiento ($\epsilon_{social}$)
$$\epsilon_{social} = \frac{\% \Delta \text{Pobreza Extrema / Total}_t}{\% \Delta \text{PIB per cápita real}_t}$$

- **$\epsilon < -1.0$ (Crecimiento Inclusivo / Pro-Pobre)**: Por cada 1% de aumento del PIB pc, la pobreza se reduce más del 1%.
- **$-0.2 < \epsilon \le 0$ (Crecimiento Desacoplado / Estéril)**: Crecimiento sin derrame social tangible.
- **$\epsilon > 0$ (Crecimiento Empobrecedor o Desacople Severo)**: Crecimiento con incremento simultáneo de la tasa de pobreza.

### 2.2. Cuadrantes de Desempeño Socioeconómico (Matriz 2x2)
1. **Cuadrante I: Crecimiento Virtuoso** ($\Delta \text{PIB} > 0, \Delta \text{Pobreza} < 0, \Delta \text{Gini} \le 0$).
2. **Cuadrante II: Crecimiento Excluyente / Concentrador** ($\Delta \text{PIB} > 0, \Delta \text{Pobreza} \ge 0 \text{ ó } \Delta \text{Gini} > 0$).
3. **Cuadrante III: Resiliencia Social** ($\Delta \text{PIB} \le 0, \Delta \text{Pobreza} \le 0$).
4. **Cuadrante IV: Doble Vulnerabilidad / Trampa de Involución** ($\Delta \text{PIB} \le 0, \Delta \text{Pobreza} > 0$).

### 2.3. Indicadores de CEPALSTAT Involucrados
- **`3894`**: Tasa de crecimiento anual del PIB real per cápita (%)
- **`3328`**: Población en situación de pobreza y pobreza extrema (%) por área geográfica
- **`340`**: Salario mínimo real (índice base 2018=100)
- **`3289`**: Índice de Gini de concentración del ingreso
- **`4788`**: Población total, según sexo (CELADE)

---

## 3. Arquitectura del Módulo (`statscepal.analysis`)

```
src/statscepal/
├── analysis/
│   ├── __init__.py
│   ├── models.py           # DecouplingRecord, CountryMetrics, DecouplingSummary
│   ├── metrics.py          # compute_elasticity, classify_quadrant, compute_decoupling_score
│   └── service.py          # DecouplingAnalyzer (orquestación, fetch, merge y armonización)
├── cli.py                  # Nuevo subcomando: statscepal analyze desacople
notebooks/
└── 01_desacople_crecimiento_bienestar.ipynb   # Notebook interactivo de investigación
```

---

## 4. Estructura del Jupyter Notebook (`notebooks/01_desacople_crecimiento_bienestar.ipynb`)

El notebook se estructura en 5 bloques pedagógicos y reproducibles:
1. **Configuración y Carga**: Inicialización del cliente `statscepal`, definición de países objetivo (`Argentina`, `Chile`, `Colombia`, `México`, `Perú`, `Uruguay`) y ventanas temporales (2015–2019 pre-pandemia vs. 2021–2023 post-pandemia).
2. **Extracción y Armonización**: Obtención de los DataFrames de los 5 indicadores de CEPAL y unión limpia por `(País, Año)`.
3. **Cálculo de Métricas y Elasticidades**: Aplicación de `compute_elasticity` y `classify_quadrant`.
4. **Visualizaciones**:
   - Scatter plot de cuadrantes con cuadrícula de referencia (Eje X: $\Delta$ PIB pc, Eje Y: $\Delta$ Pobreza).
   - Gráfico de barras comparativo de variación del Salario Mínimo Real (`340`).
5. **Diagnóstico y Exportación a Bitácora**: Generación del reporte de hallazgos y certificación en `.statscepal_cache.db`.
