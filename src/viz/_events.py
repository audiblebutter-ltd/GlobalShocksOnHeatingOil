from pathlib import Path
import pandas as pd

EVENTS_FILE = Path("data/lookups/events.csv")

def load_events():
    if not EVENTS_FILE.exists():
        return pd.DataFrame(columns=["date", "label"])
    ev = pd.read_csv(EVENTS_FILE)
    if "date" not in ev.columns or "label" not in ev.columns:
        return pd.DataFrame(columns=["date", "label"])
    ev["date"] = pd.to_datetime(ev["date"], errors="coerce")
    ev = ev.dropna(subset=["date"])
    return ev