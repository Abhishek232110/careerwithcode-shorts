#!/usr/bin/env python3
"""Render a 20-30 second 1080x1920 CuriosityBox Short (light theme) from a JSON spec.

Usage: python3 make_short.py spec.json out.mp4

spec = {
  "category": "whatif",                     # ai | whatif | paisa | kahani | facts (colour + chip)
  "hook": "Agar Earth Ghoomna Band Kar De Toh?",   # big question, <= 7 words, Hinglish
  "highlight": "Band",                      # optional: one word of the hook to mark in colour
  "teaser": "No. 3 sabse khatarnak hai",    # optional: small line under the hook (<= 6 words)
  "points": [                               # 3 cards (4 max), revealed one by one
    {"title": "<= 5 words", "text": "<= 16 words"}
  ],
  "takeaway": "<= 12 words, the punchline",
  "cta": "Follow karo, roz ek naya sawaal",
  "mood": "epic",                           # motivational | inspiring | epic | mysterious | upbeat
  "duration": 25                            # 20-30 s, more text = longer
}
All text is Hinglish in Latin script (Poppins font). No emoji in the spec: the font can't draw them.
Background music is generated here from scratch for the chosen mood (original, copyright-free).
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
DUR = 25
BOLD = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
MED = os.path.join(HERE, "fonts", "Poppins-Medium.ttf")
REG = os.path.join(HERE, "fonts", "Poppins-Regular.ttf")
F = lambda p, s: ImageFont.truetype(p, s)

INK = (27, 22, 64); INK2 = (88, 84, 120); MUTED = (140, 136, 165)
CATS = {
    "ai":     ("AI & Tech",      (37, 132, 235)),
    "whatif": ("What If?",       (124, 77, 255)),
    "paisa":  ("Paisa & Career", (18, 163, 90)),
    "kahani": ("Kahaniyaan",     (232, 108, 18)),
    "facts":  ("Amazing Facts",  (226, 62, 130)),
}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


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
    top, bot = (255, 250, 240), mix((255, 255, 255), accent, 0.10)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=mix(top, bot, y / H))
    # dotted grid for texture
    dot = mix(bot, accent, 0.18)
    for y in range(40, H, 60):
        for x in range(40, W, 60):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=dot)
    return img


class Renderer:
    def __init__(self, spec):
        self.spec = spec
        self.cat_label, self.accent = CATS.get(spec.get("category", "facts"), CATS["facts"])
        self.soft = mix((255, 255, 255), self.accent, 0.14)
        self.bg = background(self.accent)
        r = random.Random(5)
        self.blobs = [(r.uniform(0, W), r.uniform(0, H), r.uniform(160, 300), r.uniform(0, 6.28),
                       r.choice([self.accent, (255, 196, 61), (255, 122, 160)])) for _ in range(5)]
        self.sparks = [(r.uniform(60, W - 60), r.uniform(100, H - 200), r.uniform(10, 20), r.uniform(0, 6.28))
                       for _ in range(14)]
        self.box = Image.open(os.path.join(HERE, "assets", "box.png")).convert("RGBA")
        self.points = spec["points"][:4]
        n = len(self.points)
        self.t_hook = 3.4
        self.t_end = DUR - 5.5
        self.slot = (self.t_end - self.t_hook) / n
        self.f_chip = F(BOLD, 34); self.f_hook = F(BOLD, 100); self.f_teaser = F(MED, 42)
        self.f_title = F(BOLD, 58); self.f_ctitle = F(BOLD, 50); self.f_ctext = F(REG, 40)
        self.f_num = F(BOLD, 42); self.f_take = F(BOLD, 62); self.f_cta = F(BOLD, 42)
        self.f_brand = F(BOLD, 34); self.f_count = F(BOLD, 30)
        probe = ImageDraw.Draw(self.bg)
        self.hook_lines = wrap(spec["hook"], self.f_hook, W - 130, probe)
        self.title_lines = wrap(spec["hook"], self.f_title, W - 160, probe)
        self.cards = []
        for p in self.points:
            tl = wrap(p["title"], self.f_ctitle, W - 310, probe)
            xl = wrap(p.get("text", ""), self.f_ctext, W - 310, probe)
            self.cards.append((tl, xl, 48 + len(tl) * 62 + len(xl) * 54 + 44))
        self.hl = (spec.get("highlight") or "").lower().strip("?!.,")

    # ---------- decorations ----------
    def deco(self, img, t):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = ImageDraw.Draw(layer)
        for x, y, r, ph, col in self.blobs:
            xx = x + 60 * math.sin(t * 0.4 + ph); yy = y + 80 * math.cos(t * 0.3 + ph)
            g.ellipse((xx - r, yy - r, xx + r, yy + r), fill=col + (38,))
        layer = layer.filter(ImageFilter.GaussianBlur(70))
        img.paste(layer, (0, 0), layer)
        d = ImageDraw.Draw(img)
        for x, y, s, ph in self.sparks:
            k = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
            ss = s * (0.6 + 0.6 * k); yy = (y - t * 18) % (H - 200) + 100
            col = mix((255, 255, 255), self.accent, 0.35 + 0.4 * k)
            d.polygon([(x, yy - ss), (x + ss * 0.3, yy - ss * 0.3), (x + ss, yy), (x + ss * 0.3, yy + ss * 0.3),
                       (x, yy + ss), (x - ss * 0.3, yy + ss * 0.3), (x - ss, yy), (x - ss * 0.3, yy - ss * 0.3)],
                      fill=col)

    def shadow_box(self, img, box, radius, alpha=40, off=14):
        x0, y0, x1, y1 = [int(v) for v in box]
        pad = 40
        sh = Image.new("RGBA", (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad, pad + x1 - x0, pad + y1 - y0), radius,
                                             fill=self.accent + (alpha,))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        img.paste(sh, (x0 - pad, y0 - pad + off), sh)

    def chip(self, d, cx, y):
        w = d.textlength(self.cat_label, font=self.f_chip) + 84
        x = cx - w / 2
        d.rounded_rectangle((x, y, x + w, y + 66), 33, fill=self.accent)
        d.ellipse((x + 26, y + 25, x + 42, y + 41), fill=(255, 255, 255))
        d.text((x + 54, y + 11), self.cat_label, font=self.f_chip, fill=(255, 255, 255))

    def paste_box(self, img, cx, cy, scale, wobble=0.0):
        if scale <= 0.01: return
        s = int(600 * scale)
        b = self.box.resize((s, s), Image.LANCZOS)
        if wobble: b = b.rotate(wobble, resample=Image.BICUBIC)
        img.paste(b, (int(cx - s / 2), int(cy - s / 2)), b)

    def hook_text(self, d, lines, font, y, lh, k):
        for ln in lines:
            words = ln.split(" ")
            widths = [d.textlength(w, font=font) for w in words]
            space = d.textlength(" ", font=font)
            x = (W - (sum(widths) + space * (len(words) - 1))) / 2
            for w, wd in zip(words, widths):
                if self.hl and w.lower().strip("?!.,") == self.hl:
                    hk = ease((k - 0.4) / 0.6)
                    if hk > 0:
                        d.rounded_rectangle((x - 14, y + 18, x - 14 + (wd + 28) * hk, y + lh - 6), 18,
                                            fill=mix((255, 255, 255), self.accent, 0.30))
                    d.text((x, y), w, font=font, fill=self.accent)
                else:
                    d.text((x, y), w, font=font, fill=INK)
                x += wd + space
            y += lh
        return y

    # ---------- frame ----------
    def frame(self, t):
        img = self.bg.copy()
        self.deco(img, t)
        d = ImageDraw.Draw(img)
        sp = self.spec

        if t < self.t_hook:                                     # hook scene
            k = ease(t / 0.7)
            self.paste_box(img, W / 2, 610, 1.08 * back(t / 0.75), wobble=4 * math.sin(t * 5) * (1 - k * 0.6))
            d = ImageDraw.Draw(img)
            self.chip(d, W / 2, 210)
            y = 1000 + (1 - k) * 90
            y = self.hook_text(d, self.hook_lines, self.f_hook, y, 122, t / 1.2)
            if sp.get("teaser"):
                kt = ease((t - 1.2) / 0.5)
                if kt > 0:
                    tw = d.textlength(sp["teaser"], font=self.f_teaser) + 70
                    ty = y + 40
                    d.rounded_rectangle(((W - tw) / 2, ty, (W + tw) / 2, ty + 76), 38,
                                        fill=(255, 255, 255), outline=self.accent, width=3)
                    d.text(((W - tw) / 2 + 35, ty + 12), sp["teaser"], font=self.f_teaser, fill=INK)
        else:
            self.chip(d, W / 2, 140)
            y = 240
            for ln in self.title_lines:
                tw = d.textlength(ln, font=self.f_title)
                d.text(((W - tw) / 2, y), ln, font=self.f_title, fill=INK)
                y += 72
            total = sum(c[2] for c in self.cards) + 32 * (len(self.cards) - 1)
            y = max(y + 50, y + 50 + (H - 280 - (y + 50) - total) / 2)
            in_take = t >= self.t_end
            shown = 0
            for i, (tl, xl, ch) in enumerate(self.cards):
                start = self.t_hook + i * self.slot
                if t < start: break
                shown = i + 1
                k = ease((t - start) / 0.45)
                active = (not in_take) and t < start + self.slot
                x0 = 70 + (1 - k) * 260
                box = (x0, y, x0 + W - 140, y + ch)
                if active: self.shadow_box(img, box, 34)
                d = ImageDraw.Draw(img)
                d.rounded_rectangle(box, 34, fill=(255, 255, 255) if active else self.soft,
                                    outline=self.accent if active else mix(self.soft, self.accent, 0.25),
                                    width=4 if active else 2)
                d.rounded_rectangle((x0, y + 26, x0 + 10, y + ch - 26), 5, fill=self.accent)
                d.ellipse((x0 + 36, y + 38, x0 + 106, y + 108), fill=self.accent)
                num = str(i + 1); nw = d.textlength(num, font=self.f_num)
                d.text((x0 + 71 - nw / 2, y + 44), num, font=self.f_num, fill=(255, 255, 255))
                ty = y + 36
                for ln in tl:
                    d.text((x0 + 136, ty), ln, font=self.f_ctitle, fill=INK); ty += 62
                for ln in xl:
                    d.text((x0 + 136, ty), ln, font=self.f_ctext, fill=INK2); ty += 54
                y += ch + 32
            if not in_take and shown:                           # "2/3" counter
                txt = f"{shown}/{len(self.cards)}"
                tw = d.textlength(txt, font=self.f_count)
                d.text((W - 90 - tw, 160), txt, font=self.f_count, fill=MUTED)
            if in_take:                                         # takeaway + CTA
                k = ease((t - self.t_end) / 0.5)
                ov = Image.new("RGBA", (W, H), mix((255, 255, 255), self.accent, 0.08) + (int(250 * k),))
                img.paste(ov, (0, 0), ov)
                self.deco(img, t) if k > 0.95 else None
                self.paste_box(img, W / 2, 660, 0.85 * back((t - self.t_end) / 0.7))
                d = ImageDraw.Draw(img)
                lines = wrap(sp["takeaway"], self.f_take, W - 160, d)
                ty = 1010 + (1 - k) * 60
                for ln in lines:
                    tw = d.textlength(ln, font=self.f_take)
                    d.text(((W - tw) / 2, ty), ln, font=self.f_take, fill=INK)
                    ty += 82
                kc = ease((t - self.t_end - 1.0) / 0.5)
                if kc > 0:
                    cta = sp.get("cta", "Follow karo, roz kuch naya seekho")
                    pulse = 1 + 0.035 * math.sin(t * 6)
                    bw = (d.textlength(cta, font=self.f_cta) + 130) * pulse
                    by = ty + 70
                    btn = (W / 2 - bw / 2, by, W / 2 + bw / 2, by + 104)
                    self.shadow_box(img, btn, 52, alpha=70)
                    d = ImageDraw.Draw(img)
                    d.rounded_rectangle(btn, 52, fill=self.accent)
                    tw = d.textlength(cta, font=self.f_cta)
                    d.text(((W - tw) / 2, by + 24), cta, font=self.f_cta, fill=(255, 255, 255))

        bt = "CuriosityBox"; bw = d.textlength(bt, font=self.f_brand)
        d.text(((W - bw) / 2, H - 150), bt, font=self.f_brand, fill=MUTED)
        d.rectangle((0, H - 16, int(W * t / DUR), H), fill=self.accent)
        return img


# ---------------- music ----------------
SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
MOODS = {
    #            bpm  chords (root, minor?)                                       drums
    "motivational": (104, [("C", 0), ("G", 0), ("A", 1), ("F", 0)], "drive"),
    "inspiring":    (84,  [("A", 1), ("F", 0), ("C", 0), ("G", 0)], "soft"),
    "epic":         (90,  [("A", 1), ("F", 0), ("C", 0), ("G", 0)], "tom"),
    "mysterious":   (72,  [("A", 1), ("D", 1), ("A", 1), ("E", 0)], "tick"),
    "upbeat":       (118, [("C", 0), ("A", 1), ("F", 0), ("G", 0)], "bounce"),
}


def freq(semi_from_a4):
    return 440.0 * 2 ** (semi_from_a4 / 12)


def chord_notes(root, minor, octave=4):
    base = NOTE[root] - 9 + (octave - 4) * 12      # semitones from A4
    return [base, base + (3 if minor else 4), base + 7]


def tone(f, n, kind="sine", decay=None):
    t = np.arange(n) / SR
    if kind == "pluck":
        w = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)
    elif kind == "pad":
        w = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-0.003, 0, 0.003)) / 3
    else:
        w = np.sin(2 * np.pi * f * t)
    if decay: w *= np.exp(-t * decay)
    return w


def music(path, mood):
    bpm, prog, drums = MOODS.get(mood, MOODS["inspiring"])
    n = SR * DUR
    out = np.zeros(n)
    beat = 60.0 / bpm
    bar = beat * 4
    rng = np.random.default_rng(3)

    def add(sig, at, gain):
        i = int(at * SR)
        if i >= n: return
        seg = sig[: n - i]
        out[i:i + len(seg)] += seg * gain

    t0 = 0.0; ci = 0
    while t0 < DUR:
        root, minor = prog[ci % len(prog)]
        notes = chord_notes(root, minor)
        bl = int(bar * SR)
        for s in notes:                                           # pad
            add(tone(freq(s - 12), bl, "pad") * np.minimum(1, np.arange(bl) / (SR * 0.4)), t0, 0.07)
        add(tone(freq(notes[0] - 24), bl, "sine", decay=0.6), t0, 0.22)   # bass
        step = beat / 2
        arp = notes + [notes[0] + 12]
        for j in range(8):                                        # arpeggio / pluck
            if drums == "tick" and j % 2: continue
            s = arp[j % len(arp)] + (12 if drums in ("drive", "bounce", "soft") else 0)
            add(tone(freq(s), int(step * SR * 1.5), "pluck", decay=7), t0 + j * step,
                0.07 if drums != "soft" else 0.09)
        for b in range(4):                                        # drums
            at = t0 + b * beat
            kick = tone(55, int(0.25 * SR), "sine", decay=18) * np.sin(
                2 * np.pi * np.cumsum(np.linspace(120, 45, int(0.25 * SR))) / SR)
            if drums in ("drive", "bounce") or (drums == "soft" and b == 0) or (drums == "tom" and b in (0, 2)):
                add(kick, at, 0.45 if drums != "soft" else 0.25)
            if drums in ("drive", "bounce") and b in (1, 3):
                clap = rng.standard_normal(int(0.18 * SR)) * np.exp(-np.arange(int(0.18 * SR)) / SR * 30)
                add(clap, at, 0.10)
            if drums in ("drive", "bounce", "tick"):
                hat = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90)
                add(hat, at + beat / 2, 0.05 if drums != "tick" else 0.07)
            if drums == "tom" and b == 3:
                for q in range(3):
                    add(tone(110 - q * 15, int(0.2 * SR), "sine", decay=14), at + q * beat / 3, 0.25)
        t0 += bar; ci += 1
    # gentle build (louder after the hook) + fades
    tt = np.arange(n) / SR
    out *= 0.75 + 0.25 * np.clip((tt - 3) / 6, 0, 1)
    out *= np.minimum(1, np.minimum(tt / 1.2, (DUR - tt) / 1.8))
    out /= max(1e-6, np.abs(out).max()) / 0.8
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def main(spec_path, out):
    global DUR
    spec = json.load(open(spec_path))
    DUR = int(max(20, min(30, spec.get("duration", 25))))
    r = Renderer(spec)
    music(out + ".wav", spec.get("mood", "inspiring"))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for i in range(FPS * DUR):
        p.stdin.write(r.frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    os.remove(out + ".wav")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
