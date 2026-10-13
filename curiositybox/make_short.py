#!/usr/bin/env python3
"""Render a 20-30 second 1080x1920 CuriosityBox fact Short from a JSON spec.

Usage: python3 make_short.py spec.json out.mp4

spec = {
  "category": "whatif",                     # ai | whatif | paisa | kahani | facts (sets colour + chip)
  "hook": "Agar Chand Gayab Ho Jaye Toh?",  # big question, <= 7 words, Hinglish
  "points": [                               # 3-4 cards, revealed one by one
    {"title": "Raatein ekdum andheri", "text": "Chand ki roshni nahi, sirf taare dikhenge."},
    ...
  ],
  "takeaway": "Chand sirf sundar nahi, Earth ka bodyguard hai.",   # <= 12 words
  "cta": "Follow karo, roz ek naya sawaal",
  "duration": 25                            # 20-30 s, more text = longer
}
All text is Hinglish in Latin script (Poppins font). No emoji: the font cannot draw them.
"""
import json, math, os, random, struct, subprocess, sys, wave
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
DUR = 25
BOLD = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
MED = os.path.join(HERE, "fonts", "Poppins-Medium.ttf")
REG = os.path.join(HERE, "fonts", "Poppins-Regular.ttf")
F = lambda p, s: ImageFont.truetype(p, s)

