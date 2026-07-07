# VN Gold Market Analysis

Reliability-first data collection pipeline for Vietnamese SJC gold prices and external market/macro features.

The core rule is strict: **a record is accepted as historical training data only when `requested_date == business_date` and buy/sell prices are valid**. Current-only sources are kept out of historical labels.

## Repository Layout

```text
configs/                 Audited source registry
data/                    Runtime data root; generated outputs are ignored by git
docs/reports/            Final source decisions and coverage evidence
scripts/pipeline/        Production collection and QA CLIs
src/gold_collectors/     Shared collectors, parsers, and data-lake helpers
tests/                   Unit tests
```

## Setup

```powershell
conda create -y -n gold-data-crawl python=3.11 pip
conda activate gold-data-crawl
python -m pip install -e ".[agentic]"
python -m playwright install chromium
```

Optional API keys can be copied from `.env.example` into `.env`.

## Run Tests

```powershell
python -m unittest discover -s tests
```

## Main Pipeline

Audit source reliability and rebuild the registry:

```powershell
python scripts/pipeline/source_audit.py --out-dir data/experiments/audit_output
python scripts/pipeline/build_source_registry.py --audit-json data/experiments/audit_output/source_audit.json
```

Backfill the historical domestic SJC target:

```powershell
python scripts/pipeline/backfill_target.py --from 2011-07-06 --to 2026-07-06 --out-dir data/lake/audited
```

Collect external features:

```powershell
python scripts/pipeline/collect_external_features.py --from 2011-07-06 --to 2026-07-06 --out-dir data/lake/external_features
```

Generate quality reports:

```powershell
python scripts/pipeline/quality_report.py --data-lake data/lake/audited --from 2011-07-06 --to 2026-07-06
```

## Current Source Decisions

Core target:

- `sjc_official_history` is the primary historical SJC training-label source.
- Archive/current sources are excluded from labels unless they pass the audited no-leak validation.
- Current-only sources are never mixed into historical training data.

External features with proven multi-year coverage:

- SBV central USD/VND historical rate: 3,940 dates from 2011-07-06 to 2026-07-06 in the latest full check.
- yfinance daily market series: `GC=F`, `SI=F`, `CL=F`, `^VIX`, `DX-Y.NYB`, `USDVND=X`, `^GSPC`.
- FRED windowed CSV: `DGS10`, `DCOILWTICO`, `VIXCLS`, `DTWEXBGS`.
- World Bank annual Vietnam macro baseline.
- GSO macro-monitor archive.
- vnstock `VNINDEX` via provider `VCI`.

Known exclusions:

- `XAUUSD=X` is empty in this environment.
- VCB historical date API leaks current data for old dates; only current VCB FX snapshots are accepted.
- Stooq XAU/USD is blocked in this environment.

## GitHub Remote

```powershell
git remote add origin https://github.com/WuWuyn/vn-gold-market-analysis.git
```
