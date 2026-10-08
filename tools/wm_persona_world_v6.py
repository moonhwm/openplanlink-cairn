# -*- coding: utf-8 -*-
"""v6：refWorldId(v5) + 人设增量 #10「共享面之礼」——建世界 → 轮询 ready → 详情核谱系"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
BASE_DIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
PNG = BASE_DIR/"persona_luzhibai_v6_sharedsurface_20261009.png"
REF_V5 = "8rcpnKlw6xp3FtpLvZIGB9mlTipFohD7syfWSOD-bt7vYWx9jdVEIlPMdelwsS6b"
BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

def call(url, body=None, method="GET", to=60):
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:150]

PROMPT = ("第三人称：同一间「没有门窗」的居所，如今多出一张「共享面」——两席在同一张台面上同时书写。"
          "共享面上立着三条礼：其一，环形箭头标示「先取后推」（fetch → merge → push）；"
          "其二，一面护盾护住台面一角，标示「他席提交不覆盖」；其三，一枚朱红印记标示「签名树冲突必重签」。"
          "地面仍是六枚节拍节点（肯定—着法—游戏—验收—留痕—器物），侧旁三件器物（齿轮／闸门／座钟）如常，"
          "左壁数据链贯出如常。整体仍是「知其白，守其黑」的双色世界，但秩序已从「一人一室」延展为"
          "「多席共面而不相犯」。")

body = {"async": True, "perspective": "third_person", "prompt": PROMPT, "refWorldId": REF_V5,
        "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(PNG.read_bytes()).decode()}}
st, dt, txt = call(BASE + "/worlds", body, "POST")
print("=== ① 建 World v6（refWorldId=v5）⇒ HTTP %s ｜ %.2fs" % (st, dt))
wid = None
try:
    data = ((json.loads(txt).get("output") or {}).get("data") or {})
    wid = data.get("encryptedWorldId")
    print("   World ID=%s ｜ status=%s" % ((str(wid)[:18] + "…") if wid else "(未取到)", data.get("status")))
except Exception:
    print("   原始：%s" % txt[:240])

if wid:
    for i in range(4):
        time.sleep(8)
        s2, d2, t2 = call(BASE + "/worlds/build-status?encryptedWorldId=" + urllib.parse.quote(str(wid)), None, "GET")
        try:
            dd = json.loads(t2).get("output", {}).get("data", {})
        except Exception:
            dd = {}
        print("=== ② 轮询 %d ⇒ HTTP %s ｜ %.2fs ｜ status=%s ｜ 平台命名=%s" % (i+1, s2, d2, dd.get("status"), dd.get("name")))
        if dd.get("status") == "ready":
            print("   ★★ ready（平台命名：%s）" % dd.get("name"))
            print("   ★ v6 World ID：%s" % wid)
            ff = dd.get("firstFrame")
            if ff:
                out = BASE_DIR/"persona_v6_world_firstframe_20261009.png"
                try:
                    req = urllib.request.Request(ff, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        out.write_bytes(resp.read())
                    print("   ★ 首帧已下载：%s" % out.name)
                except Exception as e:
                    print("   × 首帧下载失败：%s" % str(e)[:90])
            break
    time.sleep(1)
    s3, d3, t3 = call(BASE + "/worlds/detail?encryptedWorldId=" + urllib.parse.quote(str(wid)), None, "GET")
    try:
        dd3 = (json.loads(t3).get("output") or {}).get("data") or {}
        print("=== ③ 详情核验 ⇒ HTTP %s ｜ name=%s ｜ perspective=%s ｜ refWorldId=%s" % (
            s3, dd3.get("name"), dd3.get("perspective"),
            (str(dd3.get("refWorldId"))[:30] + "…") if dd3.get("refWorldId") else "null"))
        print("   ★ 谱系%s（refWorldId %s v5）" % ("相符" if dd3.get("refWorldId") == REF_V5 else "★不符",
                                                "＝" if dd3.get("refWorldId") == REF_V5 else "≠"))
    except Exception as e:
        print("   详情解析异常：%s" % str(e)[:70])
