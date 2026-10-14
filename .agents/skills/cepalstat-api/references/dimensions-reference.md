# CEPALSTAT Dimensions Reference

Reference guide for common dimension and member IDs in UN CEPAL / ECLAC indicators.

## Common Country Member IDs (`dim_208: País__ESTANDAR`)

| Country / Region | Member ID | ISO3 |
|---|---|---|
| Total América Latina y el Caribe | `208` | - |
| Argentina | `218` | ARG |
| Bolivia (Estado Plurinacional de) | `221` | BOL |
| Brasil | `222` | BRA |
| Chile | `224` | CHL |
| Colombia | `225` | COL |
| Costa Rica | `226` | CRI |
| Cuba | `227` | CUB |
| Ecuador | `229` | ECU |
| El Salvador | `230` | SLV |
| Guatemala | `233` | GTM |
| Honduras | `235` | HND |
| México | `238` | MEX |
| Nicaragua | `239` | NIC |
| Panamá | `240` | PAN |
| Paraguay | `241` | PRY |
| Perú | `242` | PER |
| República Dominicana | `244` | DOM |
| Uruguay | `248` | URY |
| Venezuela (República Bolivariana de) | `249` | VEN |

## Standard Years (`dim_29117: Años__ESTANDAR`)

| Year | Member ID |
|---|---|
| 2018 | `29188` |
| 2019 | `29189` |
| 2020 | `29190` |
| 2021 | `29191` |
| 2022 | `29192` |
| 2023 | `29193` |
| 2024 | `29194` |

## Dimension Lookup Notes

- Different indicators might use different dimension IDs for years or sub-national breakdowns (e.g., specific indicators may use indicator-specific year dimensions rather than `dim_29117`).
- Always verify available dimensions for an indicator using `DimensionManager.get_dimensions(indicator_id)` or `GET /cepalstat/api/v1/indicator/{indicator_id}/dimensions`.
- When filtering multiple dimension members in API queries, combine member IDs using commas (e.g. `members=224,29190`).
