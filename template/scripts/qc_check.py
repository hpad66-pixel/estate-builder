#!/usr/bin/env python3
"""The voice gate. Scans the writing (book/ and docs/) for banned characters
and the banned words listed in SOUL.md. The well is exempt: dictation is
evidence and is never edited, so it is never scanned."""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
soul = (ROOT / "SOUL.md").read_text(encoding="utf-8")
m = re.search(r"<!-- banned-words -->(.*?)<!-- /banned-words -->", soul, re.S)
WORDS = [w.strip().lower() for w in m.group(1).split(",") if w.strip()] if m else []

BAD = {
    "—": "em dash",
    "–": "en dash",
    "‘": "curly quote",
    "’": "curly quote",
    "“": "curly quote",
    "”": "curly quote",
}

fails = 0
for d in ("book", "docs"):
    base = ROOT / d
    if not base.exists():
        continue
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.suffix not in {".md", ".html"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for ch, name in BAD.items():
            n = text.count(ch)
            if n:
                print(f"FAIL {p.relative_to(ROOT)}: {n} {name}(s)")
                fails += 1
        low = text.lower()
        for w in WORDS:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                print(f"FAIL {p.relative_to(ROOT)}: banned word '{w}'")
                fails += 1

print("voice gate:", "FAILED" if fails else "clean")
sys.exit(1 if fails else 0)
