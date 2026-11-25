#!/usr/bin/env python3
"""Final assembly of the Nankai Trough short.

  python compose.py EDIT.json CUTDIR AUDIODIR OUT.mp4

CUTDIR   finished 1080x1920/30fps cuts from post.py (<id>.mp4, in edit.json "cuts" order)
AUDIODIR narration file named in edit.json, sfx.wav and bgm.wav from sound.py
Telops: Noto Serif CJK JP Bold, white with a thick black outline, red/yellow emphasis, auto-fitted
to the centre safe area. Audio: narration ducks the bed and music; master at -14 LUFS, <= -1.5 dBTP.
"""
import json, os, subprocess, sys, wave
import numpy as np
import pyloudnorm as pyln
from scipy import signal

EDIT, CUTS, AUD, OUT = sys.argv[1:5]
E = json.load(open(EDIT, encoding="utf-8"))
W, H, FPS, TOTAL = E["width"], E["height"], E["fps"], E["total"]
SR = 48000
FONT = "Noto Serif CJK JP"
TMP = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_compose_tmp")
os.makedirs(TMP, exist_ok=True)


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------------- video: concatenate cuts ----------------
lst = os.path.join(TMP, "cuts.txt")


def nframes(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


with open(lst, "w") as f:
    for k, c in enumerate(E["cuts"]):
        src = os.path.abspath(os.path.join(CUTS, c[0] + ".mp4"))
        n = round(c[2] * FPS) - round(c[1] * FPS)
        off = c[4] if len(c) > 4 else 0.0
        if off or nframes(src) != n:
            dst = os.path.join(TMP, f"trim_{k:02d}_{c[0]}.mp4")
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{off:.3f}", "-i", src, "-frames:v", str(n), "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-r", str(FPS), dst])
            src = dst
        f.write(f"file '{src}'\n")
video = os.path.join(TMP, "video.mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])


# ---------------- audio ----------------
def read_audio(path, ch=2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).T.copy()


n_total = int(round(TOTAL * SR))
TEMPO = float(E["narration"].get("tempo", 1.0))


def read_narr(path):
    af = ["-af", f"atempo={TEMPO}"] if TEMPO != 1.0 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, *af, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


narr_src = read_narr(os.path.join(AUD, E["narration"]["file"]))
narr = np.zeros(n_total, np.float32)
for a, b, p in E["narration"]["lines"]:
    seg = narr_src[int(a / TEMPO * SR):int(b / TEMPO * SR)].copy()
    fl = int(0.008 * SR)
    seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
    i = int(round(p * SR))
    narr[i:i + len(seg)] += seg[: n_total - i]


def fit(x, n):
    y = np.zeros((2, n), np.float32)
    m = min(n, x.shape[1]); y[:, :m] = x[:, :m]
    return y


sfx = fit(read_audio(os.path.join(AUD, "sfx.wav")), n_total)
bgm = fit(read_audio(os.path.join(AUD, "bgm.wav")), n_total)
meter = pyln.Meter(SR)


def set_lufs(x, target):
    l = meter.integrated_loudness(x.T if x.ndim == 2 else x)
    return x * (10 ** ((target - l) / 20)), l


narr, l_n = set_lufs(narr, -16.0)
sfx, l_s = set_lufs(sfx, -24.0)
bgm, l_b = set_lufs(bgm, -31.0)
# ducking envelope from the narration (attack 30 ms, release 450 ms)
env = np.abs(narr)
env = signal.sosfilt(signal.butter(2, 8, "lp", fs=SR, output="sos"), env)
env = env / (np.percentile(env[env > 1e-4], 95) + 1e-9)
env = np.clip(env, 0, 1)
att, rel = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.45 * SR))
sm = np.zeros_like(env); v = 0.0
for i in range(0, len(env), 48):           # 1 ms control rate
    tgt = env[i]
    v = tgt + (v - tgt) * (att ** 48 if tgt > v else rel ** 48)
    sm[i:i + 48] = v
duck_b = 1 - 0.55 * sm
duck_s = 1 - 0.40 * sm
duck_s[: int(0.6 * SR)] = 1.0                # never duck the opening impact
mix = np.stack([narr, narr]) * 1.0 + sfx * duck_s + bgm * duck_b


