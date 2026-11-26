#!/usr/bin/env python3
"""Build a short quiz-style video from a beat spec (JSON), reusing finished 1080x1920 cuts.

  python build.py SPEC.json OUT.mp4
Each beat: {"say": narration (TTS text), "caps": [caption phrases], "clips": [[path, in_s], ...],
            "pause": seconds after the line, "sfx": "q"|"tick"|"ding"|"boom"|null, "big": "text" (optional big word),
            "panel": ["①10分","②5分","③2分"] (optional option panel)}
Narration: Kokoro (local, jm_kumo). Captions: Noto Serif CJK Bold, white + thick black outline, {R}/{Y} emphasis.
"""
import json, os, subprocess, sys, wave
import numpy as np
from scipy import signal
import pyloudnorm as pyln

SPEC, OUT = sys.argv[1], sys.argv[2]
S = json.load(open(SPEC, encoding="utf-8"))
W, H, FPS, SR = 1080, 1920, 30, 48000
TMP = OUT + "_tmp"; os.makedirs(TMP, exist_ok=True)
TTS_PY = "/tmp/claude-0/tts312/bin/python"; KK = "/tmp/claude-0/tts/kk.py"


def run(c, **k):
    return subprocess.run(c, check=True, **k)


def read(path, ch=1):
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).T.copy()


# ---- 1) narration per beat ----
voice = S.get("voice", "jm_kumo"); speed = str(S.get("speed", 1.05))
lines = []
for k, b in enumerate(S["beats"]):
    if not b.get("say"):
        lines.append(None); continue
    txt = os.path.join(TMP, f"l{k}.txt"); wav = os.path.join(TMP, f"l{k}.wav")
    open(txt, "w", encoding="utf-8").write(b["say"])
    if not os.path.exists(wav):
        env = dict(os.environ, SSL_CERT_FILE="/root/.ccr/ca-bundle.crt")
        run([TTS_PY, KK, txt, wav, voice, speed], capture_output=True, env=env)
    a = read(wav)[0]
    nz = np.where(np.abs(a) > 0.004)[0]
    a = a[max(0, nz[0] - 1200): nz[-1] + 9600] if len(nz) else a
    lines.append(a)

# ---- 2) timeline ----
t = float(S.get("lead", 0.25)); beats = []
for b, a in zip(S["beats"], lines):
    d = (len(a) / SR if a is not None else 0.0)
    dur = max(d + b.get("pause", 0.35), b.get("min", 0.0))
    beats.append(dict(b, start=t, speech=d, dur=dur)); t += dur
TOTAL = round(t + S.get("tail", 0.6), 2)
beats[-1]["dur"] += S.get("tail", 0.6)

# ---- 3) video: split each beat's span across its clips ----
parts = []
for k, b in enumerate(beats):
    n = len(b["clips"]); f0 = round(b["start"] * FPS); f1 = round((b["start"] + b["dur"]) * FPS)
    edges = np.linspace(f0, f1, n + 1).round().astype(int)
    for j, (path, ins) in enumerate(b["clips"]):
        nf = int(edges[j + 1] - edges[j]); dst = os.path.join(TMP, f"v{k:02d}_{j}.mp4")
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(ins), "-i", path, "-vf",
             f"scale={W}:{H},fps={FPS},tpad=stop_mode=clone:stop_duration=5", "-frames:v", str(nf), "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", dst])
        parts.append(dst)
lst = os.path.join(TMP, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
video = os.path.join(TMP, "video.mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])

# ---- 4) audio: narration + sfx + bgm ----
n = int(TOTAL * SR); narr = np.zeros(n); sfx = np.zeros(n)
for b, a in zip(beats, lines):
    if a is not None:
        i = int(b["start"] * SR); narr[i:i + len(a)] += a[: n - i]


def tone(f, d, decay=6.0, h=(1, 0.3, 0.1)):
    tt = np.arange(int(d * SR)) / SR
    return sum(w * np.sin(2 * np.pi * f * (k + 1) * tt) for k, w in enumerate(h)) * np.exp(-decay * tt)


rng = np.random.default_rng(7)
SFX = {
    "q": np.concatenate([tone(392, 0.18, 10), tone(523, 0.5, 5)]) * 0.5,
    "ding": (tone(1318, 0.9, 4) + tone(1760, 0.9, 5) * 0.6) * 0.45,
    "boom": signal.sosfilt(signal.butter(2, 120, "lp", fs=SR, output="sos"), rng.standard_normal(int(1.6 * SR))) * np.exp(-np.arange(int(1.6 * SR)) / SR * 3) * 2.5,
    "whoosh": signal.sosfilt(signal.butter(2, [400, 3000], "bp", fs=SR, output="sos"), rng.standard_normal(int(0.5 * SR))) * np.sin(np.linspace(0, np.pi, int(0.5 * SR))) * 0.5,
}
for b in beats:
    s = b.get("sfx")
    if s == "tick":
        for k in range(int(b["dur"])):
            i = int((b["start"] + k) * SR); c = tone(2000, 0.06, 60, (1,)) * 0.5; sfx[i:i + len(c)] += c[: n - i]
    elif s:
        c = SFX[s]; i = int(b["start"] * SR); sfx[i:i + len(c)] += c[: n - i]
tt = np.arange(n) / SR
bgm = sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((55, 0), (82.4, 1), (116.5, 2))) / 3
bgm = signal.sosfilt(signal.butter(2, 300, "lp", fs=SR, output="sos"), bgm) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * tt))
m = pyln.Meter(SR)
def lufs(x, target):
    l = m.integrated_loudness(x); return x * 10 ** ((target - l) / 20)
