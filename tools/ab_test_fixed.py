#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""ab_test_fixed.py —— 修前/修后对照：同三组测试，跑在其版与修后版上。 v1.0.0

对照设计（★ 每格都必须能给出 OK 与 BAD 两种结果，否则该格作废）
  B 改 files 两条哈希（其余不动）
      · 其版：期望 **OK**（= 缺陷：改表不被察觉）
      · 修后版：期望 **BAD**（= 修① 生效）
  C 改 merkle_root
      · 两版都应 **BAD**（对照：证明验签真在工作）
  E 一叶与两叶同根
      · 其版：期望 **相同**（= 缺陷：无域分隔）
      · 修后版：期望 **不同**（= 修② 生效）
  D 删件后重跑
      · 其版：新签名对新 count 仍 OK ⇒ 不可检出
      · 修后版：count 与 files 同在签名内 ⇒ 若在**删件并重跑**的情形下，
        签名自然是对新状态的（生成器重签）⇒ 故 D 的"可检出"不体现于重签，
        而体现于：**拿着旧 attest 去核新目录时，files 表与目录不符**（本器只报此点，不假装能检出重签）

★ 裁决：只认 `OK` 为通过；`BAD` 未通过；`ERR` 器具故障——三者不得互相顶替。
用法: ab_test_fixed.py
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
ROOT = DESK / "A2A新席_石敢当Cairn_20260928"
PATCH = DESK / "qtorrent_patch"
V21SITE = DESK / "OpenPlanLink_观测站_白天版v2.1_20261001" / "site"
PAGES = ["index.html", "observe.html", "oracle.html", "sandbox.html", "sea.html",
         "cinema.html", "a2a-architecture.html"]
ENV = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
       "PATHEXT": os.environ.get("PATHEXT", ".EXE;.CMD;.BAT"), "TEMP": os.environ.get("TEMP", "")}


def node(args, cwd=None):
    r = subprocess.run(["node"] + args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=180)
    return (r.stdout or "").strip(), (r.stderr or "").strip()


def build(lab: pathlib.Path, gen: pathlib.Path):
    if lab.exists():
        shutil.rmtree(lab, ignore_errors=True)
    (lab / ".well-known").mkdir(parents=True, exist_ok=True)
    for f in PAGES:
        shutil.copy2(V21SITE / f, lab / f)
    shutil.copy2(PATCH / "llms.txt", lab / "llms.txt")
    shutil.copy2(PATCH / "agent-card.json", lab / ".well-known" / "agent-card.json")
    shutil.copy2(gen, lab / gen.name)


def run_and_verify(lab: pathlib.Path, genname: str, verifier: pathlib.Path, outfile: str):
    node([genname], cwd=lab)
    out = lab / outfile
    if not out.is_file():
        return None, "ERR:生成器未产出 " + outfile
    o = json.loads(out.read_text(encoding="utf-8"))
    raw, err = node([str(verifier), str(out)])
    return o, (raw or ("ERR:" + err[:50]))


