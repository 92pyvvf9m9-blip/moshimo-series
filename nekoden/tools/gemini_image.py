"""猫の参照画像つきで Gemini に1枚作らせる。
使い方: GEMINI_KEY_FILE=鍵ファイル python3 gemini_image.py モデル名 出力.png "プロンプト"
"""
import base64, json, os, sys, urllib.request, pathlib
model, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
key = pathlib.Path(os.environ["GEMINI_KEY_FILE"]).read_text().strip()
ref = pathlib.Path(__file__).resolve().parent.parent / "character_ref.webp"
base = ("この画像の猫を主人公にしてください。見た目は参照画像と完全に同じ：太っていてフワフワの長毛の黒猫、"
        "金色に光る時計の目、茶色の革リュックと小さな布ポーチ、鈴の付いた革の首輪、後ろ足で立つ。"
        "実写映画のワンシーンのような写真のリアルさ。イラスト・アニメ・絵画風は禁止。文字やロゴは入れない。縦長9:16。\n場面：")
body = {"contents": [{"parts": [
          {"inline_data": {"mime_type": "image/webp", "data": base64.b64encode(ref.read_bytes()).decode()}},
          {"text": base + prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
req = urllib.request.Request(
    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
try:
    d = json.load(urllib.request.urlopen(req, timeout=180))
except urllib.error.HTTPError as e:
    err = json.load(e).get("error", {}); print("ERROR", err.get("code"), err.get("message", "")[:300]); sys.exit(1)
for c in d.get("candidates", []):
    for p in c.get("content", {}).get("parts", []):
        if "inlineData" in p:
            pathlib.Path(out).write_bytes(base64.b64decode(p["inlineData"]["data"])); print("saved", out); sys.exit(0)
print("NO IMAGE", json.dumps(d)[:300]); sys.exit(1)