WHITE = (255, 255, 255); SOFT = (206, 212, 230); MUTED = (150, 158, 190)
GOLD = (255, 212, 59); CARD = (255, 255, 255)
CATS = {
    "ai":     ("AI & Tech",  (77, 171, 247)),
    "whatif": ("What If?",   (177, 151, 252)),
    "paisa":  ("Paisa & Career", (105, 219, 124)),
    "kahani": ("Kahaniyaan", (255, 169, 77)),
    "facts":  ("Amazing Facts", (247, 131, 172)),
}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def wrap(text, font, width, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=font) <= width: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def background(accent):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (11, 10, 42), (40, 14, 70)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-300, 1300, 600, 2200), fill=tuple(int(c * 0.35) for c in accent))
    g.ellipse((600, -250, 1400, 550), fill=(90, 30, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.6)


def starfield(seed=11):
    r = random.Random(seed)
    return [(r.uniform(0, W), r.uniform(0, H), r.choice([1.5, 2, 2.5, 3.5]), r.uniform(0, 6.28))
            for _ in range(140)]


class Renderer:
    def __init__(self, spec):
        self.spec = spec
        cat = spec.get("category", "facts")
        self.cat_label, self.accent = CATS.get(cat, CATS["facts"])
        self.bg = background(self.accent)
        self.stars = starfield()
        self.box = Image.open(os.path.join(HERE, "assets", "box.png")).convert("RGBA")
        self.points = spec["points"][:4]
        n = len(self.points)
        self.t_hook = 3.2
        self.t_end = DUR - 5.5                      # takeaway starts here
        self.slot = (self.t_end - self.t_hook) / n  # time per card
        self.f_chip = F(BOLD, 34); self.f_hook = F(BOLD, 92); self.f_title = F(BOLD, 56)
        self.f_ctitle = F(BOLD, 50); self.f_ctext = F(REG, 40); self.f_num = F(BOLD, 40)
        self.f_take = F(BOLD, 58); self.f_cta = F(BOLD, 40); self.f_brand = F(BOLD, 34)
        probe = ImageDraw.Draw(self.bg)
        self.title_lines = wrap(spec["hook"], self.f_title, W - 160, probe)
        self.hook_lines = wrap(spec["hook"], self.f_hook, W - 140, probe)
        self.cards = []
        for p in self.points:
            tl = wrap(p["title"], self.f_ctitle, W - 300, probe)
            xl = wrap(p.get("text", ""), self.f_ctext, W - 300, probe)
            self.cards.append((tl, xl, 44 + len(tl) * 62 + len(xl) * 54 + 40))

    def draw_stars(self, d, t):
        for x, y, r, ph in self.stars:
            yy = (y - t * 12) % H
            a = 0.45 + 0.4 * math.sin(t * 2 + ph)
            c = int(255 * a)
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(c, c, min(255, c + 20)))

    def chip(self, d, cx, y, alpha=1.0):
        w = d.textlength(self.cat_label, font=self.f_chip) + 80
        x = cx - w / 2
        d.rounded_rectangle((x, y, x + w, y + 64), 32, fill=tuple(int(c * 0.28) for c in self.accent),
                            outline=self.accent, width=3)
        d.ellipse((x + 26, y + 24, x + 42, y + 40), fill=self.accent)
        d.text((x + 54, y + 10), self.cat_label, font=self.f_chip, fill=WHITE)

    def paste_box(self, img, cx, cy, scale):
        if scale <= 0.01: return
        s = int(600 * scale)
        b = self.box.resize((s, s), Image.LANCZOS)
        img.paste(b, (int(cx - s / 2), int(cy - s / 2)), b)

    def frame(self, t):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        self.draw_stars(d, t)
        sp = self.spec

        if t < self.t_hook:                                     # ---- hook scene
            k = ease(t / 0.6)
            self.paste_box(img, W / 2, 620, 1.05 * back(t / 0.7))
            d = ImageDraw.Draw(img)
            self.chip(d, W / 2, 230)
            y = 1020 + (1 - k) * 80
            for ln in self.hook_lines:
                tw = d.textlength(ln, font=self.f_hook)
                d.text(((W - tw) / 2, y), ln, font=self.f_hook, fill=WHITE if k > 0.2 else SOFT)
                y += 112
            d.rounded_rectangle((W / 2 - 90, y + 30, W / 2 + 90, y + 40), 5, fill=GOLD)
        else:                                                   # ---- cards / takeaway
            self.chip(d, W / 2, 150)
            y = 250
            for ln in self.title_lines:
                tw = d.textlength(ln, font=self.f_title)
                d.text(((W - tw) / 2, y), ln, font=self.f_title, fill=WHITE)
                y += 70
            total = sum(c[2] for c in self.cards) + 30 * (len(self.cards) - 1)
            y = max(y + 50, y + 50 + (H - 260 - (y + 50) - total) / 2)
            in_take = t >= self.t_end
            for i, (tl, xl, ch) in enumerate(self.cards):
                start = self.t_hook + i * self.slot
                if t < start: break
                k = ease((t - start) / 0.5)
                active = (not in_take) and t < start + self.slot
                x0 = 70 + (1 - k) * 300
                fill = (255, 255, 255) if active else (44, 36, 92)
                d.rounded_rectangle((x0, y, x0 + W - 140, y + ch), 34, fill=fill,
                                    outline=self.accent if active else (80, 70, 140), width=4)
                d.ellipse((x0 + 34, y + 36, x0 + 102, y + 104), fill=self.accent)
                num = str(i + 1); nw = d.textlength(num, font=self.f_num)
                d.text((x0 + 68 - nw / 2, y + 42), num, font=self.f_num, fill=(20, 16, 50))
                ty = y + 34
                for ln in tl:
                    d.text((x0 + 130, ty), ln, font=self.f_ctitle, fill=(20, 16, 50) if active else WHITE)
                    ty += 62
                for ln in xl:
                    d.text((x0 + 130, ty), ln, font=self.f_ctext, fill=(70, 70, 100) if active else SOFT)
                    ty += 54
                y += ch + 30
            if in_take:                                         # ---- takeaway + CTA
                k = ease((t - self.t_end) / 0.6)
                ov = Image.new("RGBA", (W, H), (10, 8, 34, int(248 * k)))
                img.paste(ov, (0, 0), ov)
                d = ImageDraw.Draw(img)
                self.paste_box(img, W / 2, 680, 0.8 * back((t - self.t_end) / 0.7))
                d = ImageDraw.Draw(img)
                lines = wrap(sp["takeaway"], self.f_take, W - 160, d)
                ty = 1020 + (1 - k) * 60
                for ln in lines:
                    tw = d.textlength(ln, font=self.f_take)
                    d.text(((W - tw) / 2, ty), ln, font=self.f_take, fill=GOLD)
                    ty += 78
                kc = ease((t - self.t_end - 1.2) / 0.5)
                if kc > 0:
                    cta = sp.get("cta", "Follow karo, roz kuch naya seekho")
                    bw = d.textlength(cta, font=self.f_cta) + 120
                    by = ty + 80
                    pulse = 1 + 0.03 * math.sin(t * 6)
                    bx0, bx1 = W / 2 - bw / 2 * pulse, W / 2 + bw / 2 * pulse
                    d.rounded_rectangle((bx0, by, bx1, by + 100), 50, fill=self.accent)
                    tw = d.textlength(cta, font=self.f_cta)
                    d.text(((W - tw) / 2, by + 24), cta, font=self.f_cta, fill=(15, 12, 40))

        # brand footer + progress bar
        bt = "CuriosityBox"; bw = d.textlength(bt, font=self.f_brand)
        d.text(((W - bw) / 2, H - 150), bt, font=self.f_brand, fill=MUTED)
        d.rectangle((0, H - 16, int(W * t / DUR), H), fill=self.accent)
        return img


def music(path):
    """Soft original ambient pad with a gentle pulse (no copyright issues)."""
    sr = 44100; n = sr * DUR
    chords = [(196.0, 246.94, 293.66), (164.81, 196.0, 246.94),
              (174.61, 220.0, 261.63), (146.83, 185.0, 220.0)]
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        buf = bytearray()
        for i in range(n):
            t = i / sr; ch = chords[int(t / 4) % 4]
            s = sum(math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t) for f in ch) / 3 * 0.09
            beat = t % 0.75
            s += math.sin(2 * math.pi * 880 * t) * math.exp(-beat * 30) * 0.04
            s *= min(1, t / 1.5, (DUR - t) / 1.5)
            buf += struct.pack("<h", int(max(-1, min(1, s)) * 32767))
        w.writeframes(bytes(buf))


def main(spec_path, out):
    global DUR
    spec = json.load(open(spec_path))
    DUR = int(max(20, min(30, spec.get("duration", 25))))
    r = Renderer(spec)
    music(out + ".wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "24",
                          "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for i in range(FPS * DUR):
        p.stdin.write(r.frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    os.remove(out + ".wav")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
