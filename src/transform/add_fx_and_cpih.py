#!/usr/bin/env python3
"""
Stage 3 transform: join FX + CPIH onto litres-based heating oil view.

Inputs:
- data/sample/heating_oil_usd_litres.ndjson
- data/lookups/fx_usd_gbp.csv      (columns: date, usd_per_gbp)   # USD per 1 GBP
- data/lookups/cpih.csv            (columns: period, cpih_index)  # YYYY-MM, index

Output:
- data/sample/heating_oil_gbp_real.ndjson

Notes:
- usd_per_gbp is inverted to gbp_per_usd = 1 / usd_per_gbp
- FX join: same-day else previous available day (weekends/holidays)
- CPIH join: by month (YYYY-MM)
- Real terms: ppl_real = ppl_nominal * (CPIH_base / CPIH_month)
"""

from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_right
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


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


def load_fx_csv(path: Path) -> Tuple[List[str], Dict[str, float]]:
    """
    Returns:
      sorted_dates (YYYY-MM-DD strings)
      fx_usd_per_gbp_by_date
    """
    fx: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = (row.get("date") or "").strip()
            v = (row.get("usd_per_gbp") or "").strip()
            if not d or not v:
                continue
            try:
                fx[d] = float(v)
            except ValueError:
                continue

    dates_sorted = sorted(fx.keys())
    return dates_sorted, fx


def fx_for_date_or_prev(dates_sorted: List[str], fx: Dict[str, float], target_date: str) -> Optional[float]:
    """
    Find FX rate for target_date, else most recent earlier date.
    """
    if target_date in fx:
        return fx[target_date]

    i = bisect_right(dates_sorted, target_date) - 1
    if i < 0:
        return None
    return fx[dates_sorted[i]]


def load_cpih_csv(path: Path) -> Dict[str, float]:
    """
    period is YYYY-MM
    """
    cpih: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = (row.get("period") or "").strip()
            v = (row.get("cpih_index") or "").strip()
            if not p or not v:
                continue
            try:
                cpih[p] = float(v)
            except ValueError:
                continue
    return cpih


def month_key(iso_date: str) -> str:
    # iso_date = YYYY-MM-DD
    return iso_date[:7]


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage 3: apply FX + CPIH to litres-based dataset")
    ap.add_argument("--input", default="data/sample/heating_oil_usd_litres.ndjson")
    ap.add_argument("--fx", default="data/lookups/fx_usd_gbp.csv")
    ap.add_argument("--cpih", default="data/lookups/cpih.csv")
    ap.add_argument("--output", default="data/sample/heating_oil_gbp_real.ndjson")
    args = ap.parse_args()

    in_path = Path(args.input)
    fx_path = Path(args.fx)
    cpih_path = Path(args.cpih)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")
    if not fx_path.exists():
        raise SystemExit(f"Missing FX lookup: {fx_path}")
    if not cpih_path.exists():
        raise SystemExit(f"Missing CPIH lookup: {cpih_path}")

    rows = load_ndjson(in_path)

    fx_dates_sorted, fx_usd_per_gbp = load_fx_csv(fx_path)
    cpih = load_cpih_csv(cpih_path)

    if not cpih:
        raise SystemExit("CPIH lookup loaded 0 rows (unexpected).")

    # Base CPIH month = latest available in lookup (today's money)
    base_period = sorted(cpih.keys())[-1]
    base_cpih = cpih[base_period]

    out_rows: List[Dict[str, Any]] = []
    missing_fx = 0
    missing_cpih = 0

    for r in rows:
        d = r.get("date")
        if not isinstance(d, str) or len(d) != 10:
            continue

        # Month bucket for BOTH oil + CPIH joins
        period = month_key(d)

        # We use wholesale proxy from Stage 2 (USD per litre)
        usd_per_litre = r.get("derived", {}).get("usd_per_litre_wholesale_proxy")
        if usd_per_litre is None:
            continue

        try:
            usd_per_litre = float(usd_per_litre)
        except ValueError:
            continue

        usd_per_gbp = fx_for_date_or_prev(fx_dates_sorted, fx_usd_per_gbp, d)
        if usd_per_gbp is None or usd_per_gbp == 0:
            missing_fx += 1
            continue

        gbp_per_usd = 1.0 / usd_per_gbp

        gbp_per_litre_nominal = usd_per_litre * gbp_per_usd
        pence_per_litre_nominal = gbp_per_litre_nominal * 100.0

        cpih_val = cpih.get(period)
        if cpih_val is None or cpih_val == 0:
            # fallback: use most recent earlier CPIH month (carry-forward)
            cpih_periods = sorted(cpih.keys())  # YYYY-MM strings sort correctly
            i = bisect_right(cpih_periods, period) - 1
            if i < 0:
                # nothing earlier exists; use earliest as absolute last resort
                cpih_val = cpih[cpih_periods[0]]
            else:
                cpih_val = cpih[cpih_periods[i]]
            missing_cpih += 1

        pence_per_litre_real = pence_per_litre_nominal * (base_cpih / cpih_val)

        out_rows.append(
            {
                # ✅ SOURCE OF TRUTH: oil observation date (daily)
                "date": d,

                "inputs": {
                    # ✅ Explicit contract: oil date + oil month
                    "oil_date": d,
                    "oil_period": period,  # YYYY-MM

                    "usd_per_litre_wholesale_proxy": usd_per_litre,
                    "usd_per_gbp": usd_per_gbp,
                    "gbp_per_usd": gbp_per_usd,

                    # CPIH used (month + value)
                    "cpih_period": period,
                    "cpih_index": cpih_val,
                    "cpih_base_period": base_period,
                    "cpih_base_index": base_cpih,
                },
                "derived": {
                    "gbp_per_litre_nominal": round(gbp_per_litre_nominal, 6),
                    "pence_per_litre_nominal": round(pence_per_litre_nominal, 4),
                    "pence_per_litre_real": round(pence_per_litre_real, 4),
                },
            }
        )

    write_ndjson(out_path, out_rows)

    print(f"OK: wrote {len(out_rows)} rows to {out_path}")
    print(f"Skipped due to missing FX: {missing_fx}")
    print(f"Skipped due to missing CPIH: {missing_cpih}")
    print(f"Real-terms base CPIH: {base_period} = {base_cpih}")


if __name__ == "__main__":
    main()