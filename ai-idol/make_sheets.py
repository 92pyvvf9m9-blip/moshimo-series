#!/usr/bin/env python3
"""Cut out full-body images (white background), build height-accurate group photos and comparison sheets.

  python make_sheets.py SRC_DIR OUT_DIR
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from scipy import ndimage

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
HEIGHT = {"cyan": 141, "pink": 145, "yellow": 152, "red": 155, "purple": 158, "green": 160, "blue": 163}
NAME = {"cyan": "しずく", "pink": "もも", "yellow": "ひまり", "red": "朱音", "purple": "すみれ", "green": "若葉", "blue": "蒼"}
ORDER_ROW = ["cyan", "green", "yellow", "red", "blue", "purple", "pink"]   # centre = 朱音, tall ones beside
FONT = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 28)


def cutout(path):
    im = Image.open(path).convert("RGB"); a = np.asarray(im).astype(np.int16)
    bright = a.min(axis=2) > 225; flat = (a.max(axis=2) - a.min(axis=2)) < 28
    lab, n = ndimage.label(bright & flat)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge))
    alpha = (~bg).astype(np.uint8) * 255
    alpha = np.asarray(Image.fromarray(alpha).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2)))
    rgba = np.dstack([np.asarray(im), alpha]); out = Image.fromarray(rgba, "RGBA")
    ys, xs = np.where(alpha > 40)
    return out.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)) if len(xs) else out


def group(style, w=1920, h=1080, rows=1):
    bgp = os.path.join(SRC, f"{style}_bg.png")
    bg = Image.open(bgp).convert("RGB").resize((w, h)) if os.path.exists(bgp) else Image.new("RGB", (w, h), (240, 240, 250))
    canvas = bg.convert("RGBA")
    figs = {k: cutout(os.path.join(SRC, f"{style}_full_{k}.png")) for k in HEIGHT if os.path.exists(os.path.join(SRC, f"{style}_full_{k}.png"))}
    if len(figs) < 7:
        return None
    floor = h - 30; px_per_cm = (h * 0.82) / 163 if rows == 1 else (h * 0.40) / 163
    rows_list = [ORDER_ROW] if rows == 1 else [["green", "red", "blue"], ["cyan", "yellow", "purple", "pink"]]
    for r, row in enumerate(rows_list):
        y_floor = floor if rows == 1 else (int(h * 0.50) if r == 0 else floor)
        slot = w / len(row)
        for i, k in enumerate(row):
            f = figs[k]; s = HEIGHT[k] * px_per_cm / f.height
            f2 = f.resize((max(1, int(f.width * s)), max(1, int(f.height * s))), Image.LANCZOS)
            x = int(slot * (i + 0.5) - f2.width / 2)
            sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse([x + f2.width * 0.15, y_floor - 12, x + f2.width * 0.85, y_floor + 10], fill=(0, 0, 0, 70))
            canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(6)))
            canvas.alpha_composite(f2, (x, y_floor - f2.height))
    return canvas.convert("RGB")


def sheet(files, labels, cols, cell_h, path):
    ims = [Image.open(f).convert("RGB") for f in files]
    ims = [im.resize((int(im.width * cell_h / im.height), cell_h)) for im in ims]
    cw = max(i.width for i in ims); rows = -(-len(ims) // cols)
    S = Image.new("RGB", (cw * cols, (cell_h + 40) * rows), "white"); d = ImageDraw.Draw(S)
    for n, (im, lb) in enumerate(zip(ims, labels)):
        x, y = (n % cols) * cw, (n // cols) * (cell_h + 40)
        S.paste(im, (x + (cw - im.width) // 2, y)); d.text((x + 8, y + cell_h + 4), lb, fill=(30, 30, 30), font=FONT)
    S.save(path)


for st in ["pop", "stage", "soft"]:
    g = group(st)
    if g: g.save(os.path.join(OUT, f"group_{st}_16x9.jpg"), quality=92)
    g2 = group(st, 1080, 1920, rows=2)
    if g2: g2.save(os.path.join(OUT, f"group_{st}_9x16.jpg"), quality=92)
    for shot in ["face", "full"]:
        ks = [k for k in ORDER_ROW if os.path.exists(os.path.join(SRC, f"{st}_{shot}_{k}.png"))]
        if ks:
            sheet([os.path.join(SRC, f"{st}_{shot}_{k}.png") for k in ks],
                  [f"{NAME[k]} {HEIGHT[k]}cm" for k in ks], 7, 520, os.path.join(OUT, f"sheet_{st}_{shot}.jpg"))
gs = [os.path.join(SRC, f) for f in ["group_direct_a.png", "group_direct_b.png"] if os.path.exists(os.path.join(SRC, f))]
if gs:
    sheet(gs, ["一枚生成 A", "一枚生成 B"], 2, 700, os.path.join(OUT, "group_direct.jpg"))
print("sheets done")