narr = lufs(narr, -16); sfx = lufs(sfx, -26) if np.abs(sfx).max() > 0 else sfx; bgm = lufs(bgm, -32)
env = signal.sosfilt(signal.butter(2, 6, "lp", fs=SR, output="sos"), np.abs(narr)); env = np.clip(env / (np.percentile(env, 99) + 1e-9), 0, 1)
mix = narr + sfx + bgm * (1 - 0.5 * env)
st2 = np.stack([mix, mix])


def limiter(x, ceiling_db=-2.0, look=0.005, release=0.12):
    from scipy.ndimage import minimum_filter1d
    c = 10 ** (ceiling_db / 20); nn = x.shape[1]
    up = signal.resample_poly(x, 4, 1, axis=1)
    pk = np.max(np.abs(up), axis=0)[: 4 * nn].reshape(-1, 4).max(axis=1)
    need = minimum_filter1d(np.minimum(1.0, c / np.maximum(pk, 1e-9)), size=2 * int(look * SR) + 1)
    B = 48; nb = -(-nn // B)
    blk = np.pad(need, (0, nb * B - nn), constant_values=1.0).reshape(nb, B).min(axis=1)
    r = np.exp(-B / (release * SR)); g = np.empty(nb); v = 1.0
    for i, b_ in enumerate(blk):
        v = b_ if b_ < v else b_ + (v - b_) * r; g[i] = v
    return x * np.repeat(g, B)[:nn]


for _ in range(4):
    st2 = st2 * 10 ** ((-14 - m.integrated_loudness(st2.T)) / 20)
    st2 = limiter(st2)
wavp = os.path.join(TMP, "mix.wav")
with wave.open(wavp, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st2.T, -1, 1) * 32767).astype("<i2").tobytes())

# ---- 5) captions / title bar / panels (ASS) ----
def ts(x):
    x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"
def col(s):
    return s.replace("{R}", r"{\c&H2B2BE8&}").replace("{Y}", r"{\c&H00D9FF&}").replace("{/}", r"{\c&HFFFFFF&}")
def units(s):
    import re; s = re.sub(r"\{[^}]*\}", "", s); return sum(0.6 if ord(c) < 0x2E80 else 1.0 for c in s)
ev = []
bar = S["title_bar"]
bl = bar.split("\\N")
ev.append(f"Dialogue: 0,{ts(0)},{ts(TOTAL)},Bar,,0,0,0,,{{\\pos({W//2},{330 + 60*(len(bl)-1)})\\fs{int(min(120, 960/max(units(x) for x in bl)))}}}{col(bar)}")
ev.append(f"Dialogue: 0,{ts(0)},{ts(TOTAL)},Note,,0,0,0,,{{\\pos({W//2},1360)}}{S.get('note','')}")
for b in beats:
    caps = b.get("caps") or []
    if caps:
        span = max(b["speech"], 0.8); w_ = np.array([max(1.0, units(c)) for c in caps]); edges = b["start"] + np.concatenate([[0], np.cumsum(w_) / w_.sum() * span])
        for j, c in enumerate(caps):
            e = edges[j + 1] if j < len(caps) - 1 else b["start"] + b["dur"]
            size = int(min(92, 860 / units(c)))
            ev.append(f"Dialogue: 2,{ts(edges[j])},{ts(e)},Cap,,0,0,0,,{{\\pos({W//2},1020)\\fs{size}\\fad(60,40)}}{col(c)}")
    if b.get("big"):
        size = int(min(220, 900 / units(b["big"])))
        ev.append(f"Dialogue: 3,{ts(b['start'])},{ts(b['start']+b['dur'])},Big,,0,0,0,,{{\\pos({W//2},{S.get('big_y', 760)})\\fs{size}\\fad(40,60)\\t(0,140,\\fscx112\\fscy112)\\t(140,260,\\fscx100\\fscy100)}}{col(b['big'])}")
    if b.get("panel"):
        for j, o in enumerate(b["panel"]):
            y = S.get("panel_y", 960) + j * 170
            ev.append(f"Dialogue: 1,{ts(b['start'])},{ts(b['start']+b['dur'])},Panel,,0,0,0,,{{\\pos({W//2},{y})\\fad(80,40)}}{col(o)}")
src_note = S.get("source", "")
if src_note:
    ev.append(f"Dialogue: 0,{ts(0)},{ts(TOTAL)},Note,,0,0,0,,{{\\pos({W//2},1405)}}{src_note}")
ass = os.path.join(TMP, "t.ass")
F = "Noto Serif CJK JP"
open(ass, "w", encoding="utf-8").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Bar,{F},96,&H0000D9FF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,3,22,0,5,40,40,0,1
Style: Cap,{F},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,2,0,1,9,3,5,60,60,0,1
Style: Big,{F},200,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,4,0,1,14,5,5,40,40,0,1
Style: Panel,{F},140,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,2,0,3,16,0,5,60,60,0,1
Style: Note,{F},28,&H00F0F0F0,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,3,1,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

# ---- 6) encode ----
run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wavp, "-filter_complex",
     f"[0:v]ass={ass}:fontsdir=/usr/share/fonts/opentype/noto,format=yuv420p[v]", "-map", "[v]", "-map", "1:a",
     "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-preset", "slow", "-crf", "21", "-maxrate", "6500k",
     "-bufsize", "13000k", "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-movflags", "+faststart",
     "-t", f"{TOTAL:.2f}", OUT])
print("wrote", OUT, "total", TOTAL)
json.dump([dict(start=b["start"], dur=b["dur"], say=b.get("say", "")) for b in beats], open(OUT + ".timeline.json", "w"), ensure_ascii=False, indent=1)
