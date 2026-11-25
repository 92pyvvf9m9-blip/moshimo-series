#!/usr/bin/env python3
"""QA for the finished MP4: format, duration, loudness/true peak, and a contact sheet.

  python qa.py VIDEO.mp4 SHEET.png [--times 1,2,3] [--scale 216]
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("sheet")
ap.add_argument("--times"); ap.add_argument("--scale", type=int, default=216); ap.add_argument("--cols", type=int, default=7)
a = ap.parse_args()

p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", a.video],
                              capture_output=True, text=True, check=True).stdout)
vs = next(s for s in p["streams"] if s["codec_type"] == "video")
au = next(s for s in p["streams"] if s["codec_type"] == "audio")
dur = float(p["format"]["duration"])
print(f"video {vs['codec_name']} {vs.get('profile')} {vs['width']}x{vs['height']} {vs['r_frame_rate']} {vs['pix_fmt']}")
print(f"audio {au['codec_name']} {au['sample_rate']} Hz {au['channels']} ch")
print(f"duration {dur:.2f} s, size {int(p['format']['size']) / 1e6:.1f} MB, bitrate {int(p['format']['bit_rate']) / 1e6:.1f} Mb/s")
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.video, "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
for line in r[r.rfind("Summary:"):].splitlines():
    if any(k in line for k in ("I:", "LRA:", "Peak:")):
        print("  " + line.strip())

ts = [float(x) for x in a.times.split(",")] if a.times else [round(i * dur / 28 + 0.15, 2) for i in range(28)]
ts = [t for t in ts if t < dur]
w = a.scale; h = int(w * 16 / 9)
cols = a.cols; rows = -(-len(ts) // cols)
sheet = Image.new("RGB", (cols * w, rows * h), "black")
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", max(14, w // 10))
with tempfile.TemporaryDirectory() as td:
    for k, t in enumerate(ts):
        f = os.path.join(td, f"{k}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", a.video, "-frames:v", "1",
                        "-vf", f"scale={w}:{h}", f], check=True)
        im = Image.open(f).convert("RGB")
        ImageDraw.Draw(im).text((5, 3), f"{t:.1f}s", fill=(255, 230, 0), font=font)
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(a.sheet)
print("sheet", a.sheet)
