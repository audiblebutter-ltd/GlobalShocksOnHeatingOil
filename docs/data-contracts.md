# Data Contracts

The Data & Grit website consumes the following datasets.

These contracts should remain stable.

Versioning is handled via URL prefix:


/global-shocks/v1/


---

## London Gasoil Daily Series

File:


daily_gasoil_real.json


Example structure:

```json
{
  "series": [
    {
      "date": "2020-01-01",
      "price_usd_per_tonne": 600.2,
      "price_gbp_per_litre_est": 0.54,
      "price_real_gbp_per_litre": 0.63
    }
  ],
  "last_updated": "2026-03-04"
}
Heating Oil Retail Estimate

File:

heating_oil_estimate.json

Example:

{
  "series": [
    {
      "date": "2020-01",
      "estimated_price_ppl": 52.3,
      "real_price_ppl": 61.8
    }
  ]
}

Units:

ppl = pence per litre

Shock Windows

File:

shock_windows.json

Example:

{
  "events": [
    {
      "event_id": "ukraine_2022",
      "shock_start": "2022-02",
      "peak": "2022-06",
      "stabilisation": "2023-01",
      "normalisation": "2023-08"
    }
  ]
}
Events Dataset

File:

events.json

Example:

{
  "events": [
    {
      "id": "covid_2020",
      "name": "COVID-19 Pandemic",
      "category": "pandemic",
      "start_date": "2020-03-11"
    }
  ]
}

Events are used to annotate charts.


---

# 4️⃣ `events/events.v1.yml`

```yaml
events:

  - id: covid_2020
    name: COVID-19 Pandemic Declared
    category: pandemic
    start_date: 2020-03-11
    description: WHO declares COVID-19 a global pandemic.

  - id: suez_blockage_2021
    name: Suez Canal Blockage
    category: supply_chain
    start_date: 2021-03-23
    description: Ever Given blocks the Suez Canal disrupting global trade.

  - id: ukraine_invasion_2022
    name: Russia Invades Ukraine
    category: war
    start_date: 2022-02-24
    description: Major geopolitical shock affecting global energy markets.

  - id: european_energy_crisis_2022
    name: European Energy Crisis
    category: energy
    start_date: 2022-06-01
    description: Severe supply disruption and price volatility in energy markets.

  - id: red_sea_shipping_2024
    name: Red Sea Shipping Disruptions
    category: supply_chain
    start_date: 2024-01-01
    description: Shipping disruption affecting energy transport routes.