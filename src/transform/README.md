# Transform

Stage 2 converts market prices into a litres-based view that resembles how UK heating oil is purchased.

## What it does

Input:
- Stage 1 canonical NDJSON (USD per tonne)

Output:
- NDJSON with derived:
  - litres-per-tonne conversion (density assumption)
  - USD per litre (wholesale proxy)
  - simple retail estimate model (alpha/beta)

## Run locally

```powershell
python .\src\transform\gasoil_to_heating_oil.py `
  --input ".\data\sample\gasoil_daily.ndjson" `
  --output ".\data\sample\heating_oil_usd_litres.ndjson"
  

