# Heating Oil Price Model

This document describes how London Gasoil Futures prices are translated into an estimated UK retail heating oil price.

The goal is to produce a price series comparable to typical domestic heating oil prices quoted in **pence per litre**.

---

# Market Structure

Domestic heating oil is part of the **middle distillates market**.

The supply chain is roughly:


Crude Oil
↓
Refining
↓
Middle Distillates (diesel / gasoil)
↓
Wholesale distribution
↓
Retail delivery


London Gasoil Futures act as a **market benchmark** for distillate fuels in Europe.

---

# Unit Conversion

London Gasoil prices are quoted as:


USD per metric tonne


Heating oil is sold as:


pence per litre


Therefore the first transformation converts **tonnes into litres**.

---

## Density Assumption

Typical gasoil density:


0.845 kg per litre


Therefore:


1 tonne = 1000 kg


Litres per tonne:


litres_per_tonne = 1000 / density


Which gives:


≈ 1183.5 litres per tonne


---

## Price Per Litre


usd_per_litre = usd_per_tonne / litres_per_tonne


---

# Currency Conversion

Prices are converted from USD to GBP.


gbp_per_litre = usd_per_litre / usd_gbp_rate


Exchange rate data will be sourced separately.

---

# Retail Heating Oil Estimate

Retail heating oil prices include:

• delivery logistics  
• storage  
• supplier margin  

A simple linear retail model is used.


retail_price = (wholesale_price * alpha) + beta


Example starting values:


alpha = 1.10
beta = 0.05 GBP


These values represent typical distribution costs and supplier margin.

Future improvements may calibrate this model using real retail price observations.

---

# Inflation Adjustment

To make historical comparisons meaningful, prices are expressed in **today's money**.

Formula:


real_price = nominal_price × (CPI_today / CPI_t)


This transformation removes the distortion of long-term inflation.

---

# Result

The final dataset contains:


date
gasoil_price_usd_per_tonne
wholesale_price_gbp_per_litre
estimated_retail_price_ppl
inflation_adjusted_price_ppl



This dataset forms the basis of the **Global Shocks visualisation** used on the Data & Grit website.