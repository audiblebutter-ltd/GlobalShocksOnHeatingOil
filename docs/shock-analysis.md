# Shock Detection and Recovery Analysis

This document defines how the project identifies and measures **global price shocks** in the heating oil market.

The goal is to quantify the typical lifecycle of an energy price shock.

---

# Typical Shock Lifecycle

Energy price shocks tend to follow a recognisable pattern.

| Phase | Typical Duration |
|------|------|
Spike Phase | 3–6 months |
Stabilisation | 6–12 months |
Return to Normal | ~12–18 months |

This project attempts to measure these phases directly from the data.

---

# Baseline Price

A baseline is required to determine when a price becomes abnormal.

Baseline definition:


rolling_median(previous 24 months)


The rolling median is used because it is robust against extreme spikes.

---

# Shock Trigger

A shock begins when the price exceeds the baseline by a threshold.

Trigger condition:


price > baseline × 1.25


This indicates a price at least **25% above the normal level**.

---

# Shock Peak

The peak of a shock is defined as:


maximum price between shock start and stabilisation


---

# Stabilisation Phase

Stabilisation begins when price volatility decreases.

Condition:


absolute(monthly_change) < 3%
for three consecutive months


This indicates the market has stopped rapidly adjusting.

---

# Normalisation

The shock is considered resolved when prices return near the baseline.

Condition:


price <= baseline × 1.10
for three consecutive months


This represents a price within **10% of the historical norm**.

---

# Example Lifecycle


Shock Start → Rapid Price Rise
Peak → Maximum Price
Stabilisation → Market stops swinging wildly
Normalisation → Price returns near baseline


---

# Output Metrics

For each shock event the pipeline calculates:


shock_start
peak_date
stabilisation_date
normalisation_date


From these dates we derive durations:


spike_duration
stabilisation_duration
total_recovery_time


---

# Relationship to Global Events

Shock windows are compared against the curated event dataset.

Examples:

- COVID-19 pandemic
- Russia-Ukraine war
- Suez Canal blockage
- Red Sea shipping disruption

This allows the visualisation to show **which global events triggered which price shocks**.

---

# Purpose

The objective is not prediction.

The objective is **understanding how markets recover after shocks**.