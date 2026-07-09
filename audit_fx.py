import csv
from collections import Counter

# Check FX rates structure in detail
with open("data/lake/external_features/normalized/fx_rates.csv", encoding="utf-8") as f:
    fx = list(csv.DictReader(f))
print("FX columns:", list(fx[0].keys()))
combo = Counter((r["source"], r.get("quote_type", ""), r.get("pair", "")) for r in fx)
for k, v in sorted(combo.items()):
    print(f"  {k}: {v} rows")

sbv = [r for r in fx if r["source"] == "sbv_central_fx_history"]
print(f"\nSBV sample: buy={sbv[0]['buy']}, sell={sbv[0]['sell']}")
print(f"  mid={sbv[0]['mid']}, pair={sbv[0]['pair']}, quote_type={sbv[0]['quote_type']}")
print(f"  published_at: {sbv[0]['published_at']}")
print(f"  SBV date range: {min(r['date'] for r in sbv)} -> {max(r['date'] for r in sbv)}")

vcb = [r for r in fx if r["source"] == "vietcombank_fx_xml"]
print(f"\nVCB sample: buy={vcb[0]['buy']}, sell={vcb[0]['sell']}")
print(f"  mid={vcb[0]['mid']}, pair={vcb[0]['pair']}, quote_type={vcb[0]['quote_type']}")
print(f"  VCB date range: {min(r['date'] for r in vcb)} -> {max(r['date'] for r in vcb)}")

# Also check: what USD/VND rows exist specifically?
usd_rows = [r for r in fx if "USD" in r.get("pair", "")]
print(f"\nUSD/VND rows: {len(usd_rows)}")
pairs = Counter(r["pair"] for r in usd_rows)
print(f"  Pairs: {dict(pairs)}")

# Check: is there an SBV only USD/VND central rate?
for r in sbv[:3]:
    print(f"  SBV row: date={r['date']}, pair={r['pair']}, buy={r['buy']}, sell={r['sell']}, mid={r['mid']}, qt={r['quote_type']}")
