# -*- coding: utf-8 -*-
"""技能运行器：载入 minimax_skills.json ⇒ 由 MiniMax 执行技能
用法：
  python skill_runner.py list
  python skill_runner.py show <id>
  python skill_runner.py run <id> --input "任务" [--file 路径] [--model MiniMax-M2] [--max 3000]
  python skill_runner.py selftest            # 逐技能自检（定义完整性）
★ 凭据自 .env（utf-8-sig）；值零回显；think 段自动剥离
（引号一律用「」）
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"
SKILLS = pathlib.Path(__file__).with_name("minimax_skills.json")


def key():
    for line in (HOME/".zcode"/"workspace"/"default"/"a2a-bridge"/".env").read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.startswith("MINIMAX_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def load():
    return json.loads(SKILLS.read_text(encoding="utf-8"))


def call(sysmsg, user, model, mx, to=180):
    body = {"model": model, "max_tokens": mx,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}]}
    r = urllib.request.Request("https://api.minimaxi.com/v1/chat/completions",
                               data=json.dumps(body, ensure_ascii=False).encode(), method="POST")
    r.add_header("Authorization", "Bearer " + key()); r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=to) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
        c = (j.get("choices") or [{}])[0]
        txt = (c.get("message") or {}).get("content", "")
        body_ = txt.split("</think>")[-1].strip() if "</think>" in txt else txt
        return {"ok": True, "sec": round(time.time()-t0, 1), "finish": c.get("finish_reason"),
                "usage": j.get("usage"), "text": body_, "raw_len": len(txt)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "text": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"ok": False, "text": str(e)[:200]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("id", nargs="?", default="")
    ap.add_argument("--input", default=""); ap.add_argument("--file", default="")
    ap.add_argument("--model", default="MiniMax-M2"); ap.add_argument("--max", type=int, default=3000)
    a = ap.parse_args()
    P = load()
    S = {s["id"]: s for s in P["skills"]}

    if a.cmd == "list":
        print("  技能包 %s v%s ｜ 共 %d 项" % (P["pack"], P["version"], len(P["skills"])))
        for s in P["skills"]:
            print("   %-14s %s" % (s["id"], s["title"]))
            print("      %s" % s["when"])
        sys.exit(0)

    if a.cmd == "selftest":
        bad = []
        for s in P["skills"]:
            need = ("id", "title", "when", "system", "steps", "commands", "acceptance")
            miss = [k for k in need if not s.get(k)]
            if miss: bad.append((s.get("id", "?"), miss))
        print("  自检：%d 项 ｜ 缺项 %d" % (len(P["skills"]), len(bad)))
        for i, m in bad: print("   ✗ %s 缺 %s" % (i, m))
        if not bad: print("  ✓ 全项齐备（id/title/when/system/steps/commands/acceptance）")
        sys.exit(0 if not bad else 1)

    s = S.get(a.id)
    if not s:
        print("  未知技能：%s（用 list 查看）" % a.id); sys.exit(1)

    if a.cmd == "show":
        print("  # %s（%s）" % (s["title"], s["id"]))
        print("  何时：%s" % s["when"])
        print("  步骤：%s" % " → ".join(s["steps"]))
        print("  命令：")
        for c in s["commands"]: print("    " + c)
        print("  验收：%s" % s["acceptance"])
        print("  系统提示：%s" % s["system"])
        sys.exit(0)

    if a.cmd == "run":
        user = a.input
        if a.file:
            p = pathlib.Path(a.file)
            user = (user + "\n\n" if user else "") + "【文件 %s】\n%s" % (p.name, p.read_text(encoding="utf-8-sig", errors="replace")[:14000])
        if not user:
            print("  须给 --input 或 --file"); sys.exit(1)
        sysmsg = s["system"] + "\n\n【本技能之步骤】" + " → ".join(s["steps"]) + "\n【验收标准】" + s["acceptance"]
        print("  ▶ 技能 %s ｜ 模型 %s ｜ max_tokens %d" % (s["id"], a.model, a.max))
        r = call(sysmsg, user, a.model, a.max)
        if not r["ok"]:
            print("  ✗ 调用失败：%s" % r["text"]); sys.exit(2)
        print("  HTTP 200 ｜ %.1f s ｜ finish=%s ｜ usage=%s ｜ 正文 %d 字" % (r["sec"], r["finish"], r["usage"], len(r["text"])))
        print("  ─── 产出 ───")
        print(r["text"][:4000])
        sys.exit(0)

    print("未知命令"); sys.exit(1)
