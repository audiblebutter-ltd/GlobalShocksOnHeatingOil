#!/usr/bin/env python3
"""
Stage 2 (Transform)
-------------------
Transform canonical gasoil NDJSON into a "BoilerJuice-style" litres price view.

Input:
- NDJSON from Stage 1:
  date, price_usd_per_tonne, open/high/low, volume, change_pct

Output:
- NDJSON with derived fields:
  - litres_per_tonne (based on density)
  - usd_per_litre (wholesale proxy)
  - estimated_retail_usd_per_litre (simple alpha/beta model)
  - estimated_retail_usd_per_1000l
  - ppl_proxy (pence-per-litre proxy if FX provided later)

This version is intentionally FX-neutral:
- We compute USD/L and USD/1000L.
- Later we add FX and inflation adjustment.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class TransformConfig:
    density_kg_per_litre: float = 0.845  # default used in ICE contract spec context
    retail_alpha: float = 1.10
    retail_beta_usd_per_litre: float = 0.05  # placeholder until calibrated


def litres_per_tonne(density_kg_per_litre: float) -> float:
    if density_kg_per_litre <= 0:
        raise ValueError("density_kg_per_litre must be > 0")
    # 1 tonne = 1000 kg
    return 1000.0 / density_kg_per_litre


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


def write_ndjson(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def transform(rows: List[Dict[str, Any]], cfg: TransformConfig) -> List[Dict[str, Any]]:
    lpt = litres_per_tonne(cfg.density_kg_per_litre)

    out: List[Dict[str, Any]] = []
    for r in rows:
        date = r["date"]
        usd_per_tonne = float(r["price_usd_per_tonne"])

        usd_per_l = usd_per_tonne / lpt

        # Simple retail model in USD/L (placeholder until we add FX + calibration)
        retail_usd_per_l = (usd_per_l * cfg.retail_alpha) + cfg.retail_beta_usd_per_litre

        out.append({
            "date": date,
            "gasoil_usd_per_tonne": usd_per_tonne,
            "assumptions": {
                "density_kg_per_litre": cfg.density_kg_per_litre,
                "litres_per_tonne": round(lpt, 4),
                "retail_alpha": cfg.retail_alpha,
                "retail_beta_usd_per_litre": cfg.retail_beta_usd_per_litre,
            },
            "derived": {
                "usd_per_litre_wholesale_proxy": round(usd_per_l, 6),
                "usd_per_1000l_wholesale_proxy": round(usd_per_l * 1000.0, 3),
                "usd_per_litre_retail_est": round(retail_usd_per_l, 6),
                "usd_per_1000l_retail_est": round(retail_usd_per_l * 1000.0, 3),
            }
        })

    # Keep ascending date order
    out.sort(key=lambda x: x["date"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Transform gasoil NDJSON → litres-based pricing view")
    ap.add_argument("--input", required=True, help="Input NDJSON from Stage 1")
    ap.add_argument("--output", required=True, help="Output NDJSON with derived litres pricing")
    ap.add_argument("--density", type=float, default=0.845, help="Density kg/L (default 0.845)")
    ap.add_argument("--alpha", type=float, default=1.10, help="Retail model alpha (default 1.10)")
    ap.add_argument("--beta", type=float, default=0.05, help="Retail model beta USD/L (default 0.05)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")

    cfg = TransformConfig(
        density_kg_per_litre=args.density,
        retail_alpha=args.alpha,
        retail_beta_usd_per_litre=args.beta,
    )

    rows = load_ndjson(in_path)
    out = transform(rows, cfg)
    write_ndjson(out, out_path)

    print(f"OK: transformed {len(rows)} rows → {out_path}")


if __name__ == "__main__":
    main()