# -*- coding: utf-8 -*-
"""quota-guard-ops：额度守卫（应纲要 10-11 更新新增之自建技能）
① 查余额（business.aliyuncs.com）② 探关键通道（百炼专属域四模型／MiniMax／302.AI）
③ 分级告警（A<0.5 元；B<5 元；C<20 元）④ 落 JSON ＋ 台账式一行
★ 凭据自 .env 与 CSV 自读；零回显
（引号一律用「」）
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from aliyun_api import call as acall  # noqa: E402

HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
E = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); E[k.strip()] = v.strip().strip('"').strip("'")
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "skill": "quota-guard-ops", "v": 1}

# ① 余额
try:
    p = (HOME/"OneDrive"/"桌面"/"AccessKey 阿里云百炼主账户.csv").read_text(encoding="utf-8-sig").splitlines()[1].split(",")
    st, tx = acall(p[0].strip(), p[1].strip(), "business.aliyuncs.com", {"Action": "QueryAccountBalance", "Version": "2017-12-14"})
    d = (json.loads(tx).get("Data") or {})
    R["balance"] = {"http": st, "available": d.get("AvailableAmount"), "cash": d.get("AvailableCashAmount"),
                    "credit": d.get("CreditAmount"), "currency": d.get("Currency")}
except Exception as e:
    R["balance"] = {"error": str(e)[:100]}
b = R["balance"].get("available")
try: bf = float(b) if b is not None else None
except Exception: bf = None
if bf is None: grade = "未知"
elif bf < 0.5: grade = "A-临界（<0.5 元）"
elif bf < 5: grade = "B-告警（<5 元）"
elif bf < 20: grade = "C-偏低（<20 元）"
else: grade = "D-正常（≥20 元）"
R["balance_grade"] = grade
print("  ① 余额：%s %s ⇒ ★分级 %s" % (b, R["balance"].get("currency"), grade))

# ② 关键通道
K = E.get("DASHSCOPE_API_KEY", ""); MM = E.get("MINIMAX_API_KEY", "")
WS = "https://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com"
def post(url, body, key, to=45):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp: return resp.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return -1
probe = {}
for m in ("qwen-plus", "qwen3.7-plus", "qwen3.8-omni-flash", "decision-model-preview", "qwen3.8-max"):
    probe["dashscope:" + m] = post(WS + "/compatible-mode/v1/chat/completions",
                                   {"model": m, "messages": [{"role": "user", "content": "回一字"}], "max_tokens": 8}, K)
probe["dashscope:embedding"] = post(WS + "/compatible-mode/v1/embeddings", {"model": "text-embedding-v4", "input": "额度守卫"}, K)
probe["minimax:M2"] = post("https://api.minimaxi.com/v1/chat/completions",
                           {"model": "MiniMax-M2", "messages": [{"role": "user", "content": "回一字"}], "max_tokens": 300}, MM)
for app, tag in (("adventure", "world:adventure"), ("directing", "world:directing"), ("acting", "world:acting")):
    url = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-%s/openapi/v1/worlds" % app
    r = urllib.request.Request(url, data=json.dumps({"async": True, "prompt": "试", "firstFrameImage": {"base64": "data:image/jpeg;base64,/9j/"}}).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            code = ((j.get("output") or {}).get("code"))
            probe[tag] = 200 if code == 0 else 200   # HTTP 200 ⇒ 可达（业务码另记）
            probe[tag + ":code"] = code
    except urllib.error.HTTPError as e:
        probe[tag] = e.code
    except Exception:
        probe[tag] = -1
R["probe"] = probe
print("  ② 关键通道：")
for k, v in probe.items():
    mark = {200: "✓", 401: "✗鉴权", 403: "✗资格", 429: "✗额度"}.get(v, str(v))
    print("     %-32s ⇒ %-5s %s" % (k, v, mark))

# ③ 告警
alerts = []
if grade.startswith("A"): alerts.append("★余额临界：任何按量付费调用都可能被拒")
if probe.get("dashscope:decision-model-preview") == 429: alerts.append("decision-model-preview 仍受额度墙")
if probe.get("world:adventure") in (403,): alerts.append("世界探索不可达")
if probe.get("world:directing") == 403: alerts.append("实时导演不可达（须资格）")
if probe.get("world:acting") == 403: alerts.append("角色演绎不可达（须资格）")
R["alerts"] = alerts
print("  ③ 告警 %d 条：" % len(alerts))
for a in alerts: print("     · " + a)

out = SEAT/"outbox"/"mem"/("quota_guard_%s.json" % time.strftime("%Y%m%d"))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
(EX/out.name).write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
line = "%s ｜ 余额 %s %s（%s）｜ 告警 %d 条：%s" % (R["ts"], b, R["balance"].get("currency"), grade, len(alerts), "；".join(alerts) or "无")
(SEAT/"outbox"/"mem"/"quota_guard.log").open("a", encoding="utf-8").write(line + "\n")
print("\n  ④ 落盘：%s ｜ 台账行已追加" % out.name)
print("     " + line)
