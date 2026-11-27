# 固定キャラ「時計目の黒猫」— 基準画像の作り方

参照画像：`character_ref.webp`（毎回かならず添付する）

## 共通（全部の頭に付ける）
```
Photorealistic live-action film still, NOT illustration, NOT anime, NOT painting.
The same cat as the reference image: chubby, very fluffy black long-haired cat that stands on its hind legs like a small person,
glowing golden eyes with clock faces (roman numerals) inside the irises, old brown leather backpack with a small canvas pouch,
brown leather collar with a brass bell. Real fur texture, cinematic lighting, shallow depth of field, 9:16 vertical.
Plain dark stone-wall background. No text, no logo, no watermark.
```

## 8枚（共通の後ろに1行足す）

| No | 用途 | 足す1行 |
|---|---|---|
| c1 | 通常 | Full body, front view, calm neutral expression, standing upright. |
| c2 | 驚き | Upper body, front view, eyes wide open, ears straight up, mouth slightly open, surprised. |
| c3 | 恐怖 | Upper body, front view, ears flat back, fur puffed up, pupils thin, frightened, cold blue light from the side. |
| c4 | 笑い | Upper body, front view, eyes narrowed happily, mouth open in a cheerful cat smile. |
| c5 | 横顔 | Full body, exact side profile facing right, standing upright, backpack clearly visible. |
| c6 | 後ろ姿 | Full body, back view, backpack and tail clearly visible, looking ahead into a dark tunnel. |
| c7 | 歩き | Full body, walking on hind legs mid-stride toward the camera, holding a small lit lantern. |
| c8 | 座り | Full body, sitting on a stone step, backpack beside it, relaxed. |

## 判定のしかた
- 参照画像と並べて、**目の時計・リュック・鈴・毛の長さ**の4点がそろっているものだけ合格。
- 絵っぽい（アニメ・手書き・漫画・シルエット・絵画）ものは不合格。作り直す。
- 合格した8枚は `nekoden/ref/c1.png`〜`c8.png` に保存し、以後の全話で参照に使う。
