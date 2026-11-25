#!/usr/bin/env python3
"""Assemble the vertical short from generated shots, narration and sound.

Inputs (under the work directory given as argv[1]):
  shots/shotNN.mp4   video for each shot in timeline.json (any size; cropped to 9:16)
  audio/narration_NN.mp3|wav   optional narration per shot, placed at the shot start (+offset)
  audio/sfx_NN.mp3|wav         optional sound effects per shot
  audio/bgm.mp3|wav            optional music bed (ducked low)
Output: <work>/out/nankai_trough_reels.mp4 (1080x1920, 30fps, H.264 High, AAC 48k, -14 LUFS)

  python3 compose.py WORKDIR [--placeholder]
--placeholder makes moving test footage so the telop/audio pipeline can be checked without credits.
"""
import json, os, re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text(encoding="utf-8"))
W, H, FPS = TL["width"], TL["height"], TL["fps"]
FONT = "Noto Serif CJK JP"
NARR_OFFSET = 0.15


def run(cmd):
    print("+", " ".join(str(c) for c in cmd)[:300], flush=True)
    subprocess.run(cmd, check=True)


def find(d, stem):
    for ext in (".wav", ".mp3", ".m4a", ".flac"):
        p = d / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_text(s):
    # {R}..{/} red, {Y}..{/} yellow (ASS colours are &HBBGGRR&)
    s = s.replace("{R}", r"{\c&H2A2AE6&}").replace("{Y}", r"{\c&H00D7FF&}").replace("{/}", r"{\c&HFFFFFF&}")
    return s


def build_ass(path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Telop,{FONT},104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,9,3,5,90,90,0,1
Style: Big,{FONT},150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,12,4,5,90,90,0,1
Style: Title,{FONT},124,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,4,0,1,11,4,5,90,90,0,1
Style: Source,{FONT},30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,0,1
Style: Disc,{FONT},34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    t0 = 0.0
    total = sum(s["dur"] for s in TL["shots"])
    # constant disclaimer, kept above the Reels caption/UI band
    ev.append(f"Dialogue: 0,{ts(0)},{ts(total)},Disc,,0,0,470,,{TL['disclaimer']}")
    for s in TL["shots"]:
        for item in s["telops"]:
            text, a, b = item[0], item[1], item[2]
            kind = item[3] if len(item) > 3 else "normal"
            style = {"title": "Title", "big": "Big"}.get(kind, "Telop")
            y = 860 if kind == "title" else 940
            pop = r"{\fad(80,60)\t(0,120,\fscx104\fscy104)\t(120,220,\fscx100\fscy100)}"
            ev.append(f"Dialogue: 1,{ts(t0+a)},{ts(t0+b)},{style},,0,0,0,,{{\\pos({W//2},{y})}}{pop}{ass_text(text)}")
        if s.get("src"):
            ev.append(f"Dialogue: 0,{ts(t0+0.2)},{ts(t0+s['dur'])},Source,,0,0,420,,{TL['source_note']}")
        t0 += s["dur"]
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")
    return total


def placeholder(shots_dir):
    shots_dir.mkdir(parents=True, exist_ok=True)
    for s in TL["shots"]:
        out = shots_dir / f"shot{s['id']:02d}.mp4"
        if out.exists():
            continue
        hue = s["id"] * 30
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             f"testsrc2=s=720x1280:r={FPS}:d={s['dur']}", "-vf",
             f"hue=h={hue}:s=0.4,eq=brightness=-0.15,drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc:text='PLACEHOLDER SHOT {s['id']}':fontsize=40:fontcolor=white:x=40:y=60",
             "-pix_fmt", "yuv420p", str(out)])


def main():
    work = pathlib.Path(sys.argv[1]).resolve()
    if "--placeholder" in sys.argv:
        placeholder(work / "shots")
    out_dir = work / "out"; out_dir.mkdir(parents=True, exist_ok=True)
    tmp = work / "tmp"; tmp.mkdir(exist_ok=True)

    # 1) normalise every shot to exact length, 1080x1920, 30fps, with a gentle handheld drift
    parts = []
    for s in TL["shots"]:
        src = work / "shots" / f"shot{s['id']:02d}.mp4"
        dst = tmp / f"n{s['id']:02d}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
              f"tpad=stop_mode=clone:stop_duration={s['dur']},trim=duration={s['dur']},setpts=PTS-STARTPTS,"
              "eq=contrast=1.04:saturation=0.92,format=yuv420p")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-an", "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", str(dst)])
        parts.append(dst)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])

    # 2) telops
    ass = tmp / "telop.ass"
    total = build_ass(ass)

    # 3) audio mix: narration (front), sfx, bgm (low), then loudness normalise to -14 LUFS
    adir = work / "audio"
    inputs, filters, labels = [], [], []
    t0 = 0.0
    idx = 0
    for s in TL["shots"]:
        for kind, gain in (("narration", 1.0), ("sfx", 0.55)):
            p = find(adir, f"{kind}_{s['id']:02d}")
            if p:
                inputs += ["-i", str(p)]
                idx += 1
                delay = int((t0 + (NARR_OFFSET if kind == "narration" else 0)) * 1000)
                filters.append(f"[{idx}:a]aresample=48000,volume={gain},adelay={delay}|{delay}[a{idx}]")
                labels.append(f"[a{idx}]")
        t0 += s["dur"]
    bgm = find(adir, "bgm")
    if bgm:
        inputs += ["-stream_loop", "-1", "-i", str(bgm)]
        idx += 1
        filters.append(f"[{idx}:a]aresample=48000,volume=0.12,atrim=0:{total},afade=t=out:st={total-2}:d=2[a{idx}]")
        labels.append(f"[a{idx}]")
    silent = f"anullsrc=r=48000:cl=stereo,atrim=0:{total}[base]"
    mix = f"[base]{''.join(labels)}amix=inputs={len(labels)+1}:normalize=0:duration=first[mix]"
    fc = ";".join([silent] + filters + [mix])
    premix = tmp / "premix.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc", *inputs,
         "-filter_complex", fc.replace("[0:a]", ""), "-map", "[mix]", "-t", str(total), str(premix)])
    # two-pass loudnorm
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(premix), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]+\}\s*$", r.stderr, re.S).group(0))
    lin = "linear=true" if float(m["input_i"]) > -70 else "linear=false"
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:{lin}")

    out = out_dir / "nankai_trough_reels.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-i", str(premix),
         "-filter_complex", f"[0:v]ass={ass}:fontsdir=/usr/share/fonts/opentype/noto[v];[1:a]{ln},aresample=48000[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
         "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", str(total), str(out)])
    print("wrote", out)


if __name__ == "__main__":
    main()
