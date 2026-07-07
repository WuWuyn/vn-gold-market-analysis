from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

try:
    from ._bootstrap import bootstrap
except ImportError:
    from _bootstrap import bootstrap

bootstrap()

from gold_collectors.reliability import AuditRecord, build_registry_from_audit, to_yaml, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audited source registry from source_audit output.")
    parser.add_argument("--audit-json", default="audit_output/source_audit.json")
    parser.add_argument("--out", default="configs/source_registry_audited.yaml")
    parser.add_argument("--csv-out", default="configs/source_registry_audited.csv")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    audit_path = Path(args.audit_json)
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_rows = [AuditRecord(**item) for item in payload]
    registry = build_registry_from_audit(audit_rows)
    Path(args.out).write_text(to_yaml(registry), encoding="utf-8")
    write_csv(args.csv_out, [asdict(item) for item in registry])
    print(json.dumps({"registry": args.out, "sources": len(registry)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
