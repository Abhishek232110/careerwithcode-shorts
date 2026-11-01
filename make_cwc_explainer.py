#!/usr/bin/env python3
"""Render a CareerWithCode English explainer Short: content images + English voiceover + captions.

Abhishek (Nov 1 2026): "generate images of the content, then make shorts using these images and
explain in English" (CareerWithCode only). Each scene is one image that SHOWS the topic: a code
editor, a terminal output, a memory/flow diagram or a checklist, inside the CareerWithCode poster
look (dark coding room, white/yellow Kalam headline on yellow/red brush boxes, the cartoon boy in
the "Career With Code" hoodie, red banner, yellow sticky note, CareerWithCode footer).
An English voice explains each image; burned-in captions follow the voice word by word.
The Short is always longer than 30 s (Abhishek's rule) and at most 60 s.

Voice: Kokoro TTS offline, English (default am_michael). Same model files as make_cwc_story.py.

Usage: python3 make_cwc_explainer.py spec.json out.mp4             (video + out.srt captions)
       python3 make_cwc_explainer.py spec.json out.jpg --still      (Facebook image: still_scene)
       python3 make_cwc_explainer.py spec.json outdir --images      (every scene as a PNG)

spec = {
  "voice": "am_michael", "speed": 1.0, "still_scene": 0,
  "scenes": [{
     "title": [{"text": "Python Trap!", "box": "yellow"}, {"text": "b changed a?", "box": "red"}],
     "image": {...},           # what the scene shows, one of:
        # {"type": "code", "file": "main.py", "lines": ["a = [1, 2, 3]", ...],
        #  "highlight": [2], "output": ["[1, 2, 3, 4]"]}            lines type in one by one
        # {"type": "refs", "names": ["a", "b"], "boxes": [["1","2","3"]],
        #  "links": [[0, 0], [1, 0]], "new": [[0, 3]], "label": "One list in memory"}
        #                                                         name tags -> list boxes in memory
        # {"type": "check", "items": ["...", "..."], "kind": "check|cross|steps"}
     "face": "happy|thinking|worried", "palette": "blue|orange|purple",
     "banner": "optional red banner", "note": "optional sticky\\nnote",
     "say": "English sentences the voice speaks over this image."
  }, ...]
}
"""
import json, math, os, random, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_short
import make_cwc_poster as P
from make_cwc_poster import W, H, FPS, WHITE, YELLOW, RED, BLACK, GREEN, ease, back, paste_scaled

SR = 24000
XFADE = 0.3
MONO = os.path.join(HERE, "fonts", "JetBrainsMono-Bold.ttf")
FM = lambda s: ImageFont.truetype(MONO, s)
F = P.F
CARD_W = 1000
CARD_TOP = 0          # set per scene below the headline
SYN = {"kw": (255, 121, 198), "str": (241, 250, 140), "num": (189, 147, 249),
       "com": (98, 114, 164), "fn": (80, 250, 123), "txt": (248, 248, 242)}
KW = set("def return if else elif for while in import from as class not and or is None True False "
         "print len const let var function new public static void int String "
         "func package type struct interface go chan map range defer make append nil fmt".split())


# ---------------------------------------------------------------- content images
def card(w, h, title=None):
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([26, 30, w + 26, h + 30], 30, fill=(0, 0, 0, 140))
    d.rounded_rectangle([20, 20, w + 20, h + 20], 30, fill=(22, 24, 34, 245), outline=(90, 130, 200, 170), width=3)
    if title is not None:
        d.rounded_rectangle([20, 20, w + 20, 100], 30, fill=(40, 42, 56, 255))
        d.rectangle([20, 70, w + 20, 100], fill=(40, 42, 56, 255))
        for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            d.ellipse([52 + 44 * i, 46, 78 + 44 * i, 72], fill=c)
        d.text((200, 38), title, font=FM(34), fill=(200, 205, 220))
    return im, d


def tokens(line):
    out = []
    for m in re.finditer(r"(#.*|//.*)|('[^']*'|\"[^\"]*\")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)(?=\()|([A-Za-z_]\w*)|(\s+|.)", line):
        com, s, num, fn, word, other = m.groups()
        if com: out.append((com, "com"))
        elif s: out.append((s, "str"))
        elif num: out.append((num, "num"))
        elif fn: out.append((fn, "kw" if fn in KW else "fn"))
        elif word: out.append((word, "kw" if word in KW else "txt"))
        else: out.append((other, "txt"))
    return out


