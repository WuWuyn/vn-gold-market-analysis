#!/usr/bin/env python3
"""Audit enriched data against deep-research-report requirements."""
import csv, statistics, json
from pathlib import Path

# --- 1. gold_daily_enriched ---
print("=" * 70)
print("1. gold_daily_enriched.csv — PREMIUM DECOMPOSITION")
print("=" * 70)

with open("data/lake/enriched/normalized/gold_daily_enriched.csv", encoding="utf-8") as f:
    enriched = list(csv.DictReader(f))

dates = sorted(r["date"] for r in enriched)
print(f"  Date range: {dates[0]} -> {dates[-1]} ({len(dates)} unique)")
print(f"  Total rows: {len(enriched)}")
print(f"  Columns: {list(enriched[0].keys())}")

has_premium = [r for r in enriched if r.get("premium") not in (None, "", "None")]
prems = [float(r["premium"]) for r in has_premium]
spreads = [float(r["spread_pct"]) for r in enriched if r.get("spread_pct")]
print(f"\n  Premium coverage: {len(has_premium)}/{len(enriched)} ({100*len(has_premium)/len(enriched):.1f}%)")
print(f"  Premium (VND/luong): median={statistics.median(prems):,.0f}, "
      f"min={min(prems):,.0f}, max={max(prems):,.0f}")
print(f"  Spread %: median={statistics.median(spreads):.4f} ({statistics.median(spreads)*100:.3f}%), "
      f"max={max(spreads):.4f}")
print(f"  Sell price: {min(float(r['sell_consensus']) for r in enriched):,.0f} -> "
      f"{max(float(r['sell_consensus']) for r in enriched):,.0f} VND/luong")

r = enriched[0]
print(f"\n  Sample row (first date):")
print(f"    date={r['date']}, source={r['primary_source']}")
print(f"    buy={r['buy_consensus']}, sell={r['sell_consensus']}, mid={r['mid_consensus']}")
print(f"    global_gold_usd_oz={r['global_gold_usd_oz']}")
print(f"    usd_vnd={r['usd_vnd']}")
print(f"    global_gold_vnd_per_luong={r['global_gold_vnd_per_luong']}")
print(f"    premium={r['premium']} ({r['premium_pct']})")
print(f"    spread_abs={r['spread_abs']}, spread_pct={r['spread_pct']}")
print(f"    source_count={r['source_count']}, source_dispersion={r['source_dispersion']}")

# Verify unit math
g_usd = float(r["global_gold_usd_oz"])
fx = float(r["usd_vnd"])
computed_vnd_per_luong = g_usd * fx / 25.807 * 37.5
stored_vnd_per_luong = float(r["global_gold_vnd_per_luong"])
print(f"\n  Unit verification:")
print(f"    {g_usd} USD/oz * {fx} USD/VND / 25.807 chi/oz * 37.5 chi/luong")
print(f"    = {computed_vnd_per_luong:,.2f} VND/luong (computed)")
print(f"    = {stored_vnd_per_luong:,.2f} VND/luong (stored)")
print(f"    Match: {abs(computed_vnd_per_luong - stored_vnd_per_luong) < 1}")

# --- 2. event_panel ---
print("\n" + "=" * 70)
print("2. gold_event_panel.csv — EVENT PANEL")
print("=" * 70)
with open("data/lake/enriched/normalized/gold_event_panel.csv", encoding="utf-8") as f:
    events = list(csv.DictReader(f))
types = {}
sevs = {}
for e in events:
    t = e["event_type"]
    types[t] = types.get(t, 0) + 1
    s = e.get("severity", "?")
    sevs[s] = sevs.get(s, 0) + 1
print(f"  Total events: {len(events)}")
print(f"  By type: {json.dumps(types, indent=4)}")
print(f"  By severity: {json.dumps(sevs)}")
print(f"  Columns: {list(events[0].keys())}")
# Check: does it have effective_from/effective_to for policy events?
has_eff = sum(1 for e in events if e.get("effective_from") or e.get("effective_to"))
print(f"  Events with effective_from/to: {has_eff}")
has_source = sum(1 for e in events if e.get("source_url"))
print(f"  Events with source_url: {has_source}")

# --- 3. macro_enhanced (FRED v2) ---
print("\n" + "=" * 70)
print("3. macro_enhanced.csv — FRED v2")
print("=" * 70)
with open("data/lake/external_features_v2/normalized/macro_enhanced.csv", encoding="utf-8") as f:
    macro = list(csv.DictReader(f))
series_in_v2 = {}
for r in macro:
    sid = r["series_id"]
    series_in_v2[sid] = series_in_v2.get(sid, 0) + 1
