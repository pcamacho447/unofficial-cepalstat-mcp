---
id: recipe-chl-415-pib
indicator_id: 415
indicator_name: Producto Interno Bruto (PIB) anual
country: Chile
country_iso3: CHL
country_member_id: 224
theme: Económicos > PIB y Cuentas Nacionales
unit: Millones de dólares a precios constantes
member_ids:
- 224
python_code: |
  from statscepal import CepalStatClient, DataExtractor

  client = CepalStatClient()
  extractor = DataExtractor(client)

  # Extracción de PIB anual para Chile (indicador 415)
  # Miembro: 224 (Chile)
  df = extractor.get_dataframe(
      indicator_id=415,
      members=[224],
      decode_labels=True,
  )
  print(df.head())
status: certified
date_certified: '2026-10-14'
tags:
- chile
- pib
- macroeconomia
- cuentas_nacionales
quality_report:
  total_records: 40
  null_count: 0
  null_ratio: 0.0
  has_gaps: false
  min_year: 1980
  max_year: 2023
  min_value: null
  max_value: null
antibias:
  unit_verified: true
  scale_factor_note: Millones de dólares a precios constantes.
  is_projection: false
  base_year_split: null
  warnings: []
---

# Receta: Producto Interno Bruto (PIB) anual (Chile)

## Alertas Anti-Sesgo y Calidad de Datos
- **Unidad**: Millones de dólares a precios constantes
- **Nota de Escala**: Millones de dólares a precios constantes.
- **Proyección**: No

## Resumen de Calidad de Datos
- **Total Registros**: 40
- **Rango de Años**: 1980 - 2023
- **Valores Nulos**: 0 (0.0%)
- **Brechas Temporales**: No

## Código Reproducible en Python
```python
from statscepal import CepalStatClient, DataExtractor

client = CepalStatClient()
extractor = DataExtractor(client)

# Extracción de PIB anual para Chile (indicador 415)
# Miembro: 224 (Chile)
df = extractor.get_dataframe(
    indicator_id=415,
    members=[224],
    decode_labels=True,
)
print(df.head())
```
