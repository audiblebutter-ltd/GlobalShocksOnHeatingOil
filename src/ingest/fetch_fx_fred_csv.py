#!/usr/bin/env python3
"""
Fetch FX from FRED public CSV endpoint (no API key required).

Source:
  https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK

Important:
- DEXUSUK = USD per GBP (dollars per £1)
- Later transforms will invert it when we need GBP per USD:
    gbp_per_usd = 1 / usd_per_gbp
"""

from __future__ import annotations

import argparse
import csv
import urllib.request
from pathlib import Path


FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK"


def download_fred_csv(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "GlobalShocksOnHeatingOil/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(text.splitlines()))


def write_lookup(rows, out_path: Path) -> int:
    """
    Writes:
      date,usd_per_gbp
    Skips missing values where the series uses '.'
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "usd_per_gbp"])

        for r in rows:
            d = r.get("DATE")
            v = r.get("DEXUSUK")

            if not d or not v or v.strip() == ".":
                continue

            # basic numeric validation
            try:
                float(v)
            except ValueError:
                continue

            w.writerow([d, v])
            written += 1

    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch USD per GBP FX (DEXUSUK) from FRED CSV")
    ap.add_argument("--output", default="data/lookups/fx_usd_gbp.csv", help="Output CSV path")
    args = ap.parse_args()

    rows = download_fred_csv(FRED_CSV_URL)
    out_path = Path(args.output)
    n = write_lookup(rows, out_path)

    print(f"OK: wrote {n} FX rows to {out_path}")
    print("Note: usd_per_gbp is USD per GBP (invert for GBP per USD in transforms).")


if __name__ == "__main__":
    main()