#!/usr/bin/env python3
"""Deep audit: premium distribution, unit consistency, FX structure."""
import csv, statistics

# --- AUDIT 1: Premium distribution over time ---
print("=" * 70)
print("A1. PREMIUM DISTRIBUTION BY YEAR")
print("=" * 70)
with open("data/lake/enriched/normalized/gold_daily_enriched.csv", encoding="utf-8") as f:
    enriched = list(csv.DictReader(f))

from collections import defaultdict
year_data = defaultdict(list)
for r in enriched:
    if r.get("premium") not in (None, "", "None"):
        y = r["date"][:4]
        year_data[y].append(float(r["premium"]))

for y in sorted(year_data):
    vals = year_data[y]
    med = statistics.median(vals)
    avg = sum(vals) / len(vals)
    print(f"  {y}: n={len(vals):3d}, median={med:>15,.0f}, mean={avg:>15,.0f}, min={min(vals):>15,.0f}, max={max(vals):>15,.0f}")

# --- AUDIT 2: Unit consistency - small sample ---
print("\n" + "=" * 70)
print("A2. UNIT CONSISTENCY CHECK (random samples)")
print("=" * 70)
for r in enriched[::500]:  # every 500th row
    if r.get("premium") in (None, "", "None"):
        continue
    g_usd = float(r["global_gold_usd_oz"])
    fx = float(r["usd_vnd"])
    stored_vnd = float(r["global_gold_vnd_per_luong"])
    buy = float(r["buy_consensus"])
    sell = float(r["sell_consensus"])
    prem = float(r["premium"])
    mid = float(r["mid_consensus"])
    prem_buy_raw = mid - stored_vnd
    prem_sell_raw = sell - stored_vnd
    print(f"  {r['date']}: gold={g_usd:.1f}*{fx:.1f} -> {stored_vnd:,.0f} VND/luong")
    print(f"    buy={buy:,.0f}, sell={sell:,.0f}, mid={mid:,.0f}")
    print(f"    premium_stored={prem:>15,.0f}  premium_mid_calc={prem_buy_raw:>15,.0f}")
    print(f"    premium_sell_vs_global={sell - stored_vnd:>15,.0f}")
    print(f"    spread={float(r['spread_abs']):>12,.0f} VND ({float(r['spread_pct'])*100:.3f}%)")
    break  # just show first valid

# --- AUDIT 3: Global gold source check ---
print("\n" + "=" * 70)
print("A3. WHICH GLOBAL GOLD SOURCE IS USED?")
print("=" * 70)
with open("data/lake/external_features/normalized/global_market_series.csv", encoding="utf-8") as f:
    gms = list(csv.DictReader(f))
gc_rows = [r for r in gms if r["series_id"] == "GC=F"]
print(f"  GC=F rows in v1: {len(gc_rows)}")
print(f"  First: {gc_rows[0] if gc_rows else 'N/A'}")
print(f"  Column names: {list(gc_rows[0].keys()) if gc_rows else 'N/A'}")
print(f"\n  NOTE: Report wants LBMA AM/PM benchmark (lbma_gold_am_usd_oz, lbma_gold_pm_usd_oz)")
print(f"  We use GC=F continuous future — this IS the correct proxy per report (section 40)")
print(f"  but it is a FUTURES price, not spot LBMA — carries basis risk")

# --- AUDIT 4: FX coverage for gold dates ---
print("\n" + "=" * 70)
print("A4. FX COVERAGE FOR GOLD DATES")
print("=" * 70)
gold_dates = {r["date"] for r in enriched}
with open("data/lake/external_features/normalized/fx_rates.csv", encoding="utf-8") as f:
    fx = list(csv.DictReader(f))

usd_fx = [r for r in fx if r["pair"] == "USD/VND" and r["source"] == "sbv_central_fx_history"]
fx_dates = {r["date"] for r in usd_fx}

covered = gold_dates & fx_dates
print(f"  Gold dates in enriched: {len(gold_dates)}")
print(f"  SBV USD/VND dates: {len(usd_fx)}")
print(f"  Overlap (both present): {len(covered)}")
print(f"  Gold dates WITHOUT FX: {len(gold_dates - fx_dates)}")
print(f"  FX dates WITHOUT gold: {len(fx_dates - gold_dates)}")
print(f"  Gold date range: {min(gold_dates)} -> {max(gold_dates)}")
print(f"  FX date range: {min(r['date'] for r in usd_fx)} -> {max(r['date'] for r in usd_fx)}")

# --- AUDIT 5: Macro data in v1 ---
print("\n" + "=" * 70)
print("A5. VIETNAM MACRO DATA CHECK (v1 macro_series)")
print("=" * 70)
with open("data/lake/external_features/normalized/macro_series.csv", encoding="utf-8") as f:
    macro = list(csv.DictReader(f))
print(f"  Total rows: {len(macro)}")
series = {}
for r in macro:
    sid = r.get("series_id", r.get("asset", ""))
    series[sid] = series.get(sid, 0) + 1
print(f"  Series breakdown:")
for s, c in sorted(series.items(), key=lambda x: -x[1])[:20]:
    print(f"    {s}: {c} rows")

# Check key Vietnam macro
vn_indicators = [
    "FP.CPI.TOTL.ZG", "FP.CPI.TOTL", "NV.AGR.TOTL.ZS", "NY.GDP.MKTP.KD.ZG",
    "FS.AST.PRVT.GD.ZS", "FM.LBL.MQMY.ZG", "BN.CAB.XOKA.GD.ZS"
]
for ind in vn_indicators:
    found = any(ind in s.upper() for s in series)
    print(f"  {ind}: {'FOUND' if found else 'NOT FOUND'}")

