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
pick = dict(E.get("picks", {}))
pick.update(dict(p.split("=") for p in a.pick))
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
    elif style == "ash_walk":
        dy = 6 * np.abs(np.sin(np.pi * 1.9 * t)) - 3 + smooth_noise(n, FPS, 0.4, 1.2, seed) * 3
        dx = 5 * np.sin(np.pi * 0.95 * t + seed) + smooth_noise(n, FPS, 0.3, 1.0, seed + 1) * 4
        rot = 0.35 * np.sin(np.pi * 0.95 * t + seed + 0.6)
        z = np.full(n, 1.08)
    elif style == "erupt":
        dx, dy, rot = hand(5, 0.15, 0.2, 0.8)
        z = 1.04 + 0.07 * (0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, n)))
    elif style in ("handheld", "night", "night_d4n", "shelter", "handheld_day", "ash_light", "ash", "ash_night", "ash_dawn", "ash_dusk", "night_end"):
        amp = {"handheld": 8, "night": 6, "night_d4n": 4, "shelter": 5}.get(style, 6)
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
    "dayfornight": ((0.50, 0.68, 1.00), (0.002, 0.006, 0.016), 0.30, 1.22, 0.55),
    "day":       ((1.03, 1.00, 0.95), (0.012, 0.014, 0.020), 0.88, 1.06, 1.00),
    "ash_light": ((1.00, 0.97, 0.90), (0.030, 0.028, 0.026), 0.55, 0.96, 0.86),
    "ash":       ((0.98, 0.95, 0.88), (0.045, 0.042, 0.038), 0.38, 0.92, 0.80),
    "ash_night": ((0.78, 0.86, 1.02), (0.006, 0.008, 0.016), 0.30, 1.08, 0.55),
    "ash_dawn":  ((1.02, 0.97, 0.92), (0.050, 0.046, 0.044), 0.40, 0.92, 0.92),
    "ash_dusk":  ((1.05, 0.95, 0.85), (0.030, 0.026, 0.026), 0.45, 1.00, 0.80),
    "night_end": ((0.85, 0.90, 1.05), (0.004, 0.006, 0.012), 0.40, 1.15, 0.62),
}
STYLE_GRADE = {"quake": "dusk", "quake_peak": "dusk", "aftershake": "dusk", "run": "dusk", "handheld": "dusk",
               "night": "night", "night_d4n": "dayfornight",
               "erupt": "day", "handheld_day": "day", "ash_light": "ash_light", "ash": "ash", "ash_walk": "ash",
               "ash_night": "ash_night", "ash_dawn": "ash_dawn", "ash_dusk": "ash_dusk", "night_end": "night_end", "shelter": "shelter", "dawn": "dawn", "dawn_push": "dawn", "ominous": "ominous"}

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


# ---------- falling signboard (composited in source space so it shakes with the shot) ----------
from PIL import ImageDraw, ImageFilter


def make_sign(w=176, h=66, seed=5):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for bx in (w * 0.22, w * 0.72):                      # mounting brackets
        d.rectangle([bx, 0, bx + 7, 16], fill=(58, 58, 60, 255))
    d.rectangle([0, 12, w - 1, h + 12], fill=(46, 47, 50, 255))          # metal frame
    face = (r.normal(0, 9, (h - 10, w - 12, 1)) + np.array([172, 166, 152])).clip(0, 255)
    grad = np.linspace(1.0, 0.74, h - 10)[:, None, None]                   # grime toward the bottom
    streak = 1 - 0.12 * (r.random((1, w - 12, 1)) > 0.85)                  # rain streaks
    face = (face * grad * streak).clip(0, 255).astype(np.uint8)
    im.paste(Image.fromarray(face, "RGB"), (6, 17))
    # character-like stroke clusters (deliberately not real characters)
    cell = 30
    for k in range(5):
        x0 = 12 + k * (cell + 3); y0 = 24
        for _ in range(int(r.integers(3, 6))):
            if r.random() < 0.5:
                yy = y0 + int(r.integers(0, h - 24)); xa = x0 + int(r.integers(0, 10)); xb = xa + int(r.integers(10, cell))
                d.rectangle([xa, yy, xb, yy + 3], fill=(118, 32, 30, 255))
            else:
                xx = x0 + int(r.integers(2, cell - 4)); ya = y0 + int(r.integers(0, 12)); yb = ya + int(r.integers(14, h - 26))
                d.rectangle([xx, ya, xx + 3, yb], fill=(118, 32, 30, 255))
    d.line([(1, 13), (w - 2, 13)], fill=(120, 120, 120, 255), width=1)
    return im


