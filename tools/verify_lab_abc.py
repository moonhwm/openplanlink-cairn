#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""verify_lab_abc.py —— 用【独立验签器】对实验目录那份真 attest.json 做 A/B/C 三组。 v1.0.0

★ 本轮立的判读规则：**只认 `OK` 为通过；`BAD`=未通过；`ERR`=器具故障（不得读作任何一方）。**
用法: verify_lab_abc.py
"""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAB = ROOT / "exp" / "attest_lab"
V = ROOT / "exp" / "_verify_attest.mjs"
ENV = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
       "PATHEXT": os.environ.get("PATHEXT", ".EXE;.CMD;.BAT")}


def vf(o: dict, tag: str) -> str:
    p = LAB / (tag + ".json")
    p.write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(V), str(p)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=120)
    out = (r.stdout or "").strip()
    p.unlink(missing_ok=True)
    return out if out else ("（空）stderr=" + (r.stderr or "")[:70])


def main() -> int:
    src = LAB / "attest.json"
    if not src.is_file():
        print("[ERR] 实验目录无 attest.json：%s" % src); return 2
    a = json.loads(src.read_text(encoding="utf-8"))
    print("═══ A/B/C 三组（独立验签器）═══")
    print("  file_count=%s ｜ files 条数=%d ｜ merkle_root=%s…"
          % (a["file_count"], len(a["files"]), a["merkle_root"][:24]))
    ra = vf(a, "t_A")
    print("  A 原样                 ⇒ %s（期望 OK）" % ra)

    b = json.loads(json.dumps(a))
    ks = sorted(b["files"])
    b["files"][ks[0]], b["files"][ks[1]] = b["files"][ks[1]], b["files"][ks[0]]
    rb = vf(b, "t_B")
    print("  B ★改 files 两条哈希   ⇒ %s（互换 %s ⇄ %s）" % (rb, ks[0], ks[1]))

    c = json.loads(json.dumps(a))
    c["merkle_root"] = "0" * len(c["merkle_root"])
    rc = vf(c, "t_C")
    print("  C 改 merkle_root       ⇒ %s" % rc)

    print()
    print("  ── 判读（只认 OK 为通过）──")
    print("   A 通过              = %s" % (ra == "OK"))
    print("   B 改 files 仍通过    = %s  ⇒ %s" % (rb == "OK", "★files 表不在签名覆盖内" if rb == "OK" else "（未通过或器具故障：" + rb + "）"))
    print("   C 改 root 未通过     = %s  ⇒ %s" % (rc == "BAD", "验签确实在看 root" if rc == "BAD" else "（★非 BAD，读数不可用：" + rc + "）"))
    print()
    print("  ★ 本器把「空输出」与「非 OK」分开处理 ⇒ 不会再出现轮87 那次'在失败上报成功'。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
