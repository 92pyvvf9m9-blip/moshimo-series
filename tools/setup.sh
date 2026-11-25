#!/usr/bin/env bash
# Recreate the video toolchain for this repo on a fresh Linux machine (CPU only).
#   bash tools/setup.sh            # venv at ~/.venvs/moshimo (override with VENV=...)
# Installs: FFmpeg, Noto Serif CJK, Python venv (PyTorch CPU, diffusers, faster-whisper = Whisper,
# yt-dlp, pyloudnorm), and the Node tools in tools/ (Remotion, HyperFrames).
set -euo pipefail
cd "$(dirname "$0")"
VENV="${VENV:-$HOME/.venvs/moshimo}"

if command -v apt-get >/dev/null; then
  sudo_cmd=""; [ "$(id -u)" -ne 0 ] && sudo_cmd="sudo"
  $sudo_cmd apt-get update -q
  $sudo_cmd apt-get install -y -q ffmpeg fonts-noto-cjk fonts-noto-cjk-extra
fi

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/pip" install -q -r requirements.txt

npm install --no-audit --no-fund

echo "--- versions"
ffmpeg -version | head -1
"$VENV/bin/python" -c "import torch, diffusers, faster_whisper; print('torch', torch.__version__, 'diffusers', diffusers.__version__, 'faster-whisper', faster_whisper.__version__)"
"$VENV/bin/yt-dlp" --version
npx --no-install hyperframes --version
npx --no-install remotion versions 2>/dev/null | head -3 || true
