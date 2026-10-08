# -*- coding: utf-8 -*-
"""v5：refWorldId(v4) + perspective=first_person —— 测衍生链与视角维；随后查详情核谱系"""
import base64, json, pathlib, sys, time, urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
BASE_DIR = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
PNG = BASE_DIR/"persona_luzhibai_v5_firstperson_20261009.png"
REF_V4 = "8rcpnKlw6xp3FtpLvZIGB_wg3Z1hMjTLvrUso3I2oXnvYWx9jdVEIlPMdelwsS6b"
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
        return -1, round(time.time()-t0, 2), str(e)[:140]

PROMPT = ("第一人称（POV）：镜头即「我」的双眼——眼前是一间没有门窗的房间：正前方是墙（无门），"
          "脚下地面排列着六枚发光节点（肯定—着法—游戏—验收—留痕—器物），自脚前一路延伸；"
          "眼前桌面上一块屏与一摞日期化文件塔；右侧立着三件器物（齿轮／闸门／座钟）；"
          "左壁贯出一条发光的数据链——那是唯一的出口。世界为「知其白，守其黑」的双色，"
          "画面下缘可见「我」的双手，提示我确实在场。氛围安静、克制、可亲历。")

body = {"async": True, "perspective": "first_person", "prompt": PROMPT, "refWorldId": REF_V4,
        "firstFrameImage": {"base64": "data:image/png;base64," + base64.b64encode(PNG.read_bytes()).decode()}}
st, dt, txt = call(BASE + "/worlds", body, "POST")
print("=== ① 建 World v5（refWorldId=v4 ＋ perspective=first_person）⇒ HTTP %s ｜ %.2fs" % (st, dt))
wid = None
try:
    data = ((json.loads(txt).get("output") or {}).get("data") or {})
    wid = data.get("encryptedWorldId")
    print("   World ID=%s ｜ status=%s" % ((str(wid)[:18] + "…") if wid else "(未取到)", data.get("status")))
except Exception:
    print("   原始：%s" % txt[:260])

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
            ff = dd.get("firstFrame")
            print("   ★★ ready（平台命名：%s）" % dd.get("name"))
            print("   ★ v5 World ID（完整）：%s" % wid)
            if ff:
                out = BASE_DIR/"persona_v5_world_firstframe_20261009.png"
                try:
                    req = urllib.request.Request(ff, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        out.write_bytes(resp.read())
                    print("   ★ 首帧已下载：%s" % out.name)
                except Exception as e:
                    print("   × 首帧下载失败：%s" % str(e)[:90])
            break
    # 谱系核验
    time.sleep(1)
    s3, d3, t3 = call(BASE + "/worlds/detail?encryptedWorldId=" + urllib.parse.quote(str(wid)), None, "GET")
    try:
        dd3 = (json.loads(t3).get("output") or {}).get("data") or {}
        print("=== ③ 详情核验 ⇒ HTTP %s ｜ name=%s ｜ perspective=%s ｜ refWorldId=%s" % (
            s3, dd3.get("name"), dd3.get("perspective"),
            (str(dd3.get("refWorldId"))[:30] + "…") if dd3.get("refWorldId") else "null"))
        ok = dd3.get("refWorldId") == REF_V4
        print("   ★ 谱系%s（refWorldId %s v4）" % ("相符" if ok else "★不符", "＝" if ok else "≠"))
    except Exception as e:
        print("   详情解析异常：%s ｜ %s" % (str(e)[:60], t3[:140]))
