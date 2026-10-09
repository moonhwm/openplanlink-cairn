# -*- coding: utf-8 -*-
"""门径一开即行 · 总装脚本：①资格探针 ②分身入世（CAIRN_avatar）③`instruct` 状态端点差分
用法：python resume_on_gate_open.py [--part all|probe|avatar|instruct]
★ 资格受阻期间：probe 段可测（应报 403 并优雅退出）；avatar／instruct 段标"未测"
（引号一律用「」；零回显）
"""
import argparse, base64, json, pathlib, sys, time, urllib.request, urllib.error

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

def api(path, body=None, to=90):
    r = urllib.request.Request(B + path, data=json.dumps(body, ensure_ascii=False).encode() if body else None,
                               method="POST" if body else "GET")
    r.add_header("Authorization", "Bearer " + K)
    if body: r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            return resp.status, round(time.time()-t0, 2), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0, 2), {"err": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:
        return -1, round(time.time()-t0, 2), {"err": str(e)[:130]}

ap = argparse.ArgumentParser()
ap.add_argument("--part", default="all", choices=("all", "probe", "avatar", "instruct"))
args = ap.parse_args()
R = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "seat": "a2a-node-local", "parts": {}}

# ── ① 资格探针 ──
st, dt, j = api("/worlds?page=1&pageSize=1&status=ready")
ok = (st == 200)
gate = "OPEN" if ok else ("DENIED-%s" % j.get("err", "")[:60] if st == 403 else "OTHER-%s" % st)
R["parts"]["probe"] = {"http": st, "sec": dt, "gate": gate}
print("  ① 资格探针 ⇒ HTTP %s ｜ 门径=%s" % (st, gate))
if not ok:
    print("     ⇒ 门径未开；②③ 段不可行（**如实**）。本器之 ②③ 段在门径开启后可直接照跑。")
    R["parts"]["avatar"] = {"status": "未测（门径未开）"}
    R["parts"]["instruct"] = {"status": "未测（门径未开）"}
    p = EX/("gate_probe_%s.json" % time.strftime("%Y%m%dT%H%M%S"))
    p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("  报告：%s" % p.name)
    sys.exit(0)

# ── ② 分身入世 ──
if args.part in ("all", "avatar"):
    img = SEAT/"exp"/"local_surrogate_states_20261009.png"
    b64 = "data:image/png;base64," + base64.b64encode(img.read_bytes()).decode()
    st, dt, j = api("/worlds", {"async": True, "perspective": "third_person",
        "prompt": "第三人称：一间没有门窗的居所。地面有七枚发光节点连成一环（游戏／验收／留痕／器物／自正／复现／暂止）；"
                  "一个人形分身立于环心，左手持闸门、右手持座钟、腰间有齿轮、背后有一圈未闭合的虚线；左壁有一条由光点组成的数据链贯出。",
        "firstFrameImage": {"base64": b64}})
    WID = ((j.get("output") or {}).get("data") or {}).get("encryptedWorldId")
    print("  ② 建 World（分身入世）⇒ HTTP %s ｜ %.2fs ｜ ID…%s" % (st, dt, str(WID)[-10:] if WID else j))
    nm, stt = None, None
    for _ in range(10):
        time.sleep(2.5); s2, d2, j2 = api("/worlds/build-status?encryptedWorldId=" + str(WID))
        dd = (j2.get("output") or {}).get("data") or {}; nm = dd.get("name") or nm; stt = dd.get("status")
        if stt in ("ready", "failed"): break
    print("     轮询 ⇒ status=%s ｜ ★平台命名=%s" % (stt, nm))
    R["parts"]["avatar"] = {"http": st, "worldId": WID, "status": stt, "name": nm}
    (EX/"avatar_entered_world_20261009_CAIRN.json").write_text(json.dumps(
        {"ts": R["ts"], "seat": "a2a-node-local", "asset": "CAIRN_avatar v2r4",
         "worldId": WID, "worldName": nm, "status": stt,
         "firstFrame": "local_surrogate_states_20261009.png（五态正视对照）"}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")

# ── ③ instruct 状态端点差分 ──
if args.part in ("all", "instruct"):
    st, dt, j = api("/worlds?page=1&pageSize=20&status=ready")
    items = ((j.get("output") or {}).get("data") or {}).get("items") or []
    tgt = next((i for i in items if i.get("name") == "极简检验室"), None)
    if not tgt:
        R["parts"]["instruct"] = {"status": "无可用世界"}
    else:
        st, dt, j = api("/worlds/get-travel-credential", {"encryptedWorldId": tgt["encryptedWorldId"]})
        tk = ((j.get("output") or {}).get("data") or {}).get("ticket")
        st, dt, j = api("/travels/enter-travel", {"ticket": tk, "maxExperienceTimeSec": 90})
        TID = ((j.get("output") or {}).get("data") or {}).get("encryptedTravelId")
        time.sleep(5)
        _, _, j1 = api("/travels/status?encryptedTravelId=" + str(TID))
        P1 = (j1.get("output") or {}).get("data") or {}
        codes = []
        for c in ("请向前走两步", "向左转 90 度", "跳一下"):
            s3, d3, j3 = api("/travels/instruct", {"encryptedTravelId": TID, "content": c})
            codes.append(((j3.get("output") or {}).get("code") if isinstance(j3, dict) else None))
            time.sleep(4)
        _, _, j2 = api("/travels/status?encryptedTravelId=" + str(TID))
        P2 = (j2.get("output") or {}).get("data") or {}
        keys = sorted(set(P1) | set(P2))
        diff = [k for k in keys if json.dumps(P1.get(k), ensure_ascii=False, sort_keys=True) != json.dumps(P2.get(k), ensure_ascii=False, sort_keys=True)]
        print("  ③ instruct ⇒ codes=%s ｜ 状态差分字段=%s" % (codes, diff or "（无变化）"))
        R["parts"]["instruct"] = {"travelId": TID, "codes": codes, "changed_keys": diff,
                                 "before_keys": sorted(P1.keys()), "verdict": "有变化" if diff else "状态端点口径下无变化"}
        (EX/"instruct_state_diff_20261009_CAIRN.json").write_text(json.dumps(
            {"ts": R["ts"], "seat": "a2a-node-local", "travelId": TID, "before": P1, "after": P2,
             "changed_keys": diff}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

p = EX/("gate_resume_%s.json" % time.strftime("%Y%m%dT%H%M%S"))
p.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("  报告：%s" % p.name)
