#!/usr/bin/env python3
"""Render a 20-30 s 1080x1920 "hand-written notes" coding Short from a JSON spec.

A pencil writes everything onto paper in real time: title, sketchy boxes, numbered
headings and code (letter by letter), ending as a full sketch-note cheat sheet.

Usage: python3 make_handwritten.py spec.json out.mp4

spec = {
  "label": "Go tip",                                   # small tag top-left
  "title": ["Build a ", "Web API", " in Go"],          # title parts; odd parts are coloured
  "subtitle": "No framework needed!",                  # highlighter line under the title
  "sections": [                                         # 2-3 panels
    {"heading": "Start a server", "tag": "",            # optional small sticker, e.g. "Go 1.22+"
     "code": ["line", "..."]}                           # <= 7 lines, <= 34 chars each
  ],
  "takeaway": "Go's standard library is enough!",
  "cta": "Follow CareerWithCode",
  "duration": 28                                        # 20-30 s
}
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
HAND_B = os.path.join(HERE, "fonts", "Kalam-Bold.ttf")
HAND = os.path.join(HERE, "fonts", "Kalam-Regular.ttf")
F = lambda p, s: ImageFont.truetype(p, s)

PAPER = (253, 251, 245); INK = (34, 38, 62); GRAY = (120, 126, 140)
BLUE = (28, 120, 230); RED = (226, 58, 70); GREEN = (22, 150, 80); PURPLE = (118, 70, 210)
ORANGE = (214, 100, 20); YELLOW_HL = (255, 225, 70, 150); PINK_HL = (255, 170, 190, 120)
PANEL_COLS = [(250, 120, 110), (150, 120, 240), (70, 190, 120), (80, 160, 240)]
NUM_FILL = [(255, 214, 210), (226, 216, 255), (206, 242, 220), (210, 230, 255)]
KEYWORDS = {"func", "type", "struct", "return", "package", "import", "var", "const", "if", "else",
            "for", "range", "go", "defer", "map", "chan", "nil", "true", "false", "def", "in",
            "print", "class", "None", "True", "False", "let", "async", "await"}
TYPES = {"int", "string", "bool", "error", "float64", "byte", "rune", "any"}

CPS = 30.0          # characters written per second (time-lapse handwriting)


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def tokens(line):
    out, i = [], 0
    while i < len(line):
        c = line[i]
        if line[i:i + 2] == "//" or c == "#":
            out.append((line[i:], GRAY)); break
        if c in "\"'`":
            j = line.find(c, i + 1); j = len(line) - 1 if j == -1 else j
            out.append((line[i:j + 1], ORANGE)); i = j + 1; continue
        if c.isdigit():
            j = i
            while j < len(line) and line[j].isdigit(): j += 1
            out.append((line[i:j], RED)); i = j; continue
        if c.isalpha() or c == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"): j += 1
            w = line[i:j]
            col = PURPLE if w in KEYWORDS else BLUE if (w in TYPES or (j < len(line) and line[j] == "(")) else INK
            out.append((w, col)); i = j; continue
        out.append((c, INK)); i += 1
    chars = []
    for txt, col in out:
        chars += [(ch, col) for ch in txt]
    return chars


def wobble_path(pts, rng, amp=2.2, step=14):
    """Densify a polyline and add hand jitter."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / step))
        for k in range(n):
            f = k / n
            out.append((x0 + (x1 - x0) * f + rng.uniform(-amp, amp), y0 + (y1 - y0) * f + rng.uniform(-amp, amp)))
    out.append(pts[-1])
    return out


