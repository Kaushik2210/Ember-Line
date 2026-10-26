"""Generate clearly labelled SYNTHETIC hotspot data for development and tests.

Writes under <DATA_DIR>/synthetic/. The UI shows a "SYNTHETIC DATA" banner whenever it
reads this data. Never use it as if it were real.

    uv run python ../scripts/make_synthetic.py --region punjab-haryana --start 2014-01-01 --end 2018-12-31
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from emberline.config import get_settings
from emberline.data.synthetic import generate_synthetic, write_synthetic
from emberline.regions import REGIONS, get_region


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--region", default=REGIONS[0].id, choices=[r.id for r in REGIONS])
    ap.add_argument("--start", type=date.fromisoformat, default=date(2014, 1, 1))
    ap.add_argument("--end", type=date.fromisoformat, default=date(2018, 12, 31))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data-dir", type=Path, default=None)
    args = ap.parse_args()

    root = args.data_dir or get_settings().data_dir
    region = get_region(args.region)
    df = generate_synthetic(region.bbox, args.start, args.end, seed=args.seed)
    paths = write_synthetic(root, df)
    print(f"SYNTHETIC data: {df.height} rows for {region.id}, {args.start} to {args.end}")
    for p in paths:
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
