# Event Model

The Global Shocks project uses a curated dataset of global events to provide context for price movements.

Events are used to annotate the visualisation and to compare price shocks against real-world causes.

---

# Event Categories

Events are grouped into categories to allow comparison across different types of global shocks.

| Category | Description |
|--------|--------|
war | Military conflicts affecting energy supply |
pandemic | Global health crises impacting demand and supply |
supply_chain | Logistics disruptions affecting trade routes |
energy | Structural changes in energy markets |
policy | Major government policy interventions |

---

# Event Structure

Each event is represented using the following schema.


id
name
category
start_date
end_date (optional)
description
severity


---

# Example Event

```yaml
- id: ukraine_invasion_2022
  name: Russia Invades Ukraine
  category: war
  start_date: 2022-02-24
  description: Large-scale invasion triggering global energy market disruption.
  severity: high
``` id="q1b6vo"

---

# Event Duration

Some events are point-in-time events.

Example:


COVID declared pandemic


Others represent longer periods.

Example:


European energy crisis


For these events the model supports:


start_date
end_date


This allows visualisation bands to be displayed on charts.

---

# Relationship to Shock Detection

Events do not define shocks directly.

Instead:


price shock detection → derived from price data
events → provide explanatory context


This prevents bias in analysis.

---

# Event Severity

Severity is used for visual emphasis in charts.

| Severity | Meaning |
|--------|--------|
low | minor market disturbance |
medium | noticeable price movement |
high | major global shock |

---

# Event Governance

Events are curated manually.

This ensures accuracy and avoids automated misclassification of global events.

New events are added through updates to the events dataset.

---

# Purpose

The event model allows the project to answer questions such as:

- Which types of events cause the largest price shocks?
- Which shocks take the longest to recover?
- Do supply chain disruptions behave differently than wars?

This transforms the project from a simple price chart into a structured analysis of global shocks.