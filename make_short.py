#!/usr/bin/env python3
"""Render a 15-second 1080x1920 coding explainer Short from a JSON spec.

Usage: python3 make_short.py spec.json out.mp4

spec = {
  "hook": "Stop writing loops like this 😅",      # big title, 0-3s
  "language": "Python",
  "before": ["nums = [1, 2, 3, 4]", ...],         # optional "old way" code
  "code": ["squares = [n*n for n in nums]", ...], # main code, typed out
  "output": "[1, 4, 9, 16]",                       # optional result line
  "takeaway": "One line. Same result.",            # explanation, 10-14s
  "cta": "Follow for a coding tip every day"
}
"""
import json, subprocess, sys, math, wave, struct
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 15
BG = (248, 250, 252); PANEL = (255, 255, 255); BORDER = (214, 220, 228)
FG = (31, 35, 40); MUTED = (101, 109, 118)
ACCENT = (9, 105, 218); GREEN = (26, 127, 55); YELLOW = (191, 87, 0)
RED = (207, 34, 46); PURPLE = (130, 80, 223); ORANGE = (188, 76, 0)
GRID = (236, 240, 245); BADGE = (221, 235, 255); OUTBG = (230, 246, 234)
LANG_COLORS = {"python": (55, 118, 171), "go": (0, 150, 190), "javascript": (200, 160, 0),
               "java": (176, 114, 25), "sql": (100, 90, 200), "c++": (0, 89, 156)}

SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F = lambda p, s: ImageFont.truetype(p, s)

KEYWORDS = {"def", "return", "for", "in", "if", "else", "elif", "while", "import",
            "from", "class", "const", "let", "var", "function", "new", "await",
            "async", "print", "lambda", "and", "or", "not", "True", "False", "None",
            "null", "true", "false", "console", "=>"}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def wrap(text, font, width, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= width: cur = test
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def tokens(line):
    """Very small syntax highlighter -> [(text, color)]."""
    out, i = [], 0
    while i < len(line):
        c = line[i]
        if c == "#" or line[i:i+2] == "//":
            out.append((line[i:], MUTED)); break
        if c in "\"'`":
            j = line.find(c, i + 1); j = len(line) - 1 if j == -1 else j
            out.append((line[i:j+1], GREEN)); i = j + 1; continue
        if c.isdigit():
            j = i
            while j < len(line) and (line[j].isdigit() or line[j] == "."): j += 1
            out.append((line[i:j], ORANGE)); i = j; continue
        if c.isalpha() or c == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"): j += 1
            word = line[i:j]
            col = PURPLE if word in KEYWORDS else (ACCENT if j < len(line) and line[j] == "(" else FG)
            out.append((word, col)); i = j; continue
        out.append((c, RED if c in "=+-*/<>%" else FG)); i += 1
    return out


def draw_code(d, lines, x, y, font, chars_shown, lh, dim=False):
    shown = chars_shown
    for li, line in enumerate(lines):
        if shown <= 0: break
        cx = x
        part = line[:shown]; shown -= len(line) + 1
        for txt, col in tokens(part):
            if dim: col = tuple(int(v * 0.45 + BG[k] * 0.55) for k, v in enumerate(col))
            d.text((cx, y + li * lh), txt, font=font, fill=col)
            cx += d.textlength(txt, font=font)
        last = (li, cx)
    return last if chars_shown > 0 else (0, x)


def panel(d, box, title):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 28, fill=PANEL, outline=BORDER, width=3)
    for k, col in enumerate((RED, YELLOW, GREEN)):
        d.ellipse((x0 + 34 + k * 40, y0 + 30, x0 + 58 + k * 40, y0 + 54), fill=col)
    d.text((x0 + 170, y0 + 26), title, font=F(MONO, 30), fill=MUTED)