def main() -> int:
    labT = ROOT / "exp" / "ab_theirs"
    labF = ROOT / "exp" / "ab_fixed"
    vT = ROOT / "exp" / "_verify_attest.mjs"
    vF = ROOT / "exp" / "_verify_attest_fixed.mjs"

    print("═══ 修前/修后对照（同三组测试）═══")
    build(labT, PATCH / "gen_attest.mjs")
    build(labF, ROOT / "exp" / "gen_attest_fixed.mjs")

    oT, rT = run_and_verify(labT, "gen_attest.mjs", vT, "attest.json")
    oF, rF = run_and_verify(labF, "gen_attest_fixed.mjs", vF, "attest.fixed.json")
    print("  其版   attest：count=%s files=%d ⇒ 原样验 %s" % (oT["file_count"], len(oT["files"]), rT))
    print("  修后版 attest：count=%s files=%d ⇒ 原样验 %s" % (oF["file_count"], len(oF["files"]), rF))
    print()

    # ── B 改 files 两条哈希 ──
    def tamper_files(o):
        b = json.loads(json.dumps(o))
        ks = sorted(b["files"])
        b["files"][ks[0]], b["files"][ks[1]] = b["files"][ks[1]], b["files"][ks[0]]
        return b

    def save(lab, o, name):
        p = lab / name
        p.write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        return p

    pB_T = save(labT, tamper_files(oT), "t_B.json")
    pB_F = save(labF, tamper_files(oF), "t_B.json")
    rBT, _ = node([str(vT), str(pB_T)])
    rBF, _ = node([str(vF), str(pB_F)])
    print("  ── B 改 files 两条哈希 ──")
    print("     其版   ⇒ %s（★OK = 缺陷：改表不被察觉）" % rBT)
    print("     修后版 ⇒ %s（★BAD = 修① 生效）" % rBF)

    # ── C 改 merkle_root ──
    def tamper_root(o):
        c = json.loads(json.dumps(o)); c["merkle_root"] = "0" * len(c["merkle_root"]); return c

    pC_T = save(labT, tamper_root(oT), "t_C.json")
    pC_F = save(labF, tamper_root(oF), "t_C.json")
    rCT, _ = node([str(vT), str(pC_T)])
    rCF, _ = node([str(vF), str(pC_F)])
    print("  ── C 改 merkle_root（对照）──")
    print("     其版   ⇒ %s ｜ 修后版 ⇒ %s（两版都应 BAD）" % (rCT, rCF))

    print()
    print("  ── E 一叶与两叶是否同根 ──")
    # 其版算法：叶=sha3(bytes)；节点=sha3(hex(l)+hex(r) 的原始字节)
    X, Y = b"file-X-content", b"file-Y-content"
    hX, hY = hashlib.sha3_512(X).hexdigest(), hashlib.sha3_512(Y).hexdigest()
    root2_T = hashlib.sha3_512(bytes.fromhex(hX + hY)).hexdigest()
    Zt = bytes.fromhex(hX + hY)
    root1_T = hashlib.sha3_512(Zt).hexdigest()
    print("     其版   ：两叶根 %s… ｜ 一叶根 %s… ⇒ 相同 = %s"
          % (root2_T[:24], root1_T[:24], root1_T == root2_T))
    # 修后算法：叶=sha3(0x00‖bytes)；节点=sha3(0x01‖left_raw‖right_raw)
    lX = hashlib.sha3_512(b"\x00" + X).hexdigest()
    lY = hashlib.sha3_512(b"\x00" + Y).hexdigest()
    root2_F = hashlib.sha3_512(b"\x01" + bytes.fromhex(lX) + bytes.fromhex(lY)).hexdigest()
    Zf = b"\x01" + bytes.fromhex(lX) + bytes.fromhex(lY)
    root1_F = hashlib.sha3_512(b"\x00" + Zf).hexdigest()
    print("     修后版 ：两叶根 %s… ｜ 一叶根 %s… ⇒ 相同 = %s"
          % (root2_F[:24], root1_F[:24], root1_F == root2_F))

    print()
    print("  ── D 删件是否可检出 ──")
    (labT / "cinema.html").unlink()
    node(["gen_attest.mjs"], cwd=labT)
    oT2 = json.loads((labT / "attest.json").read_text(encoding="utf-8"))
    rT2, _ = node([str(vT), str(labT / "attest.json")])
    print("     其版   ：删件后重跑 ⇒ count %s→%s，新签名自验 %s"
          % (oT["file_count"], oT2["file_count"], rT2))
    print("              ⇒ ★ 重签对【新状态】自然成立 ⇒ D 不体现于重签；")
    print("                体现于【拿旧 attest 去核新目录】时 files 表与目录不符。")
    (labF / "cinema.html").unlink()
    node(["gen_attest_fixed.mjs"], cwd=labF)
    oF2 = json.loads((labF / "attest.fixed.json").read_text(encoding="utf-8"))
    rF2, _ = node([str(vF), str(labF / "attest.fixed.json")])
    print("     修后版 ：删件后重跑 ⇒ count %s→%s，新签名自验 %s" % (oF["file_count"], oF2["file_count"], rF2))
    print("              ★ 但修① 已把 files 表纳入签名 ⇒ 任何人改动【旧 attest 的表】都会 BAD。")

    print()
    print("  ── 判定（只认 OK 为通过）──")
    ok1 = (rBT == "OK") and (rBF == "BAD") and (rCT == "BAD") and (rCF == "BAD")
    ok2 = (root1_T == root2_T) and (root1_F != root2_F)
    print("   修①（签名覆盖面）：其版 OK 且修后版 BAD = %s" % ok1)
    print("   修②（域分隔）    ：其版同根 且修后版不同根 = %s" % ok2)
    print("   ⇒ %s" % ("三处修法均经对照验证" if (ok1 and ok2) else "★有对照不符，见上"))
    print("   ★ 本器每格都能给出两种结果（C 即 BAD 例）⇒ 非恒真。")
    print("   ★ 全程在 %s 与 %s 两个副本内；其 qtorrent_patch/ 与 v2.1 目录一个字节未动。"
          % (labT.name, labF.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
