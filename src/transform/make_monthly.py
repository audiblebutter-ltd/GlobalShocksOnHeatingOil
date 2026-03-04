#!/usr/bin/env python3
"""
Stage 2.5 transform: enforce MONTHLY grain.

Input:
- data/sample/heating_oil_usd_litres.ndjson   (may contain sparse/daily points)

Output:
- data/sample/heating_oil_usd_litres_monthly.ndjson

Rule:
- bucket by month, keep the LAST observation within each month
- set output date to month-start (YYYY-MM-01) for consistent joins/plots
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def load_ndjson(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_ndjson(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage 2.5: collapse sparse/daily points to monthly grain")
    ap.add_argument("--input", default="data/sample/heating_oil_usd_litres.ndjson")
    ap.add_argument("--output", default="data/sample/heating_oil_usd_litres_monthly.ndjson")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    rows = load_ndjson(in_path)
    if not rows:
        raise SystemExit("Input had 0 rows")

    df = pd.json_normalize(rows, sep=".")
    if "date" not in df.columns:
        raise KeyError(f"'date' not found. Columns: {df.columns.tolist()}")

    df["date_raw"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_raw"]).copy()

    df["month"] = df["date_raw"].dt.to_period("M").dt.to_timestamp()

    # Keep last obs per month (by actual date_raw)
    df = (
        df.sort_values("date_raw")
          .groupby("month", as_index=False)
          .tail(1)
          .copy()
    )

    # Output date as month-start for consistent joins (YYYY-MM-01)
    df["date"] = df["month"].dt.strftime("%Y-%m-%d")

    # Drop helper cols
    df = df.drop(columns=[c for c in ["date_raw", "month"] if c in df.columns])

    # Convert back to nested dicts roughly similar to input
    # We'll reconstruct from original rows instead (safer for nested structures):
    # But easiest: use the already-flattened df to dict and then unflatten isn't worth it.
    # So we rebuild minimal structure we need downstream.

    out_rows: List[Dict[str, Any]] = []
    for rec in df.to_dict(orient="records"):
        out = {
            "date": rec["date"],
            "gasoil_usd_per_tonne": rec.get("gasoil_usd_per_tonne"),
            "assumptions": {
                "density_kg_per_litre": rec.get("assumptions.density_kg_per_litre"),
                "litres_per_tonne": rec.get("assumptions.litres_per_tonne"),
                "retail_alpha": rec.get("assumptions.retail_alpha"),
                "retail_beta_usd_per_litre": rec.get("assumptions.retail_beta_usd_per_litre"),
            },
            "derived": {
                "usd_per_litre_wholesale_proxy": rec.get("derived.usd_per_litre_wholesale_proxy"),
                "usd_per_1000l_wholesale_proxy": rec.get("derived.usd_per_1000l_wholesale_proxy"),
                "usd_per_litre_retail_est": rec.get("derived.usd_per_litre_retail_est"),
                "usd_per_1000l_retail_est": rec.get("derived.usd_per_1000l_retail_est"),
            },
        }
        out_rows.append(out)

    write_ndjson(out_path, out_rows)

    # Report
    out_df = pd.DataFrame(out_rows)
    out_df["date"] = pd.to_datetime(out_df["date"])
    print(f"OK: wrote {len(out_rows)} rows to {out_path}")
    print("min", out_df["date"].min().date(), "max", out_df["date"].max().date())
    print("unique months", out_df["date"].dt.to_period("M").nunique())


if __name__ == "__main__":
    main()