def rect_path(x0, y0, x1, y1, rng, r=26):
    pts = []
    for a in range(180, 271, 15): pts.append((x0 + r + r * math.cos(math.radians(a)), y0 + r + r * math.sin(math.radians(a))))
    for a in range(270, 361, 15): pts.append((x1 - r + r * math.cos(math.radians(a)), y0 + r + r * math.sin(math.radians(a))))
    for a in range(0, 91, 15): pts.append((x1 - r + r * math.cos(math.radians(a)), y1 - r + r * math.sin(math.radians(a))))
    for a in range(90, 181, 15): pts.append((x0 + r + r * math.cos(math.radians(a)), y1 - r + r * math.sin(math.radians(a))))
    pts.append((pts[0][0] + 18, pts[0][1] - 4))       # hand-drawn overshoot
    return wobble_path(pts, rng)


def circle_path(cx, cy, r, rng):
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-100, 290, 12)]
    return wobble_path(pts, rng, amp=1.5, step=10)


def plen(path):
    return [0.0] + list(np.cumsum([math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]))


# ---------------- items ----------------
class Item:
    dur = 0.5
    def draw(self, d, img, f): ...
    def pen(self, f): return None


class Stroke(Item):
    def __init__(self, path, color, width, dur):
        self.path, self.color, self.width, self.dur = path, color, width, dur
        self.L = plen(path)
    def _cut(self, f):
        target = self.L[-1] * f
        i = int(np.searchsorted(self.L, target))
        return self.path[:max(2, min(len(self.path), i + 1))]
    def draw(self, d, img, f):
        pts = self._cut(f)
        d.line(pts, fill=self.color, width=self.width, joint="curve")
    def pen(self, f):
        return self._cut(f)[-1]


class Highlight(Item):
    def __init__(self, box, color, dur=0.35):
        self.box, self.color, self.dur = box, color, dur
    def draw(self, d, img, f):
        x0, y0, x1, y1 = self.box
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((x0, y0, x0 + (x1 - x0) * f, y1), 10, fill=self.color)
        img.alpha_composite(layer)
    def pen(self, f):
        x0, y0, x1, y1 = self.box
        return (x0 + (x1 - x0) * f, (y0 + y1) / 2)


class Text(Item):
    """Writes chars one by one. mono=advance in px for monospace layout, else proportional."""
    def __init__(self, x, y, chars, font, mono=None):
        self.x, self.y, self.chars, self.font, self.mono = x, y, chars, font, mono
        self.dur = max(0.15, len([c for c, _ in chars if c != " "]) / CPS)
        self.pos, cx = [], x
        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        lead = True
        for ch, _ in chars:
            self.pos.append(cx)
            # keep indentation monospaced, write the rest naturally (no gaps inside words)
            if mono and lead and ch == " ": cx += mono
            else:
                lead = False
                cx += probe.textlength(ch, font=font)
        self.end = cx
        self.asc = font.getbbox("Ag")[3]
    def draw(self, d, img, f):
        n = len(self.chars)
        k = f * n
        full = int(k)
        for i in range(min(full, n)):
            ch, col = self.chars[i]
            d.text((self.pos[i], self.y), ch, font=self.font, fill=col)
        if full < n and k - full > 0:
            ch, col = self.chars[full]
            l, t, r, b = [int(round(v)) for v in d.textbbox((self.pos[full], self.y), ch, font=self.font)]
            if r > l:
                tile = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
                ImageDraw.Draw(tile).text((self.pos[full] - l + 2, self.y - t + 2), ch, font=self.font, fill=col)
                cw = max(1, int(tile.width * (k - full)))
                img.alpha_composite(tile.crop((0, 0, cw, tile.height)), (int(l - 2), int(t - 2)))
    def pen(self, f):
        n = len(self.chars); k = min(n - 1e-6, f * n); i = int(k)
        x = self.pos[i] + ((self.pos[i + 1] if i + 1 < n else self.end) - self.pos[i]) * (k - i)
        return (x, self.y + self.asc * 0.75 + 6 * math.sin(f * 40))


class Pause(Item):
    def __init__(self, dur): self.dur = dur
    def draw(self, d, img, f): pass


