#!/usr/bin/env python3
"""Submit every sitemap URL to IndexNow (Bing, Yandex, Seznam, Naver; feeds Copilot and part of ChatGPT search).

Needs a custom domain: IndexNow requires the key file at the host root (https://example.com/<key>.txt).
1. Put a random key (8-128 chars of a-z, A-Z, 0-9, -) in site.config.json "indexnow_key" and rebuild; build.py then
   writes <key>.txt next to index.html.
2. Deploy, then run:  python3 tools/indexnow.py
Run it again after real content changes (rulebook TEK-13). Never run it for unchanged pages.
"""
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "site.config.json").read_text())
key = cfg.get("indexnow_key")
if not key:
    raise SystemExit("Set indexnow_key in site.config.json first (and deploy on a custom domain).")
base = cfg["base_url"]
host = urlparse(base).netloc
if urlparse(base).path not in ("", "/"):
    raise SystemExit("IndexNow needs the key file at the host root: switch to a custom domain first (see README).")
urls = re.findall(r"<loc>(.*?)</loc>", (ROOT / "sitemap.xml").read_text())
body = json.dumps({"host": host, "key": key, "keyLocation": f"{base}{key}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=30) as r:
    print("IndexNow:", r.status, f"({len(urls)} URLs)")
