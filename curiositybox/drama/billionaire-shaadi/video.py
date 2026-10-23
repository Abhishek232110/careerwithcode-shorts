# Renders the "Billionaire Shaadi" Hindi drama short (3 scenes, ~30 s) from timeline.json + aud/*.wav
# Usage: python3 video.py out.mp4            (full render)
#        python3 video.py frame.png 12.3     (one frame at t seconds)
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TL = json.load(open(os.path.join(HERE, "timeline.json")))
W, H, FPS = 1080, 1920, TL["fps"]
S = 2  # supersample
NF = int(TL["total"] * FPS)
DEVA = os.path.join(REPO, "curiositybox", "fonts", "Poppins-Bold.ttf")
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_fc = {}


def F(s):
    s = max(8, int(s))
    if s not in _fc:
        _fc[s] = ImageFont.truetype(DEVA, s, layout_engine=ImageFont.Layout.RAQM)
    return _fc[s]


INK = (30, 20, 25)


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def back(x):
    x = max(0.0, min(1.0, x)); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, k): return a + (b - a) * k


def lerpc(a, b, k): return tuple(int(lerp(x, y, k)) for x, y in zip(a, b))


# ---------- lip-sync ----------
def load_env(name):
    w = wave.open(os.path.join(HERE, "aud", name + ".wav")); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    hop = sr // FPS
    e = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    return e / (e.max() + 1e-9)


VOICES = [dict(v, env=load_env(v["name"])) for v in TL["voices"]]


def mouth(char, t):
    for v in VOICES:
        i = int((t - v["start"]) * FPS)
        if v["char"] == char and 0 <= i < len(v["env"]):
            return min(1.0, v["env"][i] * 1.7)
    return 0.0


def speaking(t):
    for v in VOICES:
        if v["start"] - .05 <= t <= v["start"] + len(v["env"]) / FPS + .2:
            return v
    return None


# ---------- camera + drawing context ----------
class Cam:
    def __init__(self, cx, cy, z):
        self.cx, self.cy, self.z = cx, cy, z

    def pt(self, x, y):
        return (((x - self.cx) * self.z + W / 2) * S, ((y - self.cy) * self.z + H / 2) * S)


def epts(cx, cy, rx, ry, a0=0, a1=2 * math.pi, n=28):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / (n - 1)), cy + ry * math.sin(a0 + (a1 - a0) * i / (n - 1))) for i in range(n)]


