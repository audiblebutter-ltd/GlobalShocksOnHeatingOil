# Global Shocks on Heating Oil

## Overview

This project investigates how **global economic and geopolitical shocks** affect the price of **domestic heating oil in the UK**.

It uses **London Gasoil Futures** as the upstream market signal and transforms that data into an **estimated retail heating oil price per litre**, comparable to prices typically quoted by suppliers such as BoilerJuice.

The goal is to show:

- How shocks propagate through energy markets
- How long it takes for prices to stabilise
- How long it takes to return to “normal”

All values are expressed in **today's money** using UK inflation data.

---

## Core Question

How long does it take for heating oil prices to recover after a global shock?

Typical pattern observed:

| Phase | Duration |
|------|------|
| Spike Phase | 3–6 months |
| Stabilisation | 6–12 months |
| Return to Normal | ~12–18 months |

This project will measure these durations empirically.

---

## Data Sources

### Market driver
London Gas Oil Futures historical dataset

Source:
https://www.investing.com/commodities/london-gas-oil-historical-data

Frequency:
Daily

Units:
USD per metric tonne

---

### Inflation index

UK CPI or CPIH index (ONS)

Used to convert historical prices into **real terms (today's money)**.

---

### Event timeline

Curated dataset describing major global shocks such as:

- wars
- pandemics
- supply chain disruptions
- major energy policy events

---

## Transformations

Key transformations applied in the pipeline:

1. Convert **USD per tonne → USD per litre**
2. Convert **USD → GBP**
3. Estimate **retail heating oil price per litre**
4. Adjust prices into **today's money**
5. Detect **shock phases and recovery periods**

---

## Outputs

The pipeline produces chart-ready JSON datasets for use in the Data & Grit website.

Examples:
