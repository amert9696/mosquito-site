# SEO + GEO rulebook checklist: mosquito-site

Maps every rule in `~/Desktop/SEO-GEO-Kural-Kitapcigi.md` (v1.0, 26 Sep 2026) to this site. Built and checked on 24 November 2026.
Status: **Done** (in the site), **Owner** (needs the owner after deploy, off-site or with accounts), **Partial**, **N/A** (does not fit a single-game landing site).

## TEK: technical SEO

| Rule | Status | How |
|---|---|---|
| TEK-01 | Done | Every page is pre-built static HTML. Content, prices, facts, links and JSON-LD are in the first response; the site ships **zero JavaScript**. |
| TEK-02 | Done | Largest page (ja/species) is 35 KB of HTML; English home 24 KB. |
| TEK-03 | Done | No page ships `noindex` except `404.html`; nothing is changed by JS. |
| TEK-04 | Done | Self-referencing absolute canonical on every page, built from the single `base_url`; verify.py checks canonical = URL. |
| TEK-05 | Done / Owner | Real `404.html` (noindex), served by GitHub Pages and Cloudflare Pages with status 404. Old URLs (`/`, `/privacy.html`, `/terms.html`, `#support`) are kept, so no redirects are needed. If the domain moves later, 301 the github.io URLs (see README). |
| TEK-06 | Done | LCP image is the hero: AVIF 19 KB / WebP 29 KB, preloaded with `fetchpriority=high`; every `<img>` has width/height (no CLS); below-the-fold images lazy; 2 preloaded WOFF2 fonts with `font-display:swap`; one 11.5 KB CSS file; no JS, so INP is trivial. Owner: confirm in CrUX/PageSpeed after traffic. |
| TEK-07 | Done | `sitemap.xml` lists only the 86 indexable, canonical, 200 pages (404 excluded); `lastmod` comes from each page's `modified` date, not the build time. |
| TEK-08 | Done | Same HTML for mobile and desktop (responsive CSS only). |
| TEK-09 | N/A | 88 pages; no crawl budget issue. |
| TEK-10 | N/A | No faceted navigation. |
| TEK-11 | N/A | No pagination. |
| TEK-12 | Done | hreflang in HTML only (one method), reciprocal across 7 languages + `x-default` (English), mirrored in the sitemap; verify.py checks reciprocity on all 84 clustered pages. Launched together, so no delay. |
| TEK-13 | Owner | `tools/indexnow.py` + `indexnow_key` in config; needs the custom domain (key file at host root). |
| TEK-14 | Owner | Needs server logs: available on Cloudflare (Logpush / Analytics), not on GitHub Pages. |
| TEK-15 | Done | URL map kept 1:1 for the three App Store Connect URLs; README has the domain-move plan (301 from github.io). |
| TEK-16 | Done | Semantic HTML: landmarks, one `<h1>`, `<nav>` with labels, real links, `<details>` language menu, skip link, focus styles. |
| TEK-17 | Done | No scripts at all, so no back-button hijacking. |
| TEK-18 | N/A | Informational. |

## BOT: AI bots and access

| Rule | Status | How |
|---|---|---|
| BOT-01 | Done | `robots.txt` explicitly allows Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Applebot, DuckDuckBot, YandexBot. **Note:** crawlers read robots.txt only at a host root, so it takes effect on the custom domain. Until then nothing blocks them anyway. |
| BOT-02 | Done | Training and search bots are separate blocks; no search bot is blocked. |
| BOT-03 | Owner | When moving to Cloudflare: Security → Bots → turn off "Block AI bots" / AI Crawl Control blocking for search bots, so it matches robots.txt (README step). |
| BOT-04 | Done | Brand site → training bots allowed (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot). |
| BOT-05 | Owner | Only relevant with logs (Cloudflare). |
| BOT-06 | Owner | After deploy, ask ChatGPT "what does <URL> say?" for home, species, FAQ, how-to-play, guide/how-mosquitoes-find-you. |
| BOT-07 | Done | `llms.txt` (summary, key facts, links) and `llms-full.txt` (all English text). Low cost; no ranking effect expected. |
| BOT-08 | Done | No `nosnippet`; `max-snippet:-1, max-image-preview:large` to allow full snippets. |
| BOT-09 | Done | Nothing is both disallowed and noindexed. |

## MIM: architecture and internal links

| Rule | Status | How |
|---|---|---|
| MIM-01 | Done | One topic: the game and real mosquitoes behind it. The guide articles all tie back to game mechanics. |
| MIM-02 | Done | Source context: free iPhone game (revenue = installs → IAP). Central entity: Mosquito Simulator: Bite & Run. Central intent: "mosquito game / play as a mosquito". Core section: home, how to play, modes, species, FAQ. Outer section: guide articles (species biology, bites, insect games). |
| MIM-03 | Partial | Hub (`/guide/`) + 3 articles now; plan 6–12 over time (ideas in README). |
| MIM-04 | Done | One page per question: species only on `/species/`, prices only in FAQ (+ species table), support answers on `/support/` with a short `#support` block on home kept for App Store Connect. |
| MIM-05 | Done | 7-link header nav, 14-link footer, 3+ contextual body links per page with descriptive anchors, breadcrumb at the bottom, "Keep reading" on articles. |
| MIM-06 | Done | Descriptive anchors only ("Compare the five game modes", never "click here"). |
| MIM-07 | Done | Every page is linked from nav or footer; verify.py fetched 173 internal URLs, 0 broken. |
| MIM-08 | Done | The entity set exists: home, features, modes, species, FAQ, press kit (about/fact sheet), support, privacy, terms. |
| MIM-09 | Done | Every page ≤ 2 clicks from home; max depth 2 folders (`/guide/<article>/`). |
| MIM-10 | Owner | Publishing rhythm for new guides: README suggests topics. |

## SAY: on-page

| Rule | Status | How |
|---|---|---|
| SAY-01 | Done | One `<h1>` per page (checked), answer paragraph directly below. |
| SAY-02 | Done | Nothing above the H1 in `<main>`: breadcrumb is at the bottom, article dates sit under the lede, hero image is beside/below the H1. |
| SAY-03 | Done | All titles 30–60 characters (checker enforced for all 7 languages), consistent with the H1, unique (verify.py). |
| SAY-04 | Done | Pattern [intent] + [topic] + [benefit], e.g. "How to Play Mosquito Simulator: Controls & Tips". |
| SAY-05 | Done | Unique meta description per page and language, ≤ 160 chars. |
| SAY-06 | Done | H2s are real sub-questions ("Can I play offline?", "Which rooms are in the game?"), each answered in its first sentence. |
| SAY-07 | Done | Tables for comparisons (modes, species, cues, insect games, prices), numbered steps for "how", lists for tips. |
| SAY-08 | Done | Short, lowercase, hyphenated, one scheme: `/<lang>/<page>/`, English slugs in every language (no Turkish characters, TR-03). |
| SAY-09 | Done | Descriptive alt text on every image (translated), meaningful file names (`metro-night19-1280.webp`), `og:image` 1200×630. |
| SAY-10 | Done | Articles: author box (name, role, what he checked), published + updated dates in visible `<time>`. |
| SAY-11 | Done | Dense, answer-first pages; no word-count padding. |
| SAY-12 | Done | `modified` dates are set by hand in front matter, never by the build. Legal pages keep 28 Oct 2026 (only the product name changed). |
| SAY-13 | Done | No keyword stuffing; translators were told to write naturally. |

## ICR: content quality and information gain

| Rule | Status | How |
|---|---|---|
| ICR-01 | Done | Information gain: exact per-species stats from the game data, real trait → bonus mapping, which parts of the science the game bends ("Toxorhynchites never drinks blood, we made it bite anyway"). |
| ICR-02 | Done | Operator knowledge from the game repo: modes rules, reward numbers, classes, unlock levels, offline behaviour, quick-chat only, under-16 offer rules. |
| ICR-03 | Partial | Originality: yes (own data). Scale: 3 articles. Responsibility: author named, but **the owner should read and sign off** the articles and translations (AIW-05). |
| ICR-04 | Done | A competitor cannot copy the species/stat tables or the mode rules without the game data. |
| ICR-05 | Partial | AI-drafted, facts sourced and linked; human (owner) review still required. |
| ICR-06 | Partial | Own data = game stats. A future "which rooms are hardest" stat page from analytics would be stronger. |
| ICR-07 | Done | Health-adjacent article (itch) cites CDC only for medical facts, says "not medical advice", points to a healthcare provider. |
| ICR-08 | Partial | Contact, privacy, terms, press/about exist. Missing: an AI-use / editorial note page (the guide hub has a "How these guides are written" section). |
| ICR-09 | N/A | New site. |
| ICR-10 | Done | Fan-out coverage per topic: price, devices, Android, offline, languages, purchases, ads, kids, delete data, friends. |
| ICR-11 | Done | `/guide/` hub with sub-topic articles. |
| ICR-12 | Owner | Refresh dates only with real updates (new rooms, Android launch, new season). |
| ICR-13 | N/A | New site. |

## GEO: quotable page format

