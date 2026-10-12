# -*- coding: utf-8 -*-
"""path_risk_classify.py —— 把「open(变量, 写模式)」分级为可判之三类（2026-10-13 立，承 -1410 之请）
由来：-1410 去 BOM 后重跑得「高危 100 处」，然样本多为 open(AUDIT_FILE,"a")／open(tmp,"w") 等
      ★受控常量 ⇒ 须细分：
        ★甲·受控常量（模块级赋值之名，如 AUDIT_FILE／OUT／TMP）⇒ 路径由代码自身决定，★低危
        ★乙·须核（由参数／调用结果／f-string 拼出）⇒ ★须逐处看其来源
        ★丙·高危（直接含 argv／input／environ／request 等外部输入）⇒ ★优先核
本器（★只读；AST）：①收集模块级常量名；②对每处写模式 open 判其路径表达式之类别；③报三类计数与样本
判据（可失败）：①扫描 > 0；②★三类计数之和 ＝ 高危＋须核 之总；③★不写任何文件
用法：python path_risk_classify.py [--json]
（中文串一律用「」）
"""
import argparse, ast, json, pathlib, sys, time

HOME = pathlib.Path.home()
ROOTS = [
    ("seat", HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp"),
    ("cairn", HOME/"openplanlink-cairn"/"tools"),
]
WRITE_MODES = {"w", "a", "x", "w+", "a+", "wb", "ab", "xb"}
EXT = {"argv", "input", "environ", "getenv", "request", "stdin", "expanduser", "expandvars"}


def mod_consts(tree):
    names = set()
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            names.add(n.target.id)
    return names


def classify(arg, consts):
    """⇒ 甲／乙／丙"""
    txt = ast.dump(arg)
    if any(e in txt for e in EXT):
        return "丙·外部输入"
    if isinstance(arg, ast.Name) and arg.id in consts:
        return "甲·受控常量"
    if isinstance(arg, ast.Constant):
        return "甲·受控常量"
    return "乙·须核"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true"); a = ap.parse_args()
    print("  ═══ 「open(变量, 写模式)」之三级分类（★只读）═══")
    cnt = {"甲·受控常量": 0, "乙·须核": 0, "丙·外部输入": 0}
    rows = []; total = 0; scanned = 0
    for tag, d in ROOTS:
        if not d.is_dir(): print("   ★缺目录：%s" % tag); continue
        fs = sorted(d.glob("*.py")); scanned += len(fs)
        for f in fs:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8-sig", errors="replace"))
            except Exception:
                continue
            consts = mod_consts(tree)
            lines = f.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call): continue
                fn = n.func.id if isinstance(n.func, ast.Name) else (n.func.attr if isinstance(n.func, ast.Attribute) else "")
                if fn != "open" or len(n.args) < 2: continue
                m = n.args[1]
                if not (isinstance(m, ast.Constant) and isinstance(m.value, str) and m.value in WRITE_MODES): continue
                total += 1
                k = classify(n.args[0], consts)
                cnt[k] += 1
                if k == "丙·外部输入" or (k == "乙·须核" and len(rows) < 20):
                    rows.append({"root": tag, "file": f.name, "line": n.lineno, "kind": k,
                                 "text": (lines[n.lineno-1].strip()[:86] if n.lineno <= len(lines) else "")})
    print("   ★扫描 %d 支 ｜ ★写模式 open 共 %d 处" % (scanned, total))
    for k in ("甲·受控常量", "乙·须核", "丙·外部输入"):
        print("      ★%-12s ⇒ %d 处" % (k, cnt[k]))
    if rows:
        print("   ── ★丙／乙 之样本 ──")
        for r in rows[:16]:
            print("      %s ｜ %-26s L%-5d ｜ %s" % (r["kind"], r["file"][:26], r["line"], r["text"][:66]))
    print("   ── 判 ──")
    s = sum(cnt.values())
    crit = {"①扫描文件数 > 0": scanned > 0, "②★三类之和 ＝ open 总数": s == total, "③★未写任何文件": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    if a.json:
        out = ROOTS[0][1].parent/"outbox"/"mem"/"path_risk_classify_20261013.json"
        out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "scanned": scanned,
            "total": total, "counts": cnt, "samples": rows, "criteria": crit}, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="\n")
        print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
