# -*- coding: utf-8 -*-
"""302.AI 跨厂商独立复核：请 claude-opus-5 独立判定本席核心判读（零输入下世界是否有结构性演化）
- 依令条：302.AI **不用于国内模型**、**优先最先进高性能模型** ⇒ 用 claude-opus-5
- 投喂：实测数据（六帧差分表、目视一致结论、官档要点）；**不投喂本席结论**（避免诱导）⇒ 先请其独立判读，再比对
零回显：不打印键值
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
base = env.get("AI302_BASE", "https://api.302ai.cn").rstrip("/")
key = env.get("AI302_API_KEY", "")

DATA = """【实测数据（供独立判读；请勿假定任何结论）】
场景：某云平台"世界模型"（可交互三维世界）中建了一个 World（状态 ready），随后在**无任何客户端输入**的条件下开始一次会话（Travel），
服务端自动录制了约 10.77 秒视频（864×480、24fps）。平台文档说明：方向/视角/动作等控制**必须由客户端 SDK 经 RTC DataChannel 发送**；
若 30 秒内无客户端推流，会话自动结束（noStreamAutoEndTimeoutSec=30）。

对该视频抽 6 帧（t=0/2/4/6/8/10 秒，灰度化后逐像素差分）：
帧对 0→2s：平均绝对差(MAD)=2.761（0-255 灰阶），变化像素(>8)占比=4.5527%，最大差=180
帧对 2→4s：MAD=0.780，占比=1.2939%，最大差=107
帧对 4→6s：MAD=0.909，占比=1.0831%，最大差=57
帧对 6→8s：MAD=0.774，占比=1.0884%，最大差=66
帧对 8→10s：MAD=0.572，占比=0.9898%，最大差=60
首→末（0→10s）：MAD=3.918，占比=6.2064%，最大差=180
另：人工目视 t=0、t=2、t=6 三帧，**画面结构完全一致**（同一封闭房间：前方墙、左壁一条由点组成的链、地面六枚节点、右侧一块桌面与三件静物），未见物体增减、位移或场景切换。
"""

Q = DATA + """
请只输出一个 JSON（不要任何其他文字）：
{"q1_structural_change":"YES|NO|UNCERTAIN","q1_reason":"≤40字",
 "q2_emergence_supported":"YES|NO|UNCERTAIN","q2_reason":"≤40字",
 "q3_minimal_probe":"≤60字（在平台侧检测'涌现'的最小可执行方案）",
 "confidence":0.00}
判据请自定，但请在 q1/q2 的判定中体现：①"结构性变化"与"编码/光照级微动"之区分；②若控制信号必须由客户端发送，零输入下"无变化"是否为可预期结果。"""

def call(model, prompt, mx=500, to=180):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx}
    r = urllib.request.Request(base + "/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            ch = (j.get("choices") or [{}])[0]
            return 200, round(time.time()-t0, 2), str((ch.get("message") or {}).get("content") or ""), (j.get("usage") or {})
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), e.read().decode("utf-8", "replace")[:220], {}
    except Exception as e:
        return -1, round(time.time()-t0, 2), str(e)[:150], {}

for model in ["claude-opus-5", "gpt-5"]:
    st, dt, content, usage = call(model, Q)
    print("=== 302.AI · %s ⇒ HTTP %s ｜ %.2fs ｜ tokens=%s" % (model, st, dt, usage.get("total_tokens")))
    print("   %s" % content[:700].replace("\n", " "))
    if st == 200 and content:
        dest = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\cross_vendor_review_%s_20261009_CAIRN.json" % model.replace("/", "_"))
        dest.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "carrier": "302.AI (api.302ai.cn)",
                                    "model": model, "http": st, "sec": dt, "usage": usage,
                                    "note": "★投喂材料为本席实测数据；**未投喂本席结论**（免诱导）", "raw": content},
                                   ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print("   落盘：%s" % dest.name)
    time.sleep(1)
