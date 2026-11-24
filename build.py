#!/usr/bin/env python3
"""Static site builder for the Mosquito Simulator: Bite & Run website. Python 3.9+, standard library only.

    python3 build.py                       # writes the site into this folder (GitHub Pages serves the repo root)
    python3 build.py --out dist            # writes into ./dist (Cloudflare Pages: output directory "dist")
    python3 build.py --base https://example.com/   # override the base URL from site.config.json

Sources: site.config.json (the one place for base URL, contact email, App Store id), src/content/<lang>/*.html
(front matter + HTML fragment with [[placeholders]]), src/legal/*.html, src/assets/.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CONFIG = json.loads((ROOT / "site.config.json").read_text())

# language code (folder) -> (hreflang, og:locale, html lang, url prefix)
LANGS = {
    "en": ("en", "en_US", "en", ""),
    "tr": ("tr", "tr_TR", "tr", "tr/"),
    "de": ("de", "de_DE", "de", "de/"),
    "es": ("es", "es_ES", "es", "es/"),
    "pt-br": ("pt-BR", "pt_BR", "pt-BR", "pt-br/"),
    "fr": ("fr", "fr_FR", "fr", "fr/"),
    "ja": ("ja", "ja_JP", "ja", "ja/"),
}
# page key (content file stem) -> slug under the language prefix
PAGES = {
    "home": "",
    "how-to-play": "how-to-play/",
    "features": "features/",
    "modes": "modes/",
    "species": "species/",
    "guide": "guide/",
    "guide-how-mosquitoes-find-you": "guide/how-mosquitoes-find-you/",
    "guide-why-mosquito-bites-itch": "guide/why-mosquito-bites-itch/",
    "guide-games-where-you-play-as-an-insect": "guide/games-where-you-play-as-an-insect/",
    "faq": "faq/",
    "press": "press/",
    "support": "support/",
}
ARTICLES = ["guide-how-mosquitoes-find-you", "guide-why-mosquito-bites-itch", "guide-games-where-you-play-as-an-insect"]
NAV = ["how-to-play", "features", "modes", "species", "guide", "faq", "support"]
FOOT = {
    "footer_game": ["home", "how-to-play", "features", "modes", "species"],
    "footer_help": ["faq", "support", "privacy", "terms"],
    "footer_more": ["guide", *ARTICLES, "press"],
}
LEGAL = {"privacy": "privacy.html", "terms": "terms.html"}
MONTHS = {
    "en": "January February March April May June July August September October November December".split(),
    "tr": "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split(),
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split(),
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
    "pt-br": "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split(),
    "fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split(),
}

GLOBE = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/></svg>'
PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10.5 18.5h3"/></svg>'


def esc(s):
    return html.escape(s, quote=True)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def fmt_date(iso, lang):
    y, m, d = (int(x) for x in iso.split("-"))
    if lang == "ja":
        return f"{y}年{m}月{d}日"
    if lang == "de":
        return f"{d}. {MONTHS['de'][m - 1]} {y}"
    if lang in ("es", "pt-br"):
        return f"{d} de {MONTHS[lang][m - 1]} de {y}"
    return f"{d} {MONTHS[lang][m - 1]} {y}"


def read_page(path):
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


class Site:
    def __init__(self, out: Path, base_url: str, only=None):
        self.out = out
        self.base = base_url if base_url.endswith("/") else base_url + "/"
        self.path = urlparse(self.base).path or "/"  # e.g. /mosquito-site/
        self.cfg = CONFIG
        self.img = json.loads((SRC / "assets" / "img" / "manifest.json").read_text())
        self.ui, self.pages = {}, {}
        for lang in LANGS:
            d = SRC / "content" / lang
            if not d.exists() or (only and lang not in only):
                continue
            self.ui[lang] = json.loads((d / "ui.json").read_text())
            self.pages[lang] = {k: read_page(d / f"{k}.html") for k in PAGES}
        self.legal = {k: read_page(SRC / "legal" / f"{k}.html") for k in LEGAL}
        self.written = []
        self.sitemap = []

    # ---------- urls ----------
    def rel(self, lang, key):
        if key in LEGAL:
            return LEGAL[key]
        return LANGS[lang][3] + PAGES[key]

    def href(self, lang, key):
        return self.path + self.rel(lang, key)

    def abs(self, lang, key):
        return self.base + self.rel(lang, key)

    def asset(self, rel):
        return self.path + "assets/" + rel

    def asset_abs(self, rel):
        return self.base + "assets/" + rel

    def url_key(self, target):
        """[[url:...]] target -> page key."""
        if target in LEGAL:
            return target
        if target in ("", "home"):
            return "home"
        k = target.strip("/").replace("/", "-")
        if k not in PAGES:
            raise KeyError(f"unknown [[url:{target}]]")
        return k

    def label(self, lang, key):
        if key in LEGAL:
            return self.ui[lang]["privacy" if key == "privacy" else "terms"]
        if key == "home":
            return self.ui[lang]["home"]
        return self.pages[lang][key][0]["nav"]

    # ---------- media ----------
    def picture(self, key, alt, sizes, eager=False, cls=""):
        v = self.img[key]["variants"]
        largest = v[-1]
        av = ", ".join(f"{self.asset('img/' + x['stem'] + '.avif')} {x['w']}w" for x in v)
        wb = ", ".join(f"{self.asset('img/' + x['stem'] + '.webp')} {x['w']}w" for x in v)
        load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
        return (f'<picture><source type="image/avif" srcset="{av}" sizes="{sizes}">'
                f'<source type="image/webp" srcset="{wb}" sizes="{sizes}">'
                f'<img src="{self.asset("img/" + largest["stem"] + ".webp")}" width="{largest["w"]}" height="{largest["h"]}" '
                f'alt="{esc(alt)}" {load}{" class=" + chr(34) + cls + chr(34) if cls else ""}></picture>')

    def figure(self, key, alt, caption, hero=False):
        sizes = "(min-width: 900px) 560px, calc(100vw - 32px)" if hero else "(min-width: 800px) 720px, calc(100vw - 32px)"
        cls = "hero-shot" if hero else "shot"
        cap = f"<figcaption>{caption}</figcaption>" if caption else ""
        return f'<figure class="{cls}">{self.picture(key, alt, sizes, eager=hero)}{cap}</figure>'

    def image_object(self, key, caption):
        v = self.img[key]["variants"][-1]
        url = self.asset_abs("img/" + v["stem"] + ".webp")
        return {"@type": "ImageObject", "contentUrl": url, "url": url, "width": v["w"], "height": v["h"],
                "caption": caption, "creditText": self.cfg["developer_name"],
                "copyrightNotice": f"© 2026 {self.cfg['developer_name']}", "creator": {"@id": self.base + "#publisher"}}

    def cta(self, lang):
        ui = self.ui[lang]
        return (f'<div class="cta"><a class="btn-store" href="{esc(self.cfg["app_store_url"])}" rel="noopener">{PHONE}'
                f'<span>{esc(ui["cta"])}</span></a><p class="cta-note">{esc(ui["cta_note"])}</p></div>')

    # ---------- placeholders ----------
    def expand(self, lang, body, images):
        def img(m, hero=False):
            parts = m.group(1).split("|")
            key, alt = parts[0], parts[1] if len(parts) > 1 else ""
            cap = parts[2] if len(parts) > 2 else ""
            images.append((key, strip_tags(alt)))
            return self.figure(key, strip_tags(alt), cap, hero)

        body = re.sub(r"\[\[hero:([^\]]+)\]\]", lambda m: img(m, True), body)
        body = re.sub(r"\[\[img:([^\]]+)\]\]", img, body)

        def species(m):
            key, alt = m.group(1).split("|", 1)
            images.append(("species-" + key, alt))
            return self.picture("species-" + key, alt, "(min-width: 520px) 240px, 100vw", cls="species-img")
        body = re.sub(r"\[\[species:([^\]]+)\]\]", species, body)
        body = body.replace("[[cta]]", self.cta(lang))

        def email(m):
            addr = self.cfg["contact_email"]
            subj = m.group(1)
            if subj and subj.startswith("Press"):
                # press contact: a dedicated alias if configured, else the support page (keeps the personal
                # address only on support/privacy/terms and the home support section)
                if not self.cfg.get("press_email"):
                    return f'<a href="{self.href(lang, "support")}">{esc(self.label(lang, "support"))}</a>'
                addr = self.cfg["press_email"]
            q = f"?subject={quote(html.unescape(subj))}" if subj else ""
            return f'<a href="mailto:{addr}{q}">{addr}</a>'
        body = re.sub(r"\[\[email(?::([^\]]*))?\]\]", email, body)
        body = re.sub(r"\[\[url:([^\]]*)\]\]", lambda m: self.href(lang, self.url_key(m.group(1))), body)
        body = re.sub(r"\[\[asset:([^\]]+)\]\]", lambda m: self.asset(m.group(1)), body)
        body = body.replace("[[appstore]]", self.cfg["app_store_url"])
        left = re.findall(r"\[\[[^\]]*\]\]", body)
        if left:
            raise ValueError(f"unexpanded placeholders: {left}")
        return body

    # ---------- chrome ----------
    def header(self, lang, key):
        ui = self.ui[lang]
        cur = lambda k: ' aria-current="page"' if k == key else ""
        nav = "".join(f'<li><a href="{self.href(lang, k)}"{cur(k)}>{esc(self.label(lang, k))}</a></li>' for k in NAV)
        langs = []
        for code in LANGS:
            if code not in self.ui:
                continue
            target = key if key in PAGES else "home"
            if key in LEGAL:
                target = "home"
            hl = LANGS[code][0]
            ac = ' aria-current="true"' if code == lang else ""
            langs.append(f'<li><a href="{self.href(code, target)}" hreflang="{hl}" lang="{LANGS[code][2]}"{ac}>{esc(self.ui[code]["lang_name"])}</a></li>')
        short = LANGS[lang][0].split("-")[0].upper()
        return f'''<a class="skip" href="#main">{esc(ui["skip"])}</a>
<header class="site-header">
<div class="wrap bar">
<a class="brand" href="{self.href(lang, "home")}"><img src="{self.asset("img/favicon-32.png")}" srcset="{self.asset("img/icon-192.png")} 2x" width="36" height="36" alt=""><span lang="en">Mosquito Simulator<small>Bite &amp; Run</small></span></a>
<details class="lang"><summary aria-label="{esc(ui["language"])}">{GLOBE}{short}</summary><ul>{"".join(langs)}</ul></details>
<a class="btn-head" href="{esc(self.cfg["app_store_url"])}" rel="noopener">{esc(ui["cta_short"])}</a>
</div>
<nav class="nav wrap" aria-label="{esc(ui["menu"])}"><ul>{nav}</ul></nav>
</header>'''

    def footer(self, lang):
        ui = self.ui[lang]
        cols = []
        for title_key, keys in FOOT.items():
            items = "".join(f'<li><a href="{self.href(lang, k)}">{esc(self.label(lang, k))}</a></li>' for k in keys)
            cols.append(f'<div><h2>{esc(ui[title_key])}</h2><ul>{items}</ul></div>')
        langs = "".join(f'<li><a href="{self.href(c, "home")}" hreflang="{LANGS[c][0]}" lang="{LANGS[c][2]}">{esc(self.ui[c]["lang_name"])}</a></li>'
                        for c in LANGS if c in self.ui)
        cols.append(f'<div><h2>{esc(ui["language"])}</h2><ul>{langs}</ul></div>')
        return f'''<footer class="site-footer">
<div class="wrap">
<div class="foot-grid">{"".join(cols)}</div>
<div class="foot-note"><p>{esc(ui["brand_tagline"])} <a href="{esc(self.cfg["app_store_url"])}" rel="noopener">{esc(ui["cta"])}</a></p>
<p>{esc(ui["legal_note"])}</p><p>{esc(ui["footer_disclaimer"])}</p><p>{esc(ui["footer_copy"])}</p></div>
</div>
</footer>'''

    def head(self, lang, key, meta, url, alternates, jsonld, preload="", noindex=False, og_type="website"):
        hl, locale, html_lang, _ = LANGS[lang]
        alt_html = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in alternates)
        og_alt = "".join(f'<meta property="og:locale:alternate" content="{LANGS[c][1]}">' for c in LANGS if c != lang and c in self.ui and alternates)
        robots = "noindex, follow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1"
        og = self.asset_abs("img/og-card.jpg")
        analytics = self.cfg.get("analytics_head_html", "")
        ld = json.dumps(jsonld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return f'''<!doctype html>
<html lang="{html_lang}" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta["title"])}</title>
<meta name="description" content="{esc(meta["description"])}">
<link rel="canonical" href="{url}">
{alt_html}
<meta name="robots" content="{robots}">
<meta name="apple-itunes-app" content="app-id={self.cfg["app_store_id"]}">
<meta name="theme-color" content="#0b1226">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Mosquito Simulator: Bite &amp; Run">
<meta property="og:title" content="{esc(meta["title"])}">
<meta property="og:description" content="{esc(meta["description"])}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{locale}">{og_alt}
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Mosquito Simulator: Bite &amp; Run with in-game screenshots">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{self.asset("img/favicon.ico")}" sizes="48x48">
<link rel="icon" href="{self.asset("img/favicon-32.png")}" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{self.asset("img/apple-touch-icon.png")}">
<link rel="manifest" href="{self.path}site.webmanifest">
<link rel="preload" href="{self.asset("fonts/cinzel-var.woff2")}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{self.asset("fonts/barlow-regular.woff2")}" as="font" type="font/woff2" crossorigin>
{preload}<link rel="stylesheet" href="{self.asset(self.css_name)}">
<script type="application/ld+json">{ld}</script>
<!-- ANALYTICS SLOT: empty by default (no cookies, no tracking). Paste a privacy-friendly snippet into
     site.config.json "analytics_head_html" (e.g. Cloudflare Web Analytics or Plausible) and rebuild. -->{analytics}
</head>'''

    # ---------- structured data ----------
    def graph_base(self, lang):
        b = self.base
        person = {"@type": "Person", "@id": b + "#publisher", "name": self.cfg["developer_name"],
                  "alternateName": self.cfg["developer_name_ascii"], "jobTitle": "Independent game developer",
                  "url": b, "sameAs": self.cfg["developer_same_as"]}
        website = {"@type": "WebSite", "@id": b + "#website", "url": b, "name": "Mosquito Simulator: Bite & Run",
                   "inLanguage": [LANGS[c][0] for c in LANGS if c in self.ui], "publisher": {"@id": b + "#publisher"}}
        return [person, website]

    def game_node(self, lang, description):
        g = self.cfg["game"]
        shots = [("landed-on-skin", "A mosquito landed on a sleeping man's skin"), ("metro-night19", "Night 19, Metro"),
                 ("bedroom-night01", "Night 01, Sleeping Man"), ("online-1v3", "Online 1 vs 3 menu")]
        return {
            "@type": ["VideoGame", "MobileApplication"], "@id": self.base + "#game", "name": g["name"],
            "alternateName": g["alternate_names"], "description": description, "url": self.base,
            "image": self.asset_abs("img/icon-512.png"),
            "screenshot": [self.image_object(k, c) for k, c in shots],
            "operatingSystem": g["min_os"], "applicationCategory": "GameApplication", "applicationSubCategory": "Simulation",
            "genre": g["genres"], "gamePlatform": "iPhone", "playMode": ["SinglePlayer", "MultiPlayer"],
            "numberOfPlayers": {"@type": "QuantitativeValue", "minValue": 1, "maxValue": 4},
            "contentRating": g["content_rating"], "datePublished": g["release_date"], "softwareVersion": g["version"],
            "fileSize": g["file_size"], "inLanguage": g["game_languages"],
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "availability": "https://schema.org/InStock",
                       "url": self.cfg["app_store_url"], "category": "free"},
            "installUrl": self.cfg["app_store_url"], "downloadUrl": self.cfg["app_store_url"],
            "sameAs": [self.cfg["app_store_url"]],
            "author": {"@id": self.base + "#publisher"}, "publisher": {"@id": self.base + "#publisher"},
        }

    def breadcrumbs(self, lang, key):
        trail = [("home", self.label(lang, "home"))]
        if key in ARTICLES:
            trail.append(("guide", self.label(lang, "guide")))
        if key != "home":
            trail.append((key, self.label(lang, key) if key not in LEGAL else self.legal[key][0]["h1"]))
        return trail

    # ---------- pages ----------
    def build_page(self, lang, key):
        meta, raw = self.pages[lang][key]
        ui = self.ui[lang]
        images = []
        body = self.expand(lang, raw, images)
        url = self.abs(lang, key)
        page_type = meta.get("type", "page")

        # split the intro (answer-first block) from the rest
        cut = len(body)
        for marker in ("<section", '<ul class="guide-cards"'):
            i = body.find(marker)
            if i != -1:
                cut = min(cut, i)
        intro, rest = body[:cut].strip(), body[cut:].strip()
        if ui.get("lang_notice"):
            intro = intro.replace("</p>", f'</p>\n<p class="lang-notice">{esc(ui["lang_notice"])}</p>', 1)
        if page_type == "article":
            intro += (f'\n<p class="meta">{esc(ui["by"])} {esc(ui["author_name"])} · {esc(ui["published"])} '
                      f'<time datetime="{meta["published"]}">{fmt_date(meta["published"], lang)}</time> · {esc(ui["updated"])} '
                      f'<time datetime="{meta["modified"]}">{fmt_date(meta["modified"], lang)}</time></p>')

        hero = re.search(r'<figure class="hero-shot">.*?</figure>', intro, re.S)
        if key == "home" and hero:
            intro_wo = intro.replace(hero.group(0), "")
            head_html = f'<div class="wrap hero-grid"><div><h1>{esc(meta["h1"])}</h1>{intro_wo}</div>{hero.group(0)}</div>'
        else:
            head_html = f'<div class="wrap"><h1>{esc(meta["h1"])}</h1>{intro}</div>'

        extra = ""
        if page_type == "article":
            extra += (f'<aside class="author" aria-label="{esc(ui["by"])}"><img src="{self.asset("img/app-icon-256.webp")}" width="56" height="56" alt="" loading="lazy">'
                      f'<div><p><strong>{esc(ui["author_name"])}</strong></p><p>{esc(ui["author_role"])}</p><p>{esc(ui["author_note"])}</p></div></aside>')
            others = [k for k in ARTICLES if k != key] + ["species"]
            extra += (f'<nav class="related" aria-label="{esc(ui["related"])}"><h2>{esc(ui["related"])}</h2><ul>'
                      + "".join(f'<li><a href="{self.href(lang, k)}">{esc(self.label(lang, k))}</a></li>' for k in others) + "</ul></nav>")
            extra += self.cta(lang)
        trail = self.breadcrumbs(lang, key)
        crumbs = ""
        if key != "home":
            items = "".join(f'<li><a href="{self.href(lang, k)}">{esc(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{esc(n)}</li>'
                            for i, (k, n) in enumerate(trail))
            crumbs = f'<nav class="crumbs" aria-label="{esc(ui["breadcrumb_label"])}"><ol>{items}</ol></nav>'

        wide = " wide" if key in ("species",) else ""
        main = (f'<main id="main" class="{"home" if key == "home" else page_type}">'
                f'<div class="page-head">{head_html}</div>'
                f'<div class="content{wide}"><div class="wrap">{rest}{extra}{crumbs}</div></div></main>')

        # hreflang cluster
        alternates = [(LANGS[c][0], self.abs(c, key)) for c in LANGS if c in self.pages]
        alternates.append(("x-default", self.abs("en", key)))

        # JSON-LD
        b = self.base
        graph = self.graph_base(lang)
        lede_text = strip_tags(re.search(r'<p class="lede">(.*?)</p>', raw, re.S).group(1))
        webpage = {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": meta["title"],
                   "description": meta["description"], "inLanguage": LANGS[lang][0], "isPartOf": {"@id": b + "#website"},
                   "about": {"@id": b + "#game"}, "datePublished": meta["published"], "dateModified": meta["modified"]}
        seen = set()
        imgs = []
        for k, a in images:
            if k not in seen:
                seen.add(k)
                imgs.append(self.image_object(k, a))
        if imgs:
            webpage["primaryImageOfPage"] = imgs[0]
            if len(imgs) > 1:
                webpage["image"] = imgs[1:]
        if key == "home":
            graph.append(self.game_node(lang, lede_text))
        if key != "home":
            webpage["breadcrumb"] = {"@id": url + "#breadcrumb"}
            graph.append({"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": self.abs(lang, k)} for i, (k, n) in enumerate(trail)]})
        if page_type in ("faq", "support"):
            qas = re.findall(r'<section class="qa"[^>]*>\s*<h2 id="[^"]*">(.*?)</h2>\s*<div class="answer">(.*?)</div>\s*</section>', body, re.S)
            if page_type == "faq":
                webpage["@type"] = ["WebPage", "FAQPage"]
                webpage["mainEntity"] = [{"@type": "Question", "name": strip_tags(q),
                                          "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}} for q, a in qas]
            else:
                webpage["@type"] = ["WebPage", "ContactPage"]
        if page_type == "article":
            src_block = re.search(r'<section aria-labelledby="refs" class="sources">(.*?)</section>', body, re.S)
            cites = []
            if src_block:
                for li in re.findall(r"<li>(.*?)</li>", src_block.group(1), re.S):
                    link = re.search(r'href="(https?://[^"]+)"', li)
                    c = {"@type": "CreativeWork", "name": strip_tags(li)[:200]}
                    if link:
                        c["url"] = link.group(1)
                    cites.append(c)
            article = {"@type": "Article", "@id": url + "#article", "headline": meta["h1"], "description": meta["description"],
                       "inLanguage": LANGS[lang][0], "mainEntityOfPage": {"@id": url + "#webpage"},
                       "datePublished": meta["published"], "dateModified": meta["modified"],
                       "author": {"@id": b + "#publisher"}, "publisher": {"@id": b + "#publisher"},
                       "about": {"@id": b + "#game"}, "citation": cites,
                       "image": imgs[0] if imgs else self.image_object("hero-orbit", "Mosquito Simulator: Bite & Run")}
            graph.append(article)
        if page_type == "hub":
            webpage["@type"] = ["WebPage", "CollectionPage"]
            webpage["hasPart"] = [{"@id": self.abs(lang, k) + "#article"} for k in ARTICLES]
        if key == "species":
            secs = re.findall(r'<section aria-labelledby="([a-z]+)" class="species">\s*<h2 id="[a-z]+">(.*?)</h2>', body, re.S)
            graph.append({"@type": "ItemList", "@id": url + "#species", "name": meta["h1"], "numberOfItems": len(secs),
                          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{url}#{sid}", "name": strip_tags(n)}
                                              for i, (sid, n) in enumerate(secs)]})
            webpage["mainEntity"] = {"@id": url + "#species"}
        if page_type == "press":
            webpage["@type"] = ["WebPage", "AboutPage"]
        graph.append(webpage)
        jsonld = {"@context": "https://schema.org", "@graph": graph}

        preload = ""
        if key == "home" and hero:
            hk = re.search(r"\[\[hero:([^|\]]+)", raw).group(1)
            v = self.img[hk]["variants"]
            srcset = ", ".join(f"{self.asset('img/' + x['stem'] + '.avif')} {x['w']}w" for x in v)
            preload = (f'<link rel="preload" as="image" type="image/avif" imagesrcset="{srcset}" '
                       f'imagesizes="(min-width: 900px) 560px, calc(100vw - 32px)" fetchpriority="high">\n')

        if lang != "en":
            # Cinzel applies the page language's casing rules (Turkish i -> İ); keep the English brand name English.
            def brand_en(m):
                return m.group(1) + re.sub(r"(Mosquito Simulator(?:: Bite &amp; Run)?)", r'<span lang="en">\1</span>', m.group(2)) + m.group(3)
            main = re.sub(r"(<h[12][^>]*>)(.*?)(</h[12]>)", brand_en, main, flags=re.S)
        doc = (self.head(lang, key, meta, url, alternates, jsonld, preload, og_type="article" if page_type == "article" else "website")
               + "\n<body>\n" + self.header(lang, key) + "\n" + main + "\n" + self.footer(lang) + "\n</body>\n</html>\n")
        self.write(self.rel(lang, key) + ("index.html" if self.rel(lang, key).endswith("/") or self.rel(lang, key) == "" else ""), doc)
        self.sitemap.append((key, lang, meta["modified"]))

    def build_legal(self, key):
        meta, raw = self.legal[key]
        lang = "en"
        body = self.expand(lang, raw, [])
        url = self.abs(lang, key)
        trail = self.breadcrumbs(lang, key)
        graph = self.graph_base(lang) + [
            {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": meta["title"], "description": meta["description"],
             "inLanguage": "en", "isPartOf": {"@id": self.base + "#website"}, "about": {"@id": self.base + "#game"},
             "datePublished": meta["published"], "dateModified": meta["modified"], "breadcrumb": {"@id": url + "#breadcrumb"}},
            {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": self.abs(lang, k)} for i, (k, n) in enumerate(trail)]}]
        items = "".join(f'<li><a href="{self.href(lang, k)}">{esc(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{esc(n)}</li>'
                        for i, (k, n) in enumerate(trail))
        main = (f'<main id="main" class="legal"><div class="page-head"><div class="wrap"><h1>{esc(meta["h1"])}</h1></div></div>'
                f'<div class="content"><div class="wrap">{body}<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav></div></div></main>')
        doc = (self.head(lang, key, meta, url, [], {"@context": "https://schema.org", "@graph": graph})
               + "\n<body>\n" + self.header(lang, key) + "\n" + main + "\n" + self.footer(lang) + "\n</body>\n</html>\n")
        self.write(LEGAL[key], doc)
        self.sitemap.append((key, None, meta["modified"]))

    def build_404(self):
        lang = "en"
        meta = {"title": "Page not found | Mosquito Simulator: Bite & Run",
                "description": "This page does not exist. Find the game, the guides and support here."}
        links = "".join(f'<li><a href="{self.href(c, "home")}" hreflang="{LANGS[c][0]}" lang="{LANGS[c][2]}">{esc(self.ui[c]["lang_name"])}</a></li>'
                        for c in LANGS if c in self.ui)
        pages = "".join(f'<li><a href="{self.href(lang, k)}">{esc(self.label(lang, k))}</a></li>' for k in ["home", *NAV, "press"])
        main = (f'<main id="main" class="nf"><div class="wrap"><h1>Page not found</h1>'
                f'<p>The mosquito flew off with this page. Try one of these instead:</p><ul>{pages}</ul>'
                f'<h2>Other languages</h2><ul>{links}</ul>{self.cta(lang)}</div></main>')
        doc = (self.head(lang, "home", meta, self.base + "404.html", [], {"@context": "https://schema.org", "@graph": self.graph_base(lang)}, noindex=True)
               + "\n<body>\n" + self.header(lang, None) + "\n" + main + "\n" + self.footer(lang) + "\n</body>\n</html>\n")
        self.write("404.html", doc)

    # ---------- files ----------
    def write(self, rel, content, binary=False):
        p = self.out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            p.write_bytes(content)
        else:
            p.write_text(content)
        self.written.append(rel)

    def copy_assets(self):
        css = (SRC / "assets" / "site.css").read_text()
        h = hashlib.sha256(css.encode()).hexdigest()[:10]
        self.css_name = f"site.{h}.css"
        self.write("assets/" + self.css_name, css)
        for d in ("fonts", "img"):
            for f in sorted((SRC / "assets" / d).iterdir()):
                if f.name == "manifest.json" or f.name.startswith("."):
                    continue
                self.write(f"assets/{d}/{f.name}", f.read_bytes(), binary=True)

    def text_files(self):
        b = self.base
        cfg = self.cfg
        # robots.txt — template from the SEO+GEO rulebook §4.3 (brand site: search AND training bots allowed)
        bots = ["Googlebot", "Bingbot", "OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot",
                "Perplexity-User", "Applebot", "DuckDuckBot", "YandexBot"]
        train = ["GPTBot", "ClaudeBot", "Google-Extended", "Applebot-Extended", "CCBot"]
        robots = ["# Mosquito Simulator: Bite & Run. Generated by build.py.",
                  "",
                  "# Search engines and AI search/answer bots: allowed"]
        for bot in bots:
            robots += [f"User-agent: {bot}", "Allow: /", ""]
        robots.append("# Training bots: allowed (brand site: we want the game to be known to models; rulebook BOT-04)")
        for bot in train:
            robots += [f"User-agent: {bot}", "Allow: /", ""]
        robots += ["User-agent: *", "Allow: /", "", f"Sitemap: {b}sitemap.xml", ""]
        self.write("robots.txt", "\n".join(robots))

        # sitemap with hreflang alternates
        rows = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
        for key, lang, mod in self.sitemap:
            if lang is None:
                rows.append(f"<url><loc>{self.abs('en', key)}</loc><lastmod>{mod}</lastmod></url>")
                continue
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{LANGS[c][0]}" href="{self.abs(c, key)}"/>' for c in LANGS if c in self.pages)
            alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{self.abs("en", key)}"/>'
            rows.append(f"<url><loc>{self.abs(lang, key)}</loc><lastmod>{mod}</lastmod>{alts}</url>")
        rows.append("</urlset>\n")
        self.write("sitemap.xml", "\n".join(rows))

        # app-ads.txt placeholder (must live at the ROOT of the developer website domain to be read)
        self.write("app-ads.txt", "\n".join([
            "# app-ads.txt for Mosquito Simulator: Bite & Run",
            "# PLACEHOLDER: no ad network lines yet. When ads are live, paste the exact line(s) your ad network gives you,",
            "# e.g. for Google AdMob: AdMob > Apps > View all apps > app-ads.txt > \"How to set up app-ads.txt\".",
            "# Format: <ad system domain>, <your publisher id>, DIRECT, <certification authority id>",
            "# Never invent a publisher id. The file is only read at https://<developer-website-domain>/app-ads.txt, and",
            "# the domain must match the Marketing/Developer URL in App Store Connect, so it needs a custom domain (see README).",
            ""]))

        # llms.txt (summary) and llms-full.txt (all English page text)
        en = self.pages["en"]
        g = cfg["game"]
        facts = [
            f"- Platform: iPhone, {g['min_os']}. Android: not announced.",
            f"- Price: free download with optional in-app purchases (Mosquito Club US$4.99/month or US$29.99/year; items US$0.99–19.99).",
            f"- Released: {g['release_date']} (version {g['version']}). Developer and publisher: {cfg['developer_name']} (independent).",
            "- Story: 20 nights in 4 chapters (June–September) with 2 boss nights (Racket Uncle, Pest Control).",
            "- Modes: Story, Daily Night, Game of the Week, Sleepless Night (endless), Online 1 vs 3 (one human vs three mosquitoes; bots fill empty seats).",
            "- 10 playable real mosquito species: Culex, Aedes aegypti, Anopheles, Asian tiger (Aedes albopictus), gallinipper (Psorophora ciliata), Culiseta, Wyeomyia, Deinocerites, Sabethes cyaneus, Toxorhynchites.",
            "- Game languages: English, Turkish, German, Spanish, French, Arabic. Age rating 9+. Download about 393 MB.",
            f"- App Store: {cfg['app_store_url']}",
            f"- Support: {b}support/ · Privacy: {b}privacy.html · Terms: {b}terms.html",
        ]
        home_lede = strip_tags(re.search(r'<p class="lede">(.*?)</p>', en["home"][1], re.S).group(1))
        lines = ["# Mosquito Simulator: Bite & Run", "",
                 f"> {home_lede}", "",
                 "Facts as of 24 November 2026:", *facts, "", "## Pages"]
        for k in PAGES:
            lines.append(f"- [{en[k][0]['title']}]({self.abs('en', k)}): {en[k][0]['description']}")
        lines += ["", "## Other languages",
                  *(f"- {self.ui[c]['lang_name']}: {self.abs(c, 'home')}" for c in LANGS if c in self.ui and c != "en"),
                  "", "## Optional", f"- [Full text of all English pages]({b}llms-full.txt)", f"- [Press kit]({self.abs('en', 'press')})", ""]
        self.write("llms.txt", "\n".join(lines))

        full = ["# Mosquito Simulator: Bite & Run: full site text (English)", "", *facts, ""]
        for k in PAGES:
            meta, raw = en[k]
            body = self.expand("en", raw, [])
            full += [f"## {meta['h1']}", f"URL: {self.abs('en', k)}", "", html_to_text(body), ""]
        self.write("llms-full.txt", "\n".join(full))

        # Cloudflare Pages headers (GitHub Pages ignores this file)
        p = self.path
        self.write("_headers", "\n".join([
            "# Cloudflare Pages / Netlify response headers. GitHub Pages ignores this file.",
            "/*",
            "  X-Content-Type-Options: nosniff",
            "  Referrer-Policy: strict-origin-when-cross-origin",
            "  X-Frame-Options: DENY",
            "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()",
            "  Strict-Transport-Security: max-age=31536000; includeSubDomains",
            "  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; font-src 'self'; script-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests",
            "  Cache-Control: public, max-age=600, must-revalidate",
            f"{p}assets/site.*.css",
            "  Cache-Control: public, max-age=31536000, immutable",
            f"{p}assets/fonts/*",
            "  Cache-Control: public, max-age=31536000, immutable",
            f"{p}assets/img/*",
            "  Cache-Control: public, max-age=604800, stale-while-revalidate=86400",
            f"{p}llms*.txt",
            "  Content-Type: text/plain; charset=utf-8",
            ""]))

        self.write("site.webmanifest", json.dumps({
            "name": "Mosquito Simulator: Bite & Run", "short_name": "Mosquito Sim", "start_url": p, "scope": p,
            "display": "browser", "background_color": "#0b1226", "theme_color": "#0b1226",
            "icons": [{"src": self.asset("img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
                      {"src": self.asset("img/icon-512.png"), "sizes": "512x512", "type": "image/png"}]}, indent=1))
        if cfg.get("indexnow_key"):
            self.write(f"{cfg['indexnow_key']}.txt", cfg["indexnow_key"])

    def clean(self):
        man = self.out / ".build-manifest.json"
        if man.exists():
            for rel in json.loads(man.read_text()):
                p = self.out / rel
                if p.is_file():
                    p.unlink()
            # remove now-empty generated folders
            for d in sorted({(self.out / r).parent for r in json.loads(man.read_text())}, key=lambda x: -len(str(x))):
                if d != self.out and d.exists() and not any(d.iterdir()):
                    d.rmdir()

    def run(self):
        self.clean()
        self.copy_assets()
        for lang in self.pages:
            for key in PAGES:
                self.build_page(lang, key)
        for key in LEGAL:
            self.build_legal(key)
        self.build_404()
        self.text_files()
        (self.out / ".build-manifest.json").write_text(json.dumps(sorted(self.written), indent=0))
        print(f"built {len(self.written)} files into {self.out} for {self.base}")


def html_to_text(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S)
    s = re.sub(r"<figure.*?</figure>", "", s, flags=re.S)
    s = re.sub(r"<picture.*?</picture>", "", s, flags=re.S)
    s = re.sub(r"<h2[^>]*>(.*?)</h2>", lambda m: "\n### " + strip_tags(m.group(1)) + "\n", s, flags=re.S)
    s = re.sub(r"<h3[^>]*>(.*?)</h3>", lambda m: "\n#### " + strip_tags(m.group(1)) + "\n", s, flags=re.S)
    s = re.sub(r"<tr[^>]*>(.*?)</tr>", lambda m: "| " + " | ".join(strip_tags(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", m.group(1), re.S)) + " |\n", s, flags=re.S)
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: f"{strip_tags(m.group(2))} ({m.group(1)})", s, flags=re.S)
    s = re.sub(r"<li[^>]*>", "\n- ", s)
    s = re.sub(r"</(p|ul|ol|table|div|section|blockquote)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT))
    ap.add_argument("--base", default=os.environ.get("SITE_BASE_URL", CONFIG["base_url"]))
    ap.add_argument("--langs", default="", help="comma-separated subset, for quick previews")
    a = ap.parse_args()
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    Site(out, a.base, [x for x in a.langs.split(",") if x] or None).run()


if __name__ == "__main__":
    main()
