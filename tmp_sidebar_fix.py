#!/usr/bin/env python3
"""Quick wrapper: cleanup temp files and run rebuild with fixed normalize."""
import subprocess, sys
from pathlib import Path

ROOT = Path(r'C:\Users\admin\Documents\Lab Workplace\vn-gold-market-analysis')
tmp_files = [
    'tmp_audit.py', 'tmp_audit2.py', 'tmp_check_pnj.py', 'tmp_debug_pnj.py',
    'tmp_deep_diag.py', 'tmp_diag.py',
    'tmp_fix_normalize.py', 'tmp_fix_pipeline.py', 'tmp_fix_pnj_goldtype.py',
    'tmp_fix_thresh.py', 'tmp_patch.py', 'tmp_repair.py', 'tmp_repair_v2.py',
    'tmp_test_patch.py',
]
for fn in tmp_files:
    p = ROOT / fn
    if p.exists():
        p.unlink()
        print(f'Removed {fn}')
print()

proc = subprocess.run(
    [sys.executable, str(ROOT / 'tmp_final_fix.py')],
    capture_output=True, text=True, cwd=str(ROOT),
)
print(proc.stdout[-3000:])
if proc.stderr:
    print('STDERR:', proc.stderr[-500:])
