# Especificación de Diseño: Catálogo Maestro Local de Indicadores CEPALSTAT

## 1. Problema y Motivación

Actualmente, buscar un indicador en CEPALSTAT requiere realizar una petición HTTP completa a `/thematic-tree` (~1.5 MB de JSON no comprimido) en cada búsqueda en frío, o confiar en que el analista ya conoce el `indicator_id`.

La API de CEPALSTAT contiene exactamente **2,070 indicadores oficiales** distribuidos en 4 grandes pilares temáticos:
1. Demográficos y Sociales
2. Económicos (PIB, Precios, Comercio, Balanza de Pagos, Sector Público)
3. Ambientales (Recursos, Residuos, Desastres, Calidad Ambiental)
4. Temas Transversales (ODS, Género, Pueblos Indígenas, TIC)

### Objetivos de Optimización
1. **Búsqueda Instantánea Offline (0 tokens de red, < 5 ms)**: Indexar localmente los 2,070 indicadores en la base SQLite del proyecto (`.statscepal_cache.db`).
2. **Búsqueda Robusta (Case-Insensitive y Tolerante a Acentos)**: Permitir encontrar "poblacion", "PIB", "litio", "desempleo" sin fallos por mayúsculas o tildes.
3. **Resumen Estadístico y Clasificación Temática**: Capacitar a los agentes de IA para inspeccionar la taxonomía oficial de la CEPAL sin consultar la red.
4. **Cero Dependencias Externas Nuevas**: Utilizar el motor SQLite integrado en Python estándar (`sqlite3`).

---

## 2. Decisiones de Diseño Óptimas

| Decisión | Alternativa Evaluada | Razón de la Elección Óptima |
| :--- | :--- | :--- |
| **Almacén primario**: Tabla SQLite `master_indicators` en `.statscepal_cache.db` | Solo archivo JSON en disco | SQLite permite filtrado por temas, conteos agrupados (`GROUP BY theme`), ordenamiento y búsquedas instantáneas mediante consultas SQL indexadas. |
| **Descarga en bloque única**: 1 sola llamada a `/thematic-tree` | Llamar a `/metadata` por cada indicador | 2,070 llamadas individuales saturarían la API y tardarían 10 minutos. Una sola llamada al árbol toma ~5 segundos y contiene la jerarquía completa. |
| **Estrategia de Caché**: Persistente con flag `--force` | Descarga efímera en memoria | Persiste entre sesiones y ejecuciones de agentes. Solo se refresca cuando el usuario lo solicita explícitamente. |
| **Fallback en `statscepal search`**: Catálogo local primero | Siempre llamar a la red | Si el catálogo local existe, `statscepal search` responde localmente; si no existe, consulta la API con aviso para compilar el catálogo. |

---

## 3. Esquema de Datos Relacional (`master_indicators`)

```sql
CREATE TABLE IF NOT EXISTS master_indicators (
    indicator_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    order_num INTEGER,
    theme TEXT NOT NULL,
    area TEXT NOT NULL,
    subarea TEXT,
    full_path TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_indicators_name ON master_indicators(name);
CREATE INDEX IF NOT EXISTS idx_indicators_theme ON master_indicators(theme);
CREATE INDEX IF NOT EXISTS idx_indicators_area ON master_indicators(area);
```

---

## 4. Arquitectura de Módulos

```
src/statscepal/
├── catalog/                     # Nuevo submódulo de Catálogo Maestro
│   ├── __init__.py
│   ├── models.py                # Pydantic model: CatalogIndicator, CatalogStats
│   └── store.py                 # CatalogStore: build(), search(), get_stats(), export()
├── thematic_tree.py             # Integración con ThematicTree existente
└── cli.py                       # Nuevos subcomandos: statscepal catalog build|search|stats|export
```

---

## 5. Subcomandos del CLI

1. `statscepal catalog build [--force]`:
   - Descarga el árbol temático de la CEPAL y puebla la tabla `master_indicators` (2,070 filas).
2. `statscepal catalog search "<termino>" [--theme <tema>] [--limit <n>]`:
   - Búsqueda SQL con coincidencia flexible de texto.
3. `statscepal catalog stats`:
   - Muestra el conteo de indicadores por gran tema y área principal.
4. `statscepal catalog export [--output catalogo.csv|json]`:
   - Exporta el catálogo consolidado para análisis en Excel o visualizadores externos.

---

## 6. Integración con el Skill `cepalstat-api` y Agentes

- Los agentes aprenden el comando `statscepal catalog search` como paso preliminar de descubrimiento para identificar el `indicator_id` oficial antes de cualquier otra operación.
- El skill `.agents/skills/cepalstat-api/SKILL.md` se actualiza con la documentación de búsqueda offline.
