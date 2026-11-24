# mosquito-site

Landing, support and legal website for **Mosquito Simulator: Bite & Run** (iPhone, App Store id 6827985347).
Static HTML built by one Python script (standard library only). No framework, no JavaScript, no cookies.

Live (GitHub Pages): https://amert9696.github.io/mosquito-site/

App Store Connect points at three URLs that must keep working: the **support URL** (site root, with a `#support`
section), `privacy.html` and `terms.html`. All three are generated at the same paths.

## Layout

```
site.config.json      ← the one place for base URL, contact email, App Store id, analytics slot, IndexNow key
build.py              ← builds the site
src/content/<lang>/   ← page sources: en (master), tr, de, es, pt-br, fr, ja. Front matter + HTML with [[placeholders]]
src/legal/            ← privacy.html, terms.html (English + Turkish summary; not translated on purpose)
src/assets/           ← site.css, self-hosted fonts (Cinzel, Barlow; SIL OFL), processed images
tools/images.py       ← turns picked in-game frames from ../mosquito-game into AVIF/WebP, OG card, favicons
tools/check_translation.py  ← structure check of a translation against English
tools/verify.py       ← link / hreflang / JSON-LD / HTML checks against a running local server
tools/indexnow.py     ← pings IndexNow (needs a custom domain)
SEO-GEO-CHECKLIST.md  ← rulebook rule id → how the site satisfies it
```

Everything else at the top level (index.html, `tr/`, `assets/`, sitemap.xml, robots.txt, llms.txt …) is **generated**.
Do not edit it by hand; edit `src/` and rebuild. `.build-manifest.json` lists generated files so stale ones get removed.
`_config.yml` keeps `src/`, `tools/`, this README and the config out of the GitHub Pages output.

## Build and preview

```bash
python3 build.py                                   # writes the site into this folder (what GitHub Pages serves)

# local preview with the same sub-path as production
python3 build.py --out /tmp/msite/mosquito-site --base http://localhost:8765/mosquito-site/
(cd /tmp/msite && python3 -m http.server 8765)     # open http://localhost:8765/mosquito-site/
python3 tools/verify.py /tmp/msite/mosquito-site http://localhost:8765/mosquito-site/
```

Always run the plain `python3 build.py` last before committing, so the committed files carry the production base URL.

### Editing content

- English is the master. Each page file has front matter (`title` 30–60 chars, `description` ≤ 155, `h1`, `nav`,
  `published`, `modified`) and an HTML fragment. Change `modified` only when the content really changes.
- Placeholders: `[[url:species]]` localized link, `[[img:id|alt|caption]]`, `[[hero:…]]`, `[[species:id|alt]]`,
  `[[cta]]` App Store button, `[[email:Subject]]` contact link, `[[appstore]]`, `[[asset:img/file]]`.
- After changing English, update the other six languages and run `python3 tools/check_translation.py <lang>`.
  The translations are native-style copy but have not had a human native review yet: get one for ja and pt-br first.
- Images: edit the picks in `tools/images.py`, run `python3 tools/images.py`, rebuild. Only real in-game frames.

### App Store badge

Apple's official "Download on the App Store" badge could not be downloaded here, so the site uses a styled text
button (no Apple logo, nothing imitating Apple artwork). To switch to the official badge: download the localized
SVGs from https://developer.apple.com/app-store/marketing/guidelines/ (Marketing Resources → badges), save them as
`src/assets/img/badge-<lang>.svg`, and change `Site.cta()` in build.py to render `<img>` with the badge (min height
40 px, clear space ¼ of its height, unmodified).

## Contact email

`contact_email` in `site.config.json` is used on the home support section, `/support/`, privacy and terms only.
Switch it to a support alias (e.g. support@yourdomain) and rebuild. `press_email` is empty, so the press kit links to
the support page; set it to a press alias to show an address there.

## Analytics

None by default: no cookies, no consent banner needed (KVKK/GDPR). To add privacy-friendly analytics, paste the
snippet into `analytics_head_html` in `site.config.json` (e.g. Cloudflare Web Analytics beacon or Plausible) and
rebuild; `_headers` CSP must then allow that script's domain. Installs from the site show up in App Store Connect →
App Analytics → Sources → Web Referrer.

## Deploy

### GitHub Pages (current)

Repository settings → Pages → "Deploy from a branch" → `main` / root (as today). Build, commit the generated files,
push. Nothing else to configure. GitHub Pages **ignores `_headers`** (no custom headers or cache rules there).

### Cloudflare Pages + custom domain (recommended next step)

Needed for: a root-level `robots.txt`, `llms.txt`, `app-ads.txt` (AdMob only reads it at the root of the developer
website domain) and IndexNow; also gives the security/cache headers in `_headers`.

1. Buy the domain (open decision) and add it to Cloudflare.
2. Set `base_url` in `site.config.json` to `https://<domain>/` and rebuild. Everything (canonical, hreflang, sitemap,
   OG, JSON-LD, robots, llms) follows from that one value; `_headers` paths too.
3. Cloudflare Pages → Create project → connect this repo. Build command: `python3 build.py --out dist`
   (add `--base https://<domain>/` if you prefer not to change the config), output directory: `dist`.
   Or build locally and use direct upload of `dist/`.
4. Custom domain → attach. Security → Bots: make sure "Block AI bots" / AI Crawl Control does not block search bots
   (rulebook BOT-03); robots.txt already allows them.
5. Move the old URLs: in App Store Connect update Support URL, Marketing URL (= the new domain, needed for
   app-ads.txt) and Privacy Policy URL in the next version. Keep the GitHub Pages site up and replace each old page
   with a redirect page (`<meta http-equiv="refresh">` + canonical to the new URL), because GitHub Pages cannot send
   301s. Keep it for at least a year.
6. Fill `app-ads.txt` with the exact line(s) from AdMob (AdMob → Apps → app-ads.txt). Never invent publisher ids.

## After every deploy (new-site checklist, rulebook §20.2)

1. **Google Search Console:** add a property (URL-prefix `https://amert9696.github.io/mosquito-site/` now, Domain
   property after the move). Submit `sitemap.xml`. Inspect the home URL and request indexing.
2. **Bing Webmaster Tools:** import from GSC, submit the sitemap, enable AI Performance reports.
3. **Yandex Webmaster** (Turkey traffic): add and submit the sitemap.
4. **IndexNow** (custom domain only): set `indexnow_key`, rebuild, deploy, `python3 tools/indexnow.py`.
5. **Rich results test** on home, FAQ, an article and species (https://search.google.com/test/rich-results) and
   https://validator.schema.org.
6. **PageSpeed Insights** on home (mobile) and one article.
7. **Wikidata:** create an item for the game (official website, App Store app ID, developer, publication date
   2026-11-09) and add it to `developer_same_as` / game `sameAs`.
8. **AI check (dated, per model):** ask ChatGPT, Gemini, Perplexity and Claude "What is Mosquito Simulator: Bite &
   Run?" with and without web search; keep a log (rulebook OLC-04/05, ENT-10, BOT-06).

## Ideas for the next guide articles (one per 3 days at first, rulebook MIM-10)

"Do mosquitoes prefer certain blood types?", "Why do mosquitoes buzz in your ear?", "How long do mosquitoes live?",
"Mosquito vs gnat vs midge", "How the Asian tiger mosquito spread", "Night 13 (Exam Hall) walkthrough". Each must add
something the top results lack (game data, sourced numbers) and link back to species/how-to-play.
