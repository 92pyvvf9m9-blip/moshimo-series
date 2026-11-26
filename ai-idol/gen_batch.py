#!/usr/bin/env python3
"""Overnight batch: 3 styles x 7 members x (face, full) + stage backgrounds + 7-girl group attempts.
Resumable (skips existing files). Animagine XL 4.0, CPU bf16.

  python gen_batch.py OUTDIR
"""
import os, sys, time, torch
from diffusers import StableDiffusionXLPipeline, EulerAncestralDiscreteScheduler

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
Q = "masterpiece, high score, great score, absurdres"
NEG = ("nsfw, cleavage, revealing clothes, lowres, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, "
       "text, error, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, "
       "username, blurry, retro artstyle, 1990s (style), 2000s (style), sketch, realistic, photorealistic, 3d")
STYLES = {
    "pop": "pop idol illustration, sparkling eyes, blush, glossy hair highlights, sparkles, stars, cute hair ornaments, "
           "decorated idol costume, frills, ribbons, pastel and vivid colors, detailed eyes",
    "stage": "idol anime key visual, stage lighting, cel shading, vivid colors, detailed eyes, dynamic composition",
    "soft": "soft shading, delicate lineart, pastel colors, gentle light, watercolor (medium), detailed eyes",
}
MEMBERS = {
    "red":    ("red",        "reddish brown hair, medium hair, side ponytail, large eyes, slightly tsurime, energetic smile"),
    "blue":   ("navy blue",  "tall, very dark navy blue hair, long straight hair, narrow eyes, cool expression, mature"),
    "yellow": ("yellow",     "blonde hair, short bob, hairpin, round eyes, big grin"),
    "green":  ("green",      "very dark green hair, long wavy hair, tareme, gentle smile, mature, onee-san"),
    "cyan":   ("light blue", "petite, 19 years old, cute face, light blue hair, twintails, large eyes, shy smile"),
    "pink":   ("pink",       "petite, cute face, pink hair, double bun, half updo, wink"),
    "purple": ("purple",     "lavender silver hair, long hair, hair over one eye, mysterious smile, mature, elegant"),
}
SHOTS = {
    "face": ("upper body, portrait, close-up, looking at viewer, {bg}", 896, 1152),
    "full": ("full body, standing, looking at viewer, white background, simple background", 832, 1216),
}
BG = {"pop": "colorful sparkling pastel background", "stage": "concert stage background, bokeh lights",
      "soft": "soft pastel sky background"}

torch.set_num_threads(os.cpu_count())
pipe = StableDiffusionXLPipeline.from_pretrained("cagliostrolab/animagine-xl-4.0", torch_dtype=torch.bfloat16)
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
pipe.vae.enable_slicing(); pipe.vae.enable_tiling()


def gen(name, prompt, w, h, seed):
    p = os.path.join(OUT, name + ".png")
    if os.path.exists(p):
        return
    t = time.time()
    img = pipe(prompt=prompt, negative_prompt=NEG, num_inference_steps=28, guidance_scale=5.0, width=w, height=h,
               generator=torch.Generator().manual_seed(seed)).images[0]
    img.save(p)
    print("done", name, round(time.time() - t), "s", flush=True)


jobs = []
for st in STYLES:
    for shot, (sp, w, h) in SHOTS.items():
        for k, (c, desc) in MEMBERS.items():
            costume = f"japanese idol, white idol costume with {c} accents, {c} ribbon, frilled skirt"
            prompt = f"1girl, solo, adult woman, {desc}, {costume}, {sp.format(bg=BG[st])}, {STYLES[st]}, {Q}"
            jobs.append((f"{st}_{shot}_{k}", prompt, w, h, 11))
    jobs.append((f"{st}_bg", f"no humans, idol concert stage, {BG[st]}, {STYLES[st].split(',')[0]}, {Q}", 1216, 832, 5))
# group in one image (expected to be hard for the model): 2 tries
grp = ("7girls, multiple girls, japanese idol group, group photo, each girl different hair color: reddish brown, navy blue, "
       "blonde, dark green, light blue, pink, lavender, matching white idol costumes with colored accents, smile, "
       "upper body, " + STYLES["pop"] + ", " + Q)
jobs += [("group_direct_a", grp, 1216, 832, 21), ("group_direct_b", grp, 1216, 832, 22)]
# order: full bodies first (needed for the composite), then faces, backgrounds, group tries
jobs.sort(key=lambda j: (0 if "_full_" in j[0] else 1 if "_face_" in j[0] else 2 if j[0].endswith("_bg") else 3))
for j in jobs:
    gen(*j)
print("ALLDONE", flush=True)
