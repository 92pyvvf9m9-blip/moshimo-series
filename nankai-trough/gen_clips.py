#!/usr/bin/env python3
"""Generate the short motion clips locally (CPU, bf16) with AnimateDiff-Lightning + epiCRealism.

  python gen_clips.py SHOTS.json OUTDIR [--hero REF.png] [--only hero|env] [--ids 01a,05b] [--variant N]

Hero shots use IP-Adapter Plus with the protagonist reference so the face and outfit stay consistent.
Each clip: 16 frames at 448x800, saved as OUTDIR/<id>[_vN].mp4 (8 fps) and a PNG frame folder.
"""
import argparse, json, os, time
import torch
from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
from diffusers.utils import export_to_video
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("shots"); ap.add_argument("out")
ap.add_argument("--hero"); ap.add_argument("--only", choices=["hero", "env"])
ap.add_argument("--ids"); ap.add_argument("--variant", type=int, default=0)
ap.add_argument("--ip-scale", type=float, default=0.55)
ap.add_argument("--ip-weight", default="ip-adapter-plus_sd15.safetensors")
ap.add_argument("--w", type=int, default=448); ap.add_argument("--h", type=int, default=800)
a = ap.parse_args()

torch.set_num_threads(os.cpu_count())
DT = torch.bfloat16
cfg = json.load(open(a.shots, encoding="utf-8"))
clips = cfg["clips"]
if a.only:
    clips = [c for c in clips if c["hero"] == (a.only == "hero")]
if a.ids:
    want = set(a.ids.split(","))
    clips = [c for c in clips if c["id"] in want]
os.makedirs(a.out, exist_ok=True)

adapter = MotionAdapter().to("cpu", DT)
adapter.load_state_dict(load_file(hf_hub_download("ByteDance/AnimateDiff-Lightning", "animatediff_lightning_4step_diffusers.safetensors"), device="cpu"))
pipe = AnimateDiffPipeline.from_pretrained("emilianJR/epiCRealism", motion_adapter=adapter, torch_dtype=DT)
pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing", beta_schedule="linear")
pipe.vae.enable_slicing()
use_ip = any(c["hero"] for c in clips) and a.hero
if use_ip:
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name=a.ip_weight,
                         image_encoder_folder="models/image_encoder", torch_dtype=DT)
    pipe.set_ip_adapter_scale(a.ip_scale)
    ref = Image.open(a.hero).convert("RGB")

for c in clips:
    name = c["id"] + (f"_v{a.variant}" if a.variant else "")
    mp4 = os.path.join(a.out, name + ".mp4")
    if os.path.exists(mp4):
        continue
    base = cfg["base_hero"] if c["hero"] else cfg["base_env"]
    prompt = f"{base}, {c['prompt']}"
    t = time.time()
    kw = dict(prompt=prompt, guidance_scale=1.0, num_inference_steps=4, num_frames=16,
              width=c.get("w", a.w), height=c.get("h", a.h), generator=torch.Generator().manual_seed(c["seed"] + 1000 * a.variant),
              decode_chunk_size=2)
    if use_ip:
        sc = 0.0 if (not c["hero"] or c.get("ip") == "none") else c.get("ip_scale", a.ip_scale)
        pipe.set_ip_adapter_scale(sc); kw["ip_adapter_image"] = ref
    frames = pipe(**kw).frames[0]
    if use_ip:
        pipe.set_ip_adapter_scale(a.ip_scale)
    fdir = os.path.join(a.out, name + "_frames"); os.makedirs(fdir, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(os.path.join(fdir, f"{i:03d}.png"))
    export_to_video(frames, mp4, fps=8)
    print("done", name, round(time.time() - t, 1), "s", flush=True)
