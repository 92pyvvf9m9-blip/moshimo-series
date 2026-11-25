# もしもシリーズ（自然災害編）第2話 富士山 大規模噴火 — 制作フォルダ

## 納品物

| # | ファイル | 内容 |
|---|---|---|
| 1 | `output/fuji_eruption_full_60s.mp4` | フル版（TikTok用）。60.0秒、縦型1080×1920、30fps、H.264+AAC、−14 LUFS |
| 1 | `output/fuji_eruption_short_45s.mp4` | 短縮版（Reels・YouTubeショート用）。45.0秒、形式は同じ |
| 2 | `script.md` | 台本。ナレーション全文、読み上げ用ひらがな版、場面対応表（60秒版と45秒版） |
| 3 | `sources.md` | 使用した公式数字と出典の一覧。一次資料でページまで照合済み |

補助ファイル：
- `output/contact_sheet_60.png`：60秒版のコマ見本
- `output/contact_sheet_45.png`：45秒版のコマ見本
- `assets/narration_elevenlabs.mp3`：生成したナレーション音声

## 作り直し方

パイプラインは第1話と共通です（`../nankai-trough/` のスクリプト）。ツールの入れ方は `../tools/setup.sh` を参照してください。

```
python ../nankai-trough/gen_clips.py shots.json CLIPS --hero HERO_FACE.png --ip-weight ip-adapter-plus-face_sd15.safetensors
python make_edits.py                                   # edit_60.json / edit_45.json を作る
python ../nankai-trough/post.py edit_60.json CLIPS CUTS   # 灰のパーティクル・カメラの動き・グレーディング
python sound.py edit_60.json AUDIO60 && python sound.py edit_45.json AUDIO45
python ../nankai-trough/compose.py edit_60.json CUTS AUDIO60 output/fuji_eruption_full_60s.mp4
python ../nankai-trough/compose.py edit_45.json CUTS AUDIO45 output/fuji_eruption_short_45s.mp4
```

45秒版は、60秒版で仕上げたカットを先頭から短く切って再利用します（`edit_45.json` の cuts の5番目の値が切り出し開始位置）。
