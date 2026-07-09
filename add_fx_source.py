import csv

# Load FX sources
with open("data/lake/external_features/normalized/fx_rates.csv", encoding="utf-8") as f:
    fx = list(csv.DictReader(f))
with open("data/lake/external_features/normalized/global_market_series.csv", encoding="utf-8") as f:
    gms = list(csv.DictReader(f))

sbv = {r["date"]: "sbv_central" for r in fx
       if r["source"] == "sbv_central_fx_history" and r.get("mid")}
usdvnd = {r["date"][:10]: "yfinance_USDVND=X" for r in gms
          if r["series_id"] == "USDVND=X" and r.get("value")}

# Add fx_source to enriched
path = "data/lake/enriched/normalized/gold_daily_enriched.csv"
with open(path, encoding="utf-8") as f:
    enriched = list(csv.DictReader(f))

for r in enriched:
    d = r["date"]
    if d in sbv:
        r["fx_source"] = sbv[d]
    elif d in usdvnd:
        r["fx_source"] = usdvnd[d]
    else:
        r["fx_source"] = "missing"

fieldnames = sorted(enriched[0].keys())
with open(path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(enriched)

# Verify
from collections import Counter
with open(path, encoding="utf-8") as f:
    check = list(csv.DictReader(f))
src_count = Counter(r["fx_source"] for r in check)
print(f"Updated {len(check)} rows")
for k, v in sorted(src_count.items()):
    print(f"  {k}: {v} ({100*v/len(check):.1f}%)")
print(f"Columns: {sorted(check[0].keys())}")
