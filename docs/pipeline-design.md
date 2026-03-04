# Pipeline Design

This document describes the ETL pipeline used in the Global Shocks project.

The pipeline transforms **London Gasoil Futures** into an estimated **UK heating oil retail price per litre**.

The pipeline is designed for clarity and reproducibility rather than extreme performance.

---

# Stage 1 — Ingest

Source dataset:

London Gasoil Futures historical data.

Source:
https://www.investing.com/commodities/london-gas-oil-historical-data

The dataset is exported as CSV and placed into the raw data bucket.

Example location:


raw/london-gasoil/YYYY/MM/DD/source.csv


The ingest stage performs minimal processing.

Responsibilities:

• Validate file format  
• Store raw file in S3  
• Record ingestion timestamp  

---

# Stage 2 — Transform

This stage performs all data modelling.

Key transformations:

### 1 Convert tonnes to litres

London gasoil is quoted as:

USD per metric tonne.

To convert to litres:


litres_per_tonne = 1000 / density


Typical density:


0.845 kg per litre


Therefore:


litres_per_tonne ≈ 1183.5 litres


Price per litre:


usd_per_litre = usd_per_tonne / litres_per_tonne


---

### 2 Convert USD to GBP

Using daily USD/GBP exchange rate.


gbp_per_litre = usd_per_litre / usd_gbp_rate


---

### 3 Estimate retail heating oil price

Retail heating oil includes:

• transport  
• storage  
• supplier margin  

Retail estimate model:


retail_price = (wholesale_price * alpha) + beta


Example parameters:


alpha = 1.10
beta = 0.05 GBP


These values will later be calibrated against real retail prices.

---

### 4 Inflation adjustment

Prices are converted to **today's money**.

Formula:


real_price = nominal_price * (CPI_today / CPI_t)


This allows meaningful comparison across decades.

---

### 5 Shock detection

A shock is defined when price exceeds the baseline by a threshold.

Baseline:

24 month rolling median.

Shock trigger:


price > baseline * 1.25


Shock phases:

| Phase | Definition |
|------|------|
Spike | price rising above baseline |
Stabilisation | price movement slows |
Normalisation | price returns within 10% of baseline |

---

# Stage 3 — Publish

Final datasets are written to the publish zone.

Example:


global-shocks/v1/london-gasoil/daily.json
global-shocks/v1/heating-oil/estimate.json
global-shocks/v1/events/events.json


These datasets are consumed directly by the Data & Grit website.