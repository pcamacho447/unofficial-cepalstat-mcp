# Bitácoras Analíticas, Mitigación de Sesgos y Optimización de Tokens para CEPALSTAT

## 1. Contexto y Objetivos

### Problema
1. **Gasto excesivo de tokens**: Cuando un agente o analista consulta la API de CEPALSTAT para obtener datos de un país (ej. Chile), suele navegar repetitivamente árboles temáticos de miles de nodos o consultar esquemas de dimensiones completos.
2. **Riesgo de sesgo y alucinaciones**: Errores comunes en respuestas de analítica y econometría incluyen:
   - Confundir unidades de escala (ej. miles de personas vs. personas; USD corrientes vs. constantes).
   - Mezclar estimaciones históricas con proyecciones futuras (ej. corte base CELADE 2021).
   - Ignorar quiebres de series estadísticas o años con datos faltantes.
3. **Falta de reproducibilidad**: Las recetas de consulta y los scripts de extracción exitosos se pierden entre sesiones de chat.

### Objetivos
1. Crear un sistema de **Bitácoras (Codebooks / Query Recipes)** ordenadas por país, tema y modelo econométrico.
2. Implementar un **Módulo Validador Anti-Sesgo (`AntiBiasValidator`)** que certifique cada serie estadística antes de su registro.
3. Establecer un protocolo **"Bitácora Primero"** que ahorre entre un 80% y 90% de tokens de inferencia.
4. Dotar al CLI `statscepal` y a los agentes de Antigravity de comandos para consultar (`lookup`), registrar (`add`) y auditar (`audit`) bitácoras.

---

## 2. Comparativa de los 3 Enfoques

| Dimensión | Enfoque 1: Híbrido (Markdown + SQLite + Validador) | Enfoque 2: Exclusivo Markdown en Git | Enfoque 3: Almacén Vectorial (Embeddings/RAG) |
| :--- | :--- | :--- | :--- |
| **Almacenamiento** | Fichas Markdown en Git + SQLite local `.statscepal_cache.db` | Solo archivos Markdown/YAML en `bitacoras/` | ChromaDB / Vector DB + embeddings locales |
| **Gasto de tokens** | Mínimo (~150 tokens por ficha inyectada) | Mínimo (~150 tokens) | Medio-Alto (chunks + re-ranking) |
| **Velocidad de búsqueda** | Instantánea (índice SQLite por país/tema/año) | Lineal (inspección de archivos en disco) | Moderada (cálculo de embeddings) |
| **Mitigación de sesgos** | Alta (validador automático con auditoría de datos) | Manual (depende del usuario) | Baja (riesgo de similitud semántica espuria) |
| **Dependencias** | Ninguna adicional (Python estándar `sqlite3` + `pandas`) | Ninguna | Pesadas (`chromadb`, `torch`, `transformers`) |
| **Decisión** | **SELECCIONADO** (Óptimo en balance técnica/costo) | Descartado como solución única | Descartado por sobreingeniería (YAGNI) |

---

## 3. Arquitectura del Sistema

```
C:\papx\statscepal\
├── bitacoras/                      # Repositorio Git de fichas y recetas
│   ├── paises/
│   │   ├── chile/
│   │   │   ├── 4788_poblacion_total.md
│   │   │   └── 415_pib_anual.md
│   │   └── mexico/
│   ├── temas/
│   │   ├── demografia/
│   │   └── macroeconomia/
│   └── modelos/
│       └── series_tiempo/
│
├── .statscepal_cache.db            # Base de datos SQLite local (índice y caché)
│
└── src/statscepal/bitacora/        # Módulo Python del motor de bitácoras
    ├── __init__.py
    ├── models.py                   # Pydantic models (BitacoraRecipe, DataQualityReport)
    ├── store.py                    # Gestor de Markdown y sincronización SQLite
    └── validator.py                # Validador estadístico anti-sesgo
```

---

## 4. Estructura de una Ficha de Bitácora (`recipe.md`)

```yaml
---
id: recipe-chl-4788-pob
indicator_id: 4788
indicator_name: "Población total, según sexo"
country: "Chile"
country_iso3: "CHL"
country_member_id: 224
theme: "Demográficos y sociales > Demográficos"
unit: "Miles de personas, a mitad del año"
base_year_split: 2021
projection_warning: true
status: "certified"
date_certified: "2026-10-14"
tags: ["demografia", "poblacion", "chile", "celade"]
---

# Receta: Población total en Chile

## Alertas Anti-Sesgo y Calidad de Datos
- **Unidad**: Cifras expresadas en **miles de personas**. Para obtener personas totales, multiplicar por 1,000.
- **Quiebre metodológico**: El año base es **2021**. Las observaciones hasta 2021 corresponden a estimaciones y censos conciliados; las cifras a partir de 2022 son **proyecciones demográficas** sujetas a supuestos de fecundidad y migración.
- **Valores nulos**: 0% en la serie 1950-2024.

## Código Reproducible en Python
```python
from statscepal import CepalStatClient, DataExtractor

with CepalStatClient() as client:
  extractor = DataExtractor(client)
  # Chile=224, Años 2020 (29190) a 2023 (29193)
  df = extractor.get_dataframe(4788, members=[224, 29190, 29191, 29192, 29193])
```
```

---

## 5. Módulo Validador Anti-Sesgo (`AntiBiasValidator`)

Reglas que se ejecutan automáticamente antes de certificar una receta:
1. **Verificación de Unidad y Escala**: Almacena explícitamente la unidad oficial y emite advertencia si es una tasa, porcentaje o cifra multiplicada por factor.
2. **Chequeo de Quiebre Temporal / Proyecciones**: Detecta si la serie contiene proyecciones (ej. CELADE o CEPAL Proyecciones) y marca el año de quiebre.
3. **Auditoría de Datos Tabulares**:
   - Conteo de registros válidos vs. nulos (`null_count`, `null_ratio`).
   - Detección de discontinuidades temporales (gaps en años consecutivos).
   - Cálculo de estadísticas resumen (mínimo, máximo, media, mediana).
4. **Bandera de Certificación**: Solo si pasa estas comprobaciones, se marca `status: certified`.

---

## 6. Comandos CLI para Bitácoras

- `statscepal bitacora lookup <termino> [--country <pais>] [--tag <tag>]`
  - Busca en el índice local SQLite / Markdown en < 10ms.
- `statscepal bitacora add <indicator_id> --country <pais> [--members <ids>] [--tags <t1,t2>]`
  - Descarga los datos, ejecuta el validador anti-sesgo y crea el archivo Markdown + registro en SQLite.
- `statscepal bitacora list`
  - Muestra un resumen tabular de todas las recetas certificadas existentes.
- `statscepal bitacora sync`
  - Reconstruye el índice SQLite a partir de los archivos Markdown existentes en `bitacoras/`.

---

## 7. Integración con Skills y Agentes de Antigravity

- **Skill `cepalstat-api`**: Se añade el Paso 0 obligatorio:
  > *"Antes de llamar a la API externa, consulte las bitácoras locales (`statscepal bitacora lookup`). Si la receta existe, use sus códigos certificados directamente para ahorrar tokens y garantizar datos sin sesgo."*
- **Subagente `cepalstat_analyst`**: Configurado para certificar automáticamente nuevas recetas cuando una investigación econométrica concluya con éxito.
