"""備份 pickemstracker.net 的數據到 data.json（給網頁在讀不到原站時使用）。
由 GitHub Actions 每 10 分鐘執行一次，只用 Python 內建模組。
"""
import json, os, sys, urllib.request

SRC = "https://pickemstracker.net/api/data"
OUT = "data.json"

try:
    req = urllib.request.Request(SRC, headers={"User-Agent": "Worlds2026CrystalBallZH/1.0 (fan translation)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        new = json.load(r)
    if not new.get("cards"):
        raise RuntimeError("原站回傳的資料沒有題目")
except Exception as e:
    print("抓資料失敗：", e)
    sys.exit(1)

old = {}
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        try:
            old = json.load(f)
        except ValueError:
            old = {}
if old.get("cards") == new.get("cards") and old.get("games") == new.get("games"):
    print("資料沒有變化")
else:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    print(f"已更新：{new.get('games')} 場，原站更新時間 {new.get('updated')}")
