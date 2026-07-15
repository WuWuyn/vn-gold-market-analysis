#!/usr/bin/env python3
"""Full data-quality audit for the VN gold analysis lake.

This audit is intentionally read-only for analytical datasets. It profiles the
current lake and records issues that can materially invalidate the report/model,
especially unit conversion, target horizon semantics, leakage, grain, and source
semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
LAKE = ROOT / "data" / "lake"
QUALITY = LAKE / "quality"
REPORTS = ROOT / "docs" / "reports"

TROY_OZ_GRAMS = 31.1034768
GRAMS_PER_CHI = 3.75
GRAMS_PER_LUONG = 37.5
OZ_PER_LUONG_CORRECT = GRAMS_PER_LUONG / TROY_OZ_GRAMS
CURRENT_WRONG_LUONG_PER_OZ = (TROY_OZ_GRAMS / 1.205) / GRAMS_PER_LUONG

CORE_DAILY_FILES = [
    "gold_quotes_sjc_historical.csv",
    "pipeline_output_domestic_daily.csv",
    "pipeline_output_global_reference.csv",
    "pipeline_output_premium_enriched.csv",
    "pipeline_output_vn_macro_asof.csv",
    "pipeline_output_event_regime.csv",
    "modeling/model_frame_daily.csv",
    "modeling/snapshot_forecasts.csv",
    "modeling/decision_signals.csv",
    "modeling/walk_forward_predictions.csv",
    "modeling/paper_trading_ledger.csv",
    "news_availability_audit.csv",
    "source_discovery/sbv_structures.csv",
    "events/sbv_gold_policy_events.csv",
    "normalized/retail_deposit_rates.csv",
    "normalized/sbv_policy_rates.csv",
    "normalized/lbma_gold_spot_am_pm.csv",
]


@dataclass
class Finding:
    severity: str
    check: str
    status: str
    evidence: str
    impacted_artifacts: str
    recommendation: str
    confidence: str = "high"


def read_csv(rel_path: str) -> pd.DataFrame:
    path = LAKE / rel_path
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def read_json(rel_path: str) -> dict[str, Any]:
    path = LAKE / rel_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def date_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.normalize()


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def pct(value: float | int | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def profile_file(rel_path: str) -> dict[str, Any]:
    path = LAKE / rel_path
    out: dict[str, Any] = {
        "path": rel_path,
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }
    if not path.exists() or path.suffix.lower() != ".csv":
        return out
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:  # noqa: BLE001
        out["read_error"] = f"{type(exc).__name__}: {exc}"
        return out
    out.update(
        {
            "rows": int(len(df)),
            "cols": int(len(df.columns)),
            "columns": list(df.columns),
            "exact_duplicate_rows": int(df.duplicated().sum()),
        }
    )
    date_cols = [c for c in df.columns if c.lower() in {"date", "business_date", "event_date", "published_at", "available_from", "feature_date", "signal_date"}]
    date_spans = {}
    for col in date_cols[:6]:
        d = date_series(df[col]).dropna()
        if not d.empty:
            date_spans[col] = {
                "min": d.min().date().isoformat(),
                "max": d.max().date().isoformat(),
                "non_null": int(len(d)),
            }
    out["date_spans"] = date_spans
    null_rates = df.isna().mean().sort_values(ascending=False).head(20)
    out["top_null_rates"] = {str(k): float(v) for k, v in null_rates.items()}
    return out


def inventory_lake_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(p for p in LAKE.rglob("*") if p.is_file()):
        rel = path.relative_to(LAKE).as_posix()
        row: dict[str, Any] = {
            "path": rel,
            "suffix": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if path.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(path, low_memory=False)
                row["rows"] = int(len(df))
                row["cols"] = int(len(df.columns))
                row["exact_duplicate_rows"] = int(df.duplicated().sum())
                date_cols = [
                    c
                    for c in df.columns
                    if c.lower()
                    in {
                        "date",
                        "business_date",
                        "event_date",
                        "published_at",
                        "available_from",
                        "feature_date",
                        "signal_date",
                        "crawl_date",
                    }
                ]
                spans = {}
                for col in date_cols[:4]:
                    d = date_series(df[col]).dropna()
                    if not d.empty:
                        spans[col] = f"{d.min().date().isoformat()}..{d.max().date().isoformat()} ({len(d):,})"
                row["date_spans_compact"] = "; ".join(f"{k}={v}" for k, v in spans.items())
                row["columns_sample"] = ", ".join(list(df.columns)[:18])
            except Exception as exc:  # noqa: BLE001
                row["read_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


def add_finding(findings: list[Finding], severity: str, check: str, status: str, evidence: str, impacted: str, recommendation: str, confidence: str = "high") -> None:
    findings.append(Finding(severity, check, status, evidence, impacted, recommendation, confidence))


def audit_unit_conversion(findings: list[Finding]) -> dict[str, Any]:
    results: dict[str, Any] = {
        "correct_oz_per_luong": OZ_PER_LUONG_CORRECT,
        "wrong_luong_per_oz_constant": CURRENT_WRONG_LUONG_PER_OZ,
        "wrong_over_correct_factor_expected": 1 / CURRENT_WRONG_LUONG_PER_OZ / OZ_PER_LUONG_CORRECT,
    }
    for rel in ["pipeline_output_premium_enriched.csv", "modeling/model_frame_daily.csv"]:
        df = read_csv(rel)
        if df.empty:
            continue
        fx_col = "usd_vnd" if "usd_vnd" in df.columns else "usd_vnd_mid" if "usd_vnd_mid" in df.columns else None
        required = {"global_gold_usd_oz", "global_gold_vnd_per_luong"}
        if fx_col and required <= set(df.columns):
            g = numeric(df["global_gold_usd_oz"])
            fx = numeric(df[fx_col])
            stored = numeric(df["global_gold_vnd_per_luong"])
            correct = g * fx * OZ_PER_LUONG_CORRECT
            valid = correct.notna() & stored.notna() & (correct > 0)
            if valid.any():
                ratio = stored[valid] / correct[valid]
                result = {
                    "rows_checked": int(valid.sum()),
                    "stored_to_correct_median": float(ratio.median()),
                    "stored_to_correct_p05": float(ratio.quantile(0.05)),
                    "stored_to_correct_p95": float(ratio.quantile(0.95)),
                }
                if "premium_pct" in df.columns:
                    result["current_premium_pct_median"] = float(numeric(df.loc[valid, "premium_pct"]).median())
                sell_col = "sell_consensus" if "sell_consensus" in df.columns else "sell_price" if "sell_price" in df.columns else None
                if sell_col:
                    sell = numeric(df.loc[valid, sell_col])
                    correct_premium_pct = (sell - correct.loc[valid]) / correct.loc[valid]
                    result["correct_premium_pct_median"] = float(correct_premium_pct.median())
                    result["correct_positive_premium_share"] = float((correct_premium_pct > 0).mean())
                results[rel] = result
                if abs(result["stored_to_correct_median"] - 1) > 0.01:
                    add_finding(
                        findings,
                        "critical",
                        "global_gold_unit_conversion",
                        "failed",
                        f"{rel}: stored global_gold_vnd_per_luong is median {result['stored_to_correct_median']:.3f}x correct troy-ounce-to-luong conversion; expected formula is USD/oz * USD/VND * 37.5/31.1034768.",
                        "pipeline_output_premium_enriched.csv; model_frame_daily.csv; premium charts; model features; all forecast/report conclusions using premium",
                        "Fix conversion constants, rebuild premium, model frame, EDA figures, models, snapshot forecasts, paper-trading, and report before using decisions.",
                    )
    return results


def audit_horizons(findings: list[Finding]) -> dict[str, Any]:
    df = read_csv("modeling/model_frame_daily.csv")
    if df.empty or "date" not in df.columns:
        return {}
    dates = date_series(df["date"]).sort_values().reset_index(drop=True)
    full = pd.date_range(dates.min(), dates.max(), freq="D")
    missing = full.difference(dates.drop_duplicates())
    diff_counts = dates.drop_duplicates().diff().dt.days.dropna().value_counts().sort_index().to_dict()
    out: dict[str, Any] = {
        "date_min": dates.min().date().isoformat(),
        "date_max": dates.max().date().isoformat(),
        "unique_dates": int(dates.nunique()),
        "calendar_days": int(len(full)),
        "missing_calendar_days": int(len(missing)),
        "diff_counts": {str(k): int(v) for k, v in diff_counts.items()},
    }
    missing_month_targets: list[str] = []
    invalid_month_targets: list[str] = []
    stale_day_targets = [c for c in ("net_return_21d", "net_return_63d", "net_return_105d") if c in df.columns]
    for months in (1, 3, 5):
        target_col = f"target_date_{months}m"
        exit_col = f"exit_date_{months}m"
        ret_col = f"net_return_{months}m"
        if not {target_col, exit_col, ret_col} <= set(df.columns):
            missing_month_targets.append(f"{months}m")
            continue
        target_dates = date_series(df[target_col])
        exit_dates = date_series(df[exit_col])
        valid = target_dates.notna() & exit_dates.notna() & pd.to_numeric(df[ret_col], errors="coerce").notna()
        delta = (exit_dates[valid] - target_dates[valid]).dt.days
        out[f"horizon_{months}m"] = {
            "non_null_targets": int(valid.sum()),
            "exit_after_target_violations": int((delta < 0).sum()),
            "exit_lag_days_median": float(delta.median()) if not delta.empty else None,
            "exit_lag_days_max": float(delta.max()) if not delta.empty else None,
        }
        if (delta < 0).any():
            invalid_month_targets.append(f"{months}m")

    if missing_month_targets or invalid_month_targets or stale_day_targets:
        add_finding(
            findings,
            "critical",
            "target_horizon_semantics",
            "failed",
            f"Calendar-month target audit failed. missing={missing_month_targets}, invalid_exit_order={invalid_month_targets}, stale_day_targets={stale_day_targets}.",
            "model_frame_daily targets; model_results; decision_signals; snapshot_forecasts; paper_trading_ledger; report decision section",
            "Use DateOffset(months=1/3/5), nearest available future exit price, and remove stale net_return_21d/63d/105d targets from the rebuilt model frame.",
        )
    return out


def audit_grain_and_validity(findings: list[Finding]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rel in CORE_DAILY_FILES:
        df = read_csv(rel)
        if df.empty:
            out[rel] = {"exists_or_rows": False}
            continue
        date_col = "date" if "date" in df.columns else "event_date" if "event_date" in df.columns else "feature_date" if "feature_date" in df.columns else None
        info: dict[str, Any] = {"rows": int(len(df)), "cols": int(len(df.columns)), "exact_duplicate_rows": int(df.duplicated().sum())}
        if date_col:
            d = date_series(df[date_col])
            info["date_col"] = date_col
            info["date_min"] = d.min().date().isoformat() if d.notna().any() else ""
            info["date_max"] = d.max().date().isoformat() if d.notna().any() else ""
            if rel in {
                "pipeline_output_domestic_daily.csv",
                "pipeline_output_global_reference.csv",
                "pipeline_output_premium_enriched.csv",
                "pipeline_output_vn_macro_asof.csv",
                "modeling/model_frame_daily.csv",
            }:
                dup = int(d.duplicated().sum())
                info["duplicate_date_rows"] = dup
                if dup:
                    add_finding(
                        findings,
                        "high",
                        "mixed_or_duplicate_daily_grain",
                        "failed",
                        f"{rel}: {dup:,} duplicate date rows if interpreted as one-row-per-day. This table appears to be mixed source/product grain and must not be used as a daily model frame without a wider key or aggregation.",
                        rel,
                        "Declare the canonical grain, aggregate to one row per date before modeling, and reserve source/product rows for audit only.",
                    )
        for buy_col, sell_col in [("buy", "sell"), ("buy_price", "sell_price"), ("buy_consensus", "sell_consensus")]:
            if buy_col in df.columns and sell_col in df.columns:
                buy = numeric(df[buy_col])
                sell = numeric(df[sell_col])
                valid = buy.notna() & sell.notna()
                neg_spread = int(((sell < buy) & valid).sum())
                non_positive = int(((buy <= 0) | (sell <= 0)).sum())
                info[f"{buy_col}_{sell_col}_negative_spread_rows"] = neg_spread
                info[f"{buy_col}_{sell_col}_non_positive_rows"] = non_positive
                if neg_spread:
                    add_finding(
                        findings,
                        "high",
                        "negative_spread",
                        "failed",
                        f"{rel}: {neg_spread:,} rows have sell < buy for {buy_col}/{sell_col}.",
                        rel,
                        "Inspect source/unit mapping and exclude invalid target rows from model training.",
                    )
        out[rel] = info
    return out


def audit_asof_leakage(findings: list[Finding]) -> dict[str, Any]:
    df = read_csv("modeling/model_frame_daily.csv")
    if df.empty or "date" not in df.columns:
        return {}
    date = date_series(df["date"])
    checks = {
        "global_feature_date": -1,
        "gpr_feature_date": 0,
        "macro_feature_date": 0,
    }
    out: dict[str, Any] = {}
    for col, max_lag_days in checks.items():
        if col not in df.columns:
            continue
        feature_date = date_series(df[col])
        if max_lag_days < 0:
            violation = feature_date > (date + pd.Timedelta(days=max_lag_days))
            rule = f"{col} <= date{max_lag_days}"
        else:
            violation = feature_date > date
            rule = f"{col} <= date"
        valid = feature_date.notna()
        out[col] = {"valid_rows": int(valid.sum()), "violations": int((violation & valid).sum()), "rule": rule}
        if out[col]["violations"]:
            add_finding(
                findings,
                "high",
                "asof_leakage",
                "failed",
                f"model_frame_daily: {out[col]['violations']:,} rows violate {rule}.",
                "model_frame_daily; model_results; forecasts",
                "Fix as-of join and rebuild model frame before training.",
            )
    # News strict availability summary.
    news_summary = read_json("quality/news_availability_summary.json")
    if news_summary:
        strict_share = news_summary.get("strict_realtime_verified_share")
        out["news_strict_realtime_verified_share"] = strict_share
        if strict_share is not None and strict_share < 0.5:
            add_finding(
                findings,
                "high",
                "news_realtime_availability",
                "warning",
                f"Only {pct(float(strict_share))} of news rows are strict_realtime_verified; most rows are backfilled.",
                "news features; event_regime; model_frame_daily; model interpretation",
                "Exclude backfilled news from decision/paper-trading features or run sensitivity with strict-only mode.",
            )
    return out


def audit_source_semantics(findings: list[Finding]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    sbv = read_csv("source_discovery/sbv_structures.csv")
    if not sbv.empty:
        counts = sbv["classification"].value_counts(dropna=False).to_dict() if "classification" in sbv.columns else {}
        out["sbv_structure_classification_counts"] = {str(k): int(v) for k, v in counts.items()}
        row_137473 = sbv[sbv.get("content_structure_id", pd.Series(dtype=str)).astype(str).eq("137473")]
        out["sbv_137473"] = row_137473.head(1).to_dict("records")
        if not row_137473.empty and row_137473.iloc[0].get("classification") == "central_fx":
            add_finding(
                findings,
                "medium",
                "sbv_deposit_rate_source",
                "passed_with_caveat",
                "SBV structure 137473 is classified as central_fx, not deposit_rate. No verified SBV deposit history source is present.",
                "deposit opportunity cost features; report caveats",
                "Keep SBV 137473 as official central FX only; use verified deposit-rate source or forward monitoring for retail rates.",
            )
    deposit = read_csv("normalized/retail_deposit_rates.csv")
    if not deposit.empty:
        out["retail_deposit_rows"] = int(len(deposit))
        out["retail_deposit_history_status_counts"] = deposit.get("history_status", pd.Series(dtype=str)).value_counts(dropna=False).to_dict()
        if set(out["retail_deposit_history_status_counts"].keys()) == {"forward_monitoring_only"}:
            add_finding(
                findings,
                "medium",
                "deposit_history_coverage",
                "warning",
                "Retail deposit rates are forward_monitoring_only; they cannot benchmark historical 2011-2026 model returns.",
                "deposit_return_* features; opportunity cost comparison",
                "Do not include deposit excess-return claims in historical backtests until verified historical deposit data exists.",
            )
    events = read_csv("pipeline_output_event_regime.csv")
    if not events.empty and "source_type" in events.columns:
        counts = events["source_type"].fillna("missing").value_counts(dropna=False)
        out["event_source_type_counts"] = {str(k): int(v) for k, v in counts.items()}
        rule_share = float(events["source_type"].astype(str).str.contains("rule_generated", na=False).mean())
        out["event_rule_generated_share"] = rule_share
        if rule_share > 0.5:
            add_finding(
                findings,
                "medium",
                "event_panel_synthetic_share",
                "warning",
                f"{pct(rule_share)} of pipeline_output_event_regime rows are rule_generated.",
                "event features; event impact EDA; model interpretation",
                "Separate official/reputable events from calendar/rule-generated features in model sensitivity and report language.",
            )
    return out


def audit_duplicate_copies(findings: list[Finding]) -> dict[str, Any]:
    files = list(LAKE.rglob("*.csv"))
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name, []).append(path)
    out: dict[str, Any] = {}
    for name, paths in sorted(by_name.items()):
        if len(paths) < 2:
            continue
        hashes = {str(path.relative_to(LAKE)): sha256_file(path) for path in paths}
        unique_hashes = set(hashes.values())
        out[name] = {"copies": hashes, "unique_hashes": len(unique_hashes)}
        if len(unique_hashes) > 1 and name in {"gold_quotes_sjc_historical.csv", "domestic_gold_quotes.csv", "gold_daily_enriched.csv", "global_reference_daily.csv", "vn_macro_asof_panel.csv"}:
            add_finding(
                findings,
                "medium",
                "duplicate_named_artifact_drift",
                "warning",
                f"{name}: {len(paths)} copies with {len(unique_hashes)} different hashes.",
                "; ".join(hashes.keys()),
                "Declare canonical artifact paths and stop reading ambiguous duplicate filenames.",
            )
    return out


def build_markdown(findings: list[Finding], profiles: list[dict[str, Any]], checks: dict[str, Any]) -> str:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_findings = sorted(findings, key=lambda f: (severity_order.get(f.severity, 9), f.check))
    lines = [
        "# Full Data Quality Audit - VN Gold Market Analysis",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Executive Verdict",
        "",
        "The current lake is **not decision-safe** for investment conclusions until the critical issues below are fixed and all downstream artifacts are rebuilt.",
        "",
        "## Findings",
        "",
        "| Severity | Check | Status | Evidence | Impacted artifacts | Recommended fix |",
        "|---|---|---|---|---|---|",
    ]
    for f in sorted_findings:
        lines.append(
            "| "
            + " | ".join(
                str(x).replace("|", "\\|").replace("\n", " ")
                for x in [f.severity, f.check, f.status, f.evidence, f.impacted_artifacts, f.recommendation]
            )
            + " |"
        )
    lines.extend(["", "## Core Dataset Profiles", "", "| Path | Rows | Cols | Date spans | Duplicate rows |", "|---|---:|---:|---|---:|"])
    for p in profiles:
        spans = json.dumps(p.get("date_spans", {}), ensure_ascii=False)
        lines.append(f"| {p.get('path')} | {p.get('rows', '')} | {p.get('cols', '')} | {spans.replace('|', '\\|')} | {p.get('exact_duplicate_rows', '')} |")
    lines.extend(["", "## Check Details", "", "```json", json.dumps(checks, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def main() -> int:
    QUALITY.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    findings: list[Finding] = []

    profiles = [profile_file(rel) for rel in CORE_DAILY_FILES]
    lake_inventory = inventory_lake_files()
    checks = {
        "unit_conversion": audit_unit_conversion(findings),
        "horizon_semantics": audit_horizons(findings),
        "grain_and_validity": audit_grain_and_validity(findings),
        "asof_leakage": audit_asof_leakage(findings),
        "source_semantics": audit_source_semantics(findings),
        "duplicate_copies": audit_duplicate_copies(findings),
    }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": "not_decision_safe_until_rebuild",
        "findings": [asdict(f) for f in findings],
        "profiles": profiles,
        "lake_inventory": lake_inventory,
        "checks": checks,
    }
    json_path = QUALITY / "full_data_quality_audit.json"
    csv_path = QUALITY / "full_data_quality_findings.csv"
    inventory_path = QUALITY / "full_data_lake_inventory.csv"
    md_path = REPORTS / "full_data_quality_audit.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame([asdict(f) for f in findings]).to_csv(csv_path, index=False)
    pd.DataFrame(lake_inventory).to_csv(inventory_path, index=False)
    md_path.write_text(build_markdown(findings, profiles, checks), encoding="utf-8")

    print(
        json.dumps(
            {"findings": len(findings), "json": str(json_path), "csv": str(csv_path), "inventory": str(inventory_path), "md": str(md_path)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
