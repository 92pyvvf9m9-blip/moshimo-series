#!/usr/bin/env python3
"""Generate member design images with Animagine XL 4.0 (local, CPU bf16).

  python gen_members.py OUTDIR [--ids red,blue] [--seed 1] [--steps 28] [--w 832 --h 1216]
"""
import argparse, os, time, torch
from diffusers import StableDiffusionXLPipeline, EulerAncestralDiscreteScheduler

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--ids"); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--steps", type=int, default=28); ap.add_argument("--w", type=int, default=832); ap.add_argument("--h", type=int, default=1216)
a = ap.parse_args()

COMMON = ("1girl, solo, japanese idol, idol costume, white stage outfit with {c} accents, {c} ribbon, frilled skirt, "
          "standing, full body, looking at viewer, smile, simple light gradient background, "
          "modern anime style, clean lineart, vibrant colors, masterpiece, high score, great score, absurdres")
NEG = ("nsfw, cleavage, revealing clothes, lowres, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, "
       "text, error, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, "
       "username, blurry, retro artstyle, 1990s (style), 2000s (style), sketch")
MEMBERS = {
    "red":    ("red",        "adult woman, reddish brown hair, medium hair, side ponytail, large eyes, slightly tsurime, energetic smile, hand on hip, soft shading"),
    "blue":   ("navy blue",  "tall adult woman, very dark navy blue hair, long straight hair, narrow eyes, cool expression, mature"),
    "yellow": ("yellow",     "adult woman, blonde hair, short bob, hairpin, round eyes, big grin"),
    "green":  ("green",      "adult woman, very dark green hair, long wavy hair, tareme, gentle smile, mature, onee-san"),
    "cyan":   ("light blue", "petite young adult woman, 19 years old, cute face, light blue hair, twintails, large eyes, shy smile, slender"),
    "pink":   ("pink",       "petite adult woman, baby face, pink hair, double bun, half updo, wink"),
    "purple": ("purple",     "adult woman, lavender silver hair, long hair, hair over one eye, mysterious smile, mature, elegant"),
}
ids = a.ids.split(",") if a.ids else list(MEMBERS)
torch.set_num_threads(os.cpu_count())
path = "cagliostrolab/animagine-xl-4.0"
pipe = StableDiffusionXLPipeline.from_pretrained(path, torch_dtype=torch.bfloat16)
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
pipe.vae.enable_slicing(); pipe.vae.enable_tiling()
os.makedirs(a.out, exist_ok=True)
for k in ids:
    c, desc = MEMBERS[k]
    prompt = f"{desc}, " + COMMON.format(c=c)
    t = time.time()
    img = pipe(prompt=prompt, negative_prompt=NEG, num_inference_steps=a.steps, guidance_scale=5.0,
               width=a.w, height=a.h, generator=torch.Generator().manual_seed(a.seed)).images[0]
    p = os.path.join(a.out, f"{k}_s{a.seed}.png"); img.save(p)
    print("done", k, round(time.time() - t, 1), "s", p, flush=True)