def frame(spec, t):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    # subtle grid background
    for gx in range(0, W, 90): d.line((gx, 0, gx, H), fill=GRID)
    for gy in range(0, H, 90): d.line((0, gy, W, gy), fill=GRID)

    # brand badge
    d.rounded_rectangle((60, 90, 520, 160), 35, fill=BADGE)
    d.text((90, 103), "</> CareerWithCode", font=F(SANS_B, 36), fill=ACCENT)
    lang = spec.get("language", "")
    if lang:
        lw = d.textlength(lang, font=F(SANS_B, 32))
        d.rounded_rectangle((W - 100 - lw, 95, W - 60, 155), 30, fill=LANG_COLORS.get(lang.lower(), GREEN))
        d.text((W - 80 - lw, 106), lang, font=F(SANS_B, 32), fill=(255, 255, 255))
    label = spec.get("series_label", "")   # e.g. "Go Series · Part 4"
    if label:
        d.text((70, 185), label, font=F(SANS_B, 38), fill=MUTED)

    # hook title (always visible at top, pops in)
    hf = F(SANS_B, 80)
    hl = wrap(spec["hook"], hf, W - 140, d)
    a = ease(t / 0.6)
    y = 270 - int((1 - a) * 60)
    for i, line in enumerate(hl):
        col = tuple(int(BG[k] + (FG[k] - BG[k]) * a) for k in range(3))
        d.text((70, y + i * 96), line, font=hf, fill=col)
    top = 270 + len(hl) * 96 + 60

    # auto-fit code font so the longest line fits the panel
    longest = max(spec["code"] + (spec.get("before") or []), key=len)
    size = 50
    while size > 26 and d.textlength(longest, font=F(MONO, size)) > W - 220: size -= 2
    mono = F(MONO, size); lh = int(size * 1.55)
    global EXT
    EXT = {"python": ".py", "go": ".go", "javascript": ".js", "java": ".java", "sql": ".sql",
           "c++": ".cpp", "typescript": ".ts", "rust": ".rs"}.get(lang.lower(), ".txt")
    before = spec.get("before") or []
    code = spec["code"]

    # "before" panel (0.8s - 3.5s), then dims
    cy = top
    if before:
        bh = 125 + lh * len(before)
        if t > 0.8:
            panel(d, (60, cy, W - 60, cy + bh), spec.get("before_title", f"before{EXT}  the long way"))
            n = int(sum(len(l) + 1 for l in before) * ease((t - 0.8) / 1.6))
            draw_code(d, before, 100, cy + 95, mono, n, lh, dim=t > 3.5)
        cy += bh + 40

    # main code panel (3.5s - 10s) typed
    ch = 125 + lh * len(code)
    if t > (3.5 if before else 0.8):
        start = 3.5 if before else 0.8
        panel(d, (60, cy, W - 60, cy + ch), spec.get("code_title", f"after{EXT}  the clean way"))
        total = sum(len(l) + 1 for l in code)
        n = int(total * min(1, (t - start) / 4.0))
        li, cx = draw_code(d, code, 100, cy + 95, mono, n, lh)
        if n < total and int(t * 3) % 2 == 0:
            d.rectangle((cx + 4, cy + 95 + li * lh, cx + 26, cy + 95 + li * lh + 48), fill=ACCENT)
    cy += ch + 40

    # output (8.5s+)
    out = spec.get("output")
    if out and t > 8.5:
        a = ease((t - 8.5) / 0.5)
        d.rounded_rectangle((60, cy, W - 60, cy + 150), 24, fill=OUTBG, outline=GREEN, width=3)
        d.text((100, cy + 22), "Output", font=F(SANS_B, 32), fill=GREEN)
        d.text((100, cy + 66), out, font=F(MONO_B, 50), fill=FG)
        cy += 190

    # takeaway (10s+)
    if t > 10:
        a = ease((t - 10) / 0.6)
        tf = F(SANS_B, 66)
        tl = wrap(spec["takeaway"], tf, W - 160, d)
        if len(tl) > 2: tf = F(SANS_B, 54); tl = wrap(spec["takeaway"], tf, W - 160, d)
        for i, line in enumerate(tl):
            col = tuple(int(BG[k] + (YELLOW[k] - BG[k]) * a) for k in range(3))
            d.text((80, cy + 20 + i * 84 + int((1 - a) * 30)), line, font=tf, fill=col)

    # CTA (13s+)
    if t > 13:
        a = ease((t - 13) / 0.5)
        y0 = H - 230 + int((1 - a) * 80)
        d.rounded_rectangle((60, y0, W - 60, y0 + 140), 70, fill=ACCENT)
        cf = F(SANS_B, 44); cta = spec.get("cta", "Follow for a coding tip every day")
        d.text(((W - d.textlength(cta, font=cf)) / 2, y0 + 44), cta, font=cf, fill=(255, 255, 255))

    # progress bar
    d.rectangle((0, H - 18, int(W * t / DUR), H), fill=ACCENT)
    return img


def music(path):
    """Soft lo-fi style pad so the Short isn't silent (no copyright issues)."""
    sr = 44100; n = sr * DUR
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63),
              (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        buf = bytearray()
        for i in range(n):
            t = i / sr; ch = chords[int(t / 3.75) % 4]
            s = sum(math.sin(2 * math.pi * f * t) for f in ch) / 3 * 0.12
            beat = t % 0.5
            s += math.sin(2 * math.pi * 60 * t) * math.exp(-beat * 18) * 0.25 if int(t * 2) % 2 == 0 else 0
            s *= min(1, t / 1.0, (DUR - t) / 1.0)
            buf += struct.pack("<h", int(max(-1, min(1, s)) * 32767))
        w.writeframes(bytes(buf))


def main(spec_path, out):
    spec = json.load(open(spec_path))
    music(out + ".wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", out + ".wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "24",
                          "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for i in range(FPS * DUR):
        p.stdin.write(frame(spec, i / FPS).tobytes())
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
