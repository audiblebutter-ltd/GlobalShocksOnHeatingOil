#!/usr/bin/env python3
"""
Explain detected heating oil shocks by matching them to nearby events.

Inputs:
- data/sample/heating_oil_shocks.csv     (output of detect_shocks.py)
- data/lookups/events.csv                (date,label)

Output:
- reports/shocks_report.md

Logic:
- For each shock date, find events within +/- WINDOW_DAYS
- Rank by absolute distance in days (closest first)
- Compute a simple confidence score based on distance
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

SHOCKS_FILE = Path("data/sample/heating_oil_shocks.csv")
EVENTS_FILE = Path("data/lookups/events.csv")
OUT_FILE = Path("reports/shocks_report.md")

WINDOW_DAYS = 60
TOP_K_EVENTS = 3


@dataclass
class Match:
    label: str
    event_date: pd.Timestamp
    days_diff: int
    confidence: float


def confidence_from_days(days: int, window: int) -> float:
    # 1.0 when days=0, down to ~0 at edge of window
    x = max(0, window - abs(days)) / window
    return round(x, 3)


def load_events() -> pd.DataFrame:
    if not EVENTS_FILE.exists():
        return pd.DataFrame(columns=["date", "label"])
    ev = pd.read_csv(EVENTS_FILE)
    if "date" not in ev.columns or "label" not in ev.columns:
        return pd.DataFrame(columns=["date", "label"])
    ev["date"] = pd.to_datetime(ev["date"], errors="coerce")
    ev["label"] = ev["label"].astype(str)
    ev = ev.dropna(subset=["date"])
    return ev.sort_values("date").reset_index(drop=True)


def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for c in options:
        if c in df.columns:
            return c
    return None


def build_matches(shock_date: pd.Timestamp, events: pd.DataFrame) -> List[Match]:
    if events.empty:
        return []

    # filter to window
    lo = shock_date - pd.Timedelta(days=WINDOW_DAYS)
    hi = shock_date + pd.Timedelta(days=WINDOW_DAYS)
    window = events[(events["date"] >= lo) & (events["date"] <= hi)].copy()

    if window.empty:
        return []

    window["days_diff"] = (window["date"] - shock_date).dt.days
    window["abs_days"] = window["days_diff"].abs()
    window = window.sort_values(["abs_days", "date"]).head(TOP_K_EVENTS)

    out: List[Match] = []
    for _, r in window.iterrows():
        days = int(r["days_diff"])
        out.append(
            Match(
                label=str(r["label"]),
                event_date=pd.Timestamp(r["date"]),
                days_diff=days,
                confidence=confidence_from_days(days, WINDOW_DAYS),
            )
        )
    return out


def fmt_matches(matches: List[Match]) -> str:
    if not matches:
        return "_No event within window_"
    lines = []
    for m in matches:
        sign = "+" if m.days_diff > 0 else ""
        lines.append(
            f"- **{m.label}** ({m.event_date.date()} | {sign}{m.days_diff}d | conf={m.confidence})"
        )
    return "\n".join(lines)


def main() -> None:
    if not SHOCKS_FILE.exists():
        raise SystemExit(f"Missing shocks file: {SHOCKS_FILE}")
    if not EVENTS_FILE.exists():
        print(f"WARNING: events file not found: {EVENTS_FILE} (report will be eventless)")

    df = pd.read_csv(SHOCKS_FILE)
    if "date" not in df.columns:
        raise SystemExit(f"'date' missing in {SHOCKS_FILE}. Columns: {df.columns.tolist()}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    # Detect which schema you have (your updated detect_shocks has mom/yoy specific flags)
    mom_flag = pick_col(df, ["shock_flag_mom", "shock_flag"])
    yoy_flag = pick_col(df, ["shock_flag_yoy"])
    mom_score = pick_col(df, ["shock_score_mom", "shock_score"])
    yoy_score = pick_col(df, ["shock_score_yoy"])

    events = load_events()

    mom_shocks = df[df[mom_flag] == True].copy() if mom_flag else pd.DataFrame()
    yoy_shocks = df[df[yoy_flag] == True].copy() if yoy_flag else pd.DataFrame()

    if mom_score and not mom_shocks.empty:
        mom_shocks = mom_shocks.sort_values(mom_score, ascending=False)
    if yoy_score and not yoy_shocks.empty:
        yoy_shocks = yoy_shocks.sort_values(yoy_score, ascending=False)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        f.write("# Heating Oil Shock Report\n\n")
        f.write(f"- Window: ±{WINDOW_DAYS} days\n")
        f.write(f"- Events file: `{EVENTS_FILE.as_posix()}`\n")
        f.write(f"- Shocks file: `{SHOCKS_FILE.as_posix()}`\n\n")

        # --- MoM ---
        f.write("## Month-over-month shocks\n\n")
        if mom_shocks.empty:
            f.write("_No MoM shocks detected._\n\n")
        else:
            for _, r in mom_shocks.iterrows():
                d = pd.Timestamp(r["date"])
                gbp_real = r.get("gbp_real", None)
                mom_pct = r.get("mom_pct", None)
                score = r.get(mom_score, None) if mom_score else None

                f.write(f"### {d.date()}\n\n")
                f.write(f"- gbp_real: `{gbp_real}`\n")
                f.write(f"- mom_pct: `{mom_pct}`\n")
                if mom_score:
                    f.write(f"- shock_score: `{score}`\n")
                f.write("\n**Nearest events:**\n\n")
                f.write(fmt_matches(build_matches(d, events)) + "\n\n")

        # --- YoY ---
        f.write("## Year-over-year shocks\n\n")
        if yoy_shocks.empty:
            f.write("_No YoY shocks detected._\n")
        else:
            for _, r in yoy_shocks.iterrows():
                d = pd.Timestamp(r["date"])
                gbp_real = r.get("gbp_real", None)
                yoy_pct = r.get("yoy_pct", None)
                score = r.get(yoy_score, None) if yoy_score else None

                f.write(f"### {d.date()}\n\n")
                f.write(f"- gbp_real: `{gbp_real}`\n")
                f.write(f"- yoy_pct: `{yoy_pct}`\n")
                if yoy_score:
                    f.write(f"- shock_score: `{score}`\n")
                f.write("\n**Nearest events:**\n\n")
                f.write(fmt_matches(build_matches(d, events)) + "\n\n")

    print(f"OK: wrote {OUT_FILE}")


if __name__ == "__main__":
    main()