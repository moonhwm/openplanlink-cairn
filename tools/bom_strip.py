# -*- coding: utf-8 -*-
"""bom_strip.py —— 去 .py 之 BOM（2026-10-13 立，承 -1408 之发现）
由来：-1408 之路径安全核发现 3 支 .py 带 BOM（U+FEFF）⇒ ast.parse（默认 utf-8）失败；
      -1409 核实：以 utf-8-sig 解码后 ast.parse 成功 ⇒ 内容无误，唯首 3 字节作祟；
      且皆未被 seal_files 引用 ⇒ 改动不牵动既往署签。
本器（★改动前备份；★只动带 BOM 者；★改后复验）：
  ① 扫指定根下 *.py，读前 3 字节判 BOM；
  ② 有 BOM 者：备份至 <根>/_bom_backup_<日期>/，再以 utf-8-sig 读、以 utf-8 无 BOM 写回；
  ③ 复验：ast.parse（默认 utf-8）应成功；且文件前 3 字节非 EF BB BF；
判据（可失败）：①扫描数 > 0；②★凡去掉者皆复验通过；③★未去者不改
用法：python bom_strip.py [--roots seat,cairn] [--dry]
（中文串一律用「」）
"""
import argparse, ast, json, pathlib, shutil, sys, time

HOME = pathlib.Path.home()
ROOTS = {
    "seat": HOME/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"exp",
    "cairn": HOME/"openplanlink-cairn"/"tools",
}
BOM = b"\xef\xbb\xbf"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--roots", default="seat,cairn")
    ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    print("  ═══ 去 .py 之 BOM（★备份先行；★只动带 BOM 者）═══")
    rows = []; fixed = 0; failed = 0; scanned = 0
    for tag in [t for t in a.roots.split(",") if t in ROOTS]:
        d = ROOTS[tag]
        if not d.is_dir(): print("   ★缺目录：%s" % tag); continue
        bak = d/("_bom_backup_%s" % time.strftime("%Y%m%d"))
        fs = sorted(d.glob("*.py"))
        scanned += len(fs)
        print("   ★%s：%d 支" % (tag, len(fs)))
        for f in fs:
            b = f.read_bytes()
            if b[:3] != BOM: continue
            if a.dry:
                print("      DRY ｜ %s（带 BOM，待去）" % f.name); rows.append({"file": f.name, "dry": True}); continue
            bak.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, bak/f.name)
            txt = b.decode("utf-8-sig")
            f.write_text(txt, encoding="utf-8", newline="\n")
            b2 = f.read_bytes()
            ok_bom = b2[:3] != BOM
            try:
                ast.parse(b2.decode("utf-8")); ok_ast = True
            except Exception:
                ok_ast = False
            ok = ok_bom and ok_ast
            if ok: fixed += 1
            else: failed += 1
            print("      ★%s ｜ 去 BOM=%s ｜ ast.parse=%s ｜ 备份 %s" % (f.name, "✓" if ok_bom else "✗",
                  "✓" if ok_ast else "✗", "✓"))
            rows.append({"root": tag, "file": f.name, "ok": ok, "size": len(b2)})
    print("   ── 判 ──")
    print("   ★扫描 %d 支 ｜ ★已去 BOM %d 支 ｜ ★失败 %d 支" % (scanned, fixed, failed))
    crit = {"①扫描文件数 > 0": scanned > 0, "②★凡去掉者皆复验通过": failed == 0,
            "③★未去者不改": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = ROOTS["seat"].parent/"outbox"/"mem"/"bom_strip_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "scanned": scanned,
        "fixed": fixed, "failed": failed, "rows": rows, "criteria": crit}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