class Person:
    """Cartoon person. Local units: feet at (0,0), head centre (0,-790), up is negative y."""

    def __init__(self, d, cam, X, Y, sc, spec, dir=1, bow=0.0, kneel=0.0, jig=(0, 0), pale=0.0):
        self.d, self.cam, self.X, self.Y, self.sc = d, cam, X, Y, sc
        self.sp, self.dir, self.bow, self.kneel, self.jig, self.pale = spec, dir, bow, kneel, jig, pale
        self.k = cam.z * S * sc

    def P(self, x, y, up=True):
        if up:
            dy = 270 * self.kneel
            y += dy
            x += self.jig[0]; y += self.jig[1]
            if self.bow:
                th = self.bow * self.dir; px, py = 0, -420 + dy
                rx, ry = x - px, y - py
                x = px + rx * math.cos(th) - ry * math.sin(th)
                y = py + rx * math.sin(th) + ry * math.cos(th)
        return self.cam.pt(self.X + x * self.sc, self.Y + y * self.sc)

    def poly(self, pts, fill, up=True, outline=None, w=0):
        self.d.polygon([self.P(x, y, up) for x, y in pts], fill=fill, outline=outline, width=int(w * self.k) if w else 0)

    def ell(self, cx, cy, rx, ry, fill, up=True):
        self.poly(epts(cx, cy, rx, ry), fill, up)

    def line(self, pts, fill, w, up=True):
        self.d.line([self.P(x, y, up) for x, y in pts], fill=fill, width=max(1, int(w * self.k)), joint="curve")
        for x, y in (pts[0], pts[-1]):
            self.ell(x, y, w / 2, w / 2, fill, up)

    @property
    def skin(self):
        return lerpc(self.sp["skin"], (215, 222, 205), self.pale)

    def draw(self, t, mood="neutral", m=0.0, arms="down", step=None, glasses=0.0, look=0.0, photo=0.0):
        sp = self.sp; dr = self.dir
        # back hair / veil / bun
        if sp.get("veil"):
            self.poly(epts(0, -800, 108, 125, math.pi * 0.95, math.pi * 2.05) + [(118, -640), (-118, -640)], sp["veil"])
        if sp.get("hair") == "long":
            self.ell(0, -790, 84, 96, sp["hair_c"])
            self.poly([(-80, -760), (80, -760), (95, -600), (-95, -600)], sp["hair_c"])
        if sp.get("hair") == "bun":
            self.ell(-dr * 70, -840, 40, 40, sp["hair_c"])
        # legs / lower body
        self.lower(t, step)
        # torso
        top = sp["top"]
        if sp["outfit"] == "lehenga":
            self.poly([(-92, -682), (92, -682), (72, -470), (-72, -470)], top)
            self.poly([(-58, -520), (58, -520), (52, -470), (-52, -470)], sp["skin"])  # midriff
            self.poly([(-90, -682), (-30, -682), (90, -470), (40, -470)], sp["veil"])  # dupatta drape
        elif sp["outfit"] == "saree":
            self.poly([(-90, -682), (90, -682), (78, -420), (-78, -420)], top)
            self.poly([(-90, -682), (-20, -682), (88, -420), (30, -420)], sp["accent"])
        elif sp["outfit"] == "suit":
            self.poly([(-104, -684), (104, -684), (88, -380), (-88, -380)], top)
            self.poly([(-34, -684), (34, -684), (0, -540)], (245, 245, 245))
            self.poly([(-9, -676), (9, -676), (12, -560), (0, -540), (-12, -560)], (25, 25, 30))
            self.line([(-34, -684), (0, -540), (34, -684)], (55, 55, 62), 6)
        else:  # kurta / sherwani
            hem = -250 if sp["outfit"] == "kurta" else -230
            self.poly([(-100, -684), (100, -684), (92, -430), (110, hem), (-110, hem), (-92, -430)], top)
            self.line([(0, -684), (0, -470)], sp.get("accent", (200, 190, 170)), 6)
            for i in range(5):
                self.ell(10, -660 + i * 42, 6, 6, sp.get("button", (190, 170, 140)))
            for px, py, c in sp.get("patches", []):
                self.poly([(px - 26, py - 22), (px + 24, py - 26), (px + 28, py + 22), (px - 22, py + 26)], c)
                self.line([(px - 22, py - 18), (px + 20, py + 20)], (120, 95, 70), 3)
        if sp.get("garland"):
            g = [(math.cos(a) * 78, -690 + math.sin(a) * 150) for a in np.linspace(math.pi * 1.05, math.pi * -0.05, 1)]
            for i in range(17):
                a = math.pi * (1 - i / 16)
                x, y = -math.cos(a) * 82, -690 + math.sin(a) * 175
                self.ell(x, y, 17, 17, (255, 150, 0) if i % 2 else (255, 200, 20))
        if sp.get("mala"):
            for i in range(13):
                a = math.pi * (1 - i / 12)
                self.ell(-math.cos(a) * 55, -690 + math.sin(a) * 120, 8, 8, (240, 220, 140))
        # arms
        self.arms(t, arms, photo)
        # neck + head
        self.poly([(-26, -730), (26, -730), (28, -676), (-28, -676)], tuple(int(c * .9) for c in self.skin))
        for s in (-1, 1):
            self.ell(s * 66, -786, 14, 20, self.skin)
        self.ell(0, -790, 68, 80, self.skin)
        self.face(t, mood, m, glasses, look)
        self.hair_front()

    def lower(self, t, step):
        sp = self.sp; dr = self.dir
        legc = sp.get("legs", (240, 236, 225)); shoe = sp.get("shoe", (70, 45, 30))
        if sp["outfit"] in ("lehenga", "saree"):
            sk = sp["skirt"]
            pts = [(-72, -470), (72, -470)] + [(230 * math.cos(a) * .98, -10 + 25 * math.sin(a)) for a in np.linspace(0, math.pi, 12)]
            if sp["outfit"] == "saree":
                pts = [(-78, -420), (78, -420), (110, 0), (-110, 0)]
            self.poly(pts, sk, up=False if self.kneel else True)
            if sp["outfit"] == "lehenga":
                self.poly([(230, -10), (215, -70)] + [(215 * math.cos(a), -70 + 22 * math.sin(a)) for a in np.linspace(0, math.pi, 10)] + [(-230, -10)]
                          + [(230 * math.cos(a), -10 + 25 * math.sin(a)) for a in np.linspace(math.pi, 0, 10)], (230, 180, 40))
                for i in range(18):
                    x = -170 + (i % 6) * 68 + (i // 6) * 20; y = -380 + (i // 6) * 110
                    if abs(x) < 70 + (y + 470) * .38:
                        self.ell(x, y, 9, 9, (240, 195, 60))
            return
        if self.kneel > .5:
            # kneeling: thighs forward, shins on ground behind
            hip = -160
            for s in (-1, 1):
                kx = dr * 110 + s * 10
                self.line([(s * 30, hip), (kx, -35), (-dr * 60 + s * 10, -20)], legc, 56, up=False)
            if sp["outfit"] in ("kurta", "sherwani"):
                self.poly([(-100, hip - 260 + 40), (100, hip - 260 + 40), (dr * 140 + 40, -40), (dr * 140 - 160, -40)], sp["top"], up=False)
            return
        for s, ph in ((-1, 0), (1, math.pi)):
            sw = math.sin(step + ph) * 60 if step is not None else 0
            lift = max(0, -math.cos(step + ph)) * 30 if step is not None else 0
            fx = s * 38 + sw
            self.line([(s * 38, -440), (fx, -40 - lift)], legc, 54, up=False)
            self.poly([(fx - 34 + dr * 10, -48 - lift), (fx + 34 + dr * 22, -48 - lift), (fx + 38 + dr * 22, -lift), (fx - 34 + dr * 10, -lift)], shoe, up=False)

    def arms(self, t, pose, photo):
        sp = self.sp; dr = self.dir
        sl = sp.get("sleeve", sp["top"])
        for s in (-1, 1):
            sh = (s * 96, -668)
            if pose == "down":
                el, hd = (s * 128, -560), (s * 120, -450)
            elif pose == "belly":
                el, hd = (s * 145, -560), (s * 45, -500 + math.sin(t * 30) * 8)
            elif pose == "mouth" and s == -dr:
                el, hd = (s * 70, -600), (dr * 10, -745)
            elif pose == "join":
                el, hd = (s * 120, -560), (dr * 40 + s * 8, -640)
            elif pose == "point" and s == dr:
                el, hd = (dr * 190, -660), (dr * 285, -680)
            elif pose == "photo" and s == dr:
                el, hd = (dr * 150, -600), (dr * 200, -690)
            elif pose == "glasses" and s == dr:
                el, hd = (dr * 120, -700), (dr * 40, -800)
            elif pose == "run":
                a = math.sin(t * 14 + (0 if s > 0 else math.pi)) * .8
                el = (s * 120 + math.sin(a) * 40, -580); hd = (s * 110 + math.sin(a) * 110, -470 - abs(math.sin(a)) * 40)
            elif pose == "fold":
                el, hd = (s * 128, -560), (-s * 55, -570)
            else:
                el, hd = (s * 128, -560), (s * 120, -450)
            self.line([sh, el, hd], sl, 40)
            if sp.get("cuff"):
                self.ell(hd[0], hd[1], 21, 21, sp["cuff"])
            self.ell(hd[0], hd[1], 19, 19, self.skin)
            if sp.get("bangles"):
                for k in range(3):
                    self.ell(lerp(el[0], hd[0], .8 - k * .08), lerp(el[1], hd[1], .8 - k * .08), 20, 9, (230, 40, 60) if k % 2 else (240, 200, 60))
            if pose == "photo" and s == dr and photo > 0:
                hx, hy = hd
                c = (240, 232, 210)
                self.poly([(hx - 10, hy - 95), (hx + 70 * dr, hy - 100), (hx + 75 * dr, hy - 10), (hx - 5, hy - 5)], c)

    def face(self, t, mood, m, glasses, look):
        sp = self.sp; dr = self.dir
        cx = dr * 6
        lx = look if look else dr * 3
        # eyes
        for s in (-1, 1):
            ex, ey = cx + s * 27, -796
            if mood == "laugh":
                self.line([(ex - 13, ey + 2), (ex, ey - 8), (ex + 13, ey + 2)], INK, 5)
            else:
                ry = 15 if mood in ("shock", "scared") else 11
                self.ell(ex, ey, 13, ry, (255, 255, 255))
                self.ell(ex + lx * 1.5, ey + 1, 6.5, 7, INK)
                self.ell(ex + lx * 1.5 + 2, ey - 2, 2.2, 2.2, (255, 255, 255))
                if sp.get("lashes"):
                    self.line([(ex - 14, ey - ry + 2), (ex + 14, ey - ry + 2)], INK, 3.5)
            # brows
            b = {"angry": (-10, 6), "shock": (-24, -22), "scared": (-18, -26), "worried": (-14, -22), "smirk": (-14, -8),
                 "laugh": (-20, -16)}.get(mood, (-16, -14))
            inner, outer = ex - s * 12, ex + s * 14
            yi = ey - 20 + (b[0] + 10 if mood == "angry" else (b[1] if mood in ("worried", "scared") else b[0] + 2))
            yo = ey - 22 + (b[0] if mood != "angry" else b[0] - 6)
            if mood == "smirk" and s == dr: yi -= 6; yo -= 8
            self.line([(inner, yi), (outer, yo)], sp.get("brow", INK), 5)
        # nose
        self.line([(cx + dr * 2, -786), (cx + dr * 8, -766), (cx, -762)], tuple(int(c * .75) for c in self.skin), 3.5)
        if sp.get("bindi"):
            self.ell(cx, -826, 5, 5, (210, 20, 40))
            self.ell(cx, -862, 9, 9, (240, 200, 60)); self.line([(cx, -870), (cx, -900)], (240, 200, 60), 3)
        if sp.get("nosering"):
            pts = epts(cx + dr * 12, -758, 11, 11, -math.pi / 2, math.pi * 1.2, 12)
            self.line(pts, (240, 200, 60), 2.5)
        if sp.get("earrings"):
            for s in (-1, 1):
                self.ell(s * 68, -756, 8, 8, (240, 200, 60))
        # mouth
        my = -740; lip = sp.get("lip", (150, 60, 60))
        if mood == "laugh":
            self.poly(epts(cx, my - 4, 26, 24 + 6 * abs(math.sin(t * 25)), 0, math.pi, 14), (110, 25, 35))
            self.poly(epts(cx, my - 2, 20, 8, 0, math.pi, 10), (240, 120, 120))
        elif m > .08:
            self.ell(cx, my, 13 + 6 * m, 4 + 16 * m, (110, 25, 35))
            self.ell(cx, my + 6 * m, 8 + 3 * m, 3 + 5 * m, (230, 110, 110))
        elif mood in ("smile", "smirk"):
            if mood == "smirk":
                self.line([(cx - 16, my - 2), (cx + 4, my + 2), (cx + dr * 20, my - 8)], lip, 5)
            else:
                self.line(epts(cx, my - 10, 19, 12, math.pi * .15, math.pi * .85, 8), lip, 5)
        elif mood in ("angry", "worried", "scared"):
            self.line(epts(cx, my + 8, 16, 9, math.pi * 1.15, math.pi * 1.85, 8), lip, 5)
        elif mood == "shock":
            self.ell(cx, my, 11, 14, (110, 25, 35))
        else:
            self.line([(cx - 13, my), (cx + 13, my)], lip, 4.5)
        if sp.get("mustache"):
            mc = sp["mustache"]
            self.poly([(cx - 4, -758), (cx - 34, -748), (cx - 40, -736), (cx - 18, -745), (cx, -752), (cx + 18, -745), (cx + 40, -736), (cx + 34, -748), (cx + 4, -758)], mc)
        if sp.get("sweat") and mood in ("scared", "worried"):
            for k in range(2):
                ph = (t * .9 + k * .5) % 1
                self.poly(epts(-dr * 55 + k * 110 * dr, -830 + ph * 60, 7, 11), (170, 220, 255))
        if glasses > 0:
            gy = lerp(-880, -797, ease(glasses))
            for s in (-1, 1):
                self.poly([(cx + s * 27 - 22, gy - 14), (cx + s * 27 + 22, gy - 14), (cx + s * 27 + 18, gy + 14), (cx + s * 27 - 18, gy + 14)], (15, 15, 20))
                self.line([(cx + s * 27 - 14, gy - 8), (cx + s * 27 - 4, gy - 8)], (90, 90, 110), 3)
            self.line([(cx - 6, gy - 8), (cx + 6, gy - 8)], (15, 15, 20), 5)
            if sp.get("earpiece"):
                self.line([(-dr * 66, -780), (-dr * 70, -700), (-dr * 80, -660)], (220, 220, 220), 3)

    def hair_front(self):
        sp = self.sp; h = sp.get("hair")
        hc = sp.get("hair_c", INK)
        if h in ("long", "bun"):
            self.poly(epts(0, -800, 72, 86, math.pi * 1.0, math.pi * 2.0, 20) + [(40, -830), (0, -845), (-40, -830)], hc)
            if sp.get("veil"):
                self.poly(epts(0, -805, 86, 100, math.pi * 1.0, math.pi * 2.0, 20) + [(70, -830), (0, -880), (-70, -830)], sp["veil"])
                self.line(epts(0, -805, 86, 100, math.pi * 1.0, math.pi * 2.0, 20), (240, 195, 60), 7)
        elif h == "short":
            self.poly(epts(0, -800, 72, 88, math.pi * 1.02, math.pi * 1.98, 20) + [(55, -840), (20, -850), (-25, -838), (-58, -828)], hc)
        elif h == "buzz":
            self.poly(epts(0, -800, 70, 84, math.pi * 1.05, math.pi * 1.95, 20) + [(40, -852), (-40, -852)], hc)
        elif h == "safa":
            self.poly(epts(0, -820, 82, 72, math.pi * .95, math.pi * 2.05, 22), sp["safa"])
            for k in range(3):
                self.line(epts(0, -818 + k * 14, 80, 62 - k * 6, math.pi * 1.1, math.pi * 1.9, 12), sp["safa2"], 6)
            self.ell(0, -880, 13, 13, (240, 200, 60))
            self.line([(0, -885), (dirx := self.dir * 18, -960)], (255, 245, 230), 9)
            self.ell(-self.dir * 66, -720, 6, 6, (0, 0, 0, 0))


SPECS = {
    "girl": dict(skin=(238, 195, 160), hair="long", hair_c=(30, 18, 15), veil=(205, 25, 50), outfit="lehenga", top=(180, 15, 40),
                 skirt=(200, 20, 45), lip=(200, 30, 60), bindi=1, nosering=1, earrings=1, bangles=1, lashes=1, sleeve=(180, 15, 40)),
    "boy": dict(skin=(205, 150, 110), hair="short", hair_c=(25, 18, 15), outfit="kurta", top=(222, 210, 180), legs=(235, 230, 215),
                accent=(190, 175, 140), patches=[(-55, -520, (180, 150, 110)), (60, -330, (160, 140, 100))], shoe=(110, 80, 50)),
    "father": dict(skin=(232, 186, 150), hair="safa", safa=(240, 120, 30), safa2=(220, 40, 60), outfit="sherwani", top=(245, 225, 175),
                   accent=(210, 170, 70), button=(220, 175, 60), legs=(250, 245, 230), mustache=(220, 220, 215), brow=(200, 200, 200),
                   mala=1, sweat=1, shoe=(160, 40, 40)),
    "mother": dict(skin=(235, 190, 155), hair="bun", hair_c=(40, 25, 20), outfit="saree", top=(20, 130, 80), skirt=(25, 150, 90),
                   accent=(230, 180, 50), lip=(180, 40, 60), bindi=1, earrings=1, bangles=1, lashes=1),
    "uncle": dict(skin=(215, 165, 125), hair="short", hair_c=(70, 60, 55), outfit="kurta", top=(40, 80, 170), legs=(240, 235, 225),
                  accent=(220, 190, 90), mustache=(40, 30, 25)),
    "guard": dict(skin=(200, 150, 115), hair="buzz", hair_c=(20, 18, 18), outfit="suit", top=(22, 22, 28), legs=(28, 28, 34),
                  shoe=(10, 10, 12), earpiece=1, cuff=(245, 245, 245)),
}


# ---------- backgrounds (world 1080x1920, stored at 2x) ----------
def bg_mandap(dark=False):
    im = Image.new("RGB", (W * S, H * S)); d = ImageDraw.Draw(im)
    for y in range(H * S):
        k = y / (H * S)
        d.line([(0, y), (W * S, y)], fill=lerpc((120, 20, 40), (230, 110, 40), min(1, k * 1.3)))
    # draped fabric
    for i, x in enumerate(range(-40, W + 80, 90)):
        c = (200, 40, 60) if i % 2 else (245, 150, 40)
        d.polygon([(x * S, 0), ((x + 90) * S, 0), ((x + 70) * S, 1350 * S), ((x + 20) * S, 1350 * S)], fill=c)
    rng = np.random.default_rng(2)
    # fairy lights
    for _ in range(140):
        x, y = rng.uniform(0, W), rng.uniform(80, 1300); r = rng.uniform(4, 8)
        d.ellipse([(x - r * 2.5) * S, (y - r * 2.5) * S, (x + r * 2.5) * S, (y + r * 2.5) * S], fill=(255, 200, 120))
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(255, 250, 210))
    # marigold strings
    for row in range(3):
        for x0 in range(-60, W, 260):
            for k in range(24):
                u = k / 23; x = x0 + u * 260; y = 60 + row * 130 + math.sin(u * math.pi) * 90
                r = 15
                d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(255, 140, 0) if k % 2 else (255, 205, 30))
    # pillars
    for px in (70, 1010):
        d.rectangle([(px - 45) * S, 0, (px + 45) * S, 1450 * S], fill=(250, 220, 170))
        for y in range(0, 1450, 34):
            d.ellipse([(px - 30) * S, y * S, (px + 30) * S, (y + 34) * S], fill=(255, 150, 0) if (y // 34) % 2 else (250, 245, 240))
    # floor
    for y in range(1380 * S, H * S):
        k = (y - 1380 * S) / ((H - 1380) * S)
        d.line([(0, y), (W * S, y)], fill=lerpc((200, 140, 90), (140, 70, 50), k))
    for i in range(12):
        x = 90 + i * 90
        d.ellipse([(x - 30) * S, 1700 * S, (x + 30) * S, 1730 * S], fill=(250, 210, 120))
    im = im.filter(ImageFilter.GaussianBlur(3 * S))
    if dark:
        im = Image.blend(im, Image.new("RGB", im.size, (60, 0, 10)), .45)
    return im


def bg_night():
    im = Image.new("RGB", (W * S, H * S)); d = ImageDraw.Draw(im)
    for y in range(1300 * S):
        k = y / (1300 * S)
        d.line([(0, y), (W * S, y)], fill=lerpc((10, 12, 40), (70, 40, 90), k))
    rng = np.random.default_rng(9)
    for _ in range(90):
        x, y = rng.uniform(0, W), rng.uniform(0, 700); r = rng.uniform(1.5, 3.5)
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(255, 255, 240))
    # palace / venue
    d.rectangle([80 * S, 700 * S, 1000 * S, 1300 * S], fill=(60, 35, 55))
    d.polygon([(380 * S, 700 * S), (540 * S, 480 * S), (700 * S, 700 * S)], fill=(60, 35, 55))
    d.ellipse([460 * S, 470 * S, 620 * S, 600 * S], fill=(60, 35, 55))
    for wx in range(130, 980, 110):
        for wy in (780, 960, 1130):
            d.rounded_rectangle([wx * S, wy * S, (wx + 60) * S, (wy + 100) * S], radius=30 * S, fill=(255, 200, 110))
    for i in range(60):
        x = 80 + i * 15.5; y = 700 + math.sin(i / 59 * math.pi * 6) * 14 + 8
        d.ellipse([(x - 5) * S, (y - 5) * S, (x + 5) * S, (y + 5) * S], fill=(255, 230, 150))
    d.rectangle([0, 1300 * S, W * S, H * S], fill=(45, 45, 55))
    d.rectangle([0, 1300 * S, W * S, 1340 * S], fill=(90, 90, 100))
    d.polygon([(380 * S, 1340 * S), (700 * S, 1340 * S), (900 * S, H * S), (180 * S, H * S)], fill=(150, 20, 35))  # red carpet
    im = im.filter(ImageFilter.GaussianBlur(2.5 * S))
    return im


BGS = {}


def get_bg(name):
    if name not in BGS:
        BGS[name] = {"mandap": lambda: bg_mandap(), "night": bg_night, "mandap_dark": lambda: bg_mandap(True)}[name]()
    return BGS[name]


def bg_view(name, cam):
    bg = get_bg(name)
    hw, hh = W / 2 / cam.z, H / 2 / cam.z
    cx = min(max(cam.cx, hw), W - hw); cy = min(max(cam.cy, hh), H - hh)
    box = tuple(int(v * S) for v in (cx - hw, cy - hh, cx + hw, cy + hh))
    return bg.crop(box).resize((W * S, H * S), Image.BILINEAR), cx, cy


# ---------- props ----------
def car(d, cam, X, Y, sc, dirn=1, lights=True):
    def P(x, y): return cam.pt(X + x * dirn * sc, Y + y * sc)
    k = cam.z * S * sc
    body = [(-310, -60), (-300, -150), (-150, -170), (-80, -250), (130, -255), (210, -170), (300, -150), (315, -60)]
    d.polygon([P(*p) for p in body], fill=(12, 12, 16))
    d.polygon([P(-60, -238), (P(40, -238)), P(40, -175), P(-125, -175)], fill=(60, 80, 120))
    d.polygon([P(55, -238), P(125, -238), P(190, -175), P(55, -175)], fill=(60, 80, 120))
    d.line([P(-290, -130), P(300, -130)], fill=(190, 190, 200), width=max(1, int(5 * k)))
    if lights:
        d.ellipse([*P(280, -140), *P(318, -110)] if dirn > 0 else [*P(318, -140), *P(280, -110)], fill=(255, 250, 200))
    for wx in (-190, 190):
        a, b = P(wx - 60, -120), P(wx + 60, 0)
        d.ellipse([min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]], fill=(20, 20, 20))
        a, b = P(wx - 32, -92), P(wx + 32, -28)
        d.ellipse([min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]], fill=(170, 170, 180))


