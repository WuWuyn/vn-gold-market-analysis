"""Patch build_master_panel.py: update LBMA block using line-number based replacement"""
from pathlib import Path

p = Path("scripts/pipeline/build_master_panel.py")
lines = p.read_text(encoding="utf-8").splitlines()

# Line numbers (1-indexed): 507-509
# Show actual content of those lines
for i in range(506, 511):
    line = lines[i]
    ws_len = len(line) - len(line.lstrip())
    ws_type = repr(line[:ws_len])
    print(f"Line {i+1}: indent_len={ws_len}, indent={ws_type}, content={repr(line[ws_len:])}")
