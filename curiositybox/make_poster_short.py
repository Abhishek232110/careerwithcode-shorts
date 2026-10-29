#!/usr/bin/env python3
"""Render a 31-60 second 1080x1920 CuriosityBox Short in the cinematic "poster" style.

Look: dark cinematic background, red brush category tag (top left), big Hindi headline in
white and yellow with a heavy black outline, a red banner subline, a small white line and a
yellow CTA pill. Elements pop in during the first ~2 s, then the background slowly zooms
while embers drift, so the Short holds attention until the end.

Usage: python3 make_poster_short.py spec.json out.mp4

spec = {
  "tag": "रहस्य",                              # category tag, 1-3 words (Devanagari)
  "headline": [                               # 2-4 lines, each <= 14 characters works best
    {"text": "समुद्र में डूबा", "color": "white"},
    {"text": "द्वारका नगरी", "color": "yellow"}
  ],
  "banner": "सच या सिर्फ कहानी?",               # red banner line, <= 28 characters
  "facts": ["...", "...", "..."],             # 3-5 white lines shown one by one (<= 9 words each);
                                              # or a single "line" for one fixed line
  "cta": "जानिए पूरी कहानी",                    # yellow pill text; an arrow is added
  "image": "curiositybox/images/<name>.png",  # optional background picture (AI generated);
                                              # without it a procedural scene is drawn
  "scene": "temple",                          # temple | ocean | space | cave | forest | city
  "palette": "gold",                          # gold | blue | red | green | purple
  "mood": "mysterious",                       # music: motivational | inspiring | epic | mysterious | upbeat
  "duration": 35                              # 31-60 (Abhishek: every Short over 30 s)
}
All on-screen text is Hindi in Devanagari (Noto Sans Devanagari). No emoji.
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_short  # reuses the original music generator

W, H, FPS = 1080, 1920, 30
DEVA = os.path.join(HERE, "fonts", "NotoSansDevanagari-Bold.ttf")
F = lambda s: ImageFont.truetype(DEVA, s, layout_engine=ImageFont.Layout.RAQM)

WHITE = (255, 255, 255); YELLOW = (255, 214, 10); RED = (214, 18, 28); BLACK = (0, 0, 0)
PALETTES = {  # (sky top, sky bottom, light glow)
    "gold":   ((18, 10, 4),  (92, 48, 14),  (255, 176, 70)),
    "blue":   ((2, 10, 24),  (8, 58, 92),   (90, 200, 255)),
    "red":    ((16, 2, 2),   (90, 16, 10),  (255, 110, 60)),
    "green":  ((2, 14, 8),   (16, 70, 40),  (140, 255, 170)),
    "purple": ((8, 4, 22),   (54, 22, 92),  (200, 140, 255)),
}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


# ---------------------------------------------------------------- background
def gradient(top, bottom, w, h):
    y = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - y) + np.array(bottom)[None, None, :] * y
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8))


def glow(img, cx, cy, r, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.45))
    img.alpha_composite(layer)


def rays(img, cx, cy, color, rng):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for _ in range(14):
        a = rng.uniform(math.pi * 0.25, math.pi * 0.75); spread = rng.uniform(0.02, 0.06)
        L = img.size[1] * 1.4
        pts = [(cx, cy), (cx + L * math.cos(a - spread), cy + L * math.sin(a - spread)),
               (cx + L * math.cos(a + spread), cy + L * math.sin(a + spread))]
        d.polygon(pts, fill=color + (rng.randint(10, 26),))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))


def silhouette(img, scene, rng, glowc):
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    dark = (6, 4, 4, 255)
    if scene == "temple":
        base = int(h * 0.62)
        for cx, s in ((w * 0.5, 1.0), (w * 0.22, 0.62), (w * 0.8, 0.7)):
            tw = 300 * s; top = base - 760 * s
            for k in range(9):  # stacked shikhara tiers
                y0 = base - (base - top) * k / 9; y1 = base - (base - top) * (k + 1) / 9
                ww = tw * (1 - k / 11)
                d.rectangle([cx - ww / 2, y1, cx + ww / 2, y0], fill=dark)
            d.polygon([(cx - tw * 0.12, top), (cx, top - 90 * s), (cx + tw * 0.12, top)], fill=dark)
        d.rectangle([0, base, w, h], fill=dark)
    elif scene == "ocean":
        for i in range(6):  # sunken arches and pillars
            x = w * (0.1 + 0.16 * i); top = h * rng.uniform(0.55, 0.68)
            d.rectangle([x, top, x + 46, h], fill=(4, 18, 30, 230))
            d.ellipse([x - 40, top - 40, x + 86, top + 40], fill=(4, 18, 30, 230))
        d.rectangle([0, int(h * 0.78), w, h], fill=(2, 10, 18, 255))
    elif scene == "space":
        R = int(w * 0.75)
        cx, cy = int(w * 0.62), int(h * 0.36)
        planet = Image.new("RGBA", img.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(planet)
        pd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(10, 30, 60, 255))
        pd.ellipse([cx - R, cy - R, cx + R, cy + R], outline=glowc + (255,), width=10)
        img.alpha_composite(planet.filter(ImageFilter.GaussianBlur(3)))
        for _ in range(220):
            x, y = rng.randint(0, w), rng.randint(0, h); r = rng.choice((1, 1, 2, 3))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rng.randint(80, 220)))
    elif scene == "cave":
        d.polygon([(0, 0), (w * 0.28, 0), (w * 0.18, h * 0.45), (w * 0.24, h), (0, h)], fill=dark)
        d.polygon([(w, 0), (w * 0.74, 0), (w * 0.84, h * 0.4), (w * 0.76, h), (w, h)], fill=dark)
        d.rectangle([0, int(h * 0.82), w, h], fill=dark)
        x, y = w * 0.5, h * 0.62  # explorer with torch
        d.ellipse([x - 28, y - 190, x + 28, y - 134], fill=dark)
        d.polygon([(x - 60, y - 130), (x + 60, y - 130), (x + 74, y + 60), (x - 74, y + 60)], fill=dark)
        d.rectangle([x - 50, y + 60, x - 14, y + 210], fill=dark); d.rectangle([x + 14, y + 60, x + 50, y + 210], fill=dark)
        d.line([(x + 60, y - 100), (x + 120, y - 220)], fill=dark, width=12)
        glow(img, int(x + 124), int(y - 240), 120, (255, 170, 60), 200)
    elif scene == "forest":
        for i in range(14):
            x = rng.uniform(0, w); hh = rng.uniform(0.35, 0.7) * h
            d.polygon([(x, h - hh), (x - 90, h * 0.8), (x + 90, h * 0.8)], fill=dark)
        d.rectangle([0, int(h * 0.8), w, h], fill=dark)
    elif scene == "city":
        x = 0
        while x < w:
            bw = rng.randint(70, 160); bh = rng.uniform(0.15, 0.45) * h
            d.rectangle([x, h * 0.75 - bh, x + bw, h], fill=dark); x += bw + rng.randint(4, 20)
    img.alpha_composite(layer)


def build_background(spec, rng):
    bw, bh = int(W * 1.12), int(H * 1.12)  # oversized for the slow zoom
    if spec.get("image") and os.path.exists(spec["image"]):
        src = Image.open(spec["image"]).convert("RGB")
        s = max(bw / src.width, bh / src.height)
        src = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.LANCZOS)
        l, t = (src.width - bw) // 2, (src.height - bh) // 2
        img = src.crop((l, t, l + bw, t + bh)).convert("RGBA")
        glowc = PALETTES.get(spec.get("palette", "gold"), PALETTES["gold"])[2]
    else:
        top, bottom, glowc = PALETTES.get(spec.get("palette", "gold"), PALETTES["gold"])
        img = gradient(top, bottom, bw, bh).convert("RGBA")
        lx, ly = int(bw * rng.uniform(0.55, 0.75)), int(bh * 0.22)
        glow(img, lx, ly, 520, glowc, 150)
        rays(img, lx, ly, glowc, rng)
        silhouette(img, spec.get("scene", "temple"), rng, glowc)
        glow(img, bw // 2, int(bh * 0.66), 700, glowc, 40)  # fog
    # darken the lower 55% so the text pops, plus vignette
    shade = np.zeros((bh, bw), np.float32)
    yy = np.linspace(0, 1, bh)[:, None]; xx = np.linspace(-1, 1, bw)[None, :]
    shade += np.clip((yy - 0.35) / 0.65, 0, 1) * 0.62
    shade += np.clip(np.sqrt(xx ** 2 + ((yy - 0.45) * 1.6) ** 2) - 0.75, 0, 1) * 0.9
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * (1 - np.clip(shade, 0, 0.85))[..., None]
    noise = np.random.default_rng(7).normal(0, 6, arr.shape[:2])[..., None]
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8)).convert("RGBA")


# ---------------------------------------------------------------- overlays
def text_layer(text, size, fill, stroke=10, shadow=True, max_w=W - 120):
    f = F(size)
    while f.getlength(text) > max_w and size > 40:
        size -= 4; f = F(size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = 30
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 8, pad - t + 10), text, font=f, fill=(0, 0, 0, 190),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 190))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=BLACK)
    return im


def brush(w, h, color, rng, ragged=True):
    """A red paint-stroke shape with rough ends, like the sample's tags and banners."""
    im = Image.new("RGBA", (w + 60, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    for i in range(24):
        pts.append((30 + w * i / 23, 15 + rng.uniform(0, 7)))
    pts.append((w + 30 + (rng.uniform(10, 26) if ragged else 0), 15 + h * 0.5))
    for i in range(24):
        pts.append((30 + w * (23 - i) / 23, 15 + h - rng.uniform(0, 7)))
    pts.append((30 - (rng.uniform(8, 20) if ragged else 0), 15 + h * 0.5))
    d.polygon(pts, fill=color + (255,))
    for _ in range(10):  # dry-brush streaks
        y = rng.uniform(18, h + 10); x0 = rng.uniform(w * 0.6, w)
        d.line([(x0, y), (w + 40, y + rng.uniform(-3, 3))], fill=color + (rng.randint(90, 200),), width=rng.randint(2, 5))
    return im


def tag_layer(text, rng):
    t = text_layer(text, 54, WHITE, stroke=0, shadow=False)
    b = brush(t.width + 30, 92, RED, rng)
    b.alpha_composite(t, ((b.width - t.width) // 2, (b.height - t.height) // 2 - 4))
    return b


def banner_layer(text, rng):
    t = text_layer(text, 66, WHITE, stroke=4, shadow=False, max_w=W - 200)
    b = brush(min(W - 60, t.width + 80), t.height + 10, RED, rng)
    b.alpha_composite(t, ((b.width - t.width) // 2, (b.height - t.height) // 2))
    return b.rotate(-2.5, resample=Image.BICUBIC, expand=True)


def cta_layer(text):
    t = text_layer(text, 50, BLACK, stroke=0, shadow=False)
    aw, gap = 44, 14
    w, h = t.width + aw + gap + 70, 104
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([15, 21, w + 15, h + 21], radius=h // 2, fill=(0, 0, 0, 150))
    d.rounded_rectangle([15, 15, w + 15, h + 15], radius=h // 2, fill=YELLOW + (255,))
    x0 = 15 + (w - (t.width + gap + aw)) // 2
    im.alpha_composite(t, (x0, 15 + (h - t.height) // 2 - 4))
    ax, ay = x0 + t.width + gap, 15 + h // 2
    d.rectangle([ax, ay - 5, ax + aw - 16, ay + 5], fill=BLACK + (255,))
    d.polygon([(ax + aw - 22, ay - 17), (ax + aw, ay), (ax + aw - 22, ay + 17)], fill=BLACK + (255,))
    return im


def paste_scaled(dst, layer, cx, cy, k, alpha=1.0):
    if k <= 0.01 or alpha <= 0.01:
        return
    lw, lh = max(1, int(layer.width * k)), max(1, int(layer.height * k))
    im = layer.resize((lw, lh), Image.BICUBIC)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im.putalpha(a)
    dst.alpha_composite(im, (int(cx - lw / 2), int(cy - lh / 2)))


class Poster:
    def __init__(self, spec, dur):
        self.dur = dur
        rng = random.Random(spec.get("seed", hash(json.dumps(spec, ensure_ascii=False)) & 0xffff))
        self.bg = build_background(spec, rng)
        self.tag = tag_layer(spec["tag"], rng)
        self.lines = []
        n = len(spec["headline"])
        size = {1: 190, 2: 160, 3: 140}.get(n, 122)
        for ln in spec["headline"]:
            col = YELLOW if ln.get("color") == "yellow" else WHITE
            big = ln.get("big", ln.get("color") == "yellow")
            self.lines.append(text_layer(ln["text"], int(size * (1.12 if big else 0.9)), col))
        self.banner = banner_layer(spec["banner"], rng) if spec.get("banner") else None
        # "facts": 3-5 short lines shown one after another in the white-line slot, so a 30+ s
        # Short keeps revealing something new; a single "line" still works
        facts = spec.get("facts") or ([spec["line"]] if spec.get("line") else [])
        self.facts = [text_layer(f, 50, WHITE, stroke=5, max_w=W - 160) for f in facts]
        self.line = max(self.facts, key=lambda im: im.height) if self.facts else None
        self.cta = cta_layer(spec["cta"]) if spec.get("cta") else None
        self.embers = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6), rng.uniform(20, 70),
                        rng.uniform(0, 6.28)) for _ in range(70)]
        self.glowc = PALETTES.get(spec.get("palette", "gold"), PALETTES["gold"])[2]
        # vertical layout: headline block starts ~37% down, everything stacked below it
        y = int(H * 0.36); self.pos = []
        for im in self.lines:
            self.pos.append(y + im.height // 2); y += int(im.height * 0.78)
        y += 30
        self.banner_y = y + (self.banner.height // 2 if self.banner else 0)
        y += (self.banner.height if self.banner else 0) + 40
        self.line_y = y + (self.line.height // 2 if self.line else 0)
        y += (self.line.height if self.line else 0) + 30
        self.cta_y = min(H - 220, y + (self.cta.height // 2 if self.cta else 0))

    def frame(self, t):
        z = 1 + 0.10 * (t / self.dur)  # slow push-in
        bw, bh = self.bg.size
        cw, ch = int(W * 1.12 / z), int(H * 1.12 / z)
        l, tp = (bw - cw) // 2, (bh - ch) // 2
        img = self.bg.crop((l, tp, l + cw, tp + ch)).resize((W, H), Image.BILINEAR)
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, r, sp, ph in self.embers:  # drifting embers / dust
            yy = (y - sp * t) % H; xx = x + 18 * math.sin(t * 0.8 + ph)
            a = int(110 + 90 * math.sin(t * 2 + ph))
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=self.glowc + (max(0, a),))
        paste_scaled(img, self.tag, 60 + self.tag.width / 2, 150, back((t - 0.1) / 0.35))
        for i, (im, cy) in enumerate(zip(self.lines, self.pos)):
            k = back((t - 0.3 - 0.22 * i) / 0.4)
            pulse = 1 + (0.03 * math.sin((t - 2) * 3) if (t > 2 and im is self.lines[-1]) else 0)
            paste_scaled(img, im, W / 2, cy, k * pulse)
        base = 0.3 + 0.22 * len(self.lines)
        if self.banner:
            k = ease((t - base) / 0.35)
            paste_scaled(img, self.banner, W / 2 - (1 - k) * 600, self.banner_y, 1.0, k)
        if self.facts:
            start = base + 0.4; slot = max(3.0, (self.dur - start - 0.5) / len(self.facts))
            i = min(len(self.facts) - 1, int(max(0.0, t - start) // slot))
            lt = t - start - i * slot
            k = ease(lt / 0.4) if i == 0 or lt < slot else 1.0
            out = 1.0 if i == len(self.facts) - 1 else 1 - ease((lt - slot + 0.4) / 0.4)
            paste_scaled(img, self.facts[i], W / 2, self.line_y + (1 - k) * 40, 1.0, min(k, out))
        if self.cta:
            k = back((t - base - 0.8) / 0.4)
            bob = 1 + (0.05 * abs(math.sin(t * 2.6)) if t > base + 1.4 else 0)
            paste_scaled(img, self.cta, W / 2, self.cta_y, k * bob)
        return img.convert("RGB")


def main(spec_path, out):
    spec = json.load(open(spec_path))
    dur = int(max(31, min(60, spec.get("duration", 35))))
    make_short.DUR = dur
    r = Poster(spec, dur)
    make_short.music(out + ".wav", spec.get("mood", "mysterious"))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "21",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for i in range(FPS * dur):
        p.stdin.write(r.frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    os.remove(out + ".wav")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[3] == "--still":  # preview one frame at 4 s
        spec = json.load(open(sys.argv[1]))
        Poster(spec, 35).frame(4.0).save(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
