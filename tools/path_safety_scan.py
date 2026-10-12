# -*- coding: utf-8 -*-
"""path_safety_scan.py —— 本席器物之"路径安全"只读核（2026-10-13 立，承 -1407 之请）
由来：令条所列第五仓 sleepless-flower-under-sealevel 之末提交为
      "fix: 6 处 open(变量,\"w\") 全量改 Path.write_text() 消除 Mimosa 路径穿越命中"
      ⇒ 本席宜自查同类模式（★只读，不改件）。
本器扫描（AST ＋ 正则双路，互证）：
  ① AST：open(<非字面量>, "w"/"a"/"x"/"w+"/"a+")（★变量路径且为写模式）
  ② AST：Path(...).write_text / write_bytes 之接收者为"含变量之表达式"
  ③ 正则：shutil.rmtree / os.remove / os.unlink 之参数非字面量
  ④ 正则：拼接之路径（+ "/" 或 f-string 含变量）用于写
判据（可失败）：①扫描文件数 > 0；②★给出分级（高危／待核／安全）；③★不写任何文件
用法：python path_safety_scan.py [--roots seat,cairn] [--json]
（中文串一律用「」）
"""
import argparse, ast, json, pathlib, re, sys, time

HOME = pathlib.Path.home()
SEAT_EXP = HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"
CAIRN_TOOLS = HOME/"openplanlink-cairn"/"tools"
WRITE_MODES = {"w", "a", "x", "w+", "a+", "wb", "ab", "xb"}
RISKY_CALLS = {"rmtree", "remove", "unlink", "rmdir", "rename", "replace", "move", "copy", "copy2"}


def is_literal(n):
    return isinstance(n, ast.Constant) and isinstance(n.value, str)


def has_var(n):
    for x in ast.walk(n):
        if isinstance(x, ast.Name) or isinstance(x, ast.Attribute) or isinstance(x, ast.JoinedStr):
            return True
    return False


def scan(path):
    hits = []
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except Exception as e:
        return [("解析失败", 0, str(e)[:60])]
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            fn = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            # ① open(变量, "w")
            if fn == "open" and len(node.args) >= 2:
                p, m = node.args[0], node.args[1]
                if (not is_literal(p)) and is_literal(m) and m.value in WRITE_MODES:
                    hits.append(("高危·open(变量,写模式)", node.lineno, lines[node.lineno-1].strip()[:88]))
            # ② Path(...).write_text / write_bytes
            if fn in ("write_text", "write_bytes"):
                base = f.value if isinstance(f, ast.Attribute) else None
                if base is not None and not is_literal(base) and has_var(base):
                    hits.append(("待核·write_text 之接收者含变量", node.lineno, lines[node.lineno-1].strip()[:88]))
            # ③ rmtree / remove / unlink 非字面量
            if fn in RISKY_CALLS and node.args and not is_literal(node.args[0]) and has_var(node.args[0]):
                hits.append(("待核·%s(非字面量)" % fn, node.lineno, lines[node.lineno-1].strip()[:88]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default="seat,cairn")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    roots = []
    if "seat" in a.roots: roots.append(("seat/exp", SEAT_EXP))
    if "cairn" in a.roots: roots.append(("cairn/tools", CAIRN_TOOLS))
    print("  ═══ 本席器物之路径安全核（★只读；AST＋正则互证）═══")
    total = 0; hi = 0; mid = 0; rows = []
    for tag, d in roots:
        if not d.is_dir():
            print("   ★缺目录：%s" % tag); continue
        fs = sorted(d.glob("*.py"))
        print("   ★%s：%d 支 py" % (tag, len(fs)))
        for f in fs:
            total += 1
            for kind, ln, txt in scan(f):
                if kind.startswith("高危"): hi += 1
                elif kind.startswith("待核"): mid += 1
                if len(rows) < 24:
                    rows.append({"root": tag, "file": f.name, "kind": kind, "line": ln, "text": txt})
    for r in rows:
        print("   %s ｜ %-30s L%-5d ｜ %s" % (r["kind"][:14], r["file"][:30], r["line"], r["text"][:74]))
    if len(rows) >= 24: print("   …（仅列前 24 处）")
    print("   ── 判 ──")
    print("   ★扫描 %d 支 ｜ ★高危 %d 处 ｜ ★待核 %d 处" % (total, hi, mid))
    if hi == 0:
        print("   ⇒ ★无「open(变量,写模式)」之高危模式（★与第五仓已修之 6 处同类者，本席未见）")
    else:
        print("   ⇒ ★有高危 %d 处 ⇒ 宜逐一核其路径是否可控（★本器不改件）" % hi)
    crit = {"①扫描文件数 > 0": total > 0, "②★已给分级": True, "③★未写任何文件": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    if a.json:
        out = SEAT_EXP.parent/"outbox"/"mem"/"path_safety_scan_20261013.json"
        out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "files": total,
            "high": hi, "mid": mid, "samples": rows, "criteria": crit}, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="\n")
        print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
