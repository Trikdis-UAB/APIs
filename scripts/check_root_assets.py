#!/usr/bin/env python3
"""Validate that root-relative asset paths in HTML exist on disk."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = list(ROOT.rglob("*.html"))

# Match src="/path" or href='/path' (ignore protocol-relative //)
ATTR_RE = re.compile(r"(?:src|href)=[\"'](/[^\"'#?]+)")

missing: set[str] = set()
checked: set[str] = set()

for html_file in HTML_FILES:
    text = html_file.read_text(encoding="utf-8", errors="ignore")
    for match in ATTR_RE.findall(text):
        if match.startswith("//") or match == "/":
            continue
        if match in checked:
            continue
        checked.add(match)
        asset_path = ROOT / match.lstrip("/")
        if not asset_path.exists():
            missing.add(match)

if missing:
    print("Missing root-relative assets:")
    for item in sorted(missing):
        print(f"  {item}")
    sys.exit(1)

print(f"OK: {len(checked)} root-relative assets verified across {len(HTML_FILES)} HTML files.")