# ---------------- layout ----------------
def build(spec, dur_target):
    rng = random.Random(7)
    items = []
    f_title = F(HAND_B, 84); f_sub = F(HAND_B, 46); f_label = F(HAND_B, 34)
    f_head = F(HAND_B, 48); f_num = F(HAND_B, 44); f_tag = F(HAND_B, 30)
    f_code = F(HAND, 40); adv = 19.5; lh = 48
    f_take = F(HAND_B, 46); f_cta = F(HAND_B, 48)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    # label tag
    label = spec.get("label", "Coding tip")
    lw = probe.textlength(label, font=f_label) + 44
    items.append(Stroke(rect_path(50, 52, 50 + lw, 112, rng, r=20), RED, 4, 0.35))
    items.append(Text(72, 58, [(c, RED) for c in label], f_label))

    # title (centered, parts alternate ink / blue)
    parts = spec["title"]
    chars = []
    for i, p in enumerate(parts):
        chars += [(c, BLUE if i % 2 else INK) for c in p]
    tw = probe.textlength("".join(parts), font=f_title)
    if tw > W - 100:
        f_title = F(HAND_B, int(84 * (W - 100) / tw)); tw = probe.textlength("".join(parts), font=f_title)
    tx = (W - tw) / 2
    items.append(Text(tx, 130, chars, f_title))
    # wavy underline under coloured part
    items.append(Stroke(wobble_path([(tx + 10, 252), (tx + tw - 10, 248)], rng, amp=3), RED, 6, 0.35))
    sub = spec.get("subtitle", "")
    if sub:
        sw = probe.textlength(sub, font=f_sub)
        sx = (W - sw) / 2
        items.append(Highlight((sx - 16, 278, sx + sw + 16, 340), YELLOW_HL))
        items.append(Text(sx, 274, [(c, INK) for c in sub], f_sub))

    # panels
    y = 380
    secs = spec["sections"][:3]
    for si, s in enumerate(secs):
        col = PANEL_COLS[si % len(PANEL_COLS)]
        code = s["code"][:7]
        ph = 94 + len(code) * lh + 28
        x0, x1 = 44, W - 44
        items.append(Stroke(rect_path(x0, y, x1, y + ph, rng), col, 5, 0.55))
        cx, cy = x0 + 58, y + 52
        items.append(Stroke(circle_path(cx, cy, 30, rng), col, 5, 0.25))
        num = str(si + 1); nw = probe.textlength(num, font=f_num)
        items.append(Text(cx - nw / 2, cy - 33, [(num, INK)], f_num))
        hx = x0 + 108
        hw = probe.textlength(s["heading"], font=f_head)
        items.append(Highlight((hx - 10, y + 26, hx + hw + 12, y + 84), YELLOW_HL, 0.3))
        items.append(Text(hx, y + 18, [(c, INK) for c in s["heading"]], f_head))
        if s.get("tag"):
            tg = s["tag"]; tgw = probe.textlength(tg, font=f_tag) + 34
            gx = x1 - tgw - 26
            items.append(Stroke(rect_path(gx, y + 26, gx + tgw, y + 78, rng, r=16), RED, 4, 0.3))
            items.append(Text(gx + 17, y + 30, [(c, RED) for c in tg], f_tag))
        ly = y + 100
        for line in code:
            if line.strip():
                items.append(Text(x0 + 46, ly, tokens(line), f_code, mono=adv))
            ly += lh
        y += ph + 22

    # takeaway + CTA
    take = spec.get("takeaway", "")
    if take:
        tkw = probe.textlength(take, font=f_take)
        if tkw > W - 120:
            f_take = F(HAND_B, int(46 * (W - 120) / tkw)); tkw = probe.textlength(take, font=f_take)
        kx = (W - tkw) / 2
        items.append(Text(kx, y + 4, [(c, GREEN) for c in take], f_take))
        y += 84
    cta = spec.get("cta", "Follow CareerWithCode")
    cw = probe.textlength(cta, font=f_cta)
    bx0 = (W - cw) / 2 - 40; bx1 = (W + cw) / 2 + 40
    items.append(Highlight((bx0, y, bx1, y + 86), PINK_HL, 0.3))
    items.append(Stroke(rect_path(bx0, y, bx1, y + 86, rng, r=30), RED, 5, 0.45))
    items.append(Text((W - cw) / 2, y + 8, [(c, INK) for c in cta], f_cta))
    # little arrow pointing at CTA
    ax = bx1 + 20
    items.append(Stroke(wobble_path([(ax + 60, y - 30), (ax + 10, y + 30), (ax - 4, y + 40)], rng, amp=1.5), INK, 5, 0.25))
    items.append(Stroke(wobble_path([(ax - 4, y + 40), (ax + 22, y + 34)], rng, amp=1), INK, 5, 0.1))
    items.append(Stroke(wobble_path([(ax - 4, y + 40), (ax - 2, y + 14)], rng, amp=1), INK, 5, 0.1))

    # timing: small gaps between items, scale writing speed to fit the target duration
    gap = 0.06
    write = sum(it.dur for it in items) + gap * len(items)
    budget = dur_target - 0.5 - 2.8               # 0.5 s lead-in, >= 2.8 s final hold
    scale = min(1.0, budget / write) if write > 0 else 1.0
    t = 0.5; sched = []
    for it in items:
        it.dur *= scale
        sched.append((t, it)); t += it.dur + gap * scale
    return sched, t, y + 86


