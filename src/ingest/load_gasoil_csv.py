#!/usr/bin/env python3
"""
Stage 1 (Ingest)
----------------
Load and validate Investing.com 'London Gas Oil Futures Historical Data' CSV.

- Parse exported CSV from https://www.investing.com/commodities/london-gas-oil-historical-data
- Normalize dates to ISO (YYYY-MM-DD)
- Parse numeric columns (supports commas, spaces, percent signs)
- Parse volumes with K/M/B suffixes
- Output canonical NDJSON (one JSON record per line), sorted by date ascending

Designed to run locally now, and later inside AWS Lambda (same logic).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Dict, List


# Strip commas, whitespace, and percent signs from numeric strings
NUMERIC_STRIP_RE = re.compile(r"[,\s%]")


def parse_float(value: str, field_name: str, allow_empty: bool = True) -> Optional[float]:
    """
    Parse a float from strings like:
      "987.12"
      "1,104.60"
      "31.14%"
      "-"
      ""
    """
    if value is None:
        return None

    v = str(value).strip()
    if v in ("", "-", "—", "N/A"):
        if allow_empty:
            return None
        raise ValueError(f"{field_name}: missing value not allowed")

    v = NUMERIC_STRIP_RE.sub("", v)
    try:
        return float(v)
    except ValueError as e:
        raise ValueError(f"{field_name}: could not parse float from '{value}'") from e


def parse_int(value: str, field_name: str, allow_empty: bool = True) -> Optional[int]:
    """
    Parse an int from strings like:
      "12.34K" (volume)
      "1.2M"
      "0"
      "-"
    Investing exports volume in K/M/B sometimes. We'll convert to integer.
    """
    if value is None:
        return None

    v = str(value).strip()
    if v in ("", "-", "—", "N/A"):
        if allow_empty:
            return None
        raise ValueError(f"{field_name}: missing value not allowed")

    v = v.replace(",", "").strip()
    mult = 1
    if v.endswith(("K", "k")):
        mult = 1_000
        v = v[:-1]
    elif v.endswith(("M", "m")):
        mult = 1_000_000
        v = v[:-1]
    elif v.endswith(("B", "b")):
        mult = 1_000_000_000
        v = v[:-1]

    try:
        return int(float(v) * mult)
    except ValueError as e:
        raise ValueError(f"{field_name}: could not parse int from '{value}'") from e


def parse_date(value: str) -> str:
    """
    Investing date formats can vary by locale/export:
      "Mar 04, 2026"
      "2026-03-04"
      "04/03/2026"
    We normalize to ISO: YYYY-MM-DD
    """
    v = str(value).strip()
    fmts = [
        "%b %d, %Y",   # Mar 04, 2026
        "%Y-%m-%d",    # 2026-03-04
        "%d/%m/%Y",    # 04/03/2026 (UK)
        "%m/%d/%Y",    # 03/04/2026 (US) - last resort
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Date: unrecognized format '{value}'")


@dataclass(frozen=True)
class GasoilDailyRecord:
    date: str  # YYYY-MM-DD
    price_usd_per_tonne: float
    open_usd_per_tonne: Optional[float]
    high_usd_per_tonne: Optional[float]
    low_usd_per_tonne: Optional[float]
    volume: Optional[int]
    change_pct: Optional[float]
    source: str = "investing.com:london-gas-oil-historical-data"


def detect_header(fieldnames: List[str]) -> Dict[str, str]:
    """
    Maps expected canonical fields to actual CSV column names.
    Investing exports commonly use: Date, Price, Open, High, Low, Vol., Change %
    """
    if not fieldnames:
        raise ValueError("CSV has no header row")

    norm = {f.strip().lower(): f for f in fieldnames}

    def pick(*candidates: str) -> Optional[str]:
        for c in candidates:
            if c in norm:
                return norm[c]
        return None

    mapping = {
        "date": pick("date"),
        "price": pick("price", "last", "close"),
        "open": pick("open"),
        "high": pick("high"),
        "low": pick("low"),
        "volume": pick("vol.", "vol", "volume"),
        "change": pick("change %", "change%", "chg%", "change"),
    }

    if not mapping["date"] or not mapping["price"]:
        raise ValueError(
            f"Missing required columns: date/price. Found columns: {fieldnames}"
        )

    return mapping  # type: ignore


def load_records(csv_path: Path) -> Iterable[GasoilDailyRecord]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        mapping = detect_header(reader.fieldnames or [])

        for line_no, row in enumerate(reader, start=2):  # header is line 1
            try:
                date = parse_date(row[mapping["date"]])

                price = parse_float(row[mapping["price"]], "Price", allow_empty=False)
                if price is None:
                    raise ValueError("Price: missing value not allowed")

                yield GasoilDailyRecord(
                    date=date,
                    price_usd_per_tonne=price,
                    open_usd_per_tonne=parse_float(row.get(mapping["open"], ""), "Open"),
                    high_usd_per_tonne=parse_float(row.get(mapping["high"], ""), "High"),
                    low_usd_per_tonne=parse_float(row.get(mapping["low"], ""), "Low"),
                    volume=parse_int(row.get(mapping["volume"], ""), "Volume"),
                    change_pct=parse_float(row.get(mapping["change"], ""), "Change %"),
                )
            except Exception as e:
                raise ValueError(f"{csv_path.name}: error on line {line_no}: {e}") from e


def write_ndjson(records: List[GasoilDailyRecord], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
    return len(records)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Ingest Investing.com London Gasoil CSV → canonical NDJSON"
    )
    ap.add_argument("--input", required=True, help="Path to Investing.com CSV export")
    ap.add_argument("--output", required=True, help="Output NDJSON path")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")

    records = list(load_records(in_path))
    records.sort(key=lambda r: r.date)

    count = write_ndjson(records, out_path)
    print(f"OK: wrote {count} records to {out_path}")


if __name__ == "__main__":
    main()