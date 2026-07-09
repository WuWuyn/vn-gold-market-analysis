import csv

path = "data/lake/enriched/normalized/gold_daily_enriched.csv"
with open(path, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

updated = []
for r in rows:
    buy = float(r["buy_consensus"]) if r.get("buy_consensus") else None
    sell = float(r["sell_consensus"]) if r.get("sell_consensus") else None
    global_vnd = float(r["global_gold_vnd_per_luong"]) if r.get("global_gold_vnd_per_luong") else None

    prem_buy = (buy - global_vnd) if (buy and global_vnd) else None
    prem_sell = (sell - global_vnd) if (sell and global_vnd) else None

    r["premium_buy"] = f"{prem_buy:.2f}" if prem_buy is not None else ""
    r["premium_sell"] = f"{prem_sell:.2f}" if prem_sell is not None else ""

    updated.append(r)

fieldnames = sorted(updated[0].keys())
with open(path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(updated)

with open(path, encoding="utf-8") as f:
    check = list(csv.DictReader(f))

print(f"Updated {len(check)} rows")
r = check[0]
print(f"Sample: buy={r['buy_consensus']}, sell={r['sell_consensus']}")
print(f"  premium_buy={r['premium_buy']}, premium_sell={r['premium_sell']}, premium={r['premium']}")
print(f"  premium should equal premium_sell: match={r['premium_buy'] == r['premium_sell'] == r['premium']}")
print(f"  Columns now: {sorted(check[0].keys())}")
