"""從 Leaguepedia 抓 Worlds 2026 比賽數據，存成 data.json。
由 GitHub Actions 每 10 分鐘執行一次；只用 Python 內建模組，不用另外安裝套件。
可選：在 repo 的 Secrets 設 LP_USER / LP_PASS（Leaguepedia 的 Bot password），被限流的機會更低。
"""
import http.cookiejar, json, os, sys, time, urllib.parse, urllib.request

API = "https://lol.fandom.com/api.php"
UA = "Worlds2026CrystalBallTracker/1.0 (fan project hosted on GitHub Pages)"
WHERE = 'OverviewPage LIKE "2026 Season World Championship%"'
OUT = "data.json"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(params, post=False):
    params = {**params, "format": "json"}
    data = urllib.parse.urlencode(params).encode()
    if post:
        req = urllib.request.Request(API, data=data, headers={"User-Agent": UA})
    else:
        req = urllib.request.Request(API + "?" + data.decode(), headers={"User-Agent": UA})
    with opener.open(req, timeout=60) as r:
        return json.load(r)


def login():
    user, pw = os.environ.get("LP_USER"), os.environ.get("LP_PASS")
    if not user or not pw:
        return
    try:
        token = call({"action": "query", "meta": "tokens", "type": "login"})["query"]["tokens"]["logintoken"]
        res = call({"action": "login", "lgname": user, "lgpassword": pw, "lgtoken": token}, post=True)
        print("登入：", res.get("login", {}).get("result"))
    except Exception as e:
        print("登入失敗，改用匿名查詢：", e)


def cargo(**params):
    rows, offset = [], 0
    while True:
        p = {"action": "cargoquery", "limit": "500", "offset": str(offset), **params}
        for attempt in range(6):
            j = call(p)
            err = j.get("error")
            if not err:
                break
            if err.get("code") == "ratelimited" or "rate limit" in err.get("info", "").lower():
                wait = 30 * (attempt + 1)
                print(f"被限流，{wait} 秒後重試…")
                time.sleep(wait)
                continue
            raise RuntimeError(err.get("info") or err.get("code"))
        else:
            raise RuntimeError("重試多次仍被限流")
        batch = [x["title"] for x in j.get("cargoquery", [])]
        rows += batch
        time.sleep(3)  # 對 Leaguepedia 客氣一點
        if len(batch) < 500:
            return rows
        offset += 500


def main():
    login()
    games = cargo(tables="ScoreboardGames", where=WHERE, order_by="DateTime_UTC",
                  fields="GameId=gid,OverviewPage=page,Team1=t1,Team2=t2,WinTeam=win,Gamelength=lenStr,"
                         "Gamelength_Number=len,DateTime_UTC=date,Team1Bans=b1,Team2Bans=b2")
    players = cargo(tables="ScoreboardPlayers", where=WHERE,
                    fields="GameId=gid,Link=link,Team=team,Champion=champ,Kills=k,Deaths=d,Assists=a,"
                           "CS=cs,DamageToChampions=dmg,Role=role,PlayerWin=pw")
    regions = {}
    names = sorted({t for g in games for t in (g.get("t1"), g.get("t2")) if t})
    if names:
        lst = ",".join('"' + n.replace('"', '\\"') + '"' for n in names)
        for r in cargo(tables="Teams", fields="Name=name,Region=region,Short=short", where=f"Name IN ({lst})"):
            regions[r["name"]] = {"region": r.get("region"), "short": r.get("short")}

    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    if old.get("games") and len(games) < len(old["games"]):
        print("新抓到的場次比舊資料少，可能是 Leaguepedia 暫時異常，保留舊資料")
        return
    if old.get("games") == games and old.get("players") == players and old.get("regions") == regions:
        print("資料沒有變化")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"games": games, "players": players, "regions": regions,
                   "fetchedAt": int(time.time() * 1000)}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"已更新：{len(games)} 場、{len(players)} 筆選手資料")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("抓資料失敗：", e)
        sys.exit(0)  # 失敗就保留上一份 data.json，等下一輪再試