def headlight_glow(im, cam, X, Y, sc, dirn):
    gl = Image.new("L", im.size, 0); g = ImageDraw.Draw(gl)
    a = cam.pt(X + 300 * dirn * sc, Y - 125 * sc)
    b = cam.pt(X + 900 * dirn * sc, Y - 260 * sc); c = cam.pt(X + 900 * dirn * sc, Y + 40 * sc)
    g.polygon([a, b, c], fill=90)
    gl = gl.filter(ImageFilter.GaussianBlur(30 * S))
    im.paste(Image.new("RGB", im.size, (255, 245, 200)), (0, 0), gl)


def photo_card(size, t):
    """Old sepia photo: a young woman with a baby next to the young father (same mustache)."""
    w, h = size
    im = Image.new("RGB", (w * S, h * S), (200, 170, 120)); d = ImageDraw.Draw(im, "RGBA")
    for y in range(h * S):
        k = y / (h * S); d.line([(0, y), (w * S, y)], fill=lerpc((215, 185, 135), (170, 135, 90), k))
    cam = Cam(w / 2, h / 2, 1.0)
    cam.pt = lambda x, y: (x * S, y * S)
    mum = dict(SPECS["mother"], top=(150, 110, 80), skirt=(160, 120, 85), accent=(190, 160, 110), skin=(210, 175, 135))
    young = dict(SPECS["uncle"], top=(140, 105, 75), skin=(205, 168, 128), hair_c=(50, 35, 25), mustache=(45, 30, 20))
    p1 = Person(d, cam, w * .32, h * .98, h / 1000, mum, dir=1)
    p1.draw(t, "smile", 0, "join")
    p2 = Person(d, cam, w * .70, h * .98, h / 980, young, dir=-1)
    p2.draw(t, "smile", 0, "down")
    # torn edge + scratches + vignette
    rng = np.random.default_rng(3)
    for _ in range(25):
        x = rng.uniform(0, w); d.line([(x * S, 0), ((x + rng.uniform(-20, 20)) * S, h * S)], fill=(255, 240, 210, 35), width=2)
    vg = Image.new("L", im.size, 0); ImageDraw.Draw(vg).ellipse([-w * .2 * S, -h * .15 * S, w * 1.2 * S, h * 1.15 * S], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(40 * S))
    im = Image.composite(im, Image.new("RGB", im.size, (90, 60, 35)), vg)
    d = ImageDraw.Draw(im)
    tear = [(w * S, 0), (w * .86 * S, 0)] + [((w * .86 + 0.04 * w * math.sin(i * 1.7)) * S, h * i / 12 * S) for i in range(13)] + [(w * S, h * S)]
    d.polygon(tear, fill=(25, 10, 12))
    return im


