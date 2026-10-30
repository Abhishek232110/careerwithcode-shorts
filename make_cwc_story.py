#!/usr/bin/env python3
"""Render a 31-60 second CareerWithCode YouTube Short made of several poster scenes with a Hindi voiceover.

Abhishek (Oct 30 2026): "generate multiple images and make 30 sec shorts using those images and use
voice to explain this". Each scene is one CareerWithCode cartoon poster (make_cwc_poster.py design);
its "say" line is spoken over it, and the scene lasts as long as its line. Scenes cut with a short
crossfade; a quiet music bed sits under the voice. The whole Short is padded to at least 31 s.

Voice: Kokoro TTS (offline, Hindi voice hm_omega). Model files are fetched once from the
kokoro-onnx GitHub release into ~/.cache/kokoro (pip install kokoro-onnx soundfile first).

Usage: python3 make_cwc_story.py spec.json out.mp4
       python3 make_cwc_story.py spec.json out.jpg --still     (one scene fully built: for Facebook)

spec = {
  "voice": "hm_omega",                 # hm_omega | hm_psi (male), hf_alpha | hf_beta (female)
  "speed": 1.12,
  "still_scene": 4,                    # which scene becomes the Facebook image (default 0)
  "scenes": [                          # 4-6 scenes; each is a make_cwc_poster.py spec plus "say"
    {"title": [...], "list": {...}, "note": "...", "banner": "...", "face": "thinking",
     "palette": "blue",
     "say": "क्या आप जानते हो? Go में slice असल में array की एक खिड़की है।"},
    ...
  ]
}
"say" is Hindi in Devanagari; keep code words (slice, append, Python) in English letters.
One or two short sentences per scene (about 6-9 s spoken). Aim for 35-50 s in total.
"""
import json, os, subprocess, sys, urllib.request, wave
import numpy as np
from PIL import Image

import make_short
import make_cwc_poster as P

FPS, W, H = P.FPS, P.W, P.H
SR = 24000
XFADE = 0.3          # crossfade between scenes
GAP = 0.6            # pause after each line
CACHE = os.path.expanduser("~/.cache/kokoro")
URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.int8.onnx", "voices-v1.0.bin"]


def tts():
    os.makedirs(CACHE, exist_ok=True)
    for f in FILES:
        p = os.path.join(CACHE, f)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            urllib.request.urlretrieve(URL + f, p + ".part"); os.replace(p + ".part", p)
    from kokoro_onnx import Kokoro
    return Kokoro(*[os.path.join(CACHE, f) for f in FILES])


def voice_lines(spec):
    k = tts()
    out = []
    for sc in spec["scenes"]:
        s, sr = k.create(sc["say"], voice=spec.get("voice", "hm_omega"),
                         speed=spec.get("speed", 1.05), lang="hi")
        assert sr == SR
        out.append(np.asarray(s, dtype=np.float32))
    return out


def plan(spec, lines):
    """Scene lengths in seconds: each line plus a pause; the last scene stretches the Short past 30 s."""
    lens = [max(4.0, len(a) / SR + GAP + 0.4) for a in lines]
    total = sum(lens)
    if total < 31.5:
        lens[-1] += 31.5 - total
    if sum(lens) > 60:
        raise SystemExit(f"voiceover too long ({sum(lens):.1f} s); shorten the 'say' lines")
    return lens


def scene_poster(sc, dur):
    p = P.Poster(sc, dur)
    # fit the panel rows and banner inside the scene, finishing about 1.5 s before the cut
    n = len(p.row_t)
    end = max(1.6, dur - 1.5)
    if p.panel:
        p.row_t = [0.9 + i * (end - 2.2) / max(1, n) for i in range(n)]
        p.banner_t = min(p.banner_t, end - 0.4)
    else:
        p.banner_t = min(p.banner_t, 1.2)
    return p


def write_audio(path, lines, lens, total):
    voice = np.zeros(int(SR * total) + SR, dtype=np.float32)
    t = 0.0
    for a, d in zip(lines, lens):
        i = int((t + 0.25) * SR)
        voice[i:i + len(a)] += a
        t += d
    peak = np.abs(voice).max() or 1
    voice = (voice / peak * 0.9 * 32767).astype("<i2")
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(voice.tobytes())


def main(spec_path, out):
    spec = json.load(open(spec_path))
    lines = voice_lines(spec)
    lens = plan(spec, lines)
    total = sum(lens)
    dur = int(np.ceil(total))
    posters = [scene_poster(sc, d) for sc, d in zip(spec["scenes"], lens)]
    starts = np.cumsum([0] + lens[:-1])

    write_audio(out + ".voice.wav", lines, lens, total)
    make_short.DUR = dur
    make_short.music(out + ".music.wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", out + ".voice.wav", "-i", out + ".music.wav",
                          "-filter_complex", "[2:a]volume=0.22[m];[1:a][m]amix=inputs=2:duration=longest:normalize=0[a]",
                          "-map", "0:v", "-map", "[a]",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "21",
                          "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for f in range(int(total * FPS)):
        t = f / FPS
        i = max(j for j in range(len(starts)) if starts[j] <= t)
        img = posters[i].frame(t - starts[i])
        if i + 1 < len(posters) and t > starts[i + 1] - XFADE:
            a = (t - (starts[i + 1] - XFADE)) / XFADE
            img = Image.blend(img, posters[i + 1].frame(0.0), a)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    for s in (".voice.wav", ".music.wav"):
        os.remove(out + s)
    print(f"{out}: {total:.1f} s, {len(lens)} scenes")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[3] == "--still":
        spec = json.load(open(sys.argv[1]))
        sc = spec["scenes"][spec.get("still_scene", 0)]
        P.Poster(sc, 35).frame(34.0).save(sys.argv[2], quality=92)
    else:
        main(sys.argv[1], sys.argv[2])
