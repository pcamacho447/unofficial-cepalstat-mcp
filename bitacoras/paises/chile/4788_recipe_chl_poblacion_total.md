---
id: recipe-chl-4788-pob
indicator_id: 4788
indicator_name: Población total, según sexo
country: Chile
country_iso3: CHL
country_member_id: 224
theme: Demográficos y sociales > Demográficos
unit: Miles de personas, a mitad del año
member_ids:
- 224
- 29190
- 88623
python_code: |
  from statscepal import CepalStatClient, DataExtractor

  client = CepalStatClient()
  extractor = DataExtractor(client)

  # Extracción de Población total de Chile (indicador 4788)
  # Miembros: 224 (Chile), 29190 (Ambos sexos), 88623 (Total nacional)
  df = extractor.get_dataframe(
      indicator_id=4788,
      members=[224, 29190, 88623],
      decode_labels=True,
  )
  print(df.head())
status: certified
date_certified: '2026-10-14'
tags:
- chile
- poblacion
- demografia
- celade
quality_report:
  total_records: 151
  null_count: 0
  null_ratio: 0.0
  has_gaps: false
  min_year: 1950
  max_year: 2100
  min_value: null
  max_value: null
antibias:
  unit_verified: true
  scale_factor_note: Cifras expresadas en miles de personas. Multiplicar por 1,000 para personas individuales.
  is_projection: true
  base_year_split: 2021
  warnings:
  - Cifras posteriores a 2021 son proyecciones demográficas basadas en el método de componentes por cohorte.
---

# Receta: Población total, según sexo (Chile)

## Alertas Anti-Sesgo y Calidad de Datos
- **Unidad**: Miles de personas, a mitad del año
- **Nota de Escala**: Cifras expresadas en miles de personas. Multiplicar por 1,000 para personas individuales.
- **Proyección**: Sí (Post-2021)
- **Advertencias**:
  - Cifras posteriores a 2021 son proyecciones demográficas basadas en el método de componentes por cohorte.

## Resumen de Calidad de Datos
- **Total Registros**: 151
- **Rango de Años**: 1950 - 2100
- **Valores Nulos**: 0 (0.0%)
- **Brechas Temporales**: No

## Código Reproducible en Python
```python
from statscepal import CepalStatClient, DataExtractor

client = CepalStatClient()
extractor = DataExtractor(client)

# Extracción de Población total de Chile (indicador 4788)
# Miembros: 224 (Chile), 29190 (Ambos sexos), 88623 (Total nacional)
df = extractor.get_dataframe(
    indicator_id=4788,
    members=[224, 29190, 88623],
    decode_labels=True,
)
print(df.head())
```