# ---------- text ----------
def outlined(d, xy, text, font, fill, stroke, sc=(0, 0, 0)):
    d.text(xy, text, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sc)


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w_ in text.split():
        if d.textlength((cur + " " + w_).strip(), font=f) > maxw and cur:
            lines.append(cur); cur = w_
        else:
            cur = (cur + " " + w_).strip()
    return lines + [cur]


def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((70, 70), ch, font=f, embedded_color=True, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


EMO = None


# ---------- shots ----------
def shot(t):
    """Returns (bg, cam params cx, cy, z) with a slow push inside each shot."""
    C = TL["cuts"]

    def push(t0, t1, a, b):
        k = ease((t - t0) / (t1 - t0)); return tuple(lerp(x, y, k) for x, y in zip(a, b))
    if t < 1.7: return "mandap", push(0, 1.7, (540, 1000, 1.0), (540, 990, 1.08))
    if t < 4.0: return "mandap", push(1.7, 4.0, (380, 900, 1.75), (380, 880, 1.95))
    if t < 6.9: return "mandap", push(4.0, 6.9, (700, 900, 1.75), (700, 880, 2.0))
    if t < 8.4: return "mandap", push(6.9, 8.4, (560, 1000, 1.05), (640, 900, 1.5))
    if t < 9.9: return "night", push(8.4, 9.9, (540, 1060, 1.0), (540, 1060, 1.04))
    if t < 11.9: return "night", push(9.9, 11.9, (540, 1150, 1.25), (540, 1120, 1.35))
    if t < 14.0: return "night", push(11.9, 14.0, (340, 1000, 1.9), (340, 990, 2.1))
    if t < 16.2: return "night", push(14.0, 16.2, (180, 900, 1.9), (180, 890, 2.15))
    if t < 18.4: return "night", push(16.2, 18.4, (560, 880, 1.8), (560, 870, 2.05))
    if t < 19.7: return "night", push(18.4, 19.7, (540, 1130, 1.15), (540, 1100, 1.25))
    if t < 20.4: return "mandap_dark", push(19.7, 20.4, (540, 1000, 1.0), (540, 1000, 1.05))
    if t < 24.2: return "mandap_dark", push(20.4, 24.2, (420, 1060, 1.7), (420, 1060, 1.95))
    if t < 26.6: return "mandap_dark", push(24.2, 26.6, (700, 900, 1.8), (700, 880, 2.05))
    if t < 28.0: return "mandap_dark", push(26.6, 28.0, (430, 1120, 2.0), (430, 1130, 2.4))
    if t < 29.45: return "mandap_dark", push(28.0, 29.45, (750, 1020, 1.45), (780, 990, 1.6))
    return "photo", (540, 960, 1.0)


def scene1(im, d, cam, t):
    jig = lambda ph: (math.sin(t * 22 + ph) * 4, -abs(math.sin(t * 22 + ph)) * 10)
    laughing = t < 2.2 or t > 7.7
    for name, X, Y, sc, dr, ph in (("uncle", 560, 1430, .72, 1, 0), ("father", 150, 1480, .8, 1, 1), ("mother", 940, 1480, .78, -1, 2)):
        p = Person(d, cam, X, Y, sc, SPECS[name], dir=dr, jig=jig(ph) if laughing else (0, 0))
        p.draw(t, "laugh" if laughing else "smirk", 0, "belly" if laughing else "fold")
    g = dict(SPECS["girl"], garland=1); b = dict(SPECS["boy"], garland=1)
    Person(d, cam, 380, 1560, .86, g, dir=1).draw(t, "angry", mouth("girl", t), "point" if 0.8 < t < 4.0 else "down")
    Person(d, cam, 700, 1560, .9, b, dir=-1).draw(t, "smile" if t < 7.0 else "smirk", mouth("boy", t), "down")
    if laughing:
        for k in range(4):
            ph = (t * 1.3 + k * .27) % 1
            x = (120, 940, 560, 300)[k] + math.sin(t * 5 + k) * 20; y = (1000, 1020, 900, 950)[k] - ph * 160
            p = cam.pt(x, y)
            f = F(46 * cam.z * S * .8)
            d.text(p, "हा हा!" if k % 2 else "HA HA", font=f, fill=(255, 255, 255, int(255 * (1 - ph))), anchor="mm",
                   stroke_width=int(4 * S), stroke_fill=(120, 0, 20, int(255 * (1 - ph))))


GUARDS = ((270, 1580), (850, 1580), (330, 1720), (790, 1720))


def scene2(im, d, cam, t):
    u = t - 8.4
    # cars slide in
    cars = [(-600, 250, 1420, .8, 1, 0.0), (1700, 840, 1420, .8, -1, .25), (-600, 560, 1330, .6, 1, .5)]
    for x0, x1, Y, sc, dn, dl in sorted(cars, key=lambda c: c[2]):
        k = ease((u - dl) / 1.0)
        X = lerp(x0, x1, k) + (math.sin(u * 40) * 2 if k < 1 else 0)
        headlight_glow(im, cam, X, Y, sc, dn); d = ImageDraw.Draw(im, "RGBA")
        car(d, cam, X, Y, sc, dn)
    # girl at left, boy centre
    gm = mouth("girl", t)
    Person(d, cam, 140, 1620, .88, SPECS["girl"], dir=1).draw(t, "shock" if t > 9.9 else "angry", gm, "mouth" if t > 10.3 else "down")
    gl = ease((t - 16.6) / .5) if t > 16.6 else 0
    Person(d, cam, 560, 1680, .95, SPECS["boy"], dir=-1 if t < 16.2 else 1).draw(
        t, "smirk" if t > 10.3 else "smile", mouth("boy", t), "glasses" if 16.4 < t < 17.2 else ("fold" if t > 17.2 else "down"), glasses=gl)
    # bodyguards run from cars, then bow
    for i, (gx, gy) in enumerate(GUARDS):
        start = (280, 820, 280, 820)[i]
        k = ease((u - 1.0 - i * .08) / .6)
        X = lerp(start, gx, k)
        if u < 1.0 + i * .08: continue
        dr = 1 if gx < 560 else -1
        bw = ease((t - 10.35 - i * .05) / .3) * .5
        p = Person(d, cam, X, gy, .84 if gy > 1650 else .72, SPECS["guard"], dir=dr, bow=bw)
        p.draw(t, "neutral", mouth("guard", t) if i == 0 else 0, "run" if k < 1 else "join", step=u * 14 if k < 1 else None, glasses=1)
    return d


def scene3(im, d, cam, t):
    u = t - 19.7
    pale = ease((t - 26.7) / .9)
    run = ease(u / .6)
    X = lerp(-200, 430, run)
    kn = ease((u - .6) / .1)
    Person(d, cam, 960, 1560, .82, SPECS["girl"], dir=-1).draw(
        t, "shock" if t > 26.6 else "worried", 0, "mouth" if t > 28.4 else "down", look=-3 if t < 28 else -4)
    look = 4 if 24.2 < t < 26.6 else -3
    Person(d, cam, 730, 1600, .92, SPECS["boy"], dir=1 if 24.2 < t < 26.6 or t > 28 else -1).draw(
        t, "angry" if t > 25.5 else "smirk", mouth("boy", t), "photo" if t > 28.0 else "fold", glasses=0, photo=1 if t > 28.0 else 0)
    shake = (math.sin(t * 50) * 3, 0) if 20.4 < t < 24.2 else (0, 0)
    Person(d, cam, X, 1600, .88, SPECS["father"], dir=1, kneel=kn, jig=shake, pale=pale).draw(
        t, "scared" if t > 20.3 else "worried", mouth("father", t), "run" if run < 1 else "join", step=u * 16 if run < 1 else None)


def render(fi, text=True):
    t = fi / FPS
    bgname, (cx, cy, z) = shot(t)
    # impact shake
    sx = sy = 0
    for b in TL["booms"]:
        if 0 <= t - b < .35:
            a = (1 - (t - b) / .35) * 14; sx += math.sin(t * 90) * a; sy += math.cos(t * 77) * a
    if bgname == "photo":
        im = Image.new("RGB", (W * S, H * S), (20, 8, 10))
        u = t - 29.45
        pc = photo_card((760, 1000), t)
        k = back(u / .35)
        ang = (1 - ease(u / .35)) * 25 - 4
        pc = pc.resize((int(pc.width * (.4 + .6 * k)), int(pc.height * (.4 + .6 * k))), Image.LANCZOS).rotate(ang, expand=True, fillcolor=(20, 8, 10))
        im.paste(pc, (W * S // 2 - pc.width // 2 + int(sx * S), int(880 * S) - pc.height // 2 + int(sy * S)))
        im = im.resize((W, H), Image.LANCZOS)
    else:
        cam = Cam(cx + sx / z, cy + sy / z, z)
        im, ccx, ccy = bg_view(bgname, cam)
        cam.cx, cam.cy = ccx, ccy
        d = ImageDraw.Draw(im, "RGBA")
        if bgname == "mandap": scene1(im, d, cam, t)
        elif bgname == "night": scene2(im, d, cam, t)
        else: scene3(im, d, cam, t)
        im = im.resize((W, H), Image.LANCZOS)
        if bgname == "mandap_dark" and 26.6 < t < 28.0:  # pale, cold tint on the father
            im = Image.blend(im, Image.new("RGB", (W, H), (120, 150, 170)), .18 * ease((t - 26.6) / .5))
    if not text:
        return np.asarray(im.convert("RGB")).tobytes()
    d = ImageDraw.Draw(im, "RGBA")
    # vignette-ish bottom gradient for captions
    for y in range(1560, H, 6):
        a = int(170 * (y - 1560) / (H - 1560))
        d.rectangle([0, y, W, y + 6], fill=(0, 0, 0, a))
    for c in TL["cuts"]:
        if 0 <= t - c < .07:
            im = Image.blend(im, Image.new("RGB", (W, H), (255, 255, 255)), .55); d = ImageDraw.Draw(im, "RGBA")
    # hook
    if t < 2.6:
        k = back(t / .3)
        outlined(d, (W // 2, 230), "शादी के 10 मिनट बाद...", F(84 * k), (255, 255, 255), 10)
        outlined(d, (W // 2, 345), "सबके होश उड़ गए!", F(100 * k), (255, 215, 40), 11)
    if 10.4 < t < 14.0:
        k = back((t - 10.4) / .3)
        d.rounded_rectangle([170, 190, W - 170, 330], radius=40, fill=(0, 0, 0, 150))
        outlined(d, (W // 2, 262), "500 अरब की कंपनी!", F(86 * k), (255, 210, 50), 8)
    if 19.7 < t < 21.0:
        k = back((t - 19.7) / .3)
        outlined(d, (W // 2, 260), "अब बदला...", F(110 * k), (255, 60, 60), 12)
    # captions
    v = speaking(t)
    if v and t < 29.45:
        k = back((t - v["start"] + .05) / .2)
        outlined(d, (W // 2, 1640), v["who"], F(54 * k), (255, 215, 40), 8)
        f = F(64 * k)
        for j, ln in enumerate(wrap(d, v["text"], f, 960)):
            outlined(d, (W // 2, 1730 + j * 84), ln, f, (255, 255, 255), 9)
    # end card
    if t > 29.45:
        u = t - 29.45
        k = back((u - .25) / .3)
        if u > .25:
            f = F(106 * k)
            txt = "PART 2 चाहिए?"
            outlined(d, (W // 2 - 80, 1600), txt, f, (255, 225, 40), 12)
            global EMO
            if EMO is None: EMO = emoji("😱", 130)
            tw = d.textlength(txt, font=f)
            e = EMO.resize((max(1, int(130 * k)), max(1, int(130 * k))))
            im.paste(e, (int(W // 2 - 80 + tw / 2 + 18), int(1600 - e.height / 2)), e)
            outlined(d, (W // 2, 1760), "Follow करो - CuriosityBox", F(56 * min(1, k)), (255, 255, 255), 7)
    return np.asarray(im.convert("RGB")).tobytes()


def thumbnail(path):
    t = 11.0
    im = Image.frombytes("RGB", (W, H), render(int(t * FPS), text=False))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 1480, W, H], fill=(0, 0, 0, 200))
    d.rectangle([0, 0, W, 470], fill=(0, 0, 0, 120))
    outlined(d, (W // 2, 170), "गरीब समझकर ठुकराया...", F(84), (255, 255, 255), 10)
    outlined(d, (W // 2, 320), "निकला अरबपति!", F(120), (255, 210, 40), 12)
    outlined(d, (W // 2, 1650), "500 अरब का मालिक", F(92), (255, 255, 255), 10)
    outlined(d, (W // 2, 1800), "बदला | PART 1", F(72), (255, 70, 70), 8)
    im.save(path)


if __name__ == "__main__":
    out = sys.argv[1]
    if len(sys.argv) > 2:
        if sys.argv[2] == "thumb":
            thumbnail(out); sys.exit()
        Image.frombytes("RGB", (W, H), render(int(float(sys.argv[2]) * FPS))).save(out); sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", os.path.join(HERE, "aud", "mix.wav"), "-c:v", "libx264", "-preset", "medium",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(render, range(NF), chunksize=4):
            ff.stdin.write(b)
    ff.stdin.close(); ff.wait()
    print("done", out)
