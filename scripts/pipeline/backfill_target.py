from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._bootstrap import bootstrap
except ImportError:
    from _bootstrap import bootstrap

bootstrap()

from gold_collectors.full_pipeline import DataLakeWriter
from gold_collectors.http import CachedHttpClient
from gold_collectors.reliability import accepted_historical_sources, collect_historical_rows, date_range, read_registry, write_csv
from gold_collectors.http import CollectorHttpError

try:
    from tqdm import tqdm as _tqdm
except Exception:  # pragma: no cover - optional dependency
    _tqdm = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical Vietnamese SJC gold target from audited historical-valid sources only.")
    parser.add_argument("--from", dest="from_date", default="2011-07-06")
    parser.add_argument("--to", dest="to_date", default="2026-07-06")
    parser.add_argument("--registry", default="configs/source_registry_audited.yaml")
    parser.add_argument("--out-dir", default="data/lake/domestic_target")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--format", default="parquet,csv")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--show-progress", action="store_true", default=True)
    return parser.parse_args()


def _progress(items: list[str], description: str, enabled: bool) -> Any:
    if not enabled or _tqdm is None:
        return items
    return _tqdm(items, desc=description, unit="dates")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    registry = read_registry(args.registry)
    allowed_sources = accepted_historical_sources(registry)
    out_dir = Path(args.out_dir)
    writer = DataLakeWriter(out_dir, formats=args.format.split(","))
    cache_dir = args.cache_dir or str(out_dir / "raw" / "http_cache")
    http = CachedHttpClient(cache_dir=cache_dir, timeout_seconds=args.timeout, retries=args.retries, min_interval_seconds=0.35)

    rows = []
    leakage_rows = []
    dates = date_range(args.from_date, args.to_date)
    for requested_date in _progress(dates, f"Backfill historical target ({args.from_date} -> {args.to_date})", args.show_progress):
        for source in sorted(allowed_sources):
            try:
                source_rows = collect_historical_rows(source, requested_date, http)
                rows.extend(source_rows)
                if not source_rows:
                    leakage_rows.append(
                        {
                            "requested_date": requested_date,
                            "source": source,
                            "issue": "no_accepted_rows",
                            "note": "No row accepted; either empty or business_date did not match requested_date.",
                        }
                    )
            except Exception as exc:  # noqa: BLE001 - preserve resilient ingest
                leakage_rows.append(
                    {
                        "requested_date": requested_date,
                        "source": source,
                        "issue": "request_error",
                        "note": f"{type(exc).__name__}: {exc}",
                    }
                )
                if not isinstance(exc, CollectorHttpError):
                    raise

    writer.write_dataset("domestic_gold_quotes", rows)
    write_csv(out_dir / "reports" / "current_leakage_report.csv", leakage_rows)
    summary = {
        "out_dir": str(out_dir),
        "from": args.from_date,
        "to": args.to_date,
        "historical_valid_sources": sorted(allowed_sources),
        "accepted_records": len(rows),
        "leakage_or_empty_flags": len(leakage_rows),
        "target_csv": str(out_dir / "normalized" / "domestic_gold_quotes.csv"),
    }
    (out_dir / "reports" / "backfill_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
