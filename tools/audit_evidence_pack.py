#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
audit_evidence_pack.py —— 审 v2.1 的 19 张取证截图：能不能被检验。 v1.0.0

为什么
──────
`ledger/evidence/` 里 19 张截图＋`_diagnostics.json` 是该站 v2.1 的**证据**。
本席整晚的立场是：**不能被检验的证据，只是装饰。**
⇒ 故本器【不看内容好不好看】，只算六件事：
   ① `_diagnostics.json` 引用的 shot 是否都存在
   ② 是否存在【文件在、但诊断未引用】（漏登记）
   ③ 19 张是否【彼此不同】（哈希去重）
   ④ 亮/暗成对的是否【真的不同】（像素均值差）
   ⑤ 是否有【近纯色/空白】图（标准差过低）
   ⑥ `clip:true` 的细节图是否【小而非空白】

★ 结论一律由计算得出，并打印 PASS/FAIL；**每项都必须能失败**。
用法: audit_evidence_pack.py <evidence 目录>
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import statistics
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from PIL import Image
except Exception as e:
    print("[ERR] 缺 Pillow：%s" % e); sys.exit(3)


def stats_of(p: pathlib.Path):
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    try:
        with Image.open(p) as im:
            im = im.convert("L")
            w, ht = im.size
            px = list(im.getdata())
            mean = sum(px) / len(px)
            sd = statistics.pstdev(px)
        return {"bytes": len(b), "sha256": h, "w": w, "h": ht, "mean": round(mean, 2), "sd": round(sd, 2)}
    except Exception as e:
        return {"bytes": len(b), "sha256": h, "err": str(e)[:50]}


def main() -> int:
    d = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not d or not d.is_dir():
        print("用法: audit_evidence_pack.py <evidence 目录>"); return 2
    print("═══ 审取证包：%s ═══" % d)
    diag_p = d / "_diagnostics.json"
    steps = []
    if diag_p.is_file():
        diag = json.loads(diag_p.read_text(encoding="utf-8"))
        steps = diag.get("steps", diag if isinstance(diag, list) else [])
    print("  `_diagnostics.json` 记录步数 = %d" % len(steps))

    pngs = sorted([p for p in d.iterdir() if p.suffix.lower() == ".png"])
    print("  目录内 .png 数 = %d" % len(pngs))
    print()
    print("  %-30s %9s %6s %7s %7s %6s" % ("文件", "字节", "尺寸", "均值", "标准差", "裁切"))
    info = {}
    refd = set()
    for s in steps:
        shot = s.get("shot") or s.get("file") or ""
        if shot:
            refd.add(shot)
    for p in pngs:
        st = stats_of(p)
        info[p.name] = st
        note = ""
        if p.name not in refd:
            note = "★未在诊断中登记"
        print("  %-30s %9s %6s %7s %7s %6s  %s"
              % (p.name, st["bytes"],
                 ("%dx%d" % (st["w"], st["h"])) if "w" in st else "—",
                 st.get("mean", "—"), st.get("sd", "—"),
                 "是" if any(s.get("shot") == p.name and s.get("clip") for s in steps) else "否",
                 note))

    print()
    print("  ── 逐项判定（每项都能失败）──")
    fails = []

    # ① 引用但缺文件
    missing = [s.get("shot") for s in steps if s.get("shot") and not (d / s["shot"]).is_file()]
    print("  ① 诊断引用而文件缺失 = %d %s ⇒ [%s]"
          % (len(missing), (missing[:4] if missing else ""), "PASS" if not missing else "FAIL"))
    if missing: fails.append("①")

    # ② 文件在但未登记
    unreferenced = [p.name for p in pngs if p.name not in refd]
    print("  ② 文件存在而诊断未登记 = %d %s ⇒ [%s]"
          % (len(unreferenced), (unreferenced[:4] if unreferenced else ""), "PASS" if not unreferenced else "FAIL"))
    if unreferenced: fails.append("②")

    # ③ 彼此不同
    hashes = [info[p.name]["sha256"] for p in pngs]
    dup = len(hashes) - len(set(hashes))
    print("  ③ 内容重复的图 = %d（19 张中） ⇒ [%s]" % (dup, "PASS" if dup == 0 else "FAIL"))
    if dup: fails.append("③")

    # ④ 亮/暗成对是否真不同
    pairs = [("01_index_light.png", "02_index_dark.png"), ("03_observe_dark.png", "04_observe_light.png"),
             ("05_cinema_light.png", "06_cinema_dark.png"), ("08_sandbox_light.png", "13_sandbox_dark.png"),
             ("14_sea_light.png", "15_sea_dark.png"), ("16_oracle_light.png", "17_oracle_offline.png"),
             ("18_arch_dark.png", "19_arch_light.png")]
    same_pairs = []
    for a, b in pairs:
        if a in info and b in info and "mean" in info[a] and "mean" in info[b]:
            if abs(info[a]["mean"] - info[b]["mean"]) < 1.0:
                same_pairs.append((a, b, info[a]["mean"], info[b]["mean"]))
    print("  ④ 亮/暗成对而亮度几乎相同 = %d 对 %s ⇒ [%s]"
          % (len(same_pairs), (same_pairs[:2] if same_pairs else ""), "PASS" if not same_pairs else "FAIL"))
    if same_pairs: fails.append("④")

    # ⑤ 近空白（标准差 < 5）
    blanks = [(p.name, info[p.name].get("sd")) for p in pngs
              if "sd" in info[p.name] and info[p.name]["sd"] < 5]
    print("  ⑤ 近空白图（标准差<5）= %d %s ⇒ [%s]"
          % (len(blanks), (blanks[:3] if blanks else ""), "PASS" if not blanks else "FAIL"))
    if blanks: fails.append("⑤")

    # ⑥ clip 细节图应小而非常规整（本席只断言"能读到且非空白"）
    clips = [p for p in pngs if any(s.get("shot") == p.name and s.get("clip") for s in steps)]
    bad_clips = [p.name for p in clips if info[p.name].get("sd", 99) < 5]
    print("  ⑥ clip 细节图共 %d 张，其中近空白 = %d ⇒ [%s]"
          % (len(clips), len(bad_clips), "PASS" if not bad_clips else "FAIL"))
    if bad_clips: fails.append("⑥")

    print()
    print("  ── 附：运行日志 ──")
    for lg in sorted(d.glob("_run*.log")):
        txt = lg.read_text(encoding="utf-8", errors="replace")
        print("   · %s（%d B，%d 行）" % (lg.name, lg.stat().st_size, len(txt.splitlines())))
        for line in txt.strip().splitlines()[:3]:
            print("       " + line[:100])

    print()
    print("  ⇒ 六项判定：%s" % ("全 PASS —— 该证据包可被检验" if not fails else "★未过项 = " + ",".join(fails)))
    print("  ★ 本器能给出 PASS 与 FAIL 两种结果（③④⑤ 皆可失败）⇒ 非恒真。")
    print("  ★ 本器【只读】其 evidence 目录，未改动一个文件。")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
