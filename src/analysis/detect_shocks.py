import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT / "data" / "sample" / "heating_oil_gbp_real.ndjson"
OUTPUT_FILE = ROOT / "data" / "sample" / "heating_oil_shocks.csv"

REAL_COL = "derived.pence_per_litre_real"

# ---- tuning knobs ----
MIN_HISTORY_MONTHS = 24          # don't call shocks until we have enough history
MOM_STD_WINDOW = 12              # rolling volatility window for MoM (%)
YOY_STD_WINDOW = 36              # rolling volatility window for YoY (%)

MOM_ABS_PCT_THRESHOLD = 8.0      # absolute MoM move
MOM_SIGMA_MULT = 2.5             # MoM must exceed this many rolling std devs

YOY_ABS_PCT_THRESHOLD = 25.0     # absolute YoY move
YOY_SIGMA_MULT = 2.0             # YoY must exceed this many rolling std devs

def load_ndjson(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.json_normalize(rows, sep=".")


def main():
    df = load_ndjson(INPUT_FILE)

    # ---- eliminate duplicate 'date' column labels safely ----
    # If multiple 'date' columns exist, rename the first one (top-level oil date) and drop the rest.
    date_cols = [c for c in df.columns if c == "date"]
    if len(date_cols) >= 1:
        cols = list(df.columns)
        first_idx = cols.index("date")
        cols[first_idx] = "oil_date"
        df.columns = cols

        while "date" in df.columns:
            df = df.drop(columns=["date"])

    if "oil_date" not in df.columns:
        raise KeyError(f"Could not find top-level oil date. Columns: {df.columns.tolist()}")

    df["date_source"] = df["oil_date"].astype(str)
    df["date_raw"] = pd.to_datetime(df["date_source"], errors="coerce")
    df = df.dropna(subset=["date_raw"]).copy()

    if REAL_COL not in df.columns:
        raise KeyError(f"Expected {REAL_COL} not found. Columns: {df.columns.tolist()}")

    df["gbp_real"] = pd.to_numeric(df[REAL_COL], errors="coerce")
    df = df.dropna(subset=["gbp_real"]).copy()

    # ---- monthly grain (keep last observation per month) ----
    df["month"] = df["date_raw"].dt.to_period("M").dt.to_timestamp()

    df = (
        df.sort_values("date_raw")
          .groupby("month", as_index=False)
          .tail(1)
          .rename(columns={"month": "date"})  # ONLY 'date' column from here on
          .sort_values("date")
          .reset_index(drop=True)
    )

    # ---- changes ----
    df["mom_pct"] = df["gbp_real"].pct_change() * 100.0
    df["yoy_pct"] = df["gbp_real"].pct_change(12) * 100.0

    # rolling volatility
    df["mom_std_12"] = df["mom_pct"].rolling(MOM_STD_WINDOW).std()
    df["yoy_std_36"] = df["yoy_pct"].rolling(YOY_STD_WINDOW).std()

    # shock scores (z-like)
    df["shock_score_mom"] = df["mom_pct"].abs() / df["mom_std_12"]
    df["shock_score_yoy"] = df["yoy_pct"].abs() / df["yoy_std_36"]

    # ---- history guard ----
    df["history_ok"] = df.index >= MIN_HISTORY_MONTHS

    # ---- shock flags ----
    df["shock_flag_mom"] = (
        df["history_ok"]
        & df["mom_std_12"].notna()
        & (df["mom_pct"].abs() >= MOM_ABS_PCT_THRESHOLD)
        & (df["mom_pct"].abs() >= MOM_SIGMA_MULT * df["mom_std_12"])
    )

    df["shock_flag_yoy"] = (
        df["history_ok"]
        & df["yoy_std_36"].notna()
        & (df["yoy_pct"].abs() >= YOY_ABS_PCT_THRESHOLD)
        & (df["yoy_pct"].abs() >= YOY_SIGMA_MULT * df["yoy_std_36"])
    )

    # Optional: "any shock" convenience
    df["shock_flag_any"] = df["shock_flag_mom"] | df["shock_flag_yoy"]

    out_cols = [
        "date",
        "gbp_real",
        "mom_pct",
        "yoy_pct",
        "mom_std_12",
        "yoy_std_36",
        "shock_score_mom",
        "shock_score_yoy",
        "shock_flag_mom",
        "shock_flag_yoy",
        "shock_flag_any",
        "history_ok",
        "date_raw",
        "date_source",
        "inputs.oil_period",
        "inputs.cpih_period",
        REAL_COL,
    ]
    out_cols = [c for c in out_cols if c in df.columns]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df[out_cols].to_csv(OUTPUT_FILE, index=False)

    mom_shocks = df[df["shock_flag_mom"] & df["shock_score_mom"].notna()].copy()
    yoy_shocks = df[df["shock_flag_yoy"] & df["shock_score_yoy"].notna()].copy()

    print("")
    print("Shock detection complete")
    print("------------------------")
    print("Input:", INPUT_FILE)
    print("Real price column used:", REAL_COL)
    print("Total usable months:", len(df))
    print(f"MoM shocks detected: {len(mom_shocks)}")
    print(f"YoY shocks detected: {len(yoy_shocks)}")
    print("Output:", OUTPUT_FILE)
    print("")

    if len(mom_shocks):
        top = mom_shocks.sort_values("shock_score_mom", ascending=False).head(15)
        print("Top MoM shocks (by shock_score_mom)")
        print(top[["date", "gbp_real", "mom_pct", "mom_std_12", "shock_score_mom"]].to_string(index=False))
        print("")
    else:
        print("No MoM shocks detected with current thresholds.")
        print("")

    if len(yoy_shocks):
        top = yoy_shocks.sort_values("shock_score_yoy", ascending=False).head(15)
        print("Top YoY shocks (by shock_score_yoy)")
        print(top[["date", "gbp_real", "yoy_pct", "yoy_std_36", "shock_score_yoy"]].to_string(index=False))
        print("")
    else:
        print("No YoY shocks detected with current thresholds.")
        print("")


if __name__ == "__main__":
    main()