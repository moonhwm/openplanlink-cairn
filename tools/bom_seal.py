#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
bom_seal.py —— 封锚【前】的一道工序：给"给人读的中文件"原地加 UTF-8 BOM。 v1.0.0

为什么是"前置"而不是"投放时加"（轮 96 的关键推理）
────────────────────────────────────────────────────
轮 95 普查发现本席 2,630 件产出无 BOM ⇒ 在假定 ANSI 代码页的读取方（含本会话 pwsh 默认
`Get-Content`）下显示为乱码。
轮 96 本席本想"改投放器 `pilot_publish.py`，投放时加 BOM"——**读完该器后判定此路【错】**：
  其纪律第一条明写「**字节同源：投出去的就是本席封锚的那一份，不做『共享版/内部版』两套皮**」。
  ⇒ 在投放时加 BOM **正是那条纪律禁止的"两套皮"**；且 `.sha256` 会指向与源件不同的字节串，
    第三方按源件复算必然对不上 ⇒ **破坏"任何人可独立复算"这一性质。**
★ 故正确位置是【封锚之前】：**先加 BOM，再算 hash（mkled）、再投放（pilot_publish）**。
  ⇒ 于是台账 hash、`.sha256`、投放字节【三者一致指向同一个 BOM 后的文件】。

纪律
──────
1. **只给人读的扩展名加**（`.md`／`.tsv`／`.txt`）；**给程序读的一律拒绝**
   （`.py`／`.mjs`／`.json`／`.led`）——`node` 会因 BOM 报错、JSON 解析器多不容 BOM；
2. **幂等**：已有 BOM 者报 ALREADY 且不改；
3. **先写后验**：写完立即回读首 3 字节复核，不符即报错退出；
4. **不碰他人格**：只处理本席领地内的路径，越界即拒。

用法: bom_seal.py <文件路径> [更多路径…]
"""
from __future__ import annotations
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
SEAT_DIR = HERE.parent

BOM = b"\xef\xbb\xbf"
HUMAN_EXT = {".md", ".tsv", ".txt"}
MACHINE_EXT = {".py", ".mjs", ".json", ".led"}


def seal(p: pathlib.Path) -> str:
    """★ 2026-10-02 轮 29 改名：原返回 'SEALED' —— 那是【名不副实】：
    本函数【只加一个 UTF-8 BOM】，与【封签／签名／作者】毫无关系。
    ★ 这与轮 5 我修过的 `cairn_ledger.py cmd_seal`（"只算 sha256，不签名"）【同一个病】，
      只是长在另一个器上——而我每轮都把这句「✅ SEALED」当一道手续引出来。
    ⇒ 故改名：'BOM+'（加了 BOM）／'ALREADY'（本来就有）。
    返回 'BOM+' / 'ALREADY' / 'REFUSE:…' / 'ERR:…'"""
    ext = p.suffix.lower()
    if ext in MACHINE_EXT:
        return "REFUSE:程序读的扩展名（%s）不得加 BOM" % ext
    if ext not in HUMAN_EXT:
        return "REFUSE:未列入人读白名单的扩展名（%s）" % ext
    b = p.read_bytes()
    if b.startswith(BOM):
        return "ALREADY"
    p.write_bytes(BOM + b)
    back = p.read_bytes()
    if not back.startswith(BOM) or back[3:] != b:
        return "ERR:回读复核失败"
    return "BOM+"


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: bom_seal.py <文件路径> [更多路径…]")
        return 2
    bad = 0
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        if not p.is_absolute():
            p = (SEAT_DIR / p).resolve()
        if not p.is_file():
            print("  ★不存在：%s" % p); bad += 1; continue
        # ★ 不碰他人格
        if str(SEAT_DIR) not in str(p):
            print("  [REFUSE] 越界（不在本席领地内）：%s" % p); bad += 1; continue
        before = len(p.read_bytes())
        r = seal(p)
        after = len(p.read_bytes())
        mark = "✅" if r in ("BOM+", "ALREADY") else "★"
        print("  %s %-8s %s（%d → %d B）" % (mark, r, p.name, before, after))
        if r.startswith(("REFUSE", "ERR")):
            bad += 1
    print()
    print("  ★ 本器能给出 BOM+ / ALREADY / REFUSE / ERR 四种结果 ⇒ 非恒真。")
    print("  ★★★ 而「BOM+」这个词说的是它【真正做的事】：加一个 UTF-8 BOM。")
    print("      ★ 它【不是签名、不含作者、不封任何东西】——原判词「SEALED」名不副实，已于轮 29 改掉。")
    print("      ★ 同病先例：轮 5 修过 cairn_ledger.py 的 cmd_seal（『只算 sha256，不签名』）。")
    print("  ★ 顺序：先本器 → 再 mkled.py（算 hash）→ 再 pilot_publish.py（投放）。三者由此一致。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