print(f"  Total rows: {len(macro)}")
print(f"  Series found: {json.dumps(series_in_v2, indent=4)}")
print(f"  Columns: {list(macro[0].keys())}")
# Check required from report: DFII10, DGS10, T10YIE, T5YIE, VIXCLS, DTWEXBGS
required = ["DFII10", "DGS10", "T10YIE", "T5YIE", "VIXCLS", "DTWEXBGS", "STLFSI2", "NFCI", "BAA10Y", "AAA10Y", "M2SL", "DCOILWTICO"]
print(f"\n  Required series check:")
for s in required:
    in_v1 = False
    in_v2 = s in series_in_v2
    # Check v1 too
    try:
        with open("data/lake/external_features/normalized/global_market_series.csv", encoding="utf-8") as f:
            v1_rows = list(csv.DictReader(f))
        in_v1 = any(r["series_id"] == s for r in v1_rows)
    except:
        pass
    status = "OK(v2)" if in_v2 else ("OK(v1)" if in_v1 else "MISSING")
    print(f"    {s}: {status} | v1={in_v1}, v2={in_v2}")

# Check observation_date/release_date/available_from
has_release = sum(1 for r in macro if r.get("realtime_start"))
print(f"\n  realtime_start coverage: {has_release}/{len(macro)} ({100*has_release/len(macro):.0f}%)")
has_releasedate = sum(1 for r in macro if r.get("release_date")) if "release_date" in macro[0] else "N/A"
print(f"  release_date column: {'present' if 'release_date' in macro[0] else 'MISSING'}")
print(f"  available_from column: {'present' if 'available_from' in macro[0] else 'MISSING'}")

# --- 4. futures_basis ---
print("\n" + "=" * 70)
print("4. futures_basis.csv — GOLD FUTURES")
print("=" * 70)
with open("data/lake/external_features_v2/normalized/futures_basis.csv", encoding="utf-8") as f:
    fut = list(csv.DictReader(f))
print(f"  Total rows: {len(fut)}")
print(f"  Columns: {list(fut[0].keys())}")
print(f"  First date: {fut[0]['date']}, Last: {fut[-1]['date']}")

# Report requires: gc_front, gc_next, basis_pct, calendar_spread, roll_yield, open_interest, volume
required_fut = ["gc_front", "gc_next", "basis_pct", "calendar_spread", "roll_yield",
                "open_interest", "volume", "futures_basis_abs", "futures_basis_pct"]
print(f"\n  Required columns check:")
for c in required_fut:
    present = c in fut[0]
    print(f"    {c}: {'PRESENT' if present else 'MISSING'}")
print(f"\n  WHAT WE HAVE vs WHAT REPORT REQUIRES:")
print(f"  Report wants: gc_front, gc_next (TWO contracts), basis_pct, calendar_spread, roll_yield, OI")
print(f"  We have:     GC=F only (single continuous), no second contract, no basis, no OI")
print(f"  CRITICAL GAP: No term structure (no GC1!/GC2!), no basis calculation possible")

# --- 5. etf_proxy ---
print("\n" + "=" * 70)
print("5. etf_proxy.csv — GLD ETF")
print("=" * 70)
with open("data/lake/external_features_v2/normalized/etf_proxy.csv", encoding="utf-8") as f:
    etf = list(csv.DictReader(f))
print(f"  Total rows: {len(etf)}")
print(f"  Columns: {list(etf[0].keys())}")
print(f"  First date: {etf[0]['date']}, Last: {etf[-1]['date']}")
print(f"  Note field: {etf[0].get('note', 'N/A')}")
print(f"  GAP: No shares_outstanding, no flows data — only price+volume proxy")

# --- 6. FX ---
print("\n" + "=" * 70)
print("6. fx_rates.csv — USD/VND")
print("=" * 70)
with open("data/lake/external_features/normalized/fx_rates.csv", encoding="utf-8") as f:
    fx_rows = list(csv.DictReader(f))
sources = {}
for r in fx_rows:
    sources[r["source"]] = sources.get(r["source"], 0) + 1
print(f"  Total rows: {len(fx_rows)}")
print(f"  Sources: {json.dumps(sources)}")
print(f"  Columns: {list(fx_rows[0].keys())}")
print(f"  Date range: {min(r['date'] for r in fx_rows)} -> {max(r['date'] for r in fx_rows)}")
# Check: does it have vcb_usd_buy_cash, vcb_usd_sell etc?
print(f"\n  Report wants: vcb_usd_buy_cash, vcb_usd_buy_transfer, vcb_usd_sell + sbv_central_usdvnd")
# Show a few rows
for src in sources:
    sample = next(r for r in fx_rows if r["source"] == src)
    print(f"  Source '{src}': buy={sample.get('buy')}, sell={sample.get('sell')}, mid={sample.get('mid')}")

# --- 7. audited domestic gold ---
print("\n" + "=" * 70)
print("7. audited/normalized/domestic_gold_quotes.csv")
print("=" * 70)
with open("data/lake/audited/normalized/domestic_gold_quotes.csv", encoding="utf-8") as f:
    aud = list(csv.DictReader(f))
sources_aud = {}
for r in aud:
    sources_aud[r["source"]] = sources_aud.get(r["source"], 0) + 1
