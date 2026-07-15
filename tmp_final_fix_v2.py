#!/usr/bin/env python3
"""
Final comprehensive PNJ fix.

ROOT CAUSE ANALYSIS (from diagnostic):
- The PNJ raw CSV (61,778 rows) has two underlying issues:
  A) INCORRECT UNIT MULTIPLIER: tuple price types ("66.500", "85.200") have
     symbols stripped, leaving floats like 66.5 → currently falls below
     threshold → last digit becomes chi (e.g. 500 → 500 chi = 600K VND/lương).
     These values then don't update the dictionary keys because they're new
     entries not matching previous cleanup patterns.

  B) SWAPPED BUY/SELL FOR pnj_jewelry: The condition
     "if raw_buy > raw_sell" is meant to catch column swaps, but pnj_jewelry
     prices can legitimately have buy > sell (jewelry pricing is different
     from SJC bar pricing). This causes the swap to NOT happen when the
     columns genuinely are swapped on PNJ pages, resulting in inverted
     buy/sell spreads.

SOLUTION:
- Fix the buy/sell swap logic to use a domain-knowledge check:
  * pnj_jewelry: jewelry pricing has different spread patterns → skip swap
  * pnj_gold: bar pricing follows normal market conventions → keep swap if buy>sell
  * pnj_: prefix → treat consistently

- For tuple price types with periods (66.500 etc.), recognize them as already
  valid VND/luong values (not chi units) and don't apply the <1000 threshold.

- Also fix unit conversion: diamond cardetail uses chi when value<1000, but
  tuple cards (without ".000") also need to be handled.
"""
import csv
from pathlib import Path

ROOT = Path(r'C:\Users\admin\Documents\Lab Workplace\vn-gold-market-analysis')
RAW_CSV = ROOT / 'data' / 'lake' / 'gold_raw_history_all_sources_2010_2026.csv'
BACKUP = RAW_CSV.with_suffix('.pre_final_fix.csv')

# Create backup if not exists
if not BACKUP.exists():
    import shutil
    shutil.copy2(RAW_CSV, BACKUP)
    print(f"Backup created: {BACKUP}")

# Read raw CSV
rows = []
with open(RAW_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        rows.append(row)

total = len(rows)
print(f"Total rows: {total:,}")

# Apply fix
fixed_swap = 0
fixed_unit = 0
errors = 0

def is_pnj_jewelry(source, gold_type):
    """Check if this is pnj_jewelry data (has different pricing conventions)."""
    src = (source or '').lower()
    gt = (gold_type or '').lower()
    return src == 'giavang_pnj_archive' and gt in ('pnj_jewelry', 'gold_jewelry', 'trang_suc', 'nhan', 'day_chuyen', 'bong_tai')

for row in rows:
    source = row.get('source', '')
    gold_type = row.get('gold_type', '')
    provider = row.get('provider', '')

    # Parse prices
    try:
        buy = float(row['buy']) if row.get('buy') else None
        sell = float(row['sell']) if row.get('sell') else None
    except (ValueError, TypeError):
        errors += 1
        continue

    if buy is None or sell is None:
        continue

    # Fix 1: PNJ swap logic (for pnj_gold bar prices, not jewelry)
    # The issue: pnj_jewelry has buy > sell legitimately (jewelry markup)
    # But pnj_gold bar should follow normal market convention (sell > buy)
    should_swap = False
    if source == 'giavang_pnj_archive':
        if gold_type == 'pnj_gold':
            # Bar gold: normal market convention (sell >= buy)
            if buy > sell:
                should_swap = True
        elif gold_type == 'pnj_jewelry':
            # Jewelry: different pricing, don't auto-swap
            # Check if both are in reasonable VND range
            if buy > 100000 and sell > 100000:
                # Both in VND range, probably not swapped
                should_swap = False
            elif buy > sell and (buy - sell) > 5000000:
                # Large spread difference suggests swap might still apply
                should_swap = True
        elif gold_type.isdigit() or '.' in gold_type:
            # Numeric gold_type (tuple specs like "66.500") → treat as pnj_gold
            if buy > sell:
                should_swap = True

    if should_swap:
        row['buy'], row['sell'] = str(sell), str(buy)
        # Also swap spread sign if present
        try:
            old_spread = row.get('spread', '0')
            if old_spread:
                row['spread'] = str(-float(old_spread))
        except (ValueError, TypeError):
            pass
        fixed_swap += 1

    # Fix 2: Unit multiplier for tuple types with period (e.g., "66.500")
    # These are already in VND/luong, not chi units
    if gold_type and (gold_type.replace('.', '').isdigit() or (provider and 'tuple' in provider.lower())):
        # For tuple cardetail prices, the value might already be in VND
        # Check if buy < 1000 (would be chi) → multiply by 1,000,000
        if buy < 1000 and sell < 1000:
            row['buy'] = str(int(buy * 1_000_000))
            row['sell'] = str(int(sell * 1_000_000))
            fixed_unit += 1

print(f"Price swaps applied: {fixed_swap:,}")
print(f"Unit fixes applied: {fixed_unit:,}")
print(f"Parse errors: {errors:,}")

# Write fixed CSV
with open(RAW_CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

size_mb = RAW_CSV.stat().st_size / (1024 * 1024)
print(f"\nWritten: {RAW_CSV} ({size_mb:.1f} MB)")

# Verify fix
rows2 = []
with open(RAW_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows2.append(row)

for src in ['giavang_pnj_archive', 'giavang_sjc_archive', 'webgia_sjc_archive']:
    src_rows = [r for r in rows2 if r['source'] == src]
    if not src_rows:
        continue
    buy_vals = []
    sell_vals = []
    for r in src_rows:
        try:
            b = float(r['buy']) if r['buy'] else None
            s = float(r['sell']) if r['sell'] else None
            if b is not None:
                buy_vals.append(b)
            if s is not None:
                sell_vals.append(s)
        except (ValueError, TypeError):
            pass

    buy_gt_sell = sum(1 for r in src_rows
                      if r.get('buy') and r.get('sell')
                      and float(r['buy']) > float(r['sell']))
    print(f"\n{src}:")
    print(f"  Rows: {len(src_rows):,}")
    print(f"  Buy range: {min(buy_vals):,.0f} - {max(buy_vals):,.0f}" if buy_vals else "  No buy values")
    print(f"  Sell range: {min(sell_vals):,.0f} - {max(sell_vals):,.0f}" if sell_vals else "  No sell values")
    print(f"  Buy > Sell: {buy_gt_sell:,} ({buy_gt_sell/len(src_rows)*100:.1f}%)")

    # Check by gold_type
    by_type = {}
    for r in src_rows:
        gt = r.get('gold_type', 'unknown')
        by_type.setdefault(gt, 0)
        by_type[gt] += 1
    print(f"  Gold types: {dict(sorted(by_type.items(), key=lambda x: -x[1])[:5])}")
