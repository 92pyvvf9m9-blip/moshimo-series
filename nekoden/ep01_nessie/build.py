"""第1話をパートごとに作る。  使い方: python3 build.py [p01 p04 ...]（省略で全部）
素材: bg/*.jpg（背景）, cat_cut.png（猫の切り抜き）。出力: parts/pNN.mp4 → その後 join.sh でつなぐ。
直したいパートだけ番号を指定して作り直せる。"""
import subprocess, sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

H = pathlib.Path(__file__).resolve().parent
W, HH, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf"
import os
if not os.path.exists(FONT):
    FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
CAT = Image.open(H / "cat_cut.png").convert("RGBA")
CAT = CAT.crop(CAT.getbbox())
NOTE = "※伝説をもとにした創作です"


def bg(name, dark=1.0):
    im = Image.open(H / "bg" / name).convert("RGB")
    w, h = im.size
    im = im.crop((0, 0, w, int(h * 0.95)))            # 下の透かしを切る
    s = max(W / im.width, HH / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (im.width - W) // 2
    im = im.crop((x, 0, x + W, HH))
    return ImageEnhance.Brightness(im).enhance(dark) if dark != 1 else im


def cat(img, h, cx, bottom, flip=False, bright=1.0):
    c = CAT.resize((round(CAT.width * h / CAT.height), h), Image.LANCZOS)
    if flip:
        c = ImageOps.mirror(c)
    if bright != 1:
        a = c.getchannel("A"); c = ImageEnhance.Brightness(c.convert("RGB")).enhance(bright).convert("RGBA"); c.putalpha(a)
    img.paste(c, (cx - c.width // 2, bottom - c.height), c)
    return img


def text_layer(lines, y, size=96, small=False):
    t = Image.new("RGBA", (W, HH), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    f = ImageFont.truetype(FONT, size)
    for i, s in enumerate(lines):
        tw = d.textlength(s, font=f)
        d.text(((W - tw) / 2, y + i * size * 1.25), s, font=f, fill="white",
               stroke_width=max(3, size // 12), stroke_fill="black")
    if small:
        f2 = ImageFont.truetype(FONT, 30)
        d.text((W - d.textlength(NOTE, font=f2) - 30, HH - 70), NOTE, font=f2, fill=(230, 230, 230), stroke_width=2, stroke_fill="black")
    return t


def shadow_scene():
    im = bg("b05.jpg", 0.45)
    sh = Image.new("L", (W, HH), 0)
    d = ImageDraw.Draw(sh)
    d.ellipse((150, 1050, 930, 1650), fill=200)        # 胴体
    d.ellipse((560, 760, 760, 1120), fill=170)          # 首
    sh = sh.filter(ImageFilter.GaussianBlur(70))
    im.paste(Image.new("RGB", (W, HH), (0, 0, 0)), (0, 0), sh)
    return cat(im, 330, 330, 1000, bright=0.85)


def eyes_scene():
    im = Image.new("RGB", (W, HH), (0, 0, 0))
    c = Image.open(H.parent / "character_ref.webp").convert("RGB")
    eyes = c.crop((900, 220, 1160, 330)).resize((780, 330), Image.LANCZOS)   # 時計の目の部分
    m = Image.new("L", eyes.size, 0); ImageDraw.Draw(m).ellipse((40, 20, 740, 310), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(40))
    im.paste(eyes, ((W - 780) // 2, 700), m)
    return im


# 番号: (画像を作る関数, 秒, テロップ行, テロップ位置y, 注記, 効果音)
PARTS = {
    "p01": (lambda: cat(bg("b04.jpg"), 300, 400, 650), 3, ["ネッシーの背中に", "乗ってみた"], 1250, True, "hit"),
    "p02": (lambda: cat(bg("b02.jpg"), 620, 760, 1830), 4, ["イギリス・ネス湖"], 220, False, "tick"),
    "p03": (lambda: cat(bg("b05.jpg", 0.8), 420, 860, 1880), 5, ["……何か、来た。"], 260, False, "drone"),
    "p04": (lambda: cat(bg("b04.jpg"), 560, 850, 1900, flip=True), 5, ["本当に、いた。"], 220, False, "hit"),
    "p05": (lambda: cat(bg("b04.jpg"), 300, 400, 650).crop((100, 250, 700, 1317)).resize((W, HH), Image.LANCZOS), 7, ["乗せてくれた。"], 220, False, "drone"),
    "p06": (shadow_scene, 6, ["下にも、", "何かいる。"], 220, False, "low"),
    "p07": (eyes_scene, 5, ["次は、エジプトへ。"], 1300, True, "bell"),
}

SFX = {
    "hit":   "[0]volume=1[a];sine=f=45:d={d},afade=t=out:st=0:d=1.2,volume=0.9[b];[a][b]amix=2:normalize=0",
    "tick":  "[0]volume=1[a];sine=f=2400:d=0.06,apad=pad_dur={d},volume=0.5[b];[a][b]amix=2:normalize=0",
    "drone": "[0]volume=1.3[a];sine=f=55:d={d},volume=0.35[b];[a][b]amix=2:normalize=0",
    "low":   "[0]volume=0.6[a];sine=f=38:d={d},afade=t=in:d=2,volume=0.7[b];[a][b]amix=2:normalize=0",
    "bell":  "[0]volume=0.3[a];sine=f=1760:d={d},afade=t=out:st=0:d=2.5,volume=0.6[b];[a][b]amix=2:normalize=0",
}


def render(key):
    make, dur, lines, ty, note, sfx = PARTS[key]
    out = H / "parts"; out.mkdir(exist_ok=True); tmp = H / "out"; tmp.mkdir(exist_ok=True)
    make().save(tmp / f"{key}_img.png")
    text_layer(lines, ty, small=note).save(tmp / f"{key}_txt.png")
    n = dur * FPS
    vf = (f"[0]scale=2160:-1,zoompan=z='1+0.10*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{HH}:fps={FPS}[v];"
          f"[v][1]overlay=0:0,format=yuv420p[vo]")
    amb = f"anoisesrc=color=brown:amplitude=0.05:d={dur},lowpass=f=500"
    af = SFX[sfx].format(d=dur)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", tmp / f"{key}_img.png", "-i", tmp / f"{key}_txt.png",
                    "-f", "lavfi", "-i", amb,
                    "-filter_complex", vf + ";" + af.replace("[0]", "[2]") + ",atrim=0:" + str(dur) + "[ao]",
                    "-map", "[vo]", "-map", "[ao]", "-t", str(dur), "-c:v", "libx264", "-r", str(FPS),
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", out / f"{key}.mp4"], check=True)
    print("made", key)


for k in (sys.argv[1:] or PARTS):
    render(k)
