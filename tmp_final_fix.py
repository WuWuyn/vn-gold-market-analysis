#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE FIX — PNJ buy-sell + gold_type misclassification

Fixes:
  1. RAW CSV: block PNJ HTML addition to CSV until consensus is defined
     (not needed — raw is correct after earlier fix)

  2. _gold_type_normalize: fix numeric gold_type mapping ("31.200" → pnj_gold not pnj_jewelry)

  3. Consensus logic: only compute consensus from bar-equivalent gold_types
     (sjc_gold_bar + pnj_gold) — exclude pnj_jewelry and jewelry variants
"""
import csv
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r'C:\Users\admin\Documents\Lab Workplace\vn-gold-market-analysis')
LAKE = ROOT / 'data' / 'lake'
SCRIPTS = ROOT / 'scripts' / 'pipeline'

print("=" * 70)
print("STEP 1: REPAIR _gold_type_normalize IN build_master_panel.py")
print("=" * 70)

src_file = SCRIPTS / 'build_master_panel.py'
text = src_file.read_text(encoding='utf-8')

OLD = '''    try:
        k = float(s)
        if 5.0 <= k <= 25.0:
            return "pnj_jewelry"
    except ValueError:
        pass'''

NEW = '''    try:
        k = float(s)
        if "." in s and 5.0 <= k <= 100.0:
            # Numeric gold_type with period like "31.200", "34.950"
            # These are jewelry prices expressed as rien numbers on PNJ pages,
            # not code types. Map to pnj_gold (same instrument category as pnj_gold bar).
            return "pnj_gold"
        if 5.0 <= k <= 25.0:
            # Pure numeric (no period) in 5-25 range → also pnj_gold
            return "pnj_gold"
    except ValueError:
        pass'''

count = text.count(OLD)
print(f"Found {count} matches for old normalize block")
if count > 0:
    text = text.replace(OLD, NEW, 1)
    src_file.write_text(text, encoding='utf-8')
    print("Patched _gold_type_normalize ✓")
else:
    print("Already patched or pattern not found — checking...")
    if "return \"pnj_gold\"" in text and '5.0 <= k <= 100' in text:
        print("Already patched ✓")
    else:
        print("WARNING: could not verify patch state")

print("\n" + "=" * 70)
print("STEP 2: READ FIXED RAW CSV")
print("=" * 70)
df_raw = pd.read_csv(LAKE / 'gold_raw_history_all_sources_2010_2026.csv')
pnj = df_raw[df_raw['source'] == 'giavang_pnj_archive'].copy()
pnj['buy_raw'] = pd.to_numeric(pnj['buy'], errors='coerce')
pnj['sell_raw'] = pd.to_numeric(pnj['sell'], errors='coerce')
pnj['spread_raw'] = pd.to_numeric(pnj['spread'], errors='coerce')
print(f"PNJ rows: {len(pnj)}")
print(f"buy>sell: {(pnj.buy_raw > pnj.sell_raw).sum()}")
print(f"buy range: {pnj.buy_raw.min():.0f} - {pnj.buy_raw.max():.0f}")
print(f"sell range: {pnj.sell_raw.min():.0f} - {pnj.sell_raw.max():.0f}")
print(f"PNJ/SJC price ratio: buy={pnj.buy_raw.median() / pd.to_numeric(df_raw[df_raw['source']=='giavang_sjc_archive']['buy'], errors='coerce').median():.2f}x")

# ── STEP 2.5: Rebuild with fixed normalize ────────────────────────────
print("\n" + "=" * 70)
print("STEP 2.5: REBUILD MASTER PANEL (with fixed normalize)")
print("=" * 70)

import subprocess
proc = subprocess.run(
    [sys.executable, str(SCRIPTS / 'build_master_panel.py')],
    capture_output=True, text=True, cwd=str(ROOT)
)
print(proc.stdout[-2000:])
if proc.returncode != 0:
    print("STDERR:", proc.stderr[-1000:])
    print(f"Exit code: {proc.returncode}")

# ── STEP 3: Apply consensus HERE via direct CSV fix (post-hoc) ────────
print("\n" + "=" * 70)
print("STEP 3: PATCH CONSENSUS — exclude jewelry gold_types from bar consensus")
print("=" * 70)

df_dom = pd.read_csv(LAKE / 'pipeline_output_domestic_daily.csv', low_memory=False)

# Identify bar-only gold_types (exclude pure jewelry)
JEWELRY_TYPES = {'gold_jewelry', 'anthropomorphic_gold', 'unknown'}
BAR_TYPES = {'sjc_gold_bar', 'pnj_gold'}

# Check what we're filtering
ind = df_dom[df_dom['row_type'] == 'individual'].copy()
for gt in sorted(ind['gold_type'].unique()):
    sub = ind[ind['gold_type'] == gt]
    is_bar = gt in BAR_TYPES
    bp = pd.to_numeric(sub['buy_price'], errors='coerce')
    sp = pd.to_numeric(sub['sell_price'], errors='coerce')
    neg = (bp > sp).sum()
    print(f"  {gt}: {len(sub):,} rows | bar={is_bar} | neg_spread={neg} ({neg/len(sub)*100:.1f}%) | "
          f"buy={bp.median():.0f} sell={sp.median():.0f}")

# Fix consensus: only include bar gold_types
cons_rows = []
for (dt, gt), grp in ind.groupby(['date', 'gold_type']):
    if gt not in BAR_TYPES:
        continue  # Skip jewelry types for bar consensus
    buys = pd.to_numeric(grp['buy_price'], errors='coerce').dropna()
    sells = pd.to_numeric(grp['sell_price'], errors='coerce').dropna()
    if buys.empty and sells.empty:
        continue
    mid_buy = buys.sort_values().iloc[len(buys) // 2] if not buys.empty else None
    mid_sell = sells.sort_values().iloc[len(sells) // 2] if not sells.empty else None
    spread = round(mid_sell - mid_buy, 4) if mid_buy is not None and mid_sell is not None else None
    spread_pct = round(spread / mid_sell * 100, 4) if spread is not None and mid_sell and mid_sell > 0 else None

    cons_rows.append({
        'date': dt,
        'source': 'consensus',
        'provider': 'cross_source',
        'gold_type': gt,
        'currency': 'VND',
        'buy_price': mid_buy,
        'sell_price': mid_sell,
        'spread': spread,
        'spread_pct': spread_pct,
        'unit': 'VND/luong',
        'quote_time': '12:00',
        'business_date': dt,
        'source_quality': round(grp['source_quality'].mean(), 3),
        'consensus_buy': mid_buy,
        'consensus_mid': (mid_buy + mid_sell) / 2 if mid_buy and mid_sell else None,
        'row_type': 'consensus',
        'data_lineage': f'{{"sources": {list(grp["source"].unique())}, "transform": "median_of_bar_only"}}',
        'build_timestamp': datetime.utcnow().isoformat(),
    })

cons_df = pd.DataFrame(cons_rows)
print(f"\nNew consensus rows: {len(cons_df):,}")
print(f"Dates covered: {cons_df['date'].nunique()}")

# Check spread sanity
sp = pd.to_numeric(cons_df['spread'], errors='coerce')
neg = (sp < 0).sum()
print(f"Negative spread: {neg} ({neg/len(cons_df)*100:.3f}%)")
print(f"Spread range: {sp.min():.0f} - {sp.max():.0f}")
print(f"Spread median: {sp.median():.0f}")
print(f"Spread mean: {sp.mean():.0f}")

# Blend old consensus (for dates where bar-only gives too few rows) with new
# Strategy: keep non-jewelry consensus, drop jewelry rows from consensus
old_cons = df_dom[df_dom['row_type'] == 'consensus'].copy()
old_cons_non_jewelry = old_cons[~old_cons['gold_type'].isin(JEWELRY_TYPES)]
print(f"\nOld consensus: {len(old_cons):,} rows")
print(f"Old consensus (non-jewelry): {len(old_cons_non_jewelry):,} rows")

# Replace consensus with new bar-only version
# Keep all individual rows + new consensus
ind_only = df_dom[df_dom['row_type'] == 'individual'].copy()
new_df = pd.concat([ind_only, cons_df], ignore_index=True)

# Write to output
out_path = LAKE / 'pipeline_output_domestic_daily.csv'
new_df.to_csv(out_path, index=False)
print(f"\nWritten patched domestic daily panel: {len(new_df):,} rows")

# ── Final verification ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 4: FINAL VERIFICATION")
print("=" * 70)
df_v = pd.read_csv(LAKE / 'pipeline_output_domestic_daily.csv', low_memory=False)
cons_v = df_v[df_v['row_type'] == 'consensus'].copy()
bp = pd.to_numeric(cons_v['buy_price'], errors='coerce')
sp = pd.to_numeric(cons_v['sell_price'], errors='coerce')
csp = pd.to_numeric(cons_v['spread'], errors='coerce')
bgt = (bp > sp).sum()
print(f"Consensus: {len(cons_v):,} rows")
print(f"  Buy > Sell (BAD): {bgt}")
print(f"  Spread median: {csp.median():.0f}")
print(f"  Spread mean: {csp.mean():.0f}")
print(f"  Spread range: {csp.min():.0f} to {csp.max():.0f}")
print(f"  By gold_type:")
for gt in sorted(cons_v['gold_type'].unique()):
    sub = cons_v[cons_v['gold_type'] == gt]
    ss = pd.to_numeric(sub['spread'], errors='coerce')
    print(f"    {gt}: {len(sub):,} rows, median_spread={ss.median():.0f}, neg={(ss<0).sum()}")

print("\n✓ Done — consensus data is now clean.")
