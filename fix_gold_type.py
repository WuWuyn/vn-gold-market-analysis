"""Fix gold_type normalization in build_master_panel.py"""
from pathlib import Path
import re

p = Path("scripts/pipeline/build_master_panel.py")
content = p.read_text(encoding="utf-8")

# Find the function by regex
pattern = re.compile(
    r'def _gold_type_normalize\(raw: str\) -> str:\n(.*?\n)',
    re.DOTALL
)
m = pattern.search(content)
if not m:
    print("ERROR: function not found")
    exit(1)

old = m.group(0)
new = '''def _gold_type_normalize(raw: str) -> str:
    """Collapse gold_type values to a short & stable label. SJC = gold_bar,
    PNJ or *nu* = gold_jewelry, anh_huynh = anthropomorphic_gold."""
    s = (raw or "").strip().lower()
    if "sjc" in s or "bar" in s or "mieng" in s or "vang_luong" in s:
        return "sjc_gold_bar"
    if "anh_huynh" in s or "tho" in s:
        return "anthropomorphic_gold"
    if "nhan" in s or "nu" in s or "trang_suc" in s or "day_chuyen" in s or "bong_tai" in s:
        return "gold_jewelry"
    if "pnj" in s or "laz" in s:
        return "pnj_gold"
    # Numeric karat values (e.g. "17.470", "24.000") -> pnj_jewelry
    try:
        k = float(s)
        if 5 <= k <= 25:
            return "pnj_jewelry"
    except ValueError:
        pass
    return s.replace(" ", "_") if s else "other"
'''

if old in content:
    content = content.replace(old, new)
    p.write_text(content, encoding="utf-8")
    print("OK: gold_type normalization updated")
else:
    print("ERROR: old_func not found in file")
