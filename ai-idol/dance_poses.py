#!/usr/bin/env python3
"""Original beat-synced idol dance as OpenPose skeleton frames (no real choreography is copied).

  python dance_poses.py OUTDIR --bpm 128 --frames 16 --fps 8 --move sway|wave|heart|clap
Writes OUTDIR/000.png ... (OpenPose-style colored limbs on black, 512x768).
"""
import argparse, math, os
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--bpm", type=float, default=128); ap.add_argument("--frames", type=int, default=16)
ap.add_argument("--fps", type=float, default=8); ap.add_argument("--move", default="sway"); ap.add_argument("--w", type=int, default=512)
ap.add_argument("--h", type=int, default=768)
a = ap.parse_args()
W, H = a.w, a.h
# OpenPose COCO-18 limb pairs and colours
LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
COLS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170),
        (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]


def arm(sh, ang1, ang2, l1=70, l2=62):
    e = (sh[0] + l1 * math.cos(ang1), sh[1] + l1 * math.sin(ang1))
    w = (e[0] + l2 * math.cos(ang2), e[1] + l2 * math.sin(ang2))
    return e, w


def pose(t):
    beat = t * a.bpm / 60.0           # beats elapsed
    ph = 2 * math.pi * beat
    sway = 18 * math.sin(ph / 2)       # one side per beat
    bounce = 10 * abs(math.sin(ph / 2))
    cx, top = W / 2 + sway, 150 + bounce
    nose = (cx, top + 40); neck = (cx, top + 110)
    rsh, lsh = (cx - 58, top + 115), (cx + 58, top + 115)
    rh, lh = (cx - 34, top + 300), (cx + 34, top + 300)
    m = a.move
    if m == "wave":       # both arms up, waving overhead
        s = math.sin(ph)
        re, rw = arm(rsh, math.radians(-120 + 15 * s), math.radians(-100 + 25 * s))
        le, lw = arm(lsh, math.radians(-60 - 15 * s), math.radians(-80 - 25 * s))
    elif m == "heart":    # hands meet at chest (heart), opening on the off-beat
        o = 0.5 + 0.5 * math.cos(ph)
        re, rw = arm(rsh, math.radians(110 - 40 * o), math.radians(-20 - 30 * o))
        le, lw = arm(lsh, math.radians(70 + 40 * o), math.radians(200 + 30 * o))
    elif m == "clap":     # clap above the head on every beat
        o = 0.5 + 0.5 * math.cos(ph)
        re, rw = arm(rsh, math.radians(-110 - 20 * o), math.radians(-70 - 40 * o))
        le, lw = arm(lsh, math.radians(-70 + 20 * o), math.radians(-110 + 40 * o))
    else:                 # sway: arms swing with the body
        s = math.sin(ph / 2)
        re, rw = arm(rsh, math.radians(100 + 30 * s), math.radians(80 + 50 * s))
        le, lw = arm(lsh, math.radians(80 + 30 * s), math.radians(100 + 50 * s))
    step = 22 * math.sin(ph / 2)
    rk, lk = (rh[0] - 6 + step * 0.5, rh[1] + 120 - bounce * 0.6), (lh[0] + 6 + step * 0.5, lh[1] + 120 - bounce * 0.6)
    ra, la = (rh[0] - 8 + step, rh[1] + 240 - bounce), (lh[0] + 8 + step, lh[1] + 240 - bounce)
    reye, leye = (nose[0] - 14, nose[1] - 12), (nose[0] + 14, nose[1] - 12)
    rear, lear = (nose[0] - 34, nose[1] - 4), (nose[0] + 34, nose[1] - 4)
    return [nose, neck, rsh, re, rw, lsh, le, lw, rh, rk, ra, lh, lk, la, reye, leye, rear, lear]


os.makedirs(a.out, exist_ok=True)
for i in range(a.frames):
    p = pose(i / a.fps)
    im = Image.new("RGB", (W, H), "black"); d = ImageDraw.Draw(im)
    for k, (x, y) in enumerate(LIMBS):
        d.line([p[x], p[y]], fill=COLS[k], width=8)
    for k, q in enumerate(p):
        d.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=COLS[k])
    im.save(os.path.join(a.out, f"{i:03d}.png"))
print("ok", a.frames)