SIGN = None


def sign_pose(t, fx):
    ti, y0, yl, x0 = fx["t_impact"], fx["y_start"], fx["y_land"], fx["x"]
    if t <= ti:
        u = max(0.0, t) / ti
        return x0 - 26 * (1 - u), y0 + (yl - y0) * u * u, -12 + 40 * u, 0.82 + 0.22 * u, 1.0 - 0.25 * u * u
    k = t - ti
    bounce = 10 * math.sin(math.pi * min(k, 0.16) / 0.16) if k < 0.16 else 0.0
    return x0, yl - bounce, 28 - 18 * min(1.0, k / 0.16), 1.04, 0.75 - 0.2 * min(1.0, k / 0.16)


def apply_sign(frame, t, fx, fps):
    global SIGN
    if SIGN is None:
        SIGN = make_sign()
    base = Image.fromarray(frame).convert("RGBA")
    ti = fx["t_impact"]
    layer = np.zeros((base.height, base.width, 4), np.float32)
    # shadow on the pavement, growing as the sign approaches
    if t > 0:
        sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
        u = min(1.0, t / ti)
        cx, cy = fx["x"], fx["y_land"] + 30
        rw, rh = 30 + 70 * u, 6 + 12 * u
        ImageDraw.Draw(sh).ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(0, 0, 0, int(110 * u)))
        layer += np.asarray(sh.filter(ImageFilter.GaussianBlur(6)), np.float32)
    subs = 4 if t <= ti + 0.05 else 1                     # motion blur while falling (180-degree shutter)
    acc = np.zeros_like(layer)
    for k in range(subs):
        tt = t - 0.5 * (subs - 1 - k) / (subs * fps)
        x, y, ang, sc, sq = sign_pose(tt, fx)
        sp = SIGN.resize((int(SIGN.width * sc), max(4, int(SIGN.height * sc * sq))), Image.BICUBIC).rotate(ang, expand=True, resample=Image.BICUBIC)
        L = Image.new("RGBA", base.size, (0, 0, 0, 0))
        L.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
        acc += np.asarray(L, np.float32)
    acc /= subs
    # dust burst at impact
    if t > ti:
        k = t - ti
        D = Image.new("RGBA", base.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(D)
        r = np.random.default_rng(42)
        cx, cy = fx["x"], fx["y_land"] + 22
        a_c = max(0.0, 1 - k / 1.7)
        rc = 30 + 150 * (1 - math.exp(-k * 2.2))
        dd.ellipse([cx - rc * 1.3, cy - rc * 0.7, cx + rc * 1.3, cy + rc * 0.35], fill=(150, 140, 124, int(120 * a_c)))
        for _ in range(110):
            px = cx + r.uniform(-70, 70) + r.uniform(-140, 140) * k
            py = cy + r.uniform(-8, 8) + r.uniform(-170, -30) * k + 160 * k * k
            rad = 1.5 + 5 * k + r.uniform(0, 2)
            al = max(0.0, 1 - k / r.uniform(0.8, 1.6))
            dd.ellipse([px - rad, py - rad, px + rad, py + rad], fill=(158, 148, 130, int(150 * al)))
        acc_d = np.asarray(D.filter(ImageFilter.GaussianBlur(3)), np.float32)
    else:
        acc_d = None
    out = np.asarray(base, np.float32)
    for lay in (layer, acc) + ((acc_d,) if acc_d is not None else ()):
        al = lay[..., 3:4] / 255.0
        out[..., :3] = out[..., :3] * (1 - al) + lay[..., :3] * al
    return out[..., :3].clip(0, 255).astype(np.uint8)


# ---------- falling volcanic ash (screen-space particles, persistent within a cut) ----------
class AshFall:
    def __init__(self, n, density, night=False, seed=0):
        r = np.random.default_rng(seed + 991)
        k = int(900 * density)
        self.night = night
        self.depth = r.uniform(0.15, 1.0, k)                    # 1 = near the camera
        self.x = r.uniform(-60, W + 60, k)
        self.y = r.uniform(-H * 0.1, H, k)
        self.vy = (40 + 210 * self.depth) * r.uniform(0.8, 1.2, k)
        self.vx = r.uniform(8, 38, k) * self.depth
        self.ph = r.uniform(0, 6.28, k)
        self.size = 0.8 + 4.2 * self.depth ** 1.6
        self.alpha = (0.25 + 0.55 * self.depth) * r.uniform(0.6, 1.0, k)

    def step(self, i):
        dt = 1 / FPS
        t = i * dt
        self.y += self.vy * dt
        self.x += (self.vx + 14 * np.sin(1.3 * t + self.ph)) * dt
        wrap = self.y > H + 20
        self.y[wrap] -= H + 60
        self.x[self.x > W + 60] -= W + 120

    def draw(self, fr):
        lay = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(lay)
        for x, y, s_, a_, vy in zip(self.x, self.y, self.size, self.alpha, self.vy):
            streak = vy / FPS * 0.5
            d.ellipse([x - s_, y - s_ - streak, x + s_, y + s_], fill=int(255 * a_))
        m = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255.0
        col = np.array([70, 72, 78] if self.night else [212, 208, 198], np.float32)
        out = fr.astype(np.float32) * (1 - m) + col * m
        return out.clip(0, 255).astype(np.uint8)


def process(cut, idx):
    cid, s, e, style = cut
    src_id = pick.get(cid, cid)
    fdir = src_id if os.path.isabs(src_id) else os.path.join(a.clips, src_id + "_frames")
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
    rf = E.get("reframe", {}).get(cid)
    scx, scy = sw / 2, sh / 2
    if rf:
        z = z * np.linspace(rf["zoom"][0], rf["zoom"][1], n)
        scx, scy = sw * (0.5 + rf.get("cx", 0.0)), sh * (0.5 + rf.get("cy", 0.0))
    sfx_cfg = E.get("sign_fx")
    dens = E.get("ash", {}).get(cid, 0.0)
    ash = AshFall(n, dens, night=style in ("ash_night", "night_end"), seed=idx) if dens > 0 else None
    if ash is not None:
        for _ in range(int(FPS * 2)):        # pre-roll so the ash is already falling on frame 0
            ash.step(0)
    for i in range(n):
        fr_lo = lo[i]
        if sfx_cfg and cid == sfx_cfg["cut"]:
            fr_lo = apply_sign(fr_lo, i / FPS - sfx_cfg["t_start"], sfx_cfg, FPS)
        im = Image.fromarray(fr_lo)
        sc = base * z[i]
        th = math.radians(rot[i])
        # output pixel (u,v) -> source (x,y): centre-relative rotation + scale, plus camera offset
        cu, cv = W / 2 + dx[i], H / 2 + dy[i]
        ca, sa = math.cos(th) / sc, math.sin(th) / sc
        A = (ca, sa, scx - ca * cu - sa * cv, -sa, ca, scy + sa * cu - ca * cv)
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
        if ash is not None:
            ash.step(i)
            fr = ash.draw(fr)
        enc.stdin.write(grade(fr, g, rng, flash, fade_mul).tobytes())
    enc.stdin.close(); enc.wait()
    print("post", cid, "<-", src_id, n, "frames", flush=True)


ids = set(a.ids.split(",")) if a.ids else None
for k, cut in enumerate(E["cuts"]):
    if ids and cut[0] not in ids:
        continue
    process(cut, k)
