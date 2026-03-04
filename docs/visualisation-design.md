# Visualisation Design

The Global Shocks project presents heating oil prices through an interactive chart on the Data & Grit website.

The goal is to make long-term energy market behaviour easy to understand.

---

# Primary Chart

The main chart displays:

Inflation adjusted heating oil price per litre.

Time range:

1986 → present (depending on source data coverage)

This allows major global shocks to be viewed in historical context.

---

# Data Series

The chart includes the following series.

### Heating Oil Price (Real Terms)

Estimated UK retail heating oil price per litre expressed in today's money.

Derived from:

London Gasoil Futures.

---

### Heating Oil Price (Nominal)

Optional toggle showing historical prices without inflation adjustment.

This highlights how inflation distorts long-term price comparisons.

---

# Event Markers

Global events are displayed as vertical markers.

Examples include:

• COVID-19 pandemic  
• Russia–Ukraine war  
• Suez Canal blockage  
• Red Sea shipping disruption  

Each marker contains a tooltip explaining the event.

---

# Shock Windows

Detected shock periods are displayed as shaded regions.

These regions represent the full lifecycle of a price shock.


Shock Start → Peak → Stabilisation → Normalisation


---

# Recovery Metrics

A summary panel displays statistics for each shock.

Example:

| Event | Peak Increase | Spike Duration | Full Recovery |
|------|------|------|------|
COVID-19 | +32% | 4 months | 14 months |
Ukraine War | +78% | 5 months | 17 months |

These metrics are derived from the shock detection model.

---

# User Interaction

The visualisation supports the following controls.

Toggle inflation adjustment.

Toggle event markers.

Highlight individual shock windows.

---

# Purpose

The visualisation helps answer a key question:

How long does it take energy markets to recover from global shocks?

By combining market data with historical events, the project makes the behaviour of energy prices easier to understand.