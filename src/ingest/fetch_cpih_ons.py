#!/usr/bin/env python3
"""
Fetch CPIH index (2015=100) from ONS time-series generator CSV.

Series:
- L522 : CPIH INDEX 00: ALL ITEMS 2015=100 (dataset MM23)

URL (no API key):
https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/l522/mm23

Output:
data/lookups/cpih.csv with columns:
  period, cpih_index
where period is YYYY-MM (monthly only).
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import urllib.request
from pathlib import Path

ONS_CPIH_CSV_URL = (
    "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/l522/mm23"
)

MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

MONTHLY_RE = re.compile(r"^(?P<year>\d{4})\s+(?P<mon>[A-Za-z]{3})$")


def download_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "GlobalShocksOnHeatingOil/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return raw.decode("utf-8-sig", errors="replace")


def save_raw(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def to_yyyy_mm(period_str: str) -> str | None:
    s = period_str.strip().strip('"')
    m = MONTHLY_RE.match(s)
    if not m:
        return None
    year = m.group("year")
    mon = m.group("mon").upper()
    mm = MONTHS.get(mon)
    if not mm:
        return None
    return f"{year}-{mm}"


def find_data_header_line_index(lines: list[str]) -> int:
    """
    ONS generator CSV starts with a metadata block like:
      "Title","..."
      "CDID","..."
    Then later a proper table header appears, usually containing:
      "Time period","Value"
    We scan until we find that header row.
    """
    for i, line in enumerate(lines):
        l = line.strip().strip("\ufeff")
        if not l:
            continue
        norm = l.replace('"', "").strip().lower()
        # must contain both 'time period' (or 'period') and 'value'
        if ("time period" in norm or norm.startswith("period,")) and "value" in norm:
            return i
    return -1


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch CPIH (L522) from ONS generator CSV")
    ap.add_argument("--output", default="data/lookups/cpih.csv", help="Output lookup CSV")
    ap.add_argument("--raw", default="data/lookups/ons_l522_raw.csv", help="Save raw download for debugging")
    ap.add_argument("--show", type=int, default=8, help="Print first N lines of the raw download")
    args = ap.parse_args()

    out_path = Path(args.output)
    raw_path = Path(args.raw)

    text = download_text(ONS_CPIH_CSV_URL)
    save_raw(raw_path, text)

    lines = text.splitlines()
    print(f"Saved raw download to: {raw_path}")
    print(f"First {min(args.show, len(lines))} lines:")
    for l in lines[: args.show]:
        print(l)

    header_line_idx = find_data_header_line_index(lines)
    if header_line_idx < 0:
        raise SystemExit(
            "ERROR: Could not find the data table header row (expected 'Time period' and 'Value').\n"
            f"Raw saved to: {raw_path}"
        )

    # Parse only the table section (skip metadata block)
    table_text = "\n".join(lines[header_line_idx:])
    f = io.StringIO(table_text)
    reader = csv.reader(f)

    try:
        header = next(reader)
    except StopIteration:
        raise SystemExit("ERROR: ONS table section was empty (no header).")

    header = [h.strip().strip('"') for h in header]
    header_norm = [h.lower() for h in header]

    def idx_of(*names: str) -> int:
        for n in names:
            n = n.lower()
            if n in header_norm:
                return header_norm.index(n)
        return -1

    period_idx = idx_of("time period", "period")
    value_idx = idx_of("value")

    if period_idx < 0 or value_idx < 0:
        raise SystemExit(
            "ERROR: Found table header but could not locate required columns.\n"
            f"Header was: {header}\n"
            f"Raw saved to: {raw_path}"
        )

    rows_written = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as out_f:
        w = csv.writer(out_f)
        w.writerow(["period", "cpih_index"])

        for row in reader:
            if not row or len(row) <= max(period_idx, value_idx):
                continue

            period_raw = row[period_idx].strip().strip('"')
            value_raw = row[value_idx].strip().strip('"')

            period = to_yyyy_mm(period_raw)
            if period is None:
                continue

            if not value_raw or value_raw in (".", "-", "—"):
                continue

            try:
                float(value_raw)
            except ValueError:
                continue

            w.writerow([period, value_raw])
            rows_written += 1

    print(f"OK: wrote {rows_written} CPIH rows to {out_path}")


if __name__ == "__main__":
    main()