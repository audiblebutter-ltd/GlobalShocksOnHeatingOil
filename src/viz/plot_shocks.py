#!/usr/bin/env python3
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = Path("data/sample/heating_oil_shocks.csv")
OUT_FILE = Path("reports/heating_oil_real_shocks.png")


def main():
    df = pd.read_csv(INPUT_FILE)

    # Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Prefer MoM shock columns (new schema)
    flag_col = "shock_flag_mom" if "shock_flag_mom" in df.columns else "shock_flag"
    score_col = "shock_score_mom" if "shock_score_mom" in df.columns else "shock_score"

    # Filter shocks for markers
    shocks = df[df[flag_col] == True].copy()  # noqa: E712

    # Plot price series
    plt.figure(figsize=(12, 6))
    plt.plot(df["date"], df["gbp_real"], label="Real price (pence/litre)")

    # Overlay shocks as markers
    if len(shocks):
        plt.scatter(shocks["date"], shocks["gbp_real"], label=f"Shocks ({flag_col})")

    plt.title("Heating oil (real terms) with detected shocks")
    plt.xlabel("Date")
    plt.ylabel("Real price (pence per litre)")
    plt.legend()
    plt.tight_layout()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_FILE, dpi=150)

    print(f"Wrote: {OUT_FILE}")
    print(f"Shocks: {len(shocks)}")

    # Print a small table
    cols = ["date", "gbp_real", "mom_pct", score_col]
    cols = [c for c in cols if c in shocks.columns]
    if len(shocks) and cols:
        print(shocks[cols].tail(25).to_string(index=False))


if __name__ == "__main__":
    main()