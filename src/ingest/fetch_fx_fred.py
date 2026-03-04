#!/usr/bin/env python3
"""
Fetch USD→GBP FX rates from FRED and write a lookup CSV.

Series used:
- DEXUSUK (USD to GBP exchange rate)

API docs:
https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path
from typing import List, Dict, Any
import urllib.parse
import urllib.request
import json


FRED_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"


def http_get_json(url: str, timeout: int = 60) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "GlobalShocksOnHeatingOil/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_fred_series_observations(
    series_id: str,
    api_key: str,
    observation_start: str = "1986-01-01",
    observation_end: str = "",
) -> List[Dict[str, str]]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
    }
    if observation_end:
        params["observation_end"] = observation_end

    url = f"{FRED_ENDPOINT}?{urllib.parse.urlencode(params)}"
    data = http_get_json(url)

    if "observations" not in data:
        raise RuntimeError(f"Unexpected FRED response (no 'observations'). Keys: {list(data.keys())}")

    return data["observations"]


def write_fx_csv(rows: List[Dict[str, str]], out_path: Path) -> int:
    """
    Output schema:
      date, usd_to_gbp
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "usd_to_gbp"])

        for r in rows:
            d = r.get("date")
            v = r.get("value")

            # FRED uses "." to indicate missing
            if not d or not v or v.strip() in (".", ""):
                continue

            try:
                float(v)
            except ValueError:
                continue

            w.writerow([d, v])
            written += 1

    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch USD→GBP FX from FRED (DEXUSUK) into CSV")
    ap.add_argument("--output", default="data/lookups/fx_usd_gbp.csv", help="Output CSV path")
    ap.add_argument("--start", default="1986-01-01", help="Observation start date (YYYY-MM-DD)")
    ap.add_argument("--end", default="", help="Observation end date (YYYY-MM-DD). Default: latest")
    ap.add_argument("--series", default="DEXUSUK", help="FRED series_id (default DEXUSUK)")
    args = ap.parse_args()

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise SystemExit("Missing env var FRED_API_KEY (get one from FRED and set it in your environment).")

    rows = fetch_fred_series_observations(
        series_id=args.series,
        api_key=api_key,
        observation_start=args.start,
        observation_end=args.end,
    )

    out_path = Path(args.output)
    n = write_fx_csv(rows, out_path)
    print(f"OK: wrote {n} FX rows to {out_path}")


if __name__ == "__main__":
    main()