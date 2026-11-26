#!/usr/bin/env python3
"""Pose-driven dance clip for one member: AnimateDiff-Lightning + OpenPose ControlNet + IP-Adapter (member image).

  python dance_test.py MEMBER_PNG POSE_DIR OUT.mp4 --prompt "..." [--ip 0.6] [--seed 1]
"""
import argparse, os, glob, time, torch
from PIL import Image
from diffusers import AnimateDiffControlNetPipeline, ControlNetModel, MotionAdapter, EulerDiscreteScheduler
from diffusers.utils import export_to_video
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

ap = argparse.ArgumentParser()
ap.add_argument("member"); ap.add_argument("poses"); ap.add_argument("out")
ap.add_argument("--prompt", default=""); ap.add_argument("--ip", type=float, default=0.6); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--w", type=int, default=512); ap.add_argument("--h", type=int, default=768)
a = ap.parse_args()
torch.set_num_threads(os.cpu_count()); DT = torch.bfloat16
adapter = MotionAdapter().to("cpu", DT)
adapter.load_state_dict(load_file(hf_hub_download("ByteDance/AnimateDiff-Lightning", "animatediff_lightning_4step_diffusers.safetensors"), device="cpu"))
cn = ControlNetModel.from_pretrained("lllyasviel/control_v11p_sd15_openpose", torch_dtype=DT)
pipe = AnimateDiffControlNetPipeline.from_pretrained("stablediffusionapi/anything-v5", motion_adapter=adapter, controlnet=cn, torch_dtype=DT)
pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing", beta_schedule="linear")
pipe.vae.enable_slicing()
pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name="ip-adapter-plus_sd15.safetensors", image_encoder_folder="models/image_encoder", torch_dtype=DT)
pipe.set_ip_adapter_scale(a.ip)
poses = [Image.open(p).convert("RGB").resize((a.w, a.h)) for p in sorted(glob.glob(os.path.join(a.poses, "*.png")))]
ref = Image.open(a.member).convert("RGB")
t = time.time()
out = pipe(prompt=a.prompt, negative_prompt="", conditioning_frames=poses, num_frames=len(poses), width=a.w, height=a.h,
           num_inference_steps=4, guidance_scale=1.0, ip_adapter_image=ref, controlnet_conditioning_scale=1.0,
           generator=torch.Generator().manual_seed(a.seed), decode_chunk_size=2).frames[0]
fd = a.out + "_frames"; os.makedirs(fd, exist_ok=True)
for i, f in enumerate(out): f.save(os.path.join(fd, f"{i:03d}.png"))
export_to_video(out, a.out, fps=8)
print("done", a.out, round(time.time() - t, 1), "s")
