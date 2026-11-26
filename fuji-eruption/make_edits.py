#!/usr/bin/env python3
"""Write edit_60.json (TikTok full) and edit_45.json (Reels / Shorts) for the Fuji eruption episode.

Narration line boundaries are in the original TTS file's time (silence-detected); compose.py
applies the 1.05x tempo. Telop times are in the same source time and are mapped per line.
"""
import json

TEMPO = 1.05
LINES = [  # [src_start, src_end] per narration line (narration.mp3, before tempo)
    [0.00, 2.56], [3.19, 7.49], [8.25, 11.89], [12.39, 15.43], [15.88, 18.85], [19.53, 23.56], [24.00, 26.45],
    [27.18, 31.34], [32.15, 37.99], [38.75, 44.27], [44.76, 48.88], [49.51, 51.87], [52.37, 55.81], [56.50, 58.57]]
SRC = {
    "src_wg": "出典：中央防災会議 大規模噴火時の広域降灰対策検討WG報告（2020年4月）",
    "src_gl": "出典：内閣府 首都圏における広域降灰対策ガイドライン（2025年3月）",
    "src_both": "出典：中央防災会議WG報告（2020年4月）・内閣府ガイドライン（2025年3月）",
}
# [text, line, src_start, src_end, style, note]
TELOPS = [
    ["もしも今、", 0, -0.42, 1.00, "title"], ["{R}富士山{/}が", 0, 1.00, 1.75, "title"], ["噴火したら", 0, 1.75, 3.10, "title"],
    ["想定は", 1, 3.30, 4.25, "normal", "src_wg"], ["{Y}1707年 宝永噴火{/}", 1, 4.25, 6.55, "normal", "src_wg"],
    ["と同じ規模", 1, 6.55, 7.90, "normal", "src_wg"],
    ["数時間後", 2, 8.25, 9.70, "normal"], ["新宿の空が", 2, 9.70, 11.10, "normal"], ["暗くなる", 2, 11.10, 12.30, "normal"],
    ["地上の鉄道は", 3, 12.45, 13.80, "normal", "src_gl"], ["{R}微量{/}の灰で止まる", 3, 13.80, 15.80, "big", "src_gl"],
    ["駅が閉まり", 4, 15.88, 17.60, "normal"], ["人の流れが止まる", 4, 17.60, 19.30, "normal"],
    ["雨なら", 5, 19.53, 21.45, "normal", "src_gl"], ["{R}3mm{/}で停電", 5, 21.45, 23.90, "big", "src_gl"],
    ["雨なら{R}3cm{/}で", 6, 24.00, 25.10, "big", "src_gl"], ["車が走れない", 6, 25.10, 26.90, "normal", "src_gl"],
    ["夜", 7, 27.40, 27.75, "normal"], ["明かりの消えた街に", 7, 27.75, 29.70, "normal"], ["灰が積もり続ける", 7, 29.70, 31.80, "normal"],
    ["雨を含んだ灰", 8, 32.15, 33.95, "normal", "src_gl"], ["{R}30cm{/}積もれば", 8, 33.95, 35.70, "big", "src_gl"],
    ["木造家屋が", 8, 35.70, 36.75, "normal", "src_gl"], ["倒壊するおそれ", 8, 36.75, 38.40, "normal", "src_gl"],
    ["処理が必要な灰", 9, 38.80, 41.80, "normal", "src_both"], ["約{R}4.9億{/}m³", 9, 41.80, 44.70, "big", "src_both"],
    ["東日本大震災の", 10, 44.80, 46.55, "normal", "src_both"], ["災害廃棄物の", 10, 46.55, 47.95, "normal", "src_both"],
    ["約{Y}10倍{/}", 10, 47.95, 49.30, "big", "src_both"],
    ["最後の噴火から", 11, 49.55, 50.80, "normal", "src_wg"], ["{Y}300年{/}以上", 11, 50.80, 52.30, "big", "src_wg"],
    ["これは予言ではない", 12, 52.40, 54.20, "normal"], ["“{R}公式の想定{/}”だ", 12, 54.20, 56.40, "big"],
    ["次回", 13, 56.55, 57.20, "normal"], ["{Y}首都直下地震{/}編", 13, 57.20, 59.40, "big"],
]
ASH = {"f05": 0.25, "f06": 0.45, "f07": 0.5, "f08": 0.45, "f09": 0.55, "f10": 0.6, "f11": 0.7, "f12": 0.8, "f13": 0.7,
       "f14": 0.75, "f15": 0.85, "f16": 0.5, "f17": 0.65, "f18": 0.5, "f19": 0.55, "f20": 0.2, "f21": 0.2, "f22": 0.15,
       "f23": 0.35, "f24": 0.4, "f25": 0.1}