# ---------------- pencil ----------------
def pencil(img, x, y, t):
    """Small pencil whose tip sits at (x, y), leaning right."""
    layer = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    L, Wd = 200, 26
    body = [(0, -Wd / 2), (L, -Wd / 2), (L, Wd / 2), (0, Wd / 2)]
    def tr(p, ang=math.radians(-55)):
        px, py = p
        return (20 + px * math.cos(ang) - py * math.sin(ang), 240 + px * math.sin(ang) + py * math.cos(ang))
    tip = [(0, 0), (34, -Wd / 2), (34, Wd / 2)]
    d.polygon([tr(p) for p in [(34, -Wd / 2), (L - 30, -Wd / 2), (L - 30, Wd / 2), (34, Wd / 2)]], fill=(255, 196, 40))
    d.polygon([tr(p) for p in [(34, -2), (L - 30, -2), (L - 30, 4), (34, 4)]], fill=(240, 170, 20))
    d.polygon([tr(p) for p in [(L - 30, -Wd / 2), (L - 14, -Wd / 2), (L - 14, Wd / 2), (L - 30, Wd / 2)]], fill=(190, 196, 206))
    d.polygon([tr(p) for p in [(L - 14, -Wd / 2), (L, -Wd / 2), (L, Wd / 2), (L - 14, Wd / 2)]], fill=(250, 140, 160))
    d.polygon([tr(p) for p in tip], fill=(240, 214, 170))
    d.polygon([tr(p) for p in [(0, 0), (11, -4.5), (11, 4.5)]], fill=INK)
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 40), (0, 0), layer.split()[3])
    img.alpha_composite(shadow, (int(x - 20 + 10), int(y - 240 + 12)))
    img.alpha_composite(layer, (int(x - 20), int(y - 240)))


def paper():
    rng = np.random.default_rng(1)
    base = np.ones((H, W, 3)) * np.array(PAPER)
    base += rng.normal(0, 2.2, (H, W, 1))
    yy = np.linspace(0, 1, H)[:, None, None]
    base -= yy * 6
    img = Image.fromarray(np.clip(base, 0, 255).astype("uint8")).convert("RGBA")
    return img


# ---------------- audio ----------------
SR = 44100


