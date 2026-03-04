#!/usr/bin/env python3
"""
Fetch FX from FRED public CSV endpoint (no API key required).

URL:
  https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK

Expected CSV shape:
  DATE,DEXUSUK
  1971-01-04,2.3950
  ...

If the response is NOT CSV (e.g. HTML), this script will show you immediately.
"""

from __future__ import annotations

import argparse
import csv
import io
import urllib.request
from pathlib import Path

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK"


def download_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "GlobalShocksOnHeatingOil/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    # handle BOM safely
    return raw.decode("utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_fred_csv(text: str):
    """
    Robust parse:
    - Works even if there are extra columns
    - Trims header whitespace
    - Skips missing values '.'
    """
    f = io.StringIO(text)
    reader = csv.reader(f)

    try:
        header = next(reader)
    except StopIteration:
        return [], []

    header = [h.strip() for h in header]

    # FRED sometimes uses DATE and sometimes observation_date depending on endpoint
    date_idx = -1
    for name in ("DATE", "observation_date"):
        if name in header:
            date_idx = header.index(name)
            break

    try:
        series_idx = header.index("DEXUSUK")
    except ValueError:
        series_idx = -1

    return header, (date_idx, series_idx), reader


def build_lookup(text: str):
    header, idxs, reader = parse_fred_csv(text)
    if not header:
        raise RuntimeError("Downloaded content was empty (no header row).")

    date_idx, series_idx = idxs

    # If we can’t find the expected columns, show header loudly
    if date_idx < 0 or series_idx < 0:
        raise RuntimeError(
            "Could not find expected columns 'DATE' and 'DEXUSUK' in the downloaded CSV.\n"
            f"Header row was: {header}"
        )

    rows = []
    for row in reader:
        if not row or len(row) <= max(date_idx, series_idx):
            continue

        d = row[date_idx].strip()
        v = row[series_idx].strip()

        if not d or not v or v == ".":
            continue

        # validate numeric
        try:
            float(v)
        except ValueError:
            continue

        rows.append((d, v))

    return rows, header


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch USD per GBP FX (DEXUSUK) from FRED CSV")
    ap.add_argument("--output", default="data/lookups/fx_usd_gbp.csv", help="Output lookup CSV path")
    ap.add_argument("--raw", default="data/lookups/fred_dexusuk_raw.csv", help="Save raw downloaded text here")
    ap.add_argument("--show", type=int, default=5, help="Print first N lines of the raw download")
    args = ap.parse_args()

    out_path = Path(args.output)
    raw_path = Path(args.raw)

    text = download_text(FRED_CSV_URL)

    # Save raw so we can inspect exactly what came back
    write_text(raw_path, text)

    # Quick sanity: if HTML came back, say so immediately
    head = text.lstrip()[:200].lower()
    if head.startswith("<!doctype") or head.startswith("<html"):
        print(f"ERROR: FRED URL returned HTML, not CSV. Saved to: {raw_path}")
        print("First 200 chars:")
        print(text[:200])
        raise SystemExit(2)

    # Print a few lines so you can see what we got
    print(f"Saved raw download to: {raw_path}")
    lines = text.splitlines()
    print(f"First {min(args.show, len(lines))} lines:")
    for l in lines[: args.show]:
        print(l)

    rows, header = build_lookup(text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "usd_per_gbp"])
        for d, v in rows:
            w.writerow([d, v])

    print(f"OK: wrote {len(rows)} FX rows to {out_path}")
    print("Note: usd_per_gbp is USD per GBP (invert for GBP per USD in transforms).")


if __name__ == "__main__":
    main()