def limiter(x, ceiling_db=-2.0, look=0.005, release=0.12):
    """Look-ahead peak limiter on a 4x-oversampled (true-peak) estimate, 1 ms control rate."""
    from scipy.ndimage import minimum_filter1d
    c = 10 ** (ceiling_db / 20)
    n = x.shape[1]
    up = signal.resample_poly(x, 4, 1, axis=1)
    pk = np.max(np.abs(up), axis=0)[: 4 * n].reshape(-1, 4).max(axis=1)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    need = minimum_filter1d(need, size=2 * int(look * SR) + 1)
    B = 48
    nb = -(-n // B)
    blk = np.pad(need, (0, nb * B - n), constant_values=1.0).reshape(nb, B).min(axis=1)
    r = np.exp(-B / (release * SR))
    g = np.empty(nb); v = 1.0
    for i, b in enumerate(blk):
        v = b if b < v else b + (v - b) * r
        g[i] = v
    return x * np.repeat(g, B)[:n]


for _ in range(3):
    l = meter.integrated_loudness(mix.T)
    mix = mix * (10 ** ((-14.0 - l) / 20))
    mix = limiter(mix, -2.0)
l_final = meter.integrated_loudness(mix.T)
tp = 20 * np.log10(np.max(np.abs(signal.resample_poly(mix, 4, 1, axis=1))) + 1e-12)
print(f"loudness: narr {l_n:.1f} sfx {l_s:.1f} bgm {l_b:.1f} -> master {l_final:.2f} LUFS, true peak {tp:.2f} dBTP")
wav = os.path.join(TMP, "mix.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype("<i2").tobytes())


# ---------------- telops (ASS) ----------------
def line_map(idx, t):
    a, b, p = E["narration"]["all_lines"][idx] if "all_lines" in E["narration"] else E["narration"]["lines"][idx]
    return p + (t - a) / TEMPO


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def text_units(s):
    import re
    s = re.sub(r"\{[^}]*\}", "", s)
    return sum(0.62 if ord(ch) < 0x2E80 and ch not in "“”" else 1.0 for ch in s)


def colorize(s):
    return s.replace("{R}", r"{\c&H2B2BE8&}").replace("{Y}", r"{\c&H00D9FF&}").replace("{/}", r"{\c&HFFFFFF&}")


SIZES = {"title": 112, "normal": 92, "big": 140}
MAXW = 860
ev = []
tel = []
for t in E["telops"]:
    text, idx, s, e = t[0], t[1], t[2], t[3]
    style = t[4] if len(t) > 4 else "normal"
    note = t[5] if len(t) > 5 else None
    tel.append([line_map(idx, s), line_map(idx, e), text, style, note])
tel.sort(key=lambda x: x[0])
for i in range(len(tel) - 1):                      # never overlap: clamp to next start
    tel[i][1] = min(tel[i][1], tel[i + 1][0])
for s, e, text, style, note in tel:
    size = SIZES[style]
    size = int(min(size, MAXW / max(1.0, text_units(text))))
    outline = max(6, int(size * 0.085))
    y = 1060 if style == "title" else 940
    anim = r"\fad(70,50)\t(0,110,\fscx106\fscy106)\t(110,200,\fscx100\fscy100)"
    ev.append(f"Dialogue: 2,{ts(s)},{ts(e)},Telop,,0,0,0,,{{\\pos({W // 2},{y})\\fs{size}\\bord{outline}{anim}}}{colorize(text)}")
# source notes: merge contiguous telops that share a note
groups = []
for s, e, text, style, note in tel:
    if not note:
        continue
    if groups and groups[-1][2] == note and s - groups[-1][1] < 0.6:
        groups[-1][1] = e
    else:
        groups.append([s, e, note])
for s, e, note in groups:
    txt = E["src_notes"].get(note, E["src_main"])
    size = int(min(28, MAXW / text_units(txt)))
    ev.append(f"Dialogue: 1,{ts(s)},{ts(e + 0.3)},Note,,0,0,0,,{{\\pos({W // 2},1352)\\fs{size}\\fad(120,120)}}{txt}")
ev.append(f"Dialogue: 0,{ts(0)},{ts(TOTAL)},Disc,,0,0,0,,{{\\pos({W // 2},1300)}}{E['disclaimer']}")
ass = os.path.join(TMP, "telop.ass")
with open(ass, "w", encoding="utf-8") as f:
    f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Telop,{FONT},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,2,0,1,8,3,5,60,60,0,1
Style: Note,{FONT},28,&H00F0F0F0,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,3,1,5,60,60,0,1
Style: Disc,{FONT},30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,3,1,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

# ---------------- final encode ----------------
run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav,
     "-filter_complex", f"[0:v]ass={ass}:fontsdir=/usr/share/fonts/opentype/noto,format=yuv420p[v]",
     "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-level", "4.2", "-preset", "slow",
     "-crf", "21", "-maxrate", "9M", "-bufsize", "18M", "-r", str(FPS), "-g", str(FPS * 2),
     "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
     "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart",
     "-t", f"{TOTAL:.3f}", OUT])
print("wrote", OUT)
