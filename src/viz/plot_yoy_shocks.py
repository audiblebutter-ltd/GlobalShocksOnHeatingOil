#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = Path("data/sample/heating_oil_shocks.csv")
OUT_FILE = Path("reports/heating_oil_yoy_shocks.png")


def main():
    df = pd.read_csv(INPUT_FILE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    if "yoy_pct" not in df.columns:
        raise KeyError("yoy_pct not found in shocks CSV (run detect_shocks.py first).")

    flag_col = "shock_flag_yoy" if "shock_flag_yoy" in df.columns else None
    shocks = df[df[flag_col] == True].copy() if flag_col else df.iloc[0:0].copy()  # noqa: E712

    plt.figure(figsize=(12, 6))
    plt.plot(df["date"], df["yoy_pct"], label="YoY % change (real price)")

    if len(shocks):
        plt.scatter(shocks["date"], shocks["yoy_pct"], label="YoY shocks")

    plt.axhline(0, linewidth=1)
    plt.title("Heating oil (real terms) YoY % with detected YoY shocks")
    plt.xlabel("Date")
    plt.ylabel("YoY %")
    plt.legend()
    plt.tight_layout()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_FILE, dpi=150)

    print(f"Wrote: {OUT_FILE}")
    print(f"YoY shocks: {len(shocks)}")

    if len(shocks):
        cols = ["date", "gbp_real", "yoy_pct", "shock_score_yoy"]
        cols = [c for c in cols if c in shocks.columns]
        print(shocks[cols].tail(25).to_string(index=False))


if __name__ == "__main__":
    main()