print(f"  Total rows: {len(aud)}")
print(f"  Sources: {json.dumps(sources_aud)}")
print(f"  Columns: {list(aud[0].keys())}")
print(f"  Date range: {min(r['date'] for r in aud)} -> {max(r['date'] for r in aud)}")
print(f"  BUSINESS_DATE range: {min(r.get('business_date','?') for r in aud)} -> {max(r.get('business_date','?') for r in aud)}")
# Check unit: what's the buy/sell unit?
r = aud[0]
print(f"\n  Sample: currency={r['currency']}, unit={r['unit']}, buy={r['buy']}, sell={r['sell']}")
print(f"  gold_type: {r['gold_type']}")
print(f"\n  GAP: only 1 source (sjc_official_history). No PNJ, WebGia, Giavang as historical")

# --- SUMMARY ---
print("\n\n" + "=" * 70)
print("SUMMARY: GAP ANALYSIS vs deep-research-report variable map")
print("=" * 70)

report_required = [
    # (variable_name, report_priority, present_in_data, notes)
    ("lbma_gold_am_usd_oz", "MUST", False, "Not LBMA — using GC=F proxy from yfinance (v1+duplicated in v2)"),
    ("GC=F (proxy)", "MUST", True, "Present in v1 and v2 — PROXY only, not official LBMA benchmark"),
    ("sbv_central_usdvnd", "MUST", False, "SBV page returning redirect only — FX from v1 likely Vietcombank"),
    ("vcbfx_buy_cash/transfer/sell", "MUST", False, "Vietcombank FX in v1 — need to verify specific columns"),
    ("sjc_buy/sell", "MUST", True, "audited — 28k rows, sjc_official_history"),
    ("premium", "MUST", True, "enriched — 5,481 rows with premium_buy, premium_sell, premium_pct"),
    ("spread_abs/pct", "MUST", True, "enriched — present"),
    ("DFII10 (real TIPS)", "MUST", True, "macro_v2 — 4,129 obs"),
    ("DGS10 (nominal 10Y)", "MUST", True, "v1 + v2"),
    ("T10YIE (breakeven)", "MUST", True, "macro_v2 — 4,129 obs"),
    ("T5YIE (5Y breakeven)", "MUST", True, "macro_v2 — 4,129 obs"),
    ("DTWEXBGS (DXY)", "MUST", True, "v1 + v2"),
    ("VIXCLS", "MUST", True, "v1 + v2"),
    ("STLFSI2 (financial stress)", "SHOULD", True, "macro_v2 — 628 obs (short history)"),
    ("NFCI", "SHOULD", True, "macro_v2 — 862 obs"),
    ("BAA10Y / AAA10Y", "SHOULD", True, "macro_v2 — 4,124 obs"),
    ("M2SL", "SHOULD", True, "macro_v2 — 197 obs (monthly only)"),
    ("Futures term structure (2+ contracts)", "MUST", False, "CRITICAL: Only GC=F continuous, no second contract, no basis/roll yield"),
    ("Open interest futures", "MUST", False, "CRITICAL: Not collected, yfinance Ticker doesn't expose OI consistently"),
    ("GLD shares_outstanding", "SHOULD", False, "PARTIAL: GLD price+volume only, no shares outstanding"),
    ("GLD close/volume", "SHOULD", True, "v2 etf_proxy — 4,151 rows"),
    ("Vietnam CPI YoY", "MUST", False, "Need to verify in macro_series (v1 has World Bank annual)"),
    ("Industrial production", "MUST", False, "Need to verify in macro_series"),
    ("Retail sales", "MUST", False, "Need to verify in macro_series"),
    ("Credit growth", "MUST", False, "Need to verify in macro_series"),
    ("Money supply", "MUST", False, "M2SL is US only; VN money supply not found"),
    ("Policy rate / deposit rate", "MUST", False, "vn_deposit_rates has placeholder rows only (no actual rates extracted)"),
    ("Trade balance", "MUST", False, "Need to verify in macro_series"),
    ("VNINDEX", "SHOULD", True, "vn_market_series — 3,917 rows"),
    ("Event panel (Tết, Thần Tài, policy, crisis)", "MUST", True, "309 events — good coverage"),
    ("Tet proximity", "MUST", True, "14-day window with intensity tiers"),
    ("Than Tai day", "MUST", True, "Present in event panel"),
    ("Wedding season", "SHOULD", False, "NOT in event panel — missing!"),
    ("News/sentiment/attention", "SHOULD", False, "NOT collected — no GDELT, RSS, Google Trends"),
    ("Geopolitical risk (GPR)", "SHOULD", False, "PARTIAL: crisis dummies in event panel only, no daily GPR series"),
    ("Lunar calendar features", "MUST", True, "tet_proximity + than_tai cover this"),
    ("release_date/as-of", "MUST", "PARTIAL", "FRED has realtime_start; v1 WB/GSO/macro missing release_date"),
    ("source_reliability_score", "MUST", True, "audited has reliability, enriched has source_count"),
    ("revision_flag", "MUST", False, "Not implemented in any table"),
    ("stale_flag", "MUST", False, "Not implemented"),
]

for name, priority, status, notes in report_required:
    if status is True:
        s = "PRESENT"
    elif status is False:
        s = "MISSING"
    else:
        s = "PARTIAL"
    print(f"  [{priority:4s}] {name:40s} -> {s}")
    if notes:
        print(f"         NOTE: {notes}")
