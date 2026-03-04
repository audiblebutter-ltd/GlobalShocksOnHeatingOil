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


---

## Step 12C — Put your real CSV in a safe place (don’t commit it yet)
Create a rule in `.gitignore` (if not already):

Add:


data/raw/
*.csv


Then create folders:

```powershell
mkdir data\raw

Put your downloaded file in:

data/raw/London Gas Oil Futures Historical Data.csv

We can commit a tiny sample later in data/sample/ (like 30 rows), but don’t commit the full one yet unless you’re comfortable with that dataset being mirrored in your repo.

Step 12D — Run it

From repo root:

python .\src\ingest\load_gasoil_csv.py --input ".\data\raw\London Gas Oil Futures Historical Data.csv" --output ".\data\sample\gasoil_daily.ndjson"

You should see:

OK: wrote #### records to ...