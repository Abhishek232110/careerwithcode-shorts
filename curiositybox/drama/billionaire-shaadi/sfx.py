# Builds music + sfx + voice mix for the Billionaire Shaadi drama short
import numpy as np, wave, json, os
SR = 44100
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(D, "aud")
T = json.load(open(os.path.join(D, "timeline.json")))
N = int(T["total"] * SR); rng = np.random.default_rng(5)


def rd(p, speed=1.0):
    w = wave.open(p); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    if w.getnchannels() == 2: x = x.reshape(-1, 2).mean(1)
    n = int(len(x) * SR / sr / speed)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def add(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= N: return
    x = x[:N - i]; buf[i:i + len(x)] += x * g


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


def lp(x, k): return np.convolve(x, np.ones(k) / k, "same")


def boom():
    n = int(1.6 * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (110 * np.exp(-t * 3) + 32) * t) * env(n, .004, .55)
    return s * 1.1 + lp(rng.normal(0, 1, n), 40) * env(n, .002, .25) * 1.5


def whoosh():
    n = int(.4 * SR); x = rng.normal(0, 1, n); out = np.zeros(n); y = 0
    for i in range(n):
        a = .02 + .3 * np.sin(np.pi * i / n); y += a * (x[i] - y); out[i] = y
    return out * np.sin(np.pi * np.arange(n) / n) * 2


def thud():
    n = int(.45 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (85 * np.exp(-t * 7) + 40) * t) * env(n, .003, .12) + lp(rng.normal(0, 1, n), 25) * env(n, .002, .06) * 1.5


def horn():
    n = int(.55 * SR); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 415 * t)) * .5 + np.sign(np.sin(2 * np.pi * 523 * t)) * .5
    return lp(s, 6) * np.minimum(1, np.minimum(t / .02, (n / SR - t) / .05)) * .35


def engine(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + 30 * np.exp(-t * 1.5)
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .4 + lp(rng.normal(0, 1, n), 60) * 1.5
    return lp(s, 20) * np.minimum(1, t / .3) * np.minimum(1, (dur - t) / .6)


def heartbeat():
    out = np.zeros(int(.8 * SR))
    for o in (0, .22):
        n = int(.25 * SR); t = np.arange(n) / SR
        b = np.sin(2 * np.pi * (60 * np.exp(-t * 8) + 35) * t) * env(n, .003, .07)
        i = int(o * SR); out[i:i + n] += b * (1 if o == 0 else .7)
    return out


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200 + 1400 * (t / dur) ** 2
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * .25 + lp(rng.normal(0, 1, n), 4) * .3) * (t / dur) ** 2


def sting():
    n = int(2.0 * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * f * 1.004 * t)) for f in (146.8, 174.6, 220, 293.7, 349.2)) / 5
    return s * env(n, .01, .8) * 1.3


# ---- music: dramatic D minor, 92 bpm, rises in scene 2 and 3, drops out for the photo
bpm = 92; beat = 60 / bpm; t = np.arange(N) / SR
chords = [[73.4, 146.8, 174.6, 220], [58.3, 116.5, 146.8, 174.6], [49.0, 98.0, 116.5, 146.8], [55.0, 110, 138.6, 164.8]]
music = np.zeros(N)
bar = 4 * beat
for k in range(int(T["total"] / bar) + 2):
    s0 = k * bar; i0 = int(s0 * SR); n = int(bar * SR * 1.05)
    tt = np.arange(n) / SR; ch = chords[k % 4]
    pad = sum(sum(np.sin(2 * np.pi * f * h * tt) / h for h in (1, 2, 3)) * (.6 if j == 0 else .35) for j, f in enumerate(ch))
    pad *= np.minimum(1, tt / .35) * np.minimum(1, (n / SR - tt) / .3)
    seg = pad[:max(0, N - i0)]; music[i0:i0 + len(seg)] += seg * .12
for k in range(int(T["total"] / beat) + 1):
    s0 = k * beat
    inten = 0.5 if s0 < 8.4 else (1.0 if s0 < 19.7 else 1.2)
    n = int(.4 * SR); tt = np.arange(n) / SR
    if k % 2 == 0:  # dhol bass
        x = np.sin(2 * np.pi * (95 * np.exp(-tt * 9) + 55) * tt) * env(n, .002, .15)
        add(music, x, s0, .55 * inten)
    if s0 > 8.4:  # slap on the off-beat
        x = lp(rng.normal(0, 1, n), 3) * env(n, .001, .03) + np.sin(2 * np.pi * 330 * tt) * env(n, .001, .05) * .5
        add(music, x, s0 + beat / 2, .25 * inten)
music[int(29.35 * SR):] = 0  # silence for the photo reveal

# ---- voices (with music ducking)
voice = np.zeros(N)
for v in T["voices"]:
    add(voice, rd(os.path.join(A, v["name"] + ".wav")), v["start"], 1.0)
duck = lp((np.abs(voice) > .01).astype(float), int(.25 * SR))
duck = 1 - .55 * np.clip(duck * 4, 0, 1)
mix = music * duck * .9 + voice

fx = np.zeros(N)
for st, nm in T["laughs"]:
    add(fx, rd(os.path.join(A, nm + ".wav"), speed=rng.uniform(.95, 1.15)), st, .32)
for c in T["cuts"]: add(fx, whoosh(), c - .15, .35)
for b in T["booms"]: add(fx, boom(), b, .7)
add(fx, engine(2.0), 8.4, .5); add(fx, engine(1.6), 8.8, .35)
add(fx, horn(), 8.9, 1.0); add(fx, horn(), 9.35, .8)
for d in (9.35, 9.5, 9.62): add(fx, thud(), d, .5)  # car doors
for k in range(6): add(fx, thud(), 9.55 + k * .12, .2)  # footsteps
add(fx, thud(), 20.35, 1.0)  # father falls to knees
for k in range(4): add(fx, heartbeat(), 26.6 + k * .7, .9)
add(fx, riser(1.4), 28.05, .6)
add(fx, sting(), 29.45, .9)
mix += fx
mix /= max(1e-6, np.abs(mix).max()) / .93
w = wave.open(os.path.join(A, "mix.wav"), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close(); print("mix ok")
