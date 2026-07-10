"""Fix the continue indentation issue in build_master_panel.py"""
from pathlib import Path

p = Path("scripts/pipeline/build_master_panel.py")
lines = p.read_text(encoding="utf-8").split("\n")

# Line 853 = 0-indexed 852: for name in targets:
# Line 855 = 0-indexed 854: if not rows:
# Line 859 = 0-indexed 858: continue
# Line 860 = 0-indexed 859: writer.write_dataset(name, rows)
# Line 860 needs to be indented to same level as lines 855-858 (4 spaces inside the if block)
# but it should NOT be inside if not rows — it should be at the for-body level (4 spaces)

# Actually the logic is:
#   for name in targets:
#       ...header print
#       rows = ...
#       counts[name] = ...
#       if not rows:
#           print warning
#           write placeholder
#           emit manifest
#           continue    <-- this is at for-level (4 spaces) WRONG, should be 8 spaces
#       write dataset   <-- this is at for-level (4 spaces) CORRECT
#
# Wait, looking at line 860: ' writer.write_dataset(name, rows)' has 4 leading spaces
# while line 856-858 have 8 leading spaces (inside the if not rows block).
# Line 859 ' continue' has 4 leading spaces.
# So continue is at for-level, which means it continues the for loop correctly.
# The problem is writer.write_dataset(name, rows) at line 860 is NOT guarded by else.
# It will ALWAYS run, including when rows is empty.
# And continue at line 859 makes line 860 unreachable when rows is empty.

# Actually continue IS correctly at for-level (4 spaces) — it skips to next iteration.
# The issue is just that line 857 writes [{}] (placeholder) when empty, then continues.
# Line 860 is the real data write. This logic is actually fine!
# The "syntax error" I saw earlier was from a different file version.

# Let me just verify:
for i in range(849, 870):
    line = lines[i]
    indent = len(line) - len(line.lstrip())
    print(f"L{i+1:3d} [{indent:1d}s] {line[:70]}")
