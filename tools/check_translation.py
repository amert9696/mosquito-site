#!/usr/bin/env python3
"""Compare a translated content folder against the English master.

    python3 tools/check_translation.py tr

Checks, per page: same files, same front-matter keys, identical [[placeholders]] (same multiset), same element ids,
same count of structural tags, title 30-60 chars, description <= 160 chars. ui.json: same keys.
Exit code 1 on any error.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "content"
TAGS = ["section", "h2", "h3", "table", "tr", "td", "th", "li", "ol", "ul", "a", "p", "strong", "blockquote", "figure"]


def split(text):
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise ValueError("missing front matter")
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


def placeholders(body):
    out = []
    for p in re.findall(r"\[\[([^\]]*)\]\]", body):
        # alt/caption text inside [[img:id|alt|caption]] is translatable: keep only the id part
        head = p.split("|")[0]
        out.append(head)
    return Counter(out)


def main(lang):
    errors = []
    en_dir, xx_dir = ROOT / "en", ROOT / lang
    for en_file in sorted(en_dir.glob("*.html")):
        xx_file = xx_dir / en_file.name
        if not xx_file.exists():
            errors.append(f"{en_file.name}: missing")
            continue
        try:
            em, eb = split(en_file.read_text())
            xm, xb = split(xx_file.read_text())
        except ValueError as e:
            errors.append(f"{en_file.name}: {e}")
            continue
        if set(em) != set(xm):
            errors.append(f"{en_file.name}: front matter keys differ {set(em) ^ set(xm)}")
        for k in ("published", "modified", "type"):
            if em.get(k) != xm.get(k):
                errors.append(f"{en_file.name}: front matter {k} must stay {em.get(k)!r}")
        if not 30 <= len(xm.get("title", "")) <= 60:
            errors.append(f"{en_file.name}: title length {len(xm.get('title', ''))} (want 30-60): {xm.get('title')}")
        if len(xm.get("description", "")) > 160:
            errors.append(f"{en_file.name}: description length {len(xm['description'])} (max 160)")
        if placeholders(eb) != placeholders(xb):
            errors.append(f"{en_file.name}: placeholders differ: -{placeholders(eb) - placeholders(xb)} +{placeholders(xb) - placeholders(eb)}")
        ids_e, ids_x = re.findall(r'id="([^"]+)"', eb), re.findall(r'id="([^"]+)"', xb)
        if ids_e != ids_x:
            errors.append(f"{en_file.name}: element ids differ")
        for t in TAGS:
            ce, cx = len(re.findall(rf"<{t}[\s>]", eb)), len(re.findall(rf"<{t}[\s>]", xb))
            if ce != cx:
                errors.append(f"{en_file.name}: <{t}> count {cx}, English has {ce}")
        hrefs_e = [h for h in re.findall(r'href="([^"]+)"', eb)]
        hrefs_x = [h for h in re.findall(r'href="([^"]+)"', xb)]
        if hrefs_e != hrefs_x:
            errors.append(f"{en_file.name}: link targets differ (keep every href exactly as in English, same order)")
    ue = json.loads((en_dir / "ui.json").read_text())
    try:
        ux = json.loads((xx_dir / "ui.json").read_text())
        if set(ue) != set(ux):
            errors.append(f"ui.json keys differ: {set(ue) ^ set(ux)}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"ui.json: {e}")
    for e in errors:
        print("ERROR", e)
    print(f"{lang}: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
