import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv(r'C:\Users\admin\Documents\Lab Workplace\vn-gold-market-analysis\data\lake\gold_raw_history_all_sources_2010_2026.csv')
pnj = df[df.source=='giavang_pnj_archive'].copy()
pnj['gold_type'] = pnj['gold_type'].fillna('').str.strip()
print('Unique PNJ gold_types (top 30):')
print(pnj['gold_type'].value_counts().head(30).to_string())

# Show offending rows
bad_types = ['31.200','34.950','34.850','34.900','34.890','31.210','35.070','35.080','35.090']
for bt in bad_types:
    sub = pnj[pnj['gold_type'] == bt]
    if len(sub) > 0:
        print(f'\n{bt} ({len(sub)} rows):')
        print(sub[['date','buy','sell','spread']].head(3).to_string())

# pnj_jewelry sample
print('\n=== pnj_jewelry sample ===')
jr = pnj[pnj['gold_type']=='pnj_jewelry'].head(20)
print(jr[['date','buy','sell','spread','gold_type']].to_string())
