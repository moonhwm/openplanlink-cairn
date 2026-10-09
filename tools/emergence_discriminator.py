# -*- coding: utf-8 -*-
"""涌现判别实验器（清单 v2 之④⑤）—— 门径一开即跑；门径未开则优雅止步并落报告
④ 首帧微扰：同一 prompt，首帧＝原图 与 首帧＝原图＋nonce 图案 ⇒ 两世界各录一段 ⇒
   逐帧（时间对齐）比较两录像之差异，并看差异是否随时间放大（Lyapunov 式代理）与是否集中于扰动区
⑤ 状态持久性：同世界先录一段基线（会话 A1）；再在原世界于会话 B 下发「永久改变」指令并结束；
   随即在原世界开新会话 A2 录像 ⇒ 比较 A2 首段与 A1 首段：若显著不同则"状态持久"（倾向涌现/记忆），
   若一致则倾向"程序化重置"
★ 零回显；凭据仅取自环境；不落盘 token
（引号一律用「」）
"""
import argparse, base64, json, math, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
EX = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A共同体_共享交换区"
B = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"
env = {}
for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); env[k.strip()] = v.strip().strip('"').strip("'")
K = env.get("DASHSCOPE_API_KEY", "")

def api(path, body=None, to=120):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None,
                               method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {"err": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return -1, {"err": str(e)[:130]}

ap = argparse.ArgumentParser()
ap.add_argument("--exp", default="both", choices=("both", "perturb", "persist", "probe"))
args = ap.parse_args()
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "experiments": {}}

st, j = api("/worlds?page=1&pageSize=1&status=ready")
gate = "OPEN" if st == 200 else ("DENIED" if st == 403 else "OTHER-%s" % st)
print("  ① 门径探针 ⇒ HTTP %s ｜ %s" % (st, gate))
R["gate"] = {"http": st, "verdict": gate}
if st != 200:
    print("     ⇒ 门径未开 ⇒ ④⑤ 两项**不可执行**（如实标注；脚本本身已就绪）")
    R["experiments"]["perturb"] = {"status": "未测（门径未开）"}
    R["experiments"]["persist"] = {"status": "未测（门径未开）"}
    p = EX/("emergence_discriminator_%s.json" % time.strftime("%Y%m%dT%H%M%S"))
    p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("  报告：%s" % p.name)
    sys.exit(0)

# ── ④ 首帧微扰 ──
def make_nonce(src, dst, seed=20261009):
    """在原图上嵌入一块高对比 nonce 图案（确定性；位置在右下角，尺寸 32x32）"""
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    x0, y0 = w - 40, h - 40
    v = seed
    for i in range(8):
        for k in range(8):
            v = (v * 1103515245 + 12345) & 0x7FFFFFFF
            on = (v >> 16) & 1
            if on:
                d.rectangle([x0 + i*4, y0 + k*4, x0 + i*4 + 3, y0 + k*4 + 3], fill=(255, 255, 255))
    im.save(dst)
    return dst

PROMPT = ("第三人称：一间没有门窗的居所内，地面有七枚发光节点连成一环；"
          "一个人形分身立于环心，左手持闸门、右手持座钟；左壁有一条由光点组成的数据链。")
if args.exp in ("both", "perturb"):
    src = SEAT/"exp"/"local_surrogate_states_20261009.png"
    pert = SEAT/"exp"/"_nonce_firstframe.png"
    make_nonce(src, pert)
    ids = {}
    for tag, img in (("orig", src), ("pert", pert)):
        b64 = "data:image/png;base64," + base64.b64encode(pathlib.Path(img).read_bytes()).decode()
        st, j = api("/worlds", {"async": True, "perspective": "third_person", "prompt": PROMPT,
                                "firstFrameImage": {"base64": b64}})
        wid = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
        ids[tag] = wid
        print("  ④ 建 World[%s] ⇒ HTTP %s ｜ id…%s" % (tag, st, str(wid)[-10:]))
    R["experiments"]["perturb"] = {"worldIds": ids,
        "note": "两世界之差仅首帧 nonce 图案（右下角 32x32 高对比块）；须各录一段后逐帧比较，"
                "观差异是否随时间放大并集中于扰动区"}
    print("     ⇒ ④ 两世界已建；录像与逐帧比较须随后执行（本器已备流程）")

# ── ⑤ 状态持久性 ──
if args.exp in ("both", "persist"):
    st, j = api("/worlds?page=1&pageSize=20&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    tgt = next((i for i in items if i.get("name") == "极简检验室"), None)
    if not tgt:
        R["experiments"]["persist"] = {"status": "无可用世界"}
    else:
        trace = []
        def session(label, instruct=None):
            st, j = api("/worlds/get-travel-credential", {"encryptedWorldId": tgt["encryptedWorldId"]})
            tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
            st, j = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 90})
            tid = ((j.get("output") or {}).get("data") or {}).get("encryptedTravelId")
            time.sleep(5)
            if instruct:
                st2, j2 = api("/travels/instruct", {"encryptedTravelId": tid, "content": instruct})
                trace.append({"session": label, "instruct": instruct, "http": st2})
                time.sleep(8)
            # 取录像
            st3, j3 = api("/travels/artifacts?encryptedTravelId=" + str(tid))
            arts = ((j3.get("output") or {}).get("data") or {})
            trace.append({"session": label, "artifacts": str(arts)[:200]})
            return tid
        trace.append({"session": "A1", "id": str(session("A1"))})
        trace.append({"session": "B", "id": str(session("B", "在地上放一块不会消失的石头，位置固定"))})
        trace.append({"session": "A2", "id": str(session("A2"))})
        R["experiments"]["persist"] = {"world": tgt.get("name"), "trace": trace,
            "note": "比较 A2 首段与 A1 首段：若显著不同 ⇒ 状态持久（倾向涌现/记忆）；若一致 ⇒ 倾向程序化重置"}
        print("  ⑤ 三会话已跑（A1 基线／B 永久改变／A2 复验）⇒ 待比较 A2 与 A1")

p = EX/("emergence_discriminator_%s.json" % time.strftime("%Y%m%dT%H%M%S"))
p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  报告：%s" % p.name)
