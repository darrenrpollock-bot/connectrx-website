#!/usr/bin/env python3
"""Check internal links and local asset refs across HTML pages."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("*.html"))

HREF_RE = re.compile(r'''(?:href|src)=["']([^"']+)["']''', re.I)
ABS_SITE = "https://connectrx.com.au/"

errors: list[str] = []
checked = 0

for html_path in HTML_FILES:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    for raw in HREF_RE.findall(text):
        url = raw.strip()
        if not url or url.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
            continue
        # Skip JS template literals (e.g. ${a.file})
        if "${" in url:
            continue
        if url.startswith(("http://", "https://", "//")):
            # Absolute URL pointing at this site — check path exists locally when under connectrx.com.au
            if url.startswith(ABS_SITE):
                path = url[len(ABS_SITE):].split("?")[0].split("#")[0]
                if path in ("",):
                    continue
                target = ROOT / unquote(path)
                checked += 1
                if not target.exists():
                    errors.append(f"{html_path.name}: missing site asset {url}")
            continue

        # Relative ref
        path_only = url.split("?")[0].split("#")[0]
        if not path_only:
            continue
        target = (html_path.parent / unquote(path_only)).resolve()
        checked += 1
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{html_path.name}: escapes root via {url}")
            continue
        if not target.exists():
            errors.append(f"{html_path.name}: broken ref {url}")

# Required brand assets
for rel in [
    "assets/brand/connectrx-wordmark-B-forest.svg",
    "assets/brand/connectrx-wordmark-B-white.svg",
    "assets/brand/connectrx-wordmark-B-black.svg",
    "privacy.html",
]:
    checked += 1
    if not (ROOT / rel).exists():
        errors.append(f"missing required file {rel}")

# Global forbidden strings in site code (privacy draft may mention Web3Forms in legal text)
for html_path in HTML_FILES:
    if html_path.name == "privacy.html":
        continue
    text = html_path.read_text(encoding="utf-8", errors="replace")
    for bad in ("web3forms", "GekoBrown", "admin.html"):
        if bad.lower() in text.lower():
            errors.append(f"{html_path.name}: contains forbidden string {bad!r}")

if (ROOT / "admin.html").exists():
    errors.append("admin.html still present")
if (ROOT / "uploads" / "GekoBrown.png").exists():
    # Only error if referenced; file should be gone
    errors.append("uploads/GekoBrown.png still present")

print(f"Checked {checked} refs across {len(HTML_FILES)} HTML files")
if errors:
    print(f"FAIL ({len(errors)}):")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("OK")
