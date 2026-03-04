#!/usr/bin/env python3
"""
Plot Heating Oil (REAL terms) with shock points + optional event markers.
Outputs a PNG you can drop into Data & Grit posts.

Input:
- data/sample/heating_oil_gbp_real.ndjson  (one JSON per line)
Optional:
- data/sample/heating_oil_shocks.csv       (shock dates to mark)
- data/lookups/events.csv                  (columns: date,title,conf) OR (date,event,conf)

Output:
- data/out/heating_oil_shocks.png
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Any, List

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# -----------------------------
# Config
# -----------------------------
ROOT = Path(__file__).resolve().parents[2]  # project root (src/analysis -> root)

NDJSON_PATH = ROOT / "data" / "sample" / "heating_oil_gbp_real.ndjson"
SHOCKS_PATH = ROOT / "data" / "sample" / "heating_oil_shocks.csv"
EVENTS_PATH = ROOT / "data" / "lookups" / "events.csv"

OUT_DIR = ROOT / "data" / "out"
OUT_PNG = OUT_DIR / "heating_oil_shocks.png"

# Your ndjson is nested like:
# {"date":"1986-02-01","inputs":{...},"derived":{"pence_per_litre_real":26.19,...}}
PRICE_PATH = ("derived", "pence_per_litre_real")
PRICE_FALLBACK_PATH = ("derived", "pence_per_litre_nominal")

# Only used to filter event markers when conf exists
EVENT_CONF_MIN = 0.5


# -----------------------------
# Helpers
# -----------------------------
def parse_date(s: str) -> datetime:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(day=1)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        s = str(x).strip().replace(",", "")
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def get_path(d: dict, path: Tuple[str, ...]) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


@dataclass
class Event:
    date: datetime
    title: str
    conf: Optional[float] = None


def load_events(path: Path) -> List[Event]:
    if not path.exists():
        return []

    events: List[Event] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_raw = row.get("date") or row.get("Date") or row.get("period") or row.get("Period") or ""
            title = (
                        row.get("title")
                        or row.get("event")
                        or row.get("label")   # <-- this is the important one
                        or row.get("Event")
                        or "Event"
                    )
            conf_raw = row.get("conf") or row.get("confidence") or row.get("Conf")

            if not str(date_raw).strip():
                continue

            dt = parse_date(str(date_raw))
            conf = safe_float(conf_raw)
            events.append(Event(date=dt, title=str(title).strip(), conf=conf))

    return sorted(events, key=lambda e: e.date)


def load_shock_dates(path: Path) -> List[datetime]:
    """
    Loads shock dates from shocks CSV.
    Expected to contain a column named 'date' (or 'period') in YYYY-MM or YYYY-MM-DD.
    """
    if not path.exists():
        return []

    shock_dates: List[datetime] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = row.get("date") or row.get("Date") or row.get("period") or row.get("Period")
            if not d:
                continue
            shock_dates.append(parse_date(str(d)))

    # de-dupe + sort
    return sorted(set(shock_dates))


def load_series(path: Path):
    """
    Loads:
      - date (top-level key: 'date')
      - price (nested: derived.pence_per_litre_real)
    Returns:
      dates, prices, detected_keys
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if not rows:
        raise RuntimeError("status: FAIL | ndjson is empty")

    dates: List[datetime] = []
    prices: List[float] = []

    for r in rows:
        d_raw = r.get("date")
        if d_raw is None:
            continue

        # Real first, nominal fallback (just in case)
        p_raw = get_path(r, PRICE_PATH)
        if p_raw is None:
            p_raw = get_path(r, PRICE_FALLBACK_PATH)

        pv = safe_float(p_raw)
        if pv is None:
            continue

        dt = parse_date(str(d_raw))
        dates.append(dt)
        prices.append(pv)

    if not dates:
        first = rows[0]
        derived_keys = None
        if isinstance(first, dict) and isinstance(first.get("derived"), dict):
            derived_keys = list(first["derived"].keys())
        raise RuntimeError(
            "status: FAIL | no valid rows loaded after nested extraction\n"
            f"first row keys: {list(first.keys()) if isinstance(first, dict) else None}\n"
            f"derived keys: {derived_keys}\n"
            f"expected price path: {'.'.join(PRICE_PATH)}"
        )

    # sort by date
    order = sorted(range(len(dates)), key=lambda i: dates[i])
    dates = [dates[i] for i in order]
    prices = [prices[i] for i in order]

    detected = ("date", ".".join(PRICE_PATH))
    return dates, prices, detected


def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def plot(dates: List[datetime], prices: List[float], detected_keys, events: List[Event], shock_dates: List[datetime]):
    # Terminal-ish styling (Data & Grit look)
    plt.rcParams.update(
        {
            "figure.facecolor": "#070a0f",
            "axes.facecolor": "#070a0f",
            "axes.edgecolor": "#1f2a33",
            "axes.labelcolor": "#9fd6a6",
            "xtick.color": "#6fbf7a",
            "ytick.color": "#6fbf7a",
            "grid.color": "#152028",
            "text.color": "#9fd6a6",
            "font.family": "DejaVu Sans Mono",
        }
    )

    fig = plt.figure(figsize=(14, 7), dpi=160)
    ax = fig.add_subplot(111)

    ax.grid(True, which="major", linestyle="-", linewidth=0.5, alpha=0.55)
    ax.grid(True, which="minor", linestyle="-", linewidth=0.25, alpha=0.35)

    # Main line
    ax.plot(dates, prices, linewidth=1.4)

    # Shock points: overlay from shocks CSV
    if shock_dates:
        price_by_date = {d: p for d, p in zip(dates, prices)}
        sx = [d for d in shock_dates if d in price_by_date]
        sy = [price_by_date[d] for d in sx]
        if sx:
            ax.scatter(sx, sy, s=28)

    # Events: vertical lines + subtle labels (conf filter if present)
    ymax = max(prices) if prices else 1.0
    for e in events:
        if e.conf is not None and e.conf < EVENT_CONF_MIN:
            continue
        ax.axvline(e.date, linewidth=0.8, alpha=0.6)
        ax.text(
            e.date,
            ymax,
            f" {e.title}",
            rotation=90,
            va="top",
            ha="left",
            fontsize=8,
            alpha=0.8,
        )

    ax.set_title("Heating Oil (Real Terms) — shocks + events", pad=14)
    ax.set_ylabel("Pence per litre (real terms)")
    ax.set_xlabel("Month")

    # Date formatting
    ax.xaxis.set_major_locator(mdates.YearLocator(base=5))
    ax.xaxis.set_minor_locator(mdates.YearLocator(base=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    dk = detected_keys
    footer = (
        f"status: ONLINE | rows: {len(dates)} | shocks(csv): {len(shock_dates)} | events: {len(events)}\n"
        f"keys: date={dk[0]} | price={dk[1]}"
    )
    ax.text(0.01, 0.02, footer, transform=ax.transAxes, fontsize=9, alpha=0.9)

    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)


def main():
    ensure_out_dir()

    dates, prices, detected_keys = load_series(NDJSON_PATH)
    events = load_events(EVENTS_PATH)
    shock_dates = load_shock_dates(SHOCKS_PATH)

    plot(dates, prices, detected_keys, events, shock_dates)

    print(f"OK: wrote {OUT_PNG.relative_to(ROOT)}")
    print(f"rows: {len(dates)} | shocks(csv): {len(shock_dates)} | events: {len(events)}")
    print(f"keys: date={detected_keys[0]} price={detected_keys[1]}")


if __name__ == "__main__":
    main()