def audio(path, dur, sched):
    n = SR * dur
    t = np.arange(n) / SR
    out = np.zeros(n)
    rng = np.random.default_rng(4)
    # lo-fi chill: Fmaj7 - Em7 - Dm7 - Cmaj7, 82 bpm
    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]
    beat = 60 / 82; bar = beat * 4
    for b in range(int(dur / bar) + 1):
        ch = chords[b % 4]; s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR))
        if s0 >= n: break
        tt = np.arange(s1 - s0) / SR
        env = np.minimum(1, tt / 0.3) * np.exp(-tt * 0.25)
        for m in ch:
            f = 440 * 2 ** ((m - 69) / 12)
            out[s0:s1] += (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * env * 0.045
        f = 440 * 2 ** ((ch[0] - 12 - 69) / 12)
        out[s0:s1] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 1.2) * 0.16
        for q in range(4):
            k0 = int((b * bar + q * beat) * SR)
            if k0 >= n: continue
            kl = min(n - k0, int(0.22 * SR)); kt = np.arange(kl) / SR
            if q in (0, 2):
                out[k0:k0 + kl] += np.sin(2 * np.pi * (90 * np.exp(-kt * 12) + 45) * kt) * np.exp(-kt * 14) * 0.32
            else:
                out[k0:k0 + kl] += rng.standard_normal(kl) * np.exp(-kt * 26) * 0.05
            h0 = k0 + int(beat / 2 * SR); hl = min(max(0, n - h0), int(0.04 * SR))
            if hl: out[h0:h0 + hl] += rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 120) * 0.025
    # vinyl crackle
    crack = (rng.random(n) > 0.9993) * rng.standard_normal(n) * 0.08
    out += crack
    # pencil scratch while writing
    scratch = np.zeros(n)
    for st, it in sched:
        if isinstance(it, Pause): continue
        a, b2 = int(st * SR), min(n, int((st + it.dur) * SR))
        if b2 <= a: continue
        seg = rng.standard_normal(b2 - a)
        seg = np.convolve(seg, np.ones(6) / 6, mode="same")       # soften
        mod = 0.6 + 0.4 * np.abs(np.sin(np.arange(b2 - a) / SR * 2 * np.pi * 7))
        scratch[a:b2] += seg * mod * 0.05
    out += scratch
    out *= np.minimum(1, np.minimum(t / 0.8, (dur - t) / 1.5))
    out /= max(1e-6, np.abs(out).max()) / 0.75
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def main(spec_path, out):
    spec = json.load(open(spec_path))
    dur = int(max(20, min(30, spec.get("duration", 28))))
    sched, t_done, bottom = build(spec, dur)
    if bottom > H - 40:
        print(f"WARNING: content bottom at {bottom}px runs past the frame; shorten the code", file=sys.stderr)
    audio(out + ".wav", dur, sched)
    base = paper()                           # holds finished items
    bd = ImageDraw.Draw(base)
    done = 0
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "22",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    last_pen = (W * 0.75, H * 0.2)
    for fi in range(FPS * dur):
        t = fi / FPS
        while done < len(sched) and t >= sched[done][0] + sched[done][1].dur:
            sched[done][1].draw(bd, base, 1.0); done += 1
        img = base.copy()
        pen = None
        if done < len(sched):
            st, it = sched[done]
            if t >= st:
                f = (t - st) / it.dur
                it.draw(ImageDraw.Draw(img), img, f)
                pen = it.pen(f)
            else:                                               # travelling to next item
                nxt = it.pen(0.0) or last_pen
                k = ease(1 - (st - t) / 0.06) if st - t < 0.06 else 0
                pen = (last_pen[0] + (nxt[0] - last_pen[0]) * k, last_pen[1] + (nxt[1] - last_pen[1]) * k)
        if pen: last_pen = pen
        if t < t_done + 0.6:                                    # pencil leaves after writing
            k = ease((t - t_done) / 0.6) if t > t_done else 0
            px, py = last_pen if pen is None else pen
            pencil(img, px + k * 500, py + k * 300, t)
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    os.remove(out + ".wav")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