def code_image(img, shown):
    """shown = how many code lines are visible (output appears after all lines)."""
    lines, out = img["lines"], img.get("output", [])
    size = 52
    while max(FM(size).getlength(l) for l in lines + out + [""]) > CARD_W - 150 and size > 30:
        size -= 2
    f, lh = FM(size), int(size * 1.55)
    code_h = 120 + lh * len(lines) + 30
    out_h = (70 + lh * len(out) + 30) if out else 0
    im, d = card(CARD_W, code_h + out_h, img.get("file", "main.py"))
    hl = set(img.get("highlight", []))
    for i, ln in enumerate(lines[:shown]):
        y = 20 + 120 + lh * i
        if i in hl:
            d.rounded_rectangle([34, y - 8, CARD_W + 6, y + lh - 14], 12, fill=(255, 212, 0, 55), outline=YELLOW + (255,), width=3)
        d.text((44, y), str(i + 1), font=FM(int(size * 0.8)), fill=(98, 114, 164))
        x = 110
        for tok, kind in tokens(ln):
            d.text((x, y), tok, font=f, fill=SYN[kind]); x += f.getlength(tok)
    if out and shown > len(lines):
        y0 = 20 + code_h
        d.rectangle([20, y0, CARD_W + 20, y0 + 4], fill=(90, 130, 200, 170))
        d.text((44, y0 + 18), "OUTPUT", font=FM(30), fill=(150, 160, 190))
        for i, ln in enumerate(out):
            d.text((44, y0 + 70 + lh * i), "> " + ln, font=f, fill=GREEN)
    return im


def code_steps(img):
    return len(img["lines"]) + (1 if img.get("output") else 0)


