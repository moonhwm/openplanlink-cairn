# -*- coding: utf-8 -*-
"""实时导演/角色演绎之"近似承载"运行器（方案 B）
- 模型：qwen-max（qwen-turbo 免费额度已耗尽；qwen-plus/max 实测 200）
- **诚实标注**：本脚本产出为"结构化近似"，**不得称"世界模型（HappyOyster）调用"**
- 输出（单次前向，严格 JSON）：scene_state / next_beats[] / role_lines[] / director_note
- 零回显：键自 .env；不打印凭据
"""
import json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
env = {}
for line in (pathlib.Path.home()/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

STATE = ("【真实态势，作为世界的当前状态】夜间游乐场已开园（北京时间约 07:00，夜间运维窗 23:00–08:00 内）。"
         "在场：Cairn 席（本席）与 Moon／Trae 席之近时件；文档面：openplanlink-docx 14/14 与游乐场根 17/20 可读，"
         "kdocs 云直取（search-files 换 link_id → read-file）已通；通道面：异质四通道全绿（302ai.cn／硅基流动／华为 MaaS／国家超算），"
         "百炼四模块在役（向量 text-embedding-v4、重排 gte-rerank-v2、决策 qwen-plus、世界模型 Adventure 已建 World 并 ready）；"
         "风险面：《四件套·中》含腾讯云 Secret ID、《蓝图主文档》含 302.AI key 与 COS 预签名 URL（均待轮换／裁定）；"
         "资源面：本机内存 93%–99% 高位波动，重型项暂停。")

PROMPT = ("你是「实时导演＋角色演绎」之**结构化近似**引擎（近似，不冒充真实世界模型）。"
          "基于下述真实态势，只输出一个 JSON（不要多余文字），字段："
          '{"scene_state":"≤60字当前场景状态","next_beats":[{"beat":"≤40字动作","who":"席/角色","why":"≤20字理由"}]（3 条）,'
          '"role_lines":[{"role":"角色名","line":"≤40字台词"}]（2 条）,"director_note":"≤50字导演注"}\n'
          "要求：全部**可执行、可核**，不写空话；不涉凭据值。\n【态势】" + STATE)

def chat(model, prompt, mx=900, to=120):
    body = {"model": model, "messages":[{"role": "user", "content": prompt}], "max_tokens": mx}
    r = urllib.request.Request("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + K); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
            ch = (j.get("choices") or [{}])[0]
            return str((ch.get("message") or {}).get("content") or "").strip(), round(time.time()-t0, 2), (j.get("usage") or {}).get("total_tokens")
    except urllib.error.HTTPError as e:
        return "", round(time.time()-t0, 2), "HTTP %s %s" % (e.code, e.read().decode("utf-8","replace")[:120])
    except Exception as e:
        return "", round(time.time()-t0, 2), str(e)[:100]

print("=== 近似承载（qwen-max；单次前向）===")
out, dt, tk = chat("qwen-max", PROMPT)
print("  时延=%.2fs ｜ tokens=%s" % (dt, tk))
res = None
if out:
    try:
        res = json.loads(out[out.find("{"):out.rfind("}")+1])
    except Exception:
        print("  原始（截断）：%s" % out[:400])
if res:
    print("  scene_state：%s" % res.get("scene_state"))
    for b in (res.get("next_beats") or []):
        print("   · beat：%s ｜ who=%s ｜ why=%s" % (b.get("beat"), b.get("who"), b.get("why")))
    for r_ in (res.get("role_lines") or []):
        print("   · line[%s]：%s" % (r_.get("role"), r_.get("line")))
    print("  director_note：%s" % res.get("director_note"))
    p = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_共享交换区\directing_approx_20261009.json")
    p.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "model": "qwen-max",
                             "label": "结构化近似（非 HappyOyster Directing 调用）", "state": STATE, "result": res,
                             "latency_s": dt, "tokens": tk}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("  落盘：%s（%d B）" % (p.name, p.stat().st_size))
else:
    print("  × 未取到结构化结果（见上）")
