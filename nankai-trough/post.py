#!/usr/bin/env python3
"""Turn each generated 16-frame clip into a finished 1080x1920 / 30 fps cut.

  python post.py EDIT.json CLIPDIR OUTDIR [--ids 01a,02b] [--pick 05a=05a_v1]

Per cut: motion-interpolate the 8 fps frames to fill the cut's slot at 30 fps, then a single
resample to 1080x1920 with the camera move for that style (earthquake shake with long-period
sway, running bob, handheld drift, slow push-in), a film grade per time of day, grain and vignette.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("edit"); ap.add_argument("clips"); ap.add_argument("out")
ap.add_argument("--ids"); ap.add_argument("--pick", action="append", default=[])
a = ap.parse_args()
E = json.load(open(a.edit, encoding="utf-8"))
W, H, FPS = E["width"], E["height"], E["fps"]
pick = dict(p.split("=") for p in a.pick)
os.makedirs(a.out, exist_ok=True)


def smooth_noise(n, fps, f_lo, f_hi, seed):
    """Band-limited noise in [-1, 1] (sum of a few random sines in the band)."""
    r = np.random.default_rng(seed)
    t = np.arange(n) / fps
    x = np.zeros(n)
    for _ in range(5):
        f = r.uniform(f_lo, f_hi)
        x += np.sin(2 * np.pi * f * t + r.uniform(0, 2 * np.pi)) * r.uniform(0.5, 1.0)
    return x / (np.max(np.abs(x)) + 1e-9)


def camera(style, n, seed):
    """Return per-frame (dx, dy, rot_deg, zoom)."""
    t = np.arange(n) / FPS
    z = np.full(n, 1.06)
    dx = np.zeros(n); dy = np.zeros(n); rot = np.zeros(n)
    hand = lambda amp, ramp, lo=0.3, hi=1.2: (smooth_noise(n, FPS, lo, hi, seed) * amp,
                                               smooth_noise(n, FPS, lo, hi, seed + 1) * amp * 0.7,
                                               smooth_noise(n, FPS, lo * 0.8, hi * 0.8, seed + 2) * ramp)
    if style in ("quake", "quake_peak", "aftershake"):
        k = {"quake": 1.0, "quake_peak": 1.45, "aftershake": 1.0}[style]
        decay = np.exp(-t / 0.9) * 0.85 + 0.15 if style == "aftershake" else np.ones(n)
        sway_x = 30 * np.sin(2 * np.pi * 0.42 * t + seed) + 12 * np.sin(2 * np.pi * 0.9 * t + 2 * seed)
        sway_y = 14 * np.sin(2 * np.pi * 0.37 * t + 0.5 * seed)
        jit_x = smooth_noise(n, FPS, 4.5, 9.0, seed + 3) * 16
        jit_y = smooth_noise(n, FPS, 5.0, 10.0, seed + 4) * 13
        dx = (sway_x + jit_x) * k * decay
        dy = (sway_y + jit_y) * k * decay
        rot = (0.55 * np.sin(2 * np.pi * 0.47 * t + seed) + smooth_noise(n, FPS, 3, 7, seed + 5) * 0.35) * k * decay
        z = np.full(n, 1.10 + 0.06 * (k - 1))
    elif style == "run":
        dy = 15 * np.abs(np.sin(np.pi * 3.0 * t)) - 7 + smooth_noise(n, FPS, 6, 11, seed) * 3
        dx = 9 * np.sin(np.pi * 1.5 * t + seed) + smooth_noise(n, FPS, 0.5, 1.5, seed + 1) * 6
        rot = 0.7 * np.sin(np.pi * 1.5 * t + seed + 0.6)
        z = np.full(n, 1.10)
    elif style in ("handheld", "night", "shelter"):
        amp = {"handheld": 8, "night": 6, "shelter": 5}[style]
        dx, dy, rot = hand(amp, 0.25)
        z = np.linspace(1.06, 1.085, n)
    elif style in ("dawn", "dawn_push", "ominous"):
        dx, dy, rot = hand(4, 0.12, 0.2, 0.7)
        z0, z1 = {"dawn": (1.05, 1.09), "dawn_push": (1.04, 1.15), "ominous": (1.07, 1.13)}[style]
        z = z0 + (z1 - z0) * (0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, n)))
    return dx, dy, rot, z


GRADES = {
    #        gain RGB             lift RGB               sat   contrast exposure
    "dusk":    ((1.06, 1.00, 0.90), (0.010, 0.022, 0.035), 0.90, 1.08, 1.00),
    "night":   ((0.82, 0.93, 1.12), (0.004, 0.010, 0.022), 0.72, 1.10, 0.78),
    "shelter": ((1.08, 0.98, 0.84), (0.012, 0.010, 0.010), 0.85, 1.04, 0.92),
    "dawn":    ((1.05, 0.99, 0.96), (0.030, 0.026, 0.030), 0.92, 0.96, 1.02),
    "ominous": ((0.92, 0.95, 1.04), (0.006, 0.008, 0.014), 0.55, 1.12, 0.80),
}
STYLE_GRADE = {"quake": "dusk", "quake_peak": "dusk", "aftershake": "dusk", "run": "dusk", "handheld": "dusk",
               "night": "night", "shelter": "shelter", "dawn": "dawn", "dawn_push": "dawn", "ominous": "ominous"}

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
R2 = ((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.6
VIGNETTE = (1 - 0.30 * np.clip(R2, 0, 1.6))[..., None].astype(np.float32)


def grade(img, g, rng, flash=0.0, fade_mul=1.0):
    gain, lift, sat, con, expo = GRADES[g]
    x = img.astype(np.float32) / 255.0
    x = x * expo
    lum = (x @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    x = lum + (x - lum) * sat
    x = (x - 0.5) * con + 0.5
    x = x * np.array(gain, np.float32) + np.array(lift, np.float32) * (1 - x)
    x = x * VIGNETTE
    gr = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    gr = np.repeat(np.repeat(gr, 2, 0), 2, 1)[..., None]
    x = x + gr * 0.022 * (0.6 + 0.8 * (1 - np.clip(lum, 0, 1)))
    if flash:
        x = x + flash
    x = x * fade_mul
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


def process(cut, idx):
    cid, s, e, style = cut
    src_id = pick.get(cid, cid)
    fdir = os.path.join(a.clips, src_id + "_frames")
    f0, f1 = round(s * FPS), round(e * FPS)
    n = f1 - f0
    dur = n / FPS
    frames = sorted(os.listdir(fdir))
    sw, sh = Image.open(os.path.join(fdir, frames[0])).size
    # 1) motion-interpolate the 16 frames so they span exactly `dur` seconds at 30 fps
    in_rate = len(frames) / dur
    cmd = ["ffmpeg", "-v", "error", "-framerate", f"{in_rate:.5f}", "-i", os.path.join(fdir, "%03d.png"),
           "-vf", f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,tpad=stop_mode=clone:stop_duration=1",
           "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    lo = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw, 3)
    if len(lo) < n:
        lo = np.concatenate([lo, np.repeat(lo[-1:], n - len(lo), 0)])
    dx, dy, rot, z = camera(style, n, seed=idx * 7 + 3)
    rng = np.random.default_rng(idx)
    g = STYLE_GRADE[style]
    out = os.path.join(a.out, f"{cid}.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    base = max(W / sw, H / sh)
    for i in range(n):
        im = Image.fromarray(lo[i])
        sc = base * z[i]
        th = math.radians(rot[i])
        # output pixel (u,v) -> source (x,y): centre-relative rotation + scale, plus camera offset
        cu, cv = W / 2 + dx[i], H / 2 + dy[i]
        ca, sa = math.cos(th) / sc, math.sin(th) / sc
        A = (ca, sa, sw / 2 - ca * cu - sa * cv, -sa, ca, sh / 2 + sa * cu - ca * cv)
        fr = np.asarray(im.transform((W, H), Image.AFFINE, A, resample=Image.BICUBIC))
        flash = 0.0
        if cid == "01a" and i < 4:
            flash = [0.9, 0.55, 0.25, 0.08][i]
        fade_mul = 1.0
        if cid in E.get("fade_in", {}):
            fi = E["fade_in"][cid] * FPS
            fade_mul *= min(1.0, i / fi) if fi else 1.0
        if cid in E.get("fade_out", {}):
            fo = E["fade_out"][cid] * FPS
            fade_mul *= min(1.0, (n - 1 - i) / fo) if fo else 1.0
        enc.stdin.write(grade(fr, g, rng, flash, fade_mul).tobytes())
    enc.stdin.close(); enc.wait()
    print("post", cid, "<-", src_id, n, "frames", flush=True)


ids = set(a.ids.split(",")) if a.ids else None
for k, cut in enumerate(E["cuts"]):
    if ids and cut[0] not in ids:
        continue
    process(cut, k)
