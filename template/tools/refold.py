"""Blank the huge metadata strings in a STEP file (OCC's scanner cannot read string tokens of tens of kB)."""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8", errors="replace").read()
text = re.sub(r"'(?:[^']|'')*'", lambda m: m.group(0) if len(m.group(0)) < 2000 else "''", text)
open(dst, "w", encoding="utf-8").write(text)
