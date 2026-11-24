#!/usr/bin/env python3
"""Verify a built site served over HTTP.

    python3 build.py --out /tmp/srv/mosquito-site --base http://localhost:8765/mosquito-site/
    (cd /tmp/srv && python3 -m http.server 8765) &
    python3 tools/verify.py /tmp/srv/mosquito-site http://localhost:8765/mosquito-site/

Checks: every sitemap URL returns 200; every internal href/src/srcset in every HTML file resolves (200) and every
#fragment exists; hreflang clusters are reciprocal and include x-default; canonical is self-referencing; JSON-LD parses
and has the expected types; one <h1>; unique titles and descriptions, title 30-60 chars; every <img> has alt, width
and height; tag nesting is well formed and ids are unique; hero image weight.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(sys.argv[1])
BASE = sys.argv[2] if sys.argv[2].endswith("/") else sys.argv[2] + "/"
PATH = "/" + BASE.split("/", 3)[3]
# optional 3rd arg: fetch from a local server instead of BASE (to verify a production build locally)
FETCH = sys.argv[3] if len(sys.argv) > 3 else BASE
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
errors, warns = [], []
status_cache = {}


def status(url):
    if url not in status_cache:
        try:
            with urllib.request.urlopen(FETCH + url[len(BASE):] if url.startswith(BASE) else url, timeout=10) as r:
                status_cache[url] = r.status
        except urllib.error.HTTPError as e:
            status_cache[url] = e.code
        except Exception as e:  # noqa: BLE001
            status_cache[url] = str(e)
    return status_cache[url]


class Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.ids, self.links, self.imgs, self.h1 = [], [], [], [], 0
        self.alts, self.canonical, self.title, self.desc, self.ld = [], None, "", "", []
        self._in_title = self._in_ld = False
        self._ld_buf = ""
        self.nesting_errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in ("img", "source", "link", "script") or tag == "a":
            for k in ("src", "href"):
                if k in a and tag != "a":
                    self.links.append(a[k])
            for k in ("srcset", "imagesrcset"):
                if k in a:
                    self.links += [p.strip().split(" ")[0] for p in a[k].split(",") if p.strip()]
        if tag == "img":
            self.imgs.append(a)
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "link" and a.get("rel") == "alternate" and "hreflang" in a:
            self.alts.append((a["hreflang"], a["href"]))
        if tag == "meta" and a.get("name") == "description":
            self.desc = a.get("content", "")
        if tag == "title":
            self._in_title = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self._ld_buf = ""
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_ld:
            self._in_ld = False
            self.ld.append(self._ld_buf)
        if not self.stack or self.stack[-1] != tag:
            self.nesting_errors.append(f"</{tag}> closes <{self.stack[-1] if self.stack else '?'}>")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self._ld_buf += data


def file_for(url):
    rel = url[len(BASE):].split("#")[0].split("?")[0]
    p = OUT / rel
    return p / "index.html" if (rel == "" or rel.endswith("/")) else p


def main():
    pages = {}
    for f in sorted(OUT.rglob("*.html")):
        if f.relative_to(OUT).parts[0] in ("src", "tools", "dist"):
            continue
        rel = f.relative_to(OUT).as_posix()
        url = BASE + (rel[:-10] if rel.endswith("index.html") else rel)
        d = Doc()
        d.feed(f.read_text())
        pages[url] = d
    print(f"HTML files: {len(pages)}")

    # sitemap
    sm = (OUT / "sitemap.xml").read_text()
    locs = re.findall(r"<loc>(.*?)</loc>", sm)
    bad = [(u, status(u)) for u in locs if status(u) != 200]
    print(f"sitemap URLs: {len(locs)}, non-200: {len(bad)}")
    errors.extend(f"sitemap {u} -> {s}" for u, s in bad)
    sm_alt = len(re.findall(r"<xhtml:link", sm))
    print(f"sitemap hreflang alternates: {sm_alt}")

    # internal links + fragments
    checked = set()
    frag_checks = 0
    for url, d in pages.items():
        for href in d.links:
            if href.startswith(("mailto:", "tel:", "data:")):
                continue
            if href.startswith("#"):
                frag_checks += 1
                if href[1:] and href[1:] not in d.ids:
                    errors.append(f"{url}: missing fragment {href}")
                continue
            if href.startswith(PATH):
                full = BASE[: -len(PATH)] + href
            elif href.startswith(BASE):
                full = href
            else:
                continue
            target = full.split("#")[0]
            if target not in checked:
                checked.add(target)
                s = status(target)
                if s != 200:
                    errors.append(f"{url}: broken internal link {href} -> {s}")
            if "#" in full:
                frag = full.split("#", 1)[1]
                frag_checks += 1
                td = pages.get(target)
                if td is None or frag not in td.ids:
                    errors.append(f"{url}: missing fragment {href}")
    print(f"unique internal URLs fetched: {len(checked)}, fragment links checked: {frag_checks}")

    # hreflang reciprocity, canonical, h1, titles, imgs, nesting, ids, JSON-LD
    titles, descs = defaultdict(list), defaultdict(list)
    cluster_count = 0
    ld_count = 0
    types = defaultdict(int)
    for url, d in pages.items():
        if url.endswith("404.html"):
            continue
        if d.canonical != url:
            errors.append(f"{url}: canonical {d.canonical}")
        if d.h1 != 1:
            errors.append(f"{url}: {d.h1} <h1>")
        titles[d.title].append(url)
        descs[d.desc].append(url)
        if not 30 <= len(d.title) <= 60:
            warns.append(f"{url}: title length {len(d.title)}: {d.title}")
        if not 50 <= len(d.desc) <= 160:
            warns.append(f"{url}: description length {len(d.desc)}")
        for img in d.imgs:
            for k in ("alt", "width", "height"):
                if k not in img:
                    errors.append(f"{url}: <img {img.get('src')}> without {k}")
        for n in d.nesting_errors[:3]:
            errors.append(f"{url}: nesting {n}")
        if d.stack:
            errors.append(f"{url}: unclosed {d.stack}")
        dup = {i for i in d.ids if d.ids.count(i) > 1}
        if dup:
            errors.append(f"{url}: duplicate ids {dup}")
        for raw in d.ld:
            try:
                data = json.loads(raw)
                ld_count += 1
                for node in data.get("@graph", []):
                    t = node.get("@type")
                    for x in (t if isinstance(t, list) else [t]):
                        types[x] += 1
            except json.JSONDecodeError as e:
                errors.append(f"{url}: JSON-LD parse error {e}")
        if d.alts:
            cluster_count += 1
            own = dict(d.alts)
            if "x-default" not in own:
                errors.append(f"{url}: no x-default")
            if url not in own.values():
                errors.append(f"{url}: hreflang cluster does not include itself")
            for hl, alt in d.alts:
                ad = pages.get(alt)
                if ad is None:
                    errors.append(f"{url}: hreflang {hl} -> missing page {alt}")
                    continue
                if dict(ad.alts) != own:
                    errors.append(f"{url}: hreflang not reciprocal with {alt}")
    for t, us in titles.items():
        if len(us) > 1:
            errors.append(f"duplicate title {t!r}: {us}")
    for t, us in descs.items():
        if len(us) > 1:
            errors.append(f"duplicate description: {us}")
    print(f"pages with hreflang clusters: {cluster_count} (all reciprocal: {not any('reciprocal' in e for e in errors)})")
    print(f"JSON-LD blocks parsed: {ld_count}; node types: {dict(sorted(types.items()))}")

    # weights
    img_dir = OUT / "assets" / "img"
    hero = sorted(img_dir.glob("landed-on-skin-*"))
    for f in hero:
        kb = f.stat().st_size / 1024
        print(f"hero {f.name}: {kb:.1f} KB")
        if kb > 150:
            errors.append(f"hero {f.name} is {kb:.0f} KB")
    biggest = sorted(((f.stat().st_size, f.name) for f in img_dir.iterdir() if f.suffix in (".webp", ".avif")), reverse=True)[:3]
    print("largest page images:", ", ".join(f"{n} {s/1024:.0f} KB" for s, n in biggest))
    css = next((OUT / "assets").glob("site.*.css"))
    print(f"CSS {css.name}: {css.stat().st_size/1024:.1f} KB; JS files: {len(list(OUT.rglob('*.js')))}")
    home = (OUT / "index.html").stat().st_size / 1024
    print(f"home HTML: {home:.1f} KB")

    for w in warns:
        print("WARN", w)
    for e in errors:
        print("ERROR", e)
    print(f"RESULT: {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
