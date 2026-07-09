import csv
from collections import Counter

# 1. What FX sources exist in enriched?
with open("data/lake/enriched/normalized/gold_daily_enriched.csv", encoding="utf-8") as f:
    enriched = list(csv.DictReader(f))

# enriched doesn't store fx_source column, so we need to trace the code logic
print("=== FX SOURCE TRACE ===")
print("From build_premium_decomposition.py code:")
print("  1. Try SBV central rate: fx_row['source'] == 'sbv_central_fx_history' and fx_row['mid']")
print("  2. Fallback: USDVND=X from global_market_series (yfinance)")
print()

# 2. Verify SBV mid vs yfinance USDVND for overlap dates
with open("data/lake/external_features/normalized/fx_rates.csv", encoding="utf-8") as f:
    fx = list(csv.DictReader(f))

with open("data/lake/external_features/normalized/global_market_series.csv", encoding="utf-8") as f:
    gms = list(csv.DictReader(f))

sbv = {r["date"]: float(r["mid"]) for r in fx
       if r["source"] == "sbv_central_fx_history" and r.get("mid")}
usdvnd = {r["date"][:10]: float(r["value"]) for r in gms
          if r["series_id"] == "USDVND=X" and r.get("value")}

common_dates = sorted(set(sbv.keys()) & set(usdvnd.keys()))
print(f"SBV USD/VND dates: {len(sbv)}")
print(f"yfinance USDVND=X dates: {len(usdvnd)}")
print(f"Common dates: {len(common_dates)}")

if common_dates:
    diffs = [(d, sbv[d], usdvnd[d], abs(sbv[d] - usdvnd[d])) for d in common_dates[:5]]
    for d, s, y, diff in diffs:
        print(f"  {d}: SBV={s:.2f}, yf={y:.2f}, diff={diff:.2f}")
    max_diff = max(abs(sbv[d] - usdvnd[d]) for d in common_dates)
    avg_diff = sum(abs(sbv[d] - usdvnd[d]) for d in common_dates) / len(common_dates)
    print(f"  Max diff: {max_diff:.4f}, Avg diff: {avg_diff:.4f}")

# 3. Check which source was actually used in enriched
print("\n=== ENRICHED FX USAGE ===")
fx_sources = Counter()
for r in enriched:
    d = r["date"]
    if d in sbv:
        fx_sources["sbv_central"] += 1
    elif d in usdvnd:
        fx_sources["yfinance_USDVND=X_fallback"] += 1
    else:
        fx_sources["none"] += 1

for k, v in sorted(fx_sources.items()):
    print(f"  {k}: {v} rows ({100*v/len(enriched):.1f}%)")

# 4. Verify no dates use BOTH
print(f"\n  Gold date range: {min(r['date'] for r in enriched)} -> {max(r['date'] for r in enriched)}")
print(f"  Gold with no FX at all: {fx_sources.get('none', 0)}")
