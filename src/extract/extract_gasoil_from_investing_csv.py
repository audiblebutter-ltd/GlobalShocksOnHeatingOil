#!/usr/bin/env python3
"""
Extract ICE London Gasoil futures history from the 'Investing.com style' CSV:
'London Gas Oil Futures Historical Data.csv'

Writes:
- data/sample/gasoil.ndjson
with rows:
{ "date": "YYYY-MM-DD", "gasoil_usd_per_tonne": <float> }

Assumes CSV contains a Date column and a Price column.
Handles common formats:
- Date like "Mar 04, 2026" or "2026-03-04"
- Price like "1,234.50" or "1234.50"
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def parse_date(s: str) -> Optional[str]:
    s = s.strip()
    if not s:
        return None

    # Try ISO first
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s  # YYYY-MM-DD

    # Common Investing.com export: "Mar 04, 2026"
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Sometimes: "04/03/2026" (day-first) or "03/04/2026" (month-first)
    # We'll try day-first first (UK habit), then month-first.
    for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_price(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    # remove thousands separators
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def find_col(fieldnames: list[str], want: list[str]) -> Optional[str]:
    # exact / case-insensitive match first
    lower = {f.lower(): f for f in fieldnames}
    for w in want:
        if w.lower() in lower:
            return lower[w.lower()]

    # fallback: partial match
    for f in fieldnames:
        fl = f.lower()
        for w in want:
            if w.lower() in fl:
                return f
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=r"data/raw/London Gas Oil Futures Historical Data.csv")
    ap.add_argument("--output", default=r"data/sample/gasoil.ndjson")
    ap.add_argument("--price-col", default="", help="Override price column name if auto-detect fails")
    ap.add_argument("--date-col", default="", help="Override date column name if auto-detect fails")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Missing input CSV: {in_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    wrote = 0
    skipped = 0

    with in_path.open("r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row / fieldnames.")

        date_col = args.date_col.strip() or find_col(reader.fieldnames, ["Date"])
        # Investing exports typically have "Price"
        price_col = args.price_col.strip() or find_col(reader.fieldnames, ["Price", "Close", "Last"])

        if not date_col or not price_col:
            raise SystemExit(
                f"Could not detect columns. Found headers: {reader.fieldnames}\n"
                f"Detected date_col={date_col}, price_col={price_col}\n"
                "Pass --date-col and --price-col to override."
            )

        rows = []
        for row in reader:
            d = parse_date(row.get(date_col, ""))
            p = parse_price(row.get(price_col, ""))

            if not d or p is None:
                skipped += 1
                continue

            rows.append({"date": d, "gasoil_usd_per_tonne": p})

    # sort ascending by date (Investing exports are usually newest-first)
    rows.sort(key=lambda r: r["date"])

    with out_path.open("w", encoding="utf-8") as f_out:
        for r in rows:
            f_out.write(json.dumps(r, ensure_ascii=False) + "\n")
            wrote += 1

    print(f"OK: wrote {wrote} rows to {out_path}")
    print(f"Skipped rows: {skipped}")

    # quick sanity
    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        print("min", df["date"].min().date(), "max", df["date"].max().date())
        print("unique months", df["date"].dt.to_period('M').nunique())
        print(df["date"].dt.month.value_counts().sort_index().to_string())
    except Exception:
        pass


if __name__ == "__main__":
    main()