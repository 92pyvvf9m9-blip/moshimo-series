#!/usr/bin/env bash
# parts/p01.mp4〜 を番号順につないで out/ep01_nessie.mp4 を作る
set -euo pipefail
cd "$(dirname "$0")"
ls parts/p*.mp4 | sort | sed "s|^|file '$PWD/|; s|$|'|" > out/list.txt
ffmpeg -y -f concat -safe 0 -i out/list.txt -c:v libx264 -pix_fmt yuv420p -r 30 -c:a aac out/ep01_nessie.mp4
echo "完成: out/ep01_nessie.mp4"
