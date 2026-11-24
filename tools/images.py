#!/usr/bin/env python3
"""Turn picked in-game frames from the game repo into web images (AVIF + WebP at two widths),
the 1200x630 Open Graph card and the favicons. Run once after changing the picks:

    python3 tools/images.py [/path/to/mosquito-game]

Output goes to src/assets/img/ (committed). Originals stay in the game repo and never reach the site.
Needs: Pillow, ImageMagick (`magick`), `cwebp`, `avifenc`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GAME = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "mosquito-game"
OUT = ROOT / "src" / "assets" / "img"
FONTS = ROOT / "tools" / "fonts"

# id -> source (relative to the game repo). Every pick is a real in-engine frame (gameplay, cinematic camera or menu).
SHOTS = {
    "hero-orbit": "Captures/story_shots/6_perfect_orbit.jpg",
    "bedroom-night01": "Captures/story_shots/2_opening_wide.jpg",
    "sleeper-waking": "Captures/story_shots/3_waking.jpg",
    "landed-on-skin": "Captures/perch/face.jpg",
    "bite-wrist": "Captures/perch/wrist_R.jpg",
    "metro-night19": "Captures/showcase/L19_chase.png",
    "pool-night16": "Captures/showcase/L16_chase.png",
    "restaurant-night18": "Captures/showcase/L18_chase_late.png",
    "pest-control-night20": "Captures/showcase/L20_chase.png",
    "menu-home": "Captures/showcase/menu_home.png",
    "store-species": "Captures/showcase/menu_store_preview.png",
    "online-1v3": "Captures/redesign/menu_online.png",
    "levels-screen": "Captures/showcase/menu_levels.png",
    "daily-night": "Captures/redesign/popup_daily.png",
    "results": "Captures/redesign/hud_results.png",
}
SPECIES = ["culex", "aegypti", "anopheles", "albopictus", "gallinipper", "culiseta",
           "wyeomyia", "deinocerites", "sabethes", "toxorhynchites"]
ICON = "Assets/_Game/UI/AppIcon/app_icon.png"


def run(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def encode(img: Image.Image, stem: str, quality_webp=78, quality_avif=55, alpha=False):
    """Save img as stem.webp and stem.avif; returns nothing."""
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "x.png"
        img.save(png)
        run("cwebp", "-quiet", "-q", str(quality_webp), "-m", "6", *(["-alpha_q", "90"] if alpha else []), str(png),
            "-o", str(OUT / f"{stem}.webp"))
        run("avifenc", "-q", str(quality_avif), "-s", "4", str(png), str(OUT / f"{stem}.avif"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, rel in SHOTS.items():
        src = Image.open(GAME / rel).convert("RGB")
        w0, h0 = src.size
        widths = [w for w in (640, 1280) if w <= w0] or [w0]
        if w0 < 1280 and w0 not in widths:
            widths.append(w0)
        entry = {"src": rel, "variants": []}
        for w in sorted(set(widths)):
            h = round(h0 * w / w0)
            im = src.resize((w, h), Image.LANCZOS)
            stem = f"{key}-{w}"
            q = 84 if key in ("landed-on-skin", "hero-orbit") else 78
            encode(im, stem, quality_webp=q)
            entry["variants"].append({"w": w, "h": h, "stem": stem})
        manifest[key] = entry

    for sp in SPECIES:
        src = Image.open(GAME / f"Assets/_Game/Content/Shared/Store/Icons/mosq_{sp}.png").convert("RGBA")
        canvas = Image.new("RGBA", (480, 384), (0, 0, 0, 0))
        im = src.copy()
        im.thumbnail((480, 384), Image.LANCZOS)
        canvas.paste(im, ((480 - im.width) // 2, (384 - im.height) // 2), im)
        stem = f"species-{sp}"
        encode(canvas, stem, quality_webp=82, alpha=True)
        manifest[stem] = {"src": f"Store/Icons/mosq_{sp}.png", "variants": [{"w": 480, "h": 384, "stem": stem}]}

    # App icon: favicons, apple-touch-icon, press-kit download (the store icon itself).
    icon = Image.open(GAME / ICON).convert("RGB")
    for size, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (192, "icon-192.png"),
                       (512, "icon-512.png"), (1024, "app-icon-1024.png")):
        icon.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    icon.resize((48, 48), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    encode(icon.resize((256, 256), Image.LANCZOS), "app-icon-256", quality_webp=82)
    manifest["app-icon-256"] = {"src": ICON, "variants": [{"w": 256, "h": 256, "stem": "app-icon-256"}]}

    og_card(manifest)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("images:", len(manifest), "->", OUT)


def og_card(manifest):
    """1200x630 share card composed only from real frames: the orbit shot full-bleed + two in-game frames."""
    W, H = 1200, 630
    base = Image.open(GAME / SHOTS["hero-orbit"]).convert("RGB")
    s = max(W / base.width, H / base.height)
    base = base.resize((round(base.width * s), round(base.height * s)), Image.LANCZOS)
    left = (base.width - W) // 2
    base = base.crop((left, 0, left + W, H))
    shade = Image.new("L", (W, H))
    d = ImageDraw.Draw(shade)
    for x in range(W):
        d.line([(x, 0), (x, H)], fill=int(215 * max(0.0, 1 - x / 760)))
    navy = Image.new("RGB", (W, H), (9, 14, 33))
    card = Image.composite(navy, base, shade)

    def thumb(rel, box_w):
        im = Image.open(GAME / rel).convert("RGB")
        im = im.resize((box_w, round(im.height * box_w / im.width)), Image.LANCZOS)
        return im

    y = 330
    for rel in (SHOTS["metro-night19"], SHOTS["online-1v3"]):
        t = thumb(rel, 300)
        frame = Image.new("RGB", (t.width + 6, t.height + 6), (233, 226, 210))
        frame.paste(t, (3, 3))
        card.paste(frame, (850, y - 190 if rel == SHOTS["metro-night19"] else y - 30))
    draw = ImageDraw.Draw(card)
    cinzel = ImageFont.truetype(str(FONTS / "cinzel.ttf"), 64)
    cinzel.set_variation_by_axes([700])
    cinzel_s = ImageFont.truetype(str(FONTS / "cinzel.ttf"), 44)
    cinzel_s.set_variation_by_axes([700])
    barlow = ImageFont.truetype(str(FONTS / "Barlow-SemiBold.ttf"), 30)
    barlow_r = ImageFont.truetype(str(FONTS / "Barlow-Regular.ttf"), 26)
    draw.text((64, 150), "MOSQUITO", font=cinzel, fill=(245, 240, 228))
    draw.text((64, 226), "SIMULATOR", font=cinzel, fill=(245, 240, 228))
    draw.text((64, 306), "BITE & RUN", font=cinzel_s, fill=(232, 56, 72))
    draw.text((64, 392), "Play as a mosquito. 20 nights, online 1 vs 3.", font=barlow_r, fill=(214, 220, 236))
    draw.rounded_rectangle((64, 456, 470, 516), radius=30, fill=(200, 24, 48))
    draw.text((92, 469), "Free on iPhone · App Store", font=barlow, fill=(255, 255, 255))
    icon = Image.open(GAME / ICON).convert("RGB").resize((72, 72), Image.LANCZOS)
    mask = Image.new("L", (72, 72))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 71, 71), radius=16, fill=255)
    card.paste(icon, (64, 56), mask)
    card.save(OUT / "og-card.jpg", quality=86, optimize=True, progressive=True)
    manifest["og-card"] = {"src": "composite", "variants": [{"w": W, "h": H, "stem": "og-card"}]}


if __name__ == "__main__":
    main()
