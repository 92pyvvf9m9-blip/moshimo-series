# もしもシリーズ（自然災害編）南海トラフ巨大地震 — 制作フォルダ

## 納品物

| # | ファイル | 内容 |
|---|---|---|
| 1 | `output/nankai_trough_reels.mp4` | 完成動画。縦型1080×1920、30fps、69.6秒、H.264+AAC、−14 LUFS |
| 2 | `script.md` | 台本。ナレーション全文、読み上げ用テキスト、場面対応表、制作メモ |
| 3 | `sources.md` | 使用した公式数字と出典の一覧。内閣府2025年3月公表の一次資料で照合済み |

補助ファイル：
- `output/contact_sheet.png`：完成動画のコマ見本
- `assets/hero_ref.png`：主人公の基準画像
- `assets/narration_elevenlabs.mp3`：生成したナレーション音声。修正前の元データ

## 作り直し方（このフォルダのスクリプト）

```
python gen_clips.py shots.json CLIPS --only env                   # 背景カット（CPU・bf16）
python gen_clips.py shots.json CLIPS --only hero --hero REF.png   # 主人公カット（IP-Adapter）
python gen_clips.py shots_alt.json CLIPS --variant 1             # 撮り直しカット
python post.py edit.json CLIPS CUTS --pick 02b=02b_v1 ...         # 補間・カメラの動き・グレーディング
python sound.py scenes.json AUDIO                                 # 効果音・BGMの合成
python compose.py edit.json CUTS AUDIO out.mp4                    # テロップ・ミックス・書き出し
python qa.py out.mp4 sheet.png                                    # 形式・ラウドネスの確認
```

- 映像の生成に使ったモデル：
  - ByteDance/AnimateDiff-Lightning
  - emilianJR/epiCRealism
  - h94/IP-Adapter
- テロップのフォント：Noto Serif CJK JP Bold