def arrow(d, a, b, color, width=10):
    (x0, y0), (x1, y1) = a, b
    pts = []
    for i in range(31):
        t = i / 30
        cx = x0 + (x1 - x0) * 0.5
        x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * cx + 3 * (1 - t) * t ** 2 * cx + t ** 3 * x1
        y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y0 + 3 * (1 - t) * t ** 2 * y1 + t ** 3 * y1
        pts.append((x, y))
    d.line(pts, fill=color, width=width, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
    L = 34
    d.polygon([(x1, y1), (x1 - L * math.cos(ang - 0.45), y1 - L * math.sin(ang - 0.45)),
               (x1 - L * math.cos(ang + 0.45), y1 - L * math.sin(ang + 0.45))], fill=color)


def refs_image(img, shown):
    """Name tags on the left, list boxes in memory on the right, arrows from names to boxes.
    Steps: names+boxes appear, then each arrow, then the 'new' cells glow."""
    names, boxes, links = img["names"], img["boxes"], img.get("links", [])
    new = {tuple(x) for x in img.get("new", [])}
    cell = 112
    bh = 190
    h = 150 + max(len(names), len(boxes)) * 230 + 40
    im, d = card(CARD_W, h)
    d.text((60, 46), "NAMES", font=FM(36), fill=(150, 160, 190))
    d.text((430, 46), img.get("label", "MEMORY"), font=FM(36), fill=(150, 160, 190))
    d.rounded_rectangle([400, 110, CARD_W - 10, h - 10], 26, outline=(90, 130, 200, 120), width=3)
    tag_pos, box_pos = [], []
    n_rows = max(len(names), len(boxes))
    for i, nm in enumerate(names):
        cy = 150 + (h - 190) * (i + 0.5) / len(names)
        d.rounded_rectangle([50, cy - 55, 250, cy + 55], 22, fill=YELLOW + (255,))
        d.ellipse([66, cy - 12, 90, cy + 12], fill=(22, 24, 34))
        fs = 78
        while FM(fs).getlength(nm) > 130 and fs > 34:
            fs -= 4
        l, t, r, b = FM(fs).getbbox(nm)
        d.text((165 - (r + l) / 2, cy - (b + t) / 2), nm, font=FM(fs), fill=BLACK)
        tag_pos.append((250, cy))
    for j, items in enumerate(boxes):
        cy = 150 + (h - 190) * (j + 0.5) / len(boxes)
        n = len(items)
        x0 = 470
        cw = min(cell, (CARD_W - 60 - x0) // max(1, n))
        d.rounded_rectangle([x0 - 16, cy - bh / 2, x0 + cw * n + 16, cy + bh / 2], 22,
                            fill=(14, 40, 80, 255), outline=(70, 150, 255, 255), width=5)
        for k, it in enumerate(items):
            glow = (j, k) in new
            if glow and shown < len(links) + 2:
                continue
            x = x0 + cw * k
            d.rounded_rectangle([x + 6, cy - 50, x + cw - 6, cy + 50], 14,
                                fill=(255, 212, 0, 255) if glow else (30, 64, 120, 255))
            fs = 60 if len(it) < 3 else 44
            l, t, r, b = FM(fs).getbbox(it)
            d.text((x + cw / 2 - (r + l) / 2, cy - (b + t) / 2), it, font=FM(fs), fill=BLACK if glow else WHITE)
        box_pos.append((x0 - 22, cy))
    colors = [(255, 212, 0, 255), (255, 90, 90, 255), (80, 250, 123, 255)]
    for i, (a, b) in enumerate(links[:max(0, shown - 1)]):
        tx, ty = tag_pos[a]; bx, by = box_pos[b]
        off = (a - (len(names) - 1) / 2) * 40 if len(boxes) == 1 else 0
        arrow(d, (tx + 8, ty), (bx, by + off), colors[a % 3])
    return im


def refs_steps(img):
    return 1 + len(img.get("links", [])) + (1 if img.get("new") else 0)


def check_image(img, shown):
    items, kind = img["items"], img.get("kind", "check")
    rh = 128
    im, d = card(CARD_W, 60 + rh * len(items))
    for i, it in enumerate(items[:shown]):
        cy = 20 + 30 + rh * i + rh // 2; x = 60
        if kind == "cross":
            d.line([(x, cy - 28), (x + 56, cy + 28)], fill=RED, width=14)
            d.line([(x + 56, cy - 28), (x, cy + 28)], fill=RED, width=14)
        elif kind == "steps":
            d.rounded_rectangle([x, cy - 32, x + 64, cy + 32], 12, fill=(60, 70, 90))
            l, t, r, b = F(46).getbbox(str(i + 1))
            d.text((x + 32 - (r + l) / 2, cy - (b + t) / 2), str(i + 1), font=F(46), fill=WHITE)
        else:
            d.rounded_rectangle([x, cy - 32, x + 64, cy + 32], 14, fill=GREEN)
            d.line([(x + 14, cy), (x + 28, cy + 16), (x + 52, cy - 16)], fill=WHITE, width=10, joint="curve")
        mono = any(c in it for c in "()=[]._")
        fs = 54
        fo = FM if mono else F
        while fo(fs).getlength(it) > CARD_W - 190 and fs > 30:
            fs -= 2
        l, t, r, b = fo(fs).getbbox(it)
        d.text((x + 96, cy - (b + t) / 2), it, font=fo(fs), fill=YELLOW if mono else WHITE)
    return im


def table_image(img, shown):
    """Spreadsheet-style table. Rows appear one by one; then `bad` cells/rows get a red mark.
    {"type": "table", "cols": [...], "rows": [[...]], "bad": [[r, c] or [r, -1 for whole row]],
     "good_rows": [r, ...], "file": "sales.csv"}"""
    cols, rows = img["cols"], img["rows"]
    bad = [tuple(x) for x in img.get("bad", [])]
    good = set(img.get("good_rows", []))
    rh = 104
    w = CARD_W
    cw = (w - 60) / len(cols)
    im, d = card(w, 120 + rh * (len(rows) + 1) + 20, img.get("file", "data.csv"))
    y0 = 20 + 110
    d.rectangle([40, y0, w, y0 + rh], fill=(40, 70, 130, 255))
    for c, name in enumerate(cols):
        d.text((50 + cw * c + 14, y0 + 26), name, font=FM(40), fill=WHITE)
    for r, row in enumerate(rows[:shown]):
        y = y0 + rh * (r + 1)
        fill = (32, 34, 46, 255) if r % 2 else (26, 28, 38, 255)
        if r in good:
            fill = (20, 80, 40, 255)
        d.rectangle([40, y, w, y + rh], fill=fill)
        for c, val in enumerate(row):
            d.text((50 + cw * c + 14, y + 26), str(val), font=FM(42), fill=(230, 232, 240))
    if shown > len(rows):
        for r, c in bad:
            y = y0 + rh * (r + 1)
            if c < 0:
                d.rounded_rectangle([44, y + 6, w - 4, y + rh - 6], 12, outline=RED, width=7)
                d.text((w - 210, y + 24), "DUPLICATE", font=FM(34), fill=RED)
            else:
                x = 50 + cw * c
                d.rounded_rectangle([x + 4, y + 6, x + cw - 4, y + rh - 6], 12, outline=RED, width=7)
                d.text((x + 18, y + 24), img.get("blank_label", "BLANK"), font=FM(34), fill=RED)
    for c in range(1, len(cols)):
        d.line([(50 + cw * c, y0), (50 + cw * c, y0 + rh * (min(shown, len(rows)) + 1))], fill=(70, 80, 110), width=2)
    return im


def table_steps(img):
    return len(img["rows"]) + (1 if img.get("bad") else 0)


def flow_image(img, shown):
    """Numbered steps in boxes joined by arrows, two per row (zig-zag).
    {"type": "flow", "steps": [["Collect", "get the data"], ...]}"""
    steps = img["steps"]
    n = len(steps); rows = math.ceil(n / 2)
    bw, bh, gap = 420, 210, 120
    h = 60 + rows * bh + (rows - 1) * gap + 40
    im, d = card(CARD_W, h)
    cols = [(255, 212, 0), (80, 250, 123), (70, 150, 255), (255, 121, 198), (255, 150, 60), (189, 147, 249)]
    pos = []
    for i in range(n):
        r, c = divmod(i, 2)
        if r % 2: c = 1 - c
        x = 60 + c * (bw + 100); y = 60 + r * (bh + gap)
        pos.append((x, y))
    for i in range(min(shown, n)):
        x, y = pos[i]; col = cols[i % len(cols)]
        if i > 0:
            px, py = pos[i - 1]
            if py == y:
                a, b = ((px + bw, y + bh / 2), (x, y + bh / 2)) if px < x else ((px, y + bh / 2), (x + bw, y + bh / 2))
            else:
                a, b = (px + bw / 2, py + bh), (x + bw / 2, y)
            d.line([a, b], fill=(200, 205, 220), width=10)
            ang = math.atan2(b[1] - a[1], b[0] - a[0]); L = 30
            d.polygon([b, (b[0] - L * math.cos(ang - 0.5), b[1] - L * math.sin(ang - 0.5)),
                       (b[0] - L * math.cos(ang + 0.5), b[1] - L * math.sin(ang + 0.5))], fill=(200, 205, 220))
        d.rounded_rectangle([x, y, x + bw, y + bh], 28, fill=(30, 34, 50, 255), outline=col + (255,), width=6)
        d.ellipse([x + 24, y + 24, x + 94, y + 94], fill=col + (255,))
        l, t, r_, b_ = FM(44).getbbox(str(i + 1))
        d.text((x + 59 - (r_ + l) / 2, y + 59 - (b_ + t) / 2), str(i + 1), font=FM(44), fill=BLACK)
        title, sub = steps[i][0], (steps[i][1] if len(steps[i]) > 1 else "")
        fs = 64
        while F(fs).getlength(title) > bw - 130 and fs > 36: fs -= 2
        d.text((x + 112, y + 22), title, font=F(fs), fill=WHITE)
        fs = 40
        while F(fs).getlength(sub) > bw - 50 and fs > 26: fs -= 2
        d.text((x + 28, y + 128), sub, font=F(fs), fill=(190, 195, 215))
    return im


def chart_image(img, shown):
    """Bar chart; bars grow in one by one, `highlight` bar is yellow, others blue.
    {"type": "chart", "title": "Sales this week", "bars": [["Mon", 250], ...], "highlight": 5}"""
    bars = img["bars"]; hi = img.get("highlight", -1)
    h = 760
    im, d = card(CARD_W, h)
    d.text((60, 50), img.get("title", ""), font=F(54), fill=WHITE)
    top, base = 170, h - 60
    left, right = 70, CARD_W - 20
    mx = max(v for _, v in bars) or 1
    bw = (right - left) / len(bars)
    d.line([(left, base), (right, base)], fill=(150, 160, 190), width=4)
    for i, (lab, v) in enumerate(bars):
        x = left + bw * i
        l, t, r, b = FM(34).getbbox(lab)
        d.text((x + bw / 2 - (r + l) / 2, base + 10), lab, font=FM(34), fill=(200, 205, 220))
        if i >= shown:
            continue
        bh = (base - top - 60) * v / mx
        col = YELLOW if i == hi else (70, 150, 255)
        d.rounded_rectangle([x + 14, base - bh, x + bw - 14, base - 2], 10, fill=col)
        s = str(v); l, t, r, b = FM(32).getbbox(s)
        d.text((x + bw / 2 - (r + l) / 2, base - bh - 44), s, font=FM(32), fill=YELLOW if i == hi else WHITE)
    return im


IMAGES = {"code": (code_image, code_steps), "refs": (refs_image, refs_steps),
          "check": (check_image, lambda img: len(img["items"])),
          "table": (table_image, table_steps), "flow": (flow_image, lambda img: len(img["steps"])),
          "chart": (chart_image, lambda img: len(img["bars"]))}


# ---------------------------------------------------------------- captions
def caption_layer(words, active):
    """Up to 2 centred lines of big words; the spoken word is yellow."""
    s = 74; f = F(s)
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and f.getlength(" ".join(words[j] for j in cur + [i])) > 660:
            lines.append(cur); cur = []
        cur.append(i)
    lines.append(cur)
    lh = int(s * 1.3)
    im = Image.new("RGBA", (720, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        text = " ".join(words[j] for j in ln)
        x = (720 - f.getlength(text)) / 2
        for j in ln:
            d.text((x, 10 + lh * li), words[j], font=f, fill=YELLOW if j == active else WHITE,
                   stroke_width=8, stroke_fill=BLACK)
            x += f.getlength(words[j] + " ")
    return im


def chunks(sentence, n=5):
    w = sentence.split()
    k = max(1, math.ceil(len(w) / n)); size = math.ceil(len(w) / k)
    return [w[i:i + size] for i in range(0, len(w), size)]


# ---------------------------------------------------------------- voice
def voice(spec):
    """Synthesize every sentence separately so caption timing is exact per sentence.
    Returns per scene: (audio array, [(start, end, words), ...] caption chunks)."""
    import make_cwc_story as S
    k = S.tts()
    out = []
    for sc in spec["scenes"]:
        parts, caps, t = [], [], 0.25
        for sent in re.split(r"(?<=[.!?])\s+", sc["say"].strip()):
            a, sr = k.create(sent, voice=spec.get("voice", "am_michael"),
                             speed=spec.get("speed", 1.0), lang=spec.get("lang", "en-us"))
            a = np.asarray(a, np.float32)
            nz = np.where(np.abs(a) > 0.01)[0]  # trim silence so captions line up
            if len(nz):
                a = a[max(0, nz[0] - 600): nz[-1] + 1200]
            dur = len(a) / SR
            ch = chunks(sent)
            tot = sum(len(" ".join(c)) for c in ch)
            s = t
            for c in ch:
                e = s + dur * len(" ".join(c)) / tot
                caps.append((s, e, c)); s = e
            parts.append(a); parts.append(np.zeros(int(0.22 * SR), np.float32))
            t += dur + 0.22
        out.append((np.concatenate(parts), caps))
    return out


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, sc, dur, captions=()):
        self.sc, self.dur, self.caps = sc, dur, list(captions)
        rng = random.Random(sc.get("seed", 11))
        self.bg = P.build_background(sc.get("palette", "blue"), rng)
        n = len(sc["title"]); size = {1: 150, 2: 124}.get(n, 104)
        lines = [dict(ln) for ln in sc["title"]]
        self.title = [P.title_line(ln, size, rng) for ln in lines]
        y = 50; self.ty = []
        for im in self.title:
            self.ty.append(y + im.height // 2); y += int(im.height * 0.84)
        self.card_top = y + 10
        draw, steps = IMAGES[sc["image"]["type"]]
        self.n = steps(sc["image"])
        self.stages = [draw(sc["image"], k) for k in range(self.n + 1)]
        # fit the image between the headline and the caption zone
        room_h = 1180 - self.card_top
        st = self.stages[-1]
        self.k = min(1.0, room_h / st.height, (W - 40) / st.width)
        self.card_cy = self.card_top + st.height * self.k / 2
        end = max(1.5, dur * 0.7)
        self.step_t = [0.6 + i * (end - 0.6) / max(1, self.n) for i in range(self.n)]
        if sc.get("reveal"):  # optional explicit seconds for each step
            self.step_t = sc["reveal"][:self.n] + self.step_t[len(sc["reveal"]):]
        self.boy = P.boy(sc.get("face", "happy"))
        self.boy = self.boy.resize((int(self.boy.width * 0.58), int(self.boy.height * 0.58)), Image.LANCZOS)
        self.note = P.sticky_note(sc["note"], rng) if sc.get("note") else None
        self.banner = P.banner_layer(sc["banner"], rng) if sc.get("banner") else None
        self.footer = P.footer_layer()
        self.cap_cache = {}

    def frame(self, t, captions=True):
        img = self.bg.copy()
        k = ease((t - 0.1) / 0.5)
        bob = 5 * math.sin(t * 2.2)
        img.alpha_composite(self.boy, (W - self.boy.width + 20, int(1665 - self.boy.height + (1 - k) * 700 + bob)))
        for i, (im, cy) in enumerate(zip(self.title, self.ty)):
            paste_scaled(img, im, W / 2, cy, back((t - 0.05 - 0.15 * i) / 0.35))
        shown = sum(1 for s in self.step_t if t >= s)
        pop = 1 + 0.025 * max(0.0, 1 - (t - self.step_t[shown - 1]) / 0.3) if shown else 1
        ck = ease((t - 0.25) / 0.4)
        paste_scaled(img, self.stages[shown], W / 2, self.card_cy + (1 - ck) * 120, self.k * pop, ck)
        if self.banner:
            paste_scaled(img, self.banner, W / 2, self.card_cy + self.stages[-1].height * self.k / 2 + 70, back((t - self.dur * 0.55) / 0.4))
        if self.note and not captions:
            paste_scaled(img, self.note, 60 + self.note.width / 2, 1450, back((t - 0.8) / 0.4))
        if captions:
            for s, e, words in self.caps:
                if s <= t < e + 0.15:
                    a = min(len(words) - 1, int((t - s) / max(0.01, e - s) * len(words)))
                    key = (id(words), a)
                    if key not in self.cap_cache:
                        self.cap_cache[key] = caption_layer(words, a)
                    lay = self.cap_cache[key]
                    img.alpha_composite(lay, (20, 1510 - lay.height // 2))
                    break
            else:
                if self.note:
                    paste_scaled(img, self.note, 60 + self.note.width / 2, 1450, 1.0)
        paste_scaled(img, self.footer, W / 2, 1840, ease((t - 0.3) / 0.4))
        return img.convert("RGB")


# ---------------------------------------------------------------- output
def srt_time(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main(spec_path, out):
    spec = json.load(open(spec_path))
    vo = voice(spec)
    lens = [max(4.0, len(a) / SR + 0.5) for a, _ in vo]
    if sum(lens) < 32:
        lens[-1] += 32 - sum(lens)
    total = sum(lens)
    if total > 59.5:
        raise SystemExit(f"voiceover too long ({total:.1f} s); shorten the 'say' lines")
    starts = np.cumsum([0] + lens[:-1])
    scenes = [Scene(sc, d, caps) for sc, d, (_, caps) in zip(spec["scenes"], lens, vo)]

    track = np.zeros(int(SR * total) + SR, np.float32)
    for st, (a, _) in zip(starts, vo):
        i = int(st * SR); track[i:i + len(a)] += a
    track = (track / (np.abs(track).max() or 1) * 0.92 * 32767).astype("<i2")
    with wave.open(out + ".voice.wav", "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(track.tobytes())
    make_short.DUR = int(math.ceil(total))
    make_short.music(out + ".music.wav")

    with open(os.path.splitext(out)[0] + ".srt", "w") as f:
        n = 0
        for st, (_, caps) in zip(starts, vo):
            for s, e, words in caps:
                n += 1
                f.write(f"{n}\n{srt_time(st + s)} --> {srt_time(st + e)}\n{' '.join(words)}\n\n")

    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", out + ".voice.wav", "-i", out + ".music.wav",
                          "-filter_complex", "[2:a]volume=0.16[m];[1:a][m]amix=inputs=2:duration=longest:normalize=0[a]",
                          "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                          "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                          "-t", f"{total:.2f}", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        t = fi / FPS
        i = max(j for j in range(len(starts)) if starts[j] <= t)
        img = scenes[i].frame(t - starts[i])
        if i + 1 < len(scenes) and t > starts[i + 1] - XFADE:
            img = Image.blend(img, scenes[i + 1].frame(0.0), (t - (starts[i + 1] - XFADE)) / XFADE)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    for s in (".voice.wav", ".music.wav"):
        os.remove(out + s)
    print(f"{out}: {total:.1f} s, {len(scenes)} scenes")


def still(sc, path):
    s = Scene(sc, 30)
    s.frame(29.0, captions=False).save(path, quality=92)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[3] == "--still":
        spec = json.load(open(sys.argv[1]))
        still(spec["scenes"][spec.get("still_scene", 0)], sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[3] == "--images":
        spec = json.load(open(sys.argv[1])); os.makedirs(sys.argv[2], exist_ok=True)
        for i, sc in enumerate(spec["scenes"]):
            still(sc, os.path.join(sys.argv[2], f"scene_{i + 1:02}.png"))
    else:
        main(sys.argv[1], sys.argv[2])
