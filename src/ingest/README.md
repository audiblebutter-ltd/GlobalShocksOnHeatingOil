# Ingest

## Purpose

Stage 1 of the pipeline.

- Takes an exported CSV from Investing.com (London Gas Oil Futures historical data)
- Validates and normalises fields
- Outputs a canonical dataset (NDJSON) for downstream transforms

## Run locally

```powershell
python .\src\ingest\load_gasoil_csv.py `
  --input ".\data\sample\London Gas Oil Futures Historical Data.csv" `
  --output ".\data\sample\gasoil_daily.ndjson"

The output is sorted by date ascending.


