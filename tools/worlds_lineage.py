# -*- coding: utf-8 -*-
"""核验本席诸世界之谱系（worlds/detail 回显 refWorldId）——**只查本席所建，不查他席**
产出：谱系表（名称／refWorldId／prompt 前 40 字／createdAt／updatedAt）
"""
import json, pathlib, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
OUT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"/"worlds_lineage_20261009_CAIRN.json"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")
P = "8rcpnKlw6xp3FtpLvZIGB"
MINE = [
    ("夜间游乐场",      P + "3qBaKNoYO5K4KdKKOvya89fNs2BU7TeGEDpaTrloI7x"),
    ("霓虹数据游乐场",  P + "9mlTipFohD7syfWSOD-bt5fNs2BU7TeGEDpaTrloI7x"),
    ("数据圣所",        P + "9mlTipFohD7syfWSOD-bt47uUb8fS_MDUHY-F14PDMt"),
    ("器物约束",        P + "-sdIRqsVf4bn3Nd5ZSGwjtfNs2BU7TeGEDpaTrloI7x"),
    ("数据虚空",        P + "3qBaKNoYO5K4KdKKOvya887uUb8fS_MDUHY-F14PDMt"),
    ("墨档契约",        P + "zay7UPsbkqgCig4-jfNwNxfNs2BU7TeGEDpaTrloI7x"),
    ("无门窗居所(v4衍生)", P + "_wg3Z1hMjTLvrUso3I2oXnvYWx9jdVEIlPMdelwsS6b"),
]

def get(wid, to=40):
    url = BASE + "/worlds/detail?encryptedWorldId=" + urllib.parse.quote(wid)
    r = urllib.request.Request(url, method="GET"); r.add_header("Authorization", "Bearer " + K)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:200]
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:120]

rows, ids = [], {}
print("=== 本席诸世界详情（谱系核验）===")
for name, wid in MINE:
    st, dt, txt = get(wid)
    rec = {"name": name, "wid": wid, "http": st}
    try:
        dd = (json.loads(txt).get("output") or {}).get("data") or json.loads(txt).get("data") or {}
        rec.update({"api_name": dd.get("name"), "refWorldId": dd.get("refWorldId"),
                    "prompt40": str(dd.get("prompt"))[:40], "createdAt": dd.get("createdAt"),
                    "updatedAt": dd.get("updatedAt"), "status": dd.get("status")})
        ids[dd.get("name") or name] = wid
        print("   %-18s ⇒ %s ｜ 平台名=%-12s ｜ refWorldId=%s" % (
            name, st, str(dd.get("name"))[:12], (str(dd.get("refWorldId"))[:22] + "…") if dd.get("refWorldId") else "null"))
    except Exception:
        rec.update({"raw": txt[:160]})
        print("   %-18s ⇒ %s ｜ 解析失败：%s" % (name, st, txt[:100]))
    rows.append(rec)
    time.sleep(0.3)

# 谱系判读：哪些世界之 refWorldId 指向本席另一世界
name_by_id = {v: k for k, v in ids.items()}
print("\n=== ★ 谱系判读 ===")
linked = 0
for r in rows:
    ref = r.get("refWorldId")
    if ref:
        linked += 1
        print("   %s ← 衍生自 ← %s（refWorldId=%s…）" % (r["name"], name_by_id.get(ref, "（本席名单之外/他席）"), str(ref)[:26]))
print("   含 refWorldId 者=%d/%d" % (linked, len(rows)))
OUT.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local",
                           "note": "只查本席所建世界；未查他席世界之详情（守边界）", "rows": rows},
                          ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("   落盘：%s（%d B）" % (OUT.name, OUT.stat().st_size))
