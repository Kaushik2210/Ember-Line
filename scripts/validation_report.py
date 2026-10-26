"""Print a validation report for one region from cached FIRMS data.

Everything shown is computed from the cache; nothing is typed in. Run after prefetching:

    uv run python ../scripts/validation_report.py --region punjab-haryana
    uv run python ../scripts/validation_report.py --region punjab-haryana --write

--write saves the report to docs/validation/<region>.md.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from emberline.config import get_settings
from emberline.data.store import HotspotStore
from emberline.pipeline import run_analysis
from emberline.regions import REGIONS, get_region
from emberline.report import report
from emberline.science.series import METRICS

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--region", default="punjab-haryana", choices=[r.id for r in REGIONS])
    ap.add_argument("--start", type=date.fromisoformat)
    ap.add_argument("--end", type=date.fromisoformat)
    ap.add_argument("--metric", default="frp_sum_mw", choices=METRICS)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    region = get_region(args.region)
    store = HotspotStore(get_settings().data_dir)
    cov = store.coverage()
    default_start = date.fromisoformat(region.default_start)
    default_end = date.fromisoformat(region.default_end)
    start = args.start or (cov["min_date"].min() if cov.height else default_start)
    end = args.end or (cov["max_date"].max() if cov.height else default_end)
    a = run_analysis(
        store, region.bbox, start, end, metric=args.metric,
        progress=lambda m: print(f"  .. {m}", flush=True),
    )
    text = report(a, region.name, cov)
    print(text)
    if args.write:
        out = ROOT / "docs" / "validation" / f"{region.id}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