FULL_CUTS = [
    ["f01", 0.00, 1.60, "erupt"], ["f02", 1.60, 3.20, "handheld_day"],
    ["f03", 3.20, 5.50, "erupt"], ["f04", 5.50, 7.70, "handheld_day"],
    ["f05", 7.70, 10.10, "ash_light"], ["f06", 10.10, 12.20, "ash_light"], ["f08", 12.20, 15.10, "ash_light"],
    ["f09", 15.10, 16.70, "ash"], ["f10", 16.70, 18.30, "ash"],
    ["f11", 18.30, 20.30, "ash"], ["f13", 20.30, 22.40, "ash"], ["f14", 22.40, 24.00, "ash"],
    ["f15", 24.00, 27.00, "ash_walk"],
    ["f16", 27.00, 29.40, "ash_d4n"], ["f17", 29.40, 32.00, "ash_night"], ["f18", 32.00, 34.90, "ash_night"],
    ["f19", 34.90, 37.70, "ash_night"],
    ["f20", 37.70, 41.20, "ash_dawn"], ["f21", 41.20, 44.60, "ash_dawn"], ["f22", 44.60, 48.30, "ash_dawn"],
    ["f23", 48.30, 51.30, "ash_dusk"], ["f24", 51.30, 54.90, "ash_dusk"], ["f25", 54.90, 57.30, "handheld"],
    ["f26", 57.30, 60.00, "night_end"],
]
FULL_PLACE = [0.40, 3.30, 7.95, 11.85, 15.20, 18.45, 22.70, 27.25, 31.75, 38.05, 43.75, 48.75, 51.55, 57.60]

SHORT_SEQ = [("f01", 1.6), ("f02", 1.6), ("f05", 2.3), ("f06", 2.0), ("f08", 2.8), ("f11", 1.9),
             ("f13", 2.1), ("f14", 1.6), ("f15", 1.6, "end"), ("f16", 2.4), ("f17", 2.6), ("f18", 2.9), ("f19", 2.8),
             ("f20", 3.0), ("f21", 3.2), ("f23", 2.6), ("f24", 3.6), ("f25", 2.0), ("f26", 2.4, "end")]
SHORT_PLACE = {0: 0.40, 2: 3.40, 3: 7.25, 5: 10.55, 6: 14.75, 7: 17.80, 8: 22.20, 9: 28.40, 11: 34.60, 12: 37.30,
               13: 42.80}


GROUND = {"f11": {"y0": 0.02, "y1": 0.30, "alpha": 0.86}, "f14": {"y0": 0.45, "y1": 0.70, "alpha": 0.7},
          "f19": {"y0": 0.55, "y1": 0.80, "alpha": 0.55}}


PICKS = {"f16": "f05", "f24": "f23"}
REFRAME = {"f24": {"zoom": [1.42, 1.58], "cy": -0.04}}


def base(total):
    return {"picks": PICKS, "reframe": REFRAME, "fps": 30, "width": 1080, "height": 1920, "total": total,
            "disclaimer": "※内閣府の想定に基づく再現（予言ではありません）",
            "src_main": SRC["src_gl"], "src_notes": SRC, "ash": ASH, "ground_ash": GROUND}


full = base(60.0)
full["cuts"] = FULL_CUTS
full["fade_in"] = {"f16": 0.6, "f20": 0.5}
full["fade_out"] = {"f15": 0.4, "f26": 0.6}
full["narration"] = {"file": "narration.mp3", "tempo": TEMPO,
                     "lines": [[a, b, p] for (a, b), p in zip(LINES, FULL_PLACE)]}
full["telops"] = TELOPS
json.dump(full, open("edit_60.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 45 s: reuse the full-version cuts (trimmed from their start), drop narration lines 2, 5 and 11
full_len = {c[0]: round(c[2] - c[1], 2) for c in FULL_CUTS}
t = 0.0
cuts = []
for item in SHORT_SEQ:
    cid, d = item[0], item[1]
    assert d <= full_len[cid] + 1e-6, (cid, d, full_len[cid])
    style = next(c[3] for c in FULL_CUTS if c[0] == cid)
    off = round(full_len[cid] - d, 3) if len(item) > 2 and item[2] == "end" else 0.0
    cuts.append([cid, round(t, 2), round(t + d, 2), style, off])
    t += d
assert abs(t - 45.0) < 1e-6, t
short = base(45.0)
short["cuts"] = cuts
short["fade_in"] = {"f16": 0.6, "f20": 0.5}
short["fade_out"] = {"f15": 0.4, "f26": 0.6}
short["narration"] = {"file": "narration.mp3", "tempo": TEMPO,
                      "lines": [[LINES[i][0], LINES[i][1], p] for i, p in sorted(SHORT_PLACE.items())],
                      "all_lines": [[LINES[i][0], LINES[i][1], SHORT_PLACE.get(i, -100.0)] for i in range(len(LINES))]}
short["telops"] = [tl for tl in TELOPS if tl[1] in SHORT_PLACE]
json.dump(short, open("edit_45.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("cuts 60:", len(FULL_CUTS), " cuts 45:", len(cuts))