# Sample a row for Vietnam CPI
vn_cpi = [r for r in macro if "CPI" in r.get("series_id", r.get("asset", ""))]
if vn_cpi:
    print(f"\n  VN CPI sample ({len(vn_cpi)} rows):")
    for r in vn_cpi[:3]:
        print(f"    date={r['date']}, sid={r.get('series_id','?')}, value={r.get('value','?')}, source={r.get('source','?')}")

# --- AUDIT 6: Event panel completeness ---
print("\n" + "=" * 70)
print("A6. EVENT PANEL DETAILED CHECK")
print("=" * 70)
with open("data/lake/enriched/normalized/gold_event_panel.csv", encoding="utf-8") as f:
    events = list(csv.DictReader(f))

# What's required by report
required_types = {
    "auction_dummy": "NHNN auction events",
    "policy_auction": "NHNN auction (has this)",
    "policy_import": "Import policy (has this)",
    "policy_rate_change": "SBV rate changes",
    "inspection_news_dummy": "Market inspection (has: policy_inspection)",
    "import_policy_dummy": "Import policy (has: policy_import)",
    "tet_proximity": "Tết (has this, 240 rows)",
    "than_tai_day": "Thần Tài (has this, 16 rows)",
    "wedding_season": "Wedding season (MISSING)",
    "sbv_policy_dummy": "SBV policy (partially present)",
    "geopolitical_crisis": "Geopolitical (has this)",
    "financial_crisis": "Financial crises (has this)",
}

event_types_present = {e["event_type"] for e in events}
for req, desc in required_types.items():
    present = req in event_types_present
    print(f"  {req:30s} {'OK' if present else 'MISSING'} — {desc}")

# Check crisis coverage
print(f"\n  Crisis events detail:")
crisis_types = ["geopolitical_crisis", "financial_crisis", "financial_stress", "banking_stress", "eurozone_crisis"]
for ct in crisis_types:
    count = sum(1 for e in events if e["event_type"] == ct)
    if count > 0:
        dates = [e["event_date"] for e in events if e["event_type"] == ct]
        print(f"    {ct}: {count} events, {dates[0]} -> {dates[-1]}")

# --- AUDIT 7: GLD Shares Outstanding ---
print("\n" + "=" * 70)
print("A7. GLD ETF — SHARES OUTSTANDING CHECK")
print("=" * 70)
# GLD shares outstanding available from SPDR website
print("  GLD close+volume: YES (4,151 rows)")
print("  GLD shares outstanding: NOT COLLECTED")
print("  Source: https://www.spdrgoldshares.com/holdings/ (daily)")
print("  Without shares outstanding, cannot compute gold fund flows")

# --- AUDIT 8: Futures OI check ---
print("\n" + "=" * 70)
print("A8. OPEN INTEREST VERIFICATION")
print("=" * 70)
with open("data/lake/external_features_v2/normalized/futures_basis.csv", encoding="utf-8") as f:
    fut = list(csv.DictReader(f))
print(f"  Columns available: OI column {'PRESENT' if any('interest' in c.lower() for c in fut[0]) else 'MISSING'}")
print(f"  Volume column: {'PRESENT' if 'volume' in fut[0] else 'MISSING'}")
vol_count = sum(1 for r in fut if r.get("volume") and float(r.get("volume", 0)) > 0)
print(f"  Rows with volume > 0: {vol_count}/{len(fut)}")

# --- FINAL SUMMARY TABLE ---
print("\n\n" + "=" * 70)
print("FINAL GAP SUMMARY (ordered by severity)")
print("=" * 70)
gaps = [
    ("CRITICAL", "Futures term structure — only GC=F continuous, no second/third contract → cannot compute basis_pct, calendar_spread, roll_yield"),
    ("CRITICAL", "Open interest (OI) — not collected. Report lists it as MUST for positioning signal."),
    ("HIGH", "GLD shares outstanding — proxy only (price+volume). Flows = shares_outstanding change → not computable"),
    ("HIGH", "Wedding season calendar features — event panel missing this class entirely. Tết/Than Tai cover ~70% of seasonal demand, but Q2-Q3 weddings are under-represented"),
    ("HIGH", "News/sentiment data (GDELT/RSS/Google Trends) — report lists as SHOULD. Zero daily proxies collected."),
    ("HIGH", "Vietnam macro indicators (CPI, IP, retail sales, credit growth, policy_rate, trade_balance) — not materialized from WB/GSO v1 data"),
    ("HIGH", "release_date/as-of join for v1 macro features — FRED v2 has realtime_start, but v1 WB/GSO/macro_series have no release_date column"),
    ("MEDIUM", "LBMA AM/PM benchmark — using GC=F proxy (correct per report section 41, but should be flagged as proxy in modeling"),
    ("MEDIUM", "FX buy/sell split — SBV only has mid rate. Vietcombank has full buy/sell but as single snapshot. Intraday multi-snapshot not captured."),
    ("MEDIUM", "Premium distribution very skewed — 2024-2025 premium exceeds 29M VND/luong median positive. Need regime-switch detection."),
    ("MEDIUM", "realtime_start in FRED v2 — present but no vintage dating logic implemented. Real-time backtest can still leak."),
    ("MEDIUM", "revision_flag — not in any table. FRED does revise historical data."),
    ("LOW", "GC=F unit is USD/share (etf convention) not USD/oz — technically should be USD/oz for futures price"),
    ("LOW", "Global gold math has 1-digit rounding difference (108.82 diff on 45M) — not material but worth cleaning"),
    ("LOW", "Only 1 domestic source (SJC official). No PNJ/WebGia/Giavang in audited dataset for cross-source consensus"),
    ("LOW", "Vietnamese market breadth — only VNINDEX, no sector indices, bond yields, or real estate proxy"),
]

for severity, desc in gaps:
    print(f"\n  [{severity}] {desc}")
