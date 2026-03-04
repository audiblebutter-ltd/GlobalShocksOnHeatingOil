#!/usr/bin/env python3
"""
Stage 1 extract: build data/sample/gasoil.ndjson

Reads a local CSV file and writes NDJSON with:
- date: YYYY-MM-DD (or YYYY-MM-01 if only monthly period exists)
- gasoil_usd_per_tonne: float

You MUST point --input at a CSV you already have locally.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Optional


def pick_field(row: dict, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        v = row.get(c)
        if v is not None and str(v).strip() != "":
            return c
    return None


def normalise_date(row: dict) -> Optional[str]:
    d = (row.get("date") or "").strip()
    if d:
        # Accept YYYY-MM-DD
        if len(d) == 10 and d[4] == "-" and d[7] == "-":
            return d
        # Accept YYYY-MM
        if len(d) == 7 and d[4] == "-":
            return f"{d}-01"

    p = (row.get("period") or "").strip()
    if p and len(p) == 7 and p[4] == "-":
        return f"{p}-01"

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to local CSV containing gasoil prices")
    ap.add_argument("--output", default="data/sample/gasoil.ndjson")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Missing input CSV: {in_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    wrote = 0
    skipped = 0

    with in_path.open("r", encoding="utf-8", newline="") as f_in, out_path.open("w", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)

        # try to identify the price column once from header
        header = reader.fieldnames or []
        # common names
        price_candidates = [
            "gasoil_usd_per_tonne",
            "usd_per_tonne",
            "price_usd_per_tonne",
            "value",
            "price",
        ]
        # include any header that contains both 'usd' and ('ton'/'tonne')
        for h in header:
            hl = h.lower()
            if "usd" in hl and ("ton" in hl or "tonne" in hl):
                price_candidates.append(h)

        for row in reader:
            date = normalise_date(row)
            if not date:
                skipped += 1
                continue

            price_field = pick_field(row, price_candidates)
            if not price_field:
                skipped += 1
                continue

            try:
                price = float(str(row[price_field]).strip())
            except ValueError:
                skipped += 1
                continue

            f_out.write(json.dumps({"date": date, "gasoil_usd_per_tonne": price}, ensure_ascii=False) + "\n")
            wrote += 1

    print(f"OK: wrote {wrote} rows to {out_path}")
    print(f"Skipped rows: {skipped}")


if __name__ == "__main__":
    main()