#!/usr/bin/env python3
"""
Dataset Inspector (local dev tool)

Works with NDJSON files produced by this project.
Prints:
- row count
- date range
- available numeric fields
- min/max/mean for selected fields
- simple missing/null counts

Usage:
  python .\src\tools\inspect_dataset.py --input .\data\sample\gasoil_daily.ndjson
  python .\src\tools\inspect_dataset.py --input .\data\sample\heating_oil_usd_litres.ndjson --field derived.usd_per_litre_wholesale_proxy
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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


def get_nested(d: Dict[str, Any], dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def try_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    # allow numeric strings
    if isinstance(x, str):
        s = x.strip()
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def summarize_numeric(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"min": math.nan, "max": math.nan, "mean": math.nan}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def discover_numeric_fields(rows: List[Dict[str, Any]], max_fields: int = 30) -> List[str]:
    """
    Best-effort discovery:
    - top-level numeric keys
    - one-level nested under 'derived' and 'assumptions' if present
    """
    fields = set()

    for r in rows[:200]:  # sample first 200 rows
        for k, v in r.items():
            if k in ("derived", "assumptions") and isinstance(v, dict):
                for nk, nv in v.items():
                    if try_float(nv) is not None:
                        fields.add(f"{k}.{nk}")
            else:
                if try_float(v) is not None:
                    fields.add(k)

        if len(fields) >= max_fields:
            break

    return sorted(fields)[:max_fields]


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect NDJSON datasets")
    ap.add_argument("--input", required=True, help="Path to NDJSON file")
    ap.add_argument(
        "--field",
        help="Dotted field to summarise (e.g. price_usd_per_tonne or derived.usd_per_litre_wholesale_proxy). "
             "If omitted, we auto-discover numeric fields and summarise a few.",
    )
    ap.add_argument("--top", type=int, default=8, help="How many auto-discovered numeric fields to summarise")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")

    rows = load_ndjson(path)
    if not rows:
        raise SystemExit("No rows found (empty file).")

    # date range (if present)
    dates = [r.get("date") for r in rows if isinstance(r.get("date"), str)]
    dates_sorted = sorted(dates) if dates else []

    print(f"\nFile: {path}")
    print(f"Rows: {len(rows)}")
    if dates_sorted:
        print(f"Date range: {dates_sorted[0]} → {dates_sorted[-1]}")
    else:
        print("Date range: (no 'date' field found)")

    # Decide which fields to summarise
    fields: List[str]
    if args.field:
        fields = [args.field]
    else:
        fields = discover_numeric_fields(rows)
        fields = fields[: max(1, args.top)]

    print("\nNumeric field summaries:")
    for field in fields:
        vals: List[float] = []
        missing = 0
        for r in rows:
            v = get_nested(r, field) if "." in field else r.get(field)
            fv = try_float(v)
            if fv is None:
                missing += 1
            else:
                vals.append(fv)

        stats = summarize_numeric(vals)
        print(f"  - {field}")
        print(f"      present: {len(vals)}  missing: {missing}")
        print(f"      min: {stats['min']:.6g}  max: {stats['max']:.6g}  mean: {stats['mean']:.6g}")

    # Show discovered fields (helpful for copy/paste)
    if not args.field:
        all_fields = discover_numeric_fields(rows, max_fields=50)
        print("\nDiscovered numeric fields (sample):")
        for f in all_fields:
            print(f"  {f}")

    print("")


if __name__ == "__main__":
    main()