#!/usr/bin/env python3
"""Render a 31-60 second 1080x1920 CareerWithCode Short in the cartoon "poster" style.

Look (Abhishek's design sheet, Oct 27 2026): dark coding-room background, a big Hindi + English
headline in white / yellow with heavy black outline (lines can sit on a yellow or red brush box),
a checklist / steps / mistakes panel on the left, a cartoon boy in a "Career With Code" hoodie on
the right, a yellow sticky note, an optional red banner and a "CareerWithCode" footer with a
YouTube play icon. The headline and boy pop in first, then the panel rows appear one by one across the video, then
the banner (the answer) near the end; the boy breathes and the note bobs throughout.

Usage: python3 make_cwc_poster.py spec.json out.mp4      (render the video)
       python3 make_cwc_poster.py spec.json out.png --still   (preview one frame at 4 s)

spec = {
  "title": [                                    # 2-4 lines, <= 16 characters each works best
    {"text": "Python", "color": "black", "box": "yellow"},   # box: yellow | red (optional)
    {"text": "सीखने के", "color": "white"},                   # color: white | yellow | black
    {"text": "5 बंपर फायदे!", "color": "white", "box": "red"}
  ],
  "list": {"type": "check",                     # check | cross | steps
           "items": ["High Demand", "High Salary", "Beginner Friendly"]},   # 3-5, <= 18 chars
  "note": "आज नहीं तो कब?",                      # yellow sticky note, <= 2 short lines (use \\n)
  "banner": "क्या यह आपकी Job भी ले सकता है?",     # optional red banner under the panel
  "face": "happy",                              # happy | thinking | worried (boy's pose)
  "palette": "blue",                            # blue | orange | purple
  "duration": 35                                # 31-60 (Abhishek: every Short over 30 s)
}
Text font is Kalam Bold (fonts/), which has both Devanagari and Latin letters. No emoji.
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_short  # reuses the lo-fi music generator

W, H, FPS = 1080, 1920, 30
KALAM = os.path.join(HERE, "fonts", "Kalam-Bold.ttf")
F = lambda s: ImageFont.truetype(KALAM, s, layout_engine=ImageFont.Layout.RAQM)

WHITE = (255, 255, 255); YELLOW = (255, 212, 0); RED = (220, 20, 30); BLACK = (0, 0, 0)
GREEN = (34, 197, 94); SKIN = (244, 196, 160); SKIN_D = (214, 156, 122)
HAIR = (18, 18, 24); HOODIE = (24, 24, 30); HOODIE_L = (44, 44, 54)
PALETTES = {  # (top, bottom, glow)
    "blue":   ((4, 8, 22),  (14, 30, 62), (70, 150, 255)),
    "orange": ((14, 8, 6),  (60, 30, 14), (255, 150, 60)),
    "purple": ((10, 6, 24), (40, 20, 70), (170, 120, 255)),
}
COLORS = {"white": WHITE, "yellow": YELLOW, "black": BLACK}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


# ---------------------------------------------------------------- background
def build_background(pal, rng):
    top, bottom, glowc = PALETTES.get(pal, PALETTES["blue"])
    y = np.linspace(0, 1, H)[:, None, None]
    arr = np.array(top, np.float32) * (1 - y) + np.array(bottom, np.float32) * y
    arr = np.repeat(arr, W, axis=1)
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for _ in range(26):  # bokeh lights of a room at night
        x, yy, r = rng.uniform(0, W), rng.uniform(80, H * 0.75), rng.uniform(14, 60)
        c = glowc if rng.random() < 0.6 else (255, 190, 90)
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=c + (rng.randint(25, 70),))
    for i in range(6):  # shelf / window lines
        yy = rng.uniform(300, 1100)
        d.line([(rng.uniform(0, 300), yy), (rng.uniform(700, W), yy)], fill=glowc + (18,), width=3)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([520, 900, 1180, 1700], fill=glowc + (70,))  # glow behind the boy
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1640, W, H], fill=(10, 10, 14, 255))  # desk
    d.line([(0, 1640), (W, 1640)], fill=glowc + (120,), width=4)
    noise = np.random.default_rng(3).normal(0, 4, (H, W, 1))
    a = np.clip(np.asarray(img.convert("RGB")).astype(np.float32) + noise, 0, 255)
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


# ---------------------------------------------------------------- text pieces
def text_layer(text, size, fill, stroke=9, max_w=W - 100, shadow=True):
    f = F(size)
    while f.getlength(text) > max_w and size > 36:
        size -= 4; f = F(size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = 26
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 9), text, font=f, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    sf = WHITE if fill == BLACK else BLACK
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=fill,
                            stroke_width=stroke if fill != BLACK else 0, stroke_fill=sf)
    return im


def brush_box(w, h, color, rng):
    im = Image.new("RGBA", (w + 50, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(25 + w * i / 19, 15 + rng.uniform(0, 8)) for i in range(20)]
    pts.append((w + 25 + rng.uniform(6, 18), 15 + h / 2))
    pts += [(25 + w * (19 - i) / 19, 15 + h - rng.uniform(0, 8)) for i in range(20)]
    pts.append((25 - rng.uniform(6, 18), 15 + h / 2))
    d.polygon(pts, fill=color + (255,))
    return im


def title_line(ln, size, rng):
    col = COLORS.get(ln.get("color", "white"), WHITE)
    box = {"yellow": YELLOW, "red": RED}.get(ln.get("box"))
    if box and col == WHITE and box == YELLOW:
        col = BLACK
    t = text_layer(ln["text"], size, col, stroke=0 if col == BLACK else 9, shadow=not box,
                   max_w=W - 160 if box else W - 90)
    if not box:
        return t
    b = brush_box(t.width - 10, int(t.height * 0.72), box, rng)
    b.alpha_composite(t, ((b.width - t.width) // 2, (b.height - t.height) // 2 - 4))
    sh = Image.new("RGBA", (b.width + 30, b.height + 30), (0, 0, 0, 0))
    sh.alpha_composite(b, (15, 15))
    return sh.rotate(rng.uniform(-3, 3), resample=Image.BICUBIC, expand=True)


def list_panel(spec_list, shown=None):
    """The panel with only the first `shown` rows filled in (all rows when None)."""
    kind = spec_list.get("type", "check"); items = spec_list["items"][:5]
    f = F(46)
    rows = []
    for i, it in enumerate(items):
        s = 46
        while F(s).getlength(it) > 380 and s > 30:
            s -= 2
        rows.append((it, F(s)))
    rh = 92; w, h = 540, 40 + rh * len(rows)
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([15, 21, w + 15, h + 21], 26, fill=(0, 0, 0, 120))
    d.rounded_rectangle([15, 15, w + 15, h + 15], 26, fill=(14, 22, 40, 230), outline=(90, 130, 200, 160), width=3)
    for i, (it, fo) in enumerate(rows[:shown]):
        cy = 15 + 20 + rh * i + rh // 2; x = 45
        if kind == "cross":
            d.line([(x, cy - 22), (x + 44, cy + 22)], fill=RED + (255,), width=12)
            d.line([(x + 44, cy - 22), (x, cy + 22)], fill=RED + (255,), width=12)
        elif kind == "steps":
            d.rounded_rectangle([x, cy - 24, x + 48, cy + 24], 8, fill=(60, 70, 90, 255))
            n = str(i + 1); l, t, r, b = F(38).getbbox(n)
            d.text((x + 24 - (r + l) / 2, cy - (b + t) / 2), n, font=F(38), fill=WHITE)
        else:
            d.rounded_rectangle([x, cy - 24, x + 48, cy + 24], 10, fill=GREEN + (255,))
            d.line([(x + 10, cy), (x + 21, cy + 12), (x + 39, cy - 12)], fill=WHITE, width=8, joint="curve")
        l, t, r, b = fo.getbbox(it)
        d.text((x + 70, cy - (b + t) / 2), it, font=fo, fill=WHITE)
    return im


def sticky_note(text, rng):
    lines = text.split("\n")[:2]
    s = 56
    while max(F(s).getlength(l) for l in lines) > 360 and s > 34:
        s -= 2
    fo = F(s); lh = int(s * 1.25)
    w = int(max(fo.getlength(l) for l in lines)) + 70; h = lh * len(lines) + 60
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([24, 28, w + 24, h + 28], fill=(0, 0, 0, 120))
    d.polygon([(20, 20), (w + 20, 20), (w + 20, h + 6), (w + 4, h + 20), (20, h + 20)], fill=YELLOW + (255,))
    d.polygon([(w + 20, h + 6), (w + 4, h + 20), (w + 4, h + 6)], fill=(210, 170, 0, 255))
    d.rectangle([w // 2 - 30, 12, w // 2 + 50, 34], fill=(255, 255, 255, 140))  # tape
    for i, l in enumerate(lines):
        lw = fo.getlength(l)
        d.text((20 + (w - lw) / 2, 50 + lh * i - s * 0.2), l, font=fo, fill=BLACK)
    im = im.filter(ImageFilter.SMOOTH)
    return im.rotate(rng.uniform(-6, -2), resample=Image.BICUBIC, expand=True)


def banner_layer(text, rng):
    t = text_layer(text, 58, WHITE, stroke=5, shadow=False, max_w=W - 160)
    b = brush_box(t.width, t.height - 10, RED, rng)
    b.alpha_composite(t, ((b.width - t.width) // 2, (b.height - t.height) // 2 - 4))
    return b.rotate(-2, resample=Image.BICUBIC, expand=True)


def footer_layer():
    t = text_layer("CareerWithCode", 50, WHITE, stroke=0, shadow=False)
    im = Image.new("RGBA", (t.width + 110, max(t.height, 80)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cy = im.height // 2
    d.rounded_rectangle([10, cy - 26, 86, cy + 26], 16, fill=(255, 0, 0, 255))
    d.polygon([(40, cy - 14), (40, cy + 14), (64, cy)], fill=WHITE)
    im.alpha_composite(t, (96, (im.height - t.height) // 2))
    return im


# ---------------------------------------------------------------- the boy
def boy(face):
    """Flat cartoon boy in a black 'Career With Code' hoodie. Canvas 640x980, feet cut at bottom."""
    S = 2  # draw at 2x, downscale for smooth edges
    cw, ch = 640 * S, 980 * S
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    p = lambda *v: [x * S for x in v]
    # hood behind the head and body
    d.ellipse(p(150, 470, 490, 700), fill=HOODIE_L)
    d.rounded_rectangle(p(40, 600, 600, 1100), 150 * S, fill=HOODIE)
    d.ellipse(p(205, 520, 435, 640), fill=HOODIE_L)  # hood collar
    d.rectangle(p(270, 520, 370, 600), fill=SKIN_D)  # neck
    d.ellipse(p(250, 560, 390, 630), fill=SKIN_D)
    for x in (285, 355):  # drawstrings
        d.line(p(x, 620, x - 4, 690), fill=(225, 225, 225), width=7 * S)
        d.ellipse(p(x - 12, 684, x + 4, 704), fill=(225, 225, 225))
    fo = ImageFont.truetype(KALAM, 62 * S)
    for i, word in enumerate(("Career", "With", "Code")):
        l, t, r, b = fo.getbbox(word)
        d.text(((cw - (r - l)) / 2 - l, (715 + 62 * i) * S), word, font=fo, fill=(235, 235, 235))
    # head
    d.ellipse(p(150, 300, 200, 380), fill=SKIN); d.ellipse(p(440, 300, 490, 380), fill=SKIN)  # ears
    d.ellipse(p(160, 150, 480, 560), fill=SKIN, outline=(90, 55, 40), width=4 * S)
    # hair: a big cap plus a spiky fringe
    d.ellipse(p(150, 120, 490, 330), fill=HAIR)
    d.ellipse(p(130, 170, 230, 360), fill=HAIR); d.ellipse(p(410, 170, 510, 340), fill=HAIR)
    for x0, x1, tip in ((170, 260, (215, 310)), (230, 320, (270, 300)), (290, 380, (340, 315)),
                        (350, 440, (400, 300)), (400, 480, (460, 330)), (120, 200, (150, 330))):
        d.polygon(p(x0, 230, x1, 230, *tip), fill=HAIR)
    for x, y, r in ((210, 140, 45), (300, 120, 50), (390, 135, 45), (450, 180, 38), (175, 190, 38)):
        d.ellipse(p(x - r, y - r, x + r, y + r), fill=HAIR)
    # face
    look = {"thinking": (-8, -10), "worried": (0, 4)}.get(face, (0, 0))
    for ex in (255, 385):
        d.ellipse(p(ex - 46, 360, ex + 46, 456), fill=WHITE, outline=(40, 30, 30), width=3 * S)
        cx, cy = ex + look[0], 410 + look[1]
        d.ellipse(p(cx - 30, cy - 32, cx + 30, cy + 32), fill=(78, 46, 26))
        d.ellipse(p(cx - 17, cy - 18, cx + 17, cy + 18), fill=(10, 8, 8))
        d.ellipse(p(cx + 4, cy - 20, cx + 18, cy - 6), fill=WHITE)
    if face == "worried":
        d.line(p(205, 335, 290, 350), fill=HAIR, width=13 * S); d.line(p(350, 350, 435, 335), fill=HAIR, width=13 * S)
    elif face == "thinking":
        d.line(p(205, 345, 295, 330), fill=HAIR, width=13 * S); d.line(p(345, 320, 435, 340), fill=HAIR, width=13 * S)
    else:
        d.arc(p(205, 315, 300, 365), 200, 330, fill=HAIR, width=13 * S)
        d.arc(p(340, 315, 435, 365), 210, 340, fill=HAIR, width=13 * S)
    d.arc(p(300, 445, 340, 485), 20, 160, fill=SKIN_D, width=6 * S)  # nose
    d.ellipse(p(195, 465, 245, 495), fill=(240, 150, 140)); d.ellipse(p(395, 465, 445, 495), fill=(240, 150, 140))
    if face == "happy":
        d.chord(p(255, 470, 385, 545), 0, 180, fill=(150, 30, 40))
        d.rectangle(p(270, 505, 370, 515), fill=WHITE)
        d.ellipse(p(295, 520, 345, 540), fill=(230, 100, 110))
    elif face == "worried":
        d.ellipse(p(295, 495, 345, 535), fill=(150, 30, 40))
    else:
        d.arc(p(285, 490, 365, 525), 20, 160, fill=(150, 30, 40), width=7 * S)
    # arms
    if face == "thinking":  # hand on chin
        d.line(p(540, 760, 470, 640, 400, 560), fill=HOODIE_L, width=70 * S, joint="curve")
        d.ellipse(p(355, 510, 440, 590), fill=SKIN)
        d.ellipse(p(385, 495, 420, 530), fill=SKIN)
    elif face == "worried":  # hands on head
        for sx in (1, -1):
            cx = 320 + sx * 190
            d.line(p(320 + sx * 260, 800, cx + sx * 40, 520, cx, 260), fill=HOODIE_L, width=64 * S, joint="curve")
            d.ellipse(p(cx - 45, 200, cx + 45, 290), fill=SKIN)
    else:  # pointing up, excited
        d.line(p(560, 780, 600, 560, 590, 430), fill=HOODIE_L, width=70 * S, joint="curve")
        d.ellipse(p(550, 360, 630, 450), fill=SKIN)
        d.rounded_rectangle(p(578, 270, 606, 380), 14 * S, fill=SKIN)
    return im.resize((640, 980), Image.LANCZOS)


# ---------------------------------------------------------------- composition
def paste_scaled(dst, layer, cx, cy, k, alpha=1.0):
    if k <= 0.01 or alpha <= 0.01:
        return
    lw, lh = max(1, int(layer.width * k)), max(1, int(layer.height * k))
    im = layer.resize((lw, lh), Image.BICUBIC)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    dst.alpha_composite(im, (int(cx - lw / 2), int(cy - lh / 2)))


class Poster:
    def __init__(self, spec, dur):
        self.dur = dur
        rng = random.Random(spec.get("seed", 7))
        self.bg = build_background(spec.get("palette", "blue"), rng)
        n = len(spec["title"])
        size = {1: 170, 2: 140, 3: 122}.get(n, 104)
        self.title = [title_line(ln, size, rng) for ln in spec["title"]]
        self.panel = list_panel(spec["list"]) if spec.get("list") else None
        # rows are revealed one by one across the video so a 30+ s Short keeps giving something new
        self.stages = [list_panel(spec["list"], k) for k in range(len(spec["list"]["items"][:5]) + 1)] if self.panel else []
        n = max(1, len(self.stages) - 1)
        self.row_t = [2.0 + i * (dur * 0.72 - 2.0) / n for i in range(n)]
        self.banner_t = (self.row_t[-1] + 3.0) if self.panel else 1.2
        self.note = sticky_note(spec["note"], rng) if spec.get("note") else None
        self.banner = banner_layer(spec["banner"], rng) if spec.get("banner") else None
        self.boy = boy(spec.get("face", "happy"))
        self.footer = footer_layer()
        self.glowc = PALETTES.get(spec.get("palette", "blue"), PALETTES["blue"])[2]
        y = 70; self.ty = []
        for im in self.title:
            self.ty.append(y + im.height // 2); y += int(im.height * 0.86)
        self.mid = max(y + 30, 640)
        self.panel_y = self.mid + (self.panel.height // 2 if self.panel else 0)

    def frame(self, t):
        img = self.bg.copy()
        # boy rises in from the bottom, then breathes
        k = ease((t - 0.2) / 0.6)
        breathe = 6 * math.sin(t * 2.2)
        bx, by = W - self.boy.width + 10, 1660 - self.boy.height + (1 - k) * 900 + breathe
        img.alpha_composite(self.boy, (int(bx), int(by)))
        for i, (im, cy) in enumerate(zip(self.title, self.ty)):
            kk = back((t - 0.1 - 0.2 * i) / 0.4)
            paste_scaled(img, im, W / 2, cy, kk)
        base = 0.1 + 0.2 * len(self.title)
        if self.panel:
            kk = ease((t - base - 0.2) / 0.4)
            shown = sum(1 for rt in self.row_t if t >= rt)
            pop = 1 + 0.03 * max(0.0, 1 - (t - self.row_t[shown - 1]) / 0.3) if shown else 1
            paste_scaled(img, self.stages[shown], 40 + self.panel.width / 2 - (1 - kk) * 700, self.panel_y, pop)
        if self.banner:
            kk = back((t - self.banner_t) / 0.4)
            paste_scaled(img, self.banner, W / 2, 1700, kk)
        if self.note:
            kk = back((t - base - 0.9) / 0.4)
            bob = 1 + (0.04 * abs(math.sin(t * 2.4)) if t > base + 1.5 else 0)
            ny = 1440
            if self.panel:
                ny = min(max(ny, self.panel_y + self.panel.height // 2 + self.note.height // 2 + 10), 1500)
            paste_scaled(img, self.note, 60 + self.note.width / 2, ny, kk * bob)
        paste_scaled(img, self.footer, W / 2, 1835, ease((t - 0.3) / 0.4))
        return img.convert("RGB")


def main(spec_path, out):
    spec = json.load(open(spec_path))
    dur = int(max(31, min(60, spec.get("duration", 35))))
    make_short.DUR = dur
    r = Poster(spec, dur)
    make_short.music(out + ".wav")
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
    if len(sys.argv) == 4 and sys.argv[3] == "--still":
        Poster(json.load(open(sys.argv[1])), 35).frame(34.0).save(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
