#!/usr/bin/env python3
"""
Stage 2 transform: convert gasoil USD/tonne to a heating-oil USD/litre proxy.

Input (NDJSON) should contain either:
- date: YYYY-MM-DD   (preferred)
or
- period: YYYY-MM    (acceptable)

Output:
- data/sample/heating_oil_usd_litres.ndjson

Why this exists:
- We take a gasoil wholesale proxy (USD/tonne) and convert to USD/litre using density assumptions.
- Then apply a simple retail uplift proxy.

IMPORTANT:
- We MUST NOT manufacture January-only dates.
- If the source is only yearly (no month), we fail rather than invent fake months.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Assumptions (kept from your existing dataset)
DEFAULT_DENSITY_KG_PER_LITRE = 0.845
DEFAULT_RETAIL_ALPHA = 1.1
DEFAULT_RETAIL_BETA_USD_PER_LITRE = 0.05


def load_ndjson(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name}: invalid JSON on line {line_no}: {e}") from e
    return rows


def write_ndjson(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def normalise_date(r: Dict[str, Any]) -> Optional[str]:
    """
    Return a YYYY-MM-DD string.

    Accepts:
    - r['date'] as YYYY-MM-DD
    - r['period'] as YYYY-MM -> coerced to YYYY-MM-01

    Rejects:
    - year-only data (cannot invent months)
    """
    d = r.get("date")
    if isinstance(d, str):
        d = d.strip()
        if len(d) == 10 and d[4] == "-" and d[7] == "-":
            return d  # YYYY-MM-DD
        # If someone passed YYYY-MM, coerce to first-of-month
        if len(d) == 7 and d[4] == "-":
            return f"{d}-01"

    p = r.get("period")
    if isinstance(p, str):
        p = p.strip()
        if len(p) == 7 and p[4] == "-":
            return f"{p}-01"

    # If we only have a year, do NOT guess months
    y = r.get("year")
    if y is not None:
        raise ValueError(
            "Input appears to be yearly-only (has 'year' but no monthly 'date'/'period'). "
            "Cannot safely create a monthly time series from annual points."
        )

    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage 2: gasoil USD/tonne -> heating oil USD/litre proxy")
    ap.add_argument("--input", default="data/sample/gasoil.ndjson")
    ap.add_argument("--output", default="data/sample/heating_oil_usd_litres.ndjson")
    ap.add_argument("--density", type=float, default=DEFAULT_DENSITY_KG_PER_LITRE)
    ap.add_argument("--retail-alpha", type=float, default=DEFAULT_RETAIL_ALPHA)
    ap.add_argument("--retail-beta", type=float, default=DEFAULT_RETAIL_BETA_USD_PER_LITRE)
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    density = float(args.density)
    litres_per_tonne = 1000.0 / density  # 1000 kg per tonne / kg per litre

    rows = load_ndjson(in_path)

    out_rows: List[Dict[str, Any]] = []
    skipped = 0

    for r in rows:
        d = normalise_date(r)
        if not d:
            skipped += 1
            continue

        # Accept gasoil price either as a top-level key or nested key, depending on your stage 1
        usd_per_tonne = (
            r.get("gasoil_usd_per_tonne")
            or r.get("usd_per_tonne")
            or r.get("price_usd_per_tonne")
        )

        if usd_per_tonne is None:
            skipped += 1
            continue

        try:
            usd_per_tonne = float(usd_per_tonne)
        except ValueError:
            skipped += 1
            continue

        usd_per_l = usd_per_tonne / litres_per_tonne

        # crude retail proxy
        usd_per_l_retail = (usd_per_l * float(args.retail_alpha)) + float(args.retail_beta)
        usd_per_1000l_retail = usd_per_l_retail * 1000.0

        out_rows.append(
            {
                "date": d,  # ✅ real date/period preserved
                "gasoil_usd_per_tonne": usd_per_tonne,
                "assumptions": {
                    "density_kg_per_litre": density,
                    "litres_per_tonne": round(litres_per_tonne, 3),
                    "retail_alpha": float(args.retail_alpha),
                    "retail_beta_usd_per_litre": float(args.retail_beta),
                },
                "derived": {
                    "usd_per_litre_wholesale_proxy": round(usd_per_l, 6),
                    "usd_per_1000l_wholesale_proxy": round(usd_per_l * 1000.0, 3),
                    "usd_per_litre_retail_est": round(usd_per_l_retail, 6),
                    "usd_per_1000l_retail_est": round(usd_per_1000l_retail, 3),
                },
            }
        )

    write_ndjson(out_path, out_rows)

    print(f"OK: wrote {len(out_rows)} rows to {out_path}")
    print(f"Skipped rows: {skipped}")
    if out_rows:
        # quick sanity
        import pandas as pd
        df = pd.DataFrame(out_rows)
        df["date"] = pd.to_datetime(df["date"])
        print("min", df["date"].min().date(), "max", df["date"].max().date())
        print("unique months", df["date"].dt.to_period('M').nunique())


if __name__ == "__main__":
    main()