| Rule | Status | How |
|---|---|---|
| GEO-01 | Done | Every page opens with a bold, self-contained answer sentence in the first ~60 words (`.lede`). |
| GEO-02 | Done | Ledes name the game, the platform, the date and the number ("20 rooms", "9 November 2026", "iOS 15"). |
| GEO-03 | Done | Articles: statistics (70 cm, 34 °C, 430 species / 30–40 vectors, 41,006 copies), named researchers, sources linked inline + numbered source list. |
| GEO-04 | Done | Price list, OS requirement, size, languages, release date as plain HTML text/tables. |
| GEO-05 | Done | Citable pages beyond the landing page: species, FAQ, modes, articles. |
| GEO-06 | Owner | Run a fan-out test (FanoutFox / Qforia) for "mosquito game iphone", "mosquito simulator", "games where you play as a mosquito". |
| GEO-07 | Done | Covers "free", "price", "vs/alternatives" (insect games comparison, fair, with disclosure), current year dates. |
| GEO-08 | Done | Decision data: price, devices, who it suits (kids/age), modes, what's free. |
| GEO-09 | Done | Definition sentences: "Mosquito Simulator: Bite & Run is a free iPhone game in which you play as a mosquito." |
| GEO-10 | Done | Short sentences, one idea each, exact numbers. |
| GEO-11 | Owner | No gameplay video yet (existing trailers are AI-generated). Record a real 30–60 s capture for YouTube and the App Preview. |
| GEO-12 | Done | Pages are short and dense (English home about 700 words). |
| GEO-13 | Done | No artificial chunking; one page per topic. |
| GEO-14 | Done | No hidden text, no "AI version", no prompt injection. |

## ENT: entity and structured data

| Rule | Status | How |
|---|---|---|
| ENT-01 | Partial | Brand card is consistent across site, schema, llms.txt and the App Store (name, release date, developer). Owner: keep the same facts on social profiles. |
| ENT-02 | Done | `@graph` linked by `@id`: Person (publisher) → WebSite → WebPage → VideoGame/MobileApplication, Article, BreadcrumbList, FAQPage, ItemList, ImageObject. Person `sameAs` = App Store developer page. Add social/Wikidata URLs to `developer_same_as` when they exist. |
| ENT-03 | Owner | Create a Wikidata item for the game (instance of video game; platform iOS; developer; publication date 2026-11-09; official website; App Store ID P3861) and add it to `developer_same_as`/game sameAs. |
| ENT-04 | Owner | Monitor AI answers for wrong facts; fix the source (App Store text, press). |
| ENT-05 | Partial | Person schema present; a separate author/profile page was not built (one-person studio). |
| ENT-06 | Done | Schema used for clarity, not expected to raise citations. |
| ENT-07 | Done | Uses SoftwareApplication family (VideoGame + MobileApplication with `offers` price 0 USD, `operatingSystem`, `applicationCategory` GameApplication), Article, BreadcrumbList, ImageObject. No Review/AggregateRating (the game has no ratings yet; nothing is invented). |
| ENT-08 | Done | FAQPage kept (harmless) and the FAQ is fully visible. |
| ENT-09 | Done | JSON-LD is generated from the visible page (lede, FAQ Q&A, breadcrumbs, species headings, source lists). |
| ENT-10 | Owner | Ask ChatGPT/Gemini/Claude "what is Mosquito Simulator: Bite & Run?" with and without web search; log answers with date and model. |

## DIS: off-site

All **Owner** (off-site work): DIS-01 source-gap table per quarter; DIS-02 get listed in third-party "games where you play as an insect / mosquito games" lists; DIS-03 a small data story (e.g. "which room do players fail most") for press; DIS-04 journalist requests; DIS-05/06/07 link quality over quantity; DIS-08 YouTube gameplay video (strongest correlated signal); DIS-09 Reddit (r/iosgaming, r/AppHookup) and Ekşi Sözlük with an honest, declared account; DIS-10 diversify; DIS-11 N/A (no review sites for small mobile games besides App Store ratings, which need the in-game review prompt); DIS-12 distribution: clips → TikTok/Reels/Shorts, species page → Pinterest/Reddit; DIS-13 N/A; DIS-14 no paid links. The press kit page supports DIS-03/04.

## ETC: e-commerce

N/A for ETC-01…ETC-12 (no store on the site; purchases happen in the App Store). ETC-07 analogue: no AI-generated image is presented as gameplay; all screenshots are in-engine frames.

## YRL: local SEO

N/A (no physical location).

## YSK: bans

| Rule | Status | How |
|---|---|---|
| YSK-01 | Done | 12 pages × 7 languages, each with unique, useful content; no programmatic filler. |
| YSK-02 | Done | Of the 8 risky templates only a fair comparison (insect games) is used once, with disclosure and no ranking. |
| YSK-03 | Done | No self-crowning lists; our game is listed last and not ranked. |
| YSK-04 | Done | No prompt injection or "remember us" tricks; llms.txt is factual. |
| YSK-05/06/07 | Done | None. |
| YSK-08 | Done | No pop-ups, no interstitials, no cookie banner (no cookies), no ads on the site. |
| YSK-09 | Done | None. |
| YSK-10 | Partial | Translations were written as native copy and machine-checked for structure, but **need a native-speaker review** before heavy promotion (especially ja and pt-BR). The pt-BR and ja pages state clearly that the game itself is not in those languages. |

## OLC: measurement

| Rule | Status | How |
|---|---|---|
| OLC-01 | Owner | Add the site to Google Search Console (URL-prefix property for the github.io sub-path, or Domain property for the custom domain); submit `sitemap.xml`. |
| OLC-02 | Owner | Bing Webmaster Tools (import from GSC), submit the sitemap, watch AI Performance. |
| OLC-03 | Owner / slot | No analytics by default (no cookies, KVKK-friendly). A marked slot (`analytics_head_html` in `site.config.json`, rendered in every `<head>`) takes Cloudflare Web Analytics or Plausible. If GA4 is ever added, add the AI-referrer channel regex from the rulebook and a consent banner (TR-09). |
| OLC-04/05 | Owner | 30–50 prompt set (e.g. "best mosquito game iPhone", "game where you play as a mosquito", "mosquito simulator free") in 2 engines, dated. |
| OLC-06…15 | Owner | GSC routines after data exists. App Store Connect → App Analytics "Web Referrer" shows installs coming from this site. |

## DON: conversion

| Rule | Status | How |
|---|---|---|
| DON-01 | Owner | Numbers (App Store Connect web referrer), behaviour (optional Clarity), own eyes (phone test). |
| DON-02 | Done | Phone-tested layout at 390 px: CTA visible in the first screen, nothing covers it, no layout shift. |
| DON-03 | Done | What, for whom (age 9+), features, how it works, price logic, contact. |
| DON-04 | N/A | No WhatsApp channel. |
| DON-05 | N/A | No sign-up funnel. |
| DON-06 | Done | One clear next step on every page: "Download free on the App Store" in the header, the hero and at the end of each page, plus Apple's Smart App Banner (`apple-itunes-app`, app-id 6827985347). Styled text link, no imitation Apple artwork (the official badge could not be downloaded in this environment; README explains how to drop it in). |

## TR: Turkey

| Rule | Status | How |
|---|---|---|
| TR-01 | Owner | Use post-Feb-2026 baselines in reports. |
| TR-02 | Owner | Yandex Webmaster + IndexNow (YandexBot allowed in robots.txt). |
| TR-03/04 | Done | ASCII, English slugs everywhere (`/tr/how-to-play/`); no Turkish characters in URLs. Turkish casing handled in headings (brand kept `lang="en"` so Cinzel doesn't render "MOSQUİTO"). |
| TR-05 | Done | One Turkish page per topic. |
| TR-06/07/08 | Done / Owner | Turkish pages exist with native copy and the live Turkish store name "Sivrisinek Oyunu: Isır ve Kaç"; English versions exist for TR-07. Community work is the owner's. |
| TR-09 | Done | No analytics/cookies by default, so no consent banner needed. |
| TR-10/11/12 | N/A | Informational. |

## AIW: using AI for SEO

| Rule | Status | How |
|---|---|---|
| AIW-01 | Done | Built a repeatable loop (`build.py`, `tools/check_translation.py`, `tools/verify.py`) instead of copy-pasted pages. |
| AIW-02 | Done | Numbers come from live sources (iTunes Lookup API on 24 Nov 2026, game data files, cited studies); none invented. |
| AIW-03 | Owner | Run an independent review in a clean session before publishing. |
| AIW-04 | Partial | This file + README act as status/verification docs. |
| AIW-05 | Owner | **Nothing was deployed or committed.** The owner reviews and publishes. |
| AIW-06/07/08 | N/A | Process advice. |
| AIW-09 | Done | Unverifiable claims were removed during writing (e.g. Android availability of a competitor, unverified CDC wording). |

## Section 20 checklists

- **20.1 per page:** intent, 150-word answer, single H1, title 30–60, information gain, stats/quotes/sources (articles), question H2s, format by intent, decision data in HTML, author/date (articles), 3+ contextual links, matching schema, no cannibalisation, mobile CTA test, ≤ 2 risky templates: all done.
- **20.2 new site:** robots + sitemap done; GSC, Bing, Yandex, IndexNow, Cloudflare bot settings, Wikidata, analytics are **Owner** steps listed in the README.
