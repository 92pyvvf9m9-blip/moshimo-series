# 第1話「ネッシーの背中に乗ってみた」— パート分割表

7パートに分けて1本ずつ作り、最後に `join.sh` でつなぐ。
直したいパートだけ作り直して、もう一度つなげば完成し直せる。

## 共通（全パートで同じ）
- 縦 1080x1920、30fps
- 猫の参照画像：`../character_ref.webp`（毎回これを渡す）
- 猫の固定指定（英語プロンプトの先頭に必ず入れる）：
  `chubby fluffy black long-haired cat, glowing golden clock-face eyes, brown leather backpack, leather collar with brass bell`
- 画面の端に小さく「※伝説をもとにした創作です」（p01 と p07 だけでも可）

## パート一覧

| No | 秒 | 長さ | 画像プロンプト（英語） | 動き | ナレーション | テロップ | 効果音 |
|---|---|---|---|---|---|---|---|
| p01 | 0-3 | 3s | (cat) sitting on top of the head of a giant long-necked lake monster rising from a misty dark lake, dawn fog, cinematic | ゆっくりズームイン | ネッシーに会いに、ネス湖まで行ってきた。 | ネッシーの背中に 乗ってみた | 水しぶき |
| p02 | 3-7 | 4s | (cat) standing on a rocky shore of a vast misty Scottish loch at dawn, holding up a glowing lantern, clock eyes flashing | 目が光る→引き | イギリス、ネス湖。深さは200メートル以上。 | イギリス・ネス湖 | 時計のカチッ |
| p03 | 7-12 | 5s | dark loch surface with bubbles and a V-shaped ripple approaching, (cat) small in foreground, ears perked | 波紋が近づく横パン | ……何か、来た。 | （なし） | 泡の音・低い音 |
| p04 | 12-17 | 5s | huge long neck and small head emerging from the water, (cat) looking up in awe, low angle | 下から上へティルト | 本当に、いた。 | 本当に、いた。 | 水が割れる音 |
| p05 | 17-24 | 7s | (cat) riding on the back of the lake monster gliding across the loch, wake behind, morning light through fog | 横移動・揺れ | 乗せてくれた。 | （なし） | 水を切る音・明るいBGM |
| p06 | 24-30 | 6s | view from above: (cat) on the monster's back peering down into the water, a second much larger shadow visible deep below | ゆっくりズーム→影に寄る | ……あれ。下にも、何かいる。 | 下にも、何かいる。 | BGM停止・低い音 |
| p07 | 30-35 | 5s | pitch black, only two glowing golden clock-face eyes visible | 暗転→目だけ光る | （なし） | 次は、エジプトへ。 | 鈴「チリン」 |

## 作業の順番
1. 画像：各パート1枚 → `parts/p01.png` 〜 `p07.png`
2. 音声：各パートのナレーション → `parts/p01.wav` …（無い所は無音でOK）
3. パート動画：画像＋動き＋音声＋テロップ → `parts/p01.mp4` 〜 `p07.mp4`
4. つなぐ：`bash join.sh` → `out/ep01_nessie.mp4`

## 直す時
- 例：p04の首の形が変 → p04.png を作り直す → p04.mp4 を作り直す → `bash join.sh`
- 他のパートには触らない。変更は下の記録に1行書く。

## 変更記録
| 日付 | パート | 何を変えたか | 理由 |
|---|---|---|---|

## 画像の作り方（クレジット切れ対策・上から順に使う）
1. **Sunra（無料の毎日クレジット）**：sunra.ai を1日1回開くとその日の分が付く。`character_ref.webp` を参照に渡せるので猫がそろう。
2. **Gemini アプリ（スマホ・無料）**：猫の画像を添付して「この猫で、〜の場面を縦長で」と頼む。参照画像が使えるので一番の予備。
3. **Pollinations（登録不要・自動）**：品質が低く、透かしが入り、猫がそろわない（2026-11-27 試験済み）。背景だけの場面（p03 の湖面、p07 の暗闇）に限って使う。
- 1日1本のために必要なのは画像7枚だけ。背景だけの場面は使い回してよい。
| 2026-11-27 | 全体 | 他アプリなしで作る方式に変更：背景=無料生成（bg/）、猫=元画像の切り抜き（cat_cut.png）、`python3 build.py` でパート作成 | 他アプリを開く手間をなくすため |
| 2026-11-27 | p01,p04 | テロップが猫に重なったので位置を移動 | 見やすさ |
| 2026-11-27 | p05 | 猫が首の横に浮いていたので、頭の上に乗った寄りの画に変更 | 「乗った」に見えるように |
