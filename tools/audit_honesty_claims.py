#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读审计：我自己写了多少次"不证作者"，以及本席到底有没有签名能力。
r"""audit_honesty_claims.py —— 审【我自己那套"诚实边界"】里，哪些是【给定】，哪些是【选择】。 v1.0.0

立此器的缘由（写下来，免得下次再犯）
──────────────────────────────────────
我用 PowerShell 的 `Get-ChildItem <目录> -File -Include *.md` 搜"我写过多少次不证作者"，
得到 **0**。而我知道答案绝不是 0。
★ 病根：`-Include` 不配 `-Recurse`（且路径不含通配符）时会【静默返回空】——
   **不是报错，是给一个【假零】**。差一点据此写出与事实相反的话。
⇒ 故本器用 Python 逐文件读字节判子串，**并把"命中 0"时【打印判据与搜索范围】**，
   使"零"这个结果本身可被质疑（本席规矩：一个 not-found 必须报出所用模式与范围）。

产出
──────
  A. 我在多少件里写过「不证作者 / signed=false」——按目录与件分类
  B. 本席是否存在【真实签名能力】：密钥材料、签名代码、以及那些"看起来能签"的器到底做什么
  C. 把每条"诚实边界"分成【给定】与【选择】两栏（★ 这是本器的重点）
"""
from __future__ import annotations
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = {
    "不证作者": re.compile("不证作者"),
    "signed=false": re.compile(r"signed\s*=\s*false|signed=false"),
    "哈希链≠签名": re.compile("哈希链≠签名"),
    "只证一致": re.compile("只证一致"),
}
KEY_NAME = re.compile(r"\.pem$|\.key$|^id_|_key\.|keypair|\.pub$", re.I)
SIGN_CODE = re.compile(r"ed25519|SigningKey|from_private|load_pem|generate_key|createSign|privateKey", re.I)
SKIP = ("__pycache__", "handshake", "_整理", ".venv")


def hits(root: pathlib.Path):
    out = {k: [] for k in PATTERNS}
    scanned = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(k in str(p) for k in SKIP):
            continue
        if p.suffix.lower() not in (".md", ".json", ".py", ".js", ".mjs", ".txt", ".tsv"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        for k, pat in PATTERNS.items():
            if pat.search(t):
                out[k].append(p)
    return out, scanned


def main() -> int:
    print("═══ 诚实边界审计（只读·字面搜索）═══")
    print("  席位 = %s" % SEAT)
    print("  ★ 搜索范围：%s 递归；扩展名 .md/.json/.py/.js/.mjs/.txt/.tsv；排除 %s"
          % (SEAT.name, "、".join(SKIP)))

    h, scanned = hits(SEAT)
    print("  扫过可读文本件 = %d" % scanned)
    print()
    print("  ── A · 我写过多少次那句话 ──")
    for k, v in h.items():
        occ = 0
        for p in v:
            try:
                occ += len(PATTERNS[k].findall(p.read_text(encoding="utf-8", errors="replace")))
            except Exception:
                pass
        print("     %-16s 命中件数 = %4d ｜ 出现次数 = %d" % (k, len(v), occ))
    # ★ 若命中为 0，必须打印判据与范围（本席规矩：一个 not-found 必须报出所用模式与范围）
    for k, v in h.items():
        if not v:
            print("     ★ 「%s」命中 0 —— 搜索模式 = %s ｜ 范围 = %s ⇒ 该零是【有范围的零】"
                  % (k, PATTERNS[k].pattern, SEAT))

    print()
    print("  ── B · 本席到底有没有【真实签名能力】 ──")
    keys = [p for p in SEAT.rglob("*") if p.is_file() and KEY_NAME.search(p.name)
            and not any(x in str(p) for x in SKIP)]
    print("     疑似密钥材料 = %d" % len(keys))
    for p in keys[:8]:
        print("        " + str(p).replace(str(SEAT), "<席位>"))
    coders = []
    for p in SEAT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".py", ".mjs", ".js"):
            continue
        if any(x in str(p) for x in SKIP):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if SIGN_CODE.search(t):
            coders.append(p)
    print("     含签名相关代码的器 = %d" % len(coders))
    for p in coders[:10]:
        print("        " + str(p).replace(str(SEAT), "<席位>"))
    lg = SEAT / "ledger" / "cairn_ledger.py"
    if lg.is_file():
        t = lg.read_text(encoding="utf-8", errors="replace")
        print("     ★ 本席台账器 cairn_ledger.py：含真签名代码 = %s" % bool(SIGN_CODE.search(t)))
        print("     ★ 但其 `seal` 子命令【只打印 sha256】——名字自称「封缄」，实际是哈希 ⇒ 名不副实")

    print()
    print("  ── C · 把「诚实边界」分两栏 ──")
    print("     【给定】（我改变不了）:")
    print("        · 哈希链的数学性质：链自洽 ≠ 内容为真")
    print("        · 另一席位是否联署：不在我控制内")
    print("     【选择】（我一直把它写成了给定）:")
    print("        · ★ signed=false —— 我从没签发过席位密钥。这不是链的性质，是我没做的动作。")
    print("        · ★ 本席有能生成密钥的器（见 B），故「做不到」这一说法【未经检验】。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
