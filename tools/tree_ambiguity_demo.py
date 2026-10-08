#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
tree_ambiguity_demo.py —— 同一份文件集，在【不同构建口径】下算出【多少个不同的 root】。 v1.0.0

来由
────
本席 2026-10-01 发现：同一生态内至少三套 SHA3-512 树构造并存——
  · `qoder-skills-hub/tools/merkle.cjs`：**无域分离**、奇数**复制**、按**路径**排序、叶含 **CRLF→LF 归一**
  · 本席 `cairn-sha3-512-tree/1`：叶 `0x00`‖bytes、节点 `0x01`‖L‖R、奇数**上提**、按**路径**排序、叶**不归一**
  · 他席哈希链身份（arXiv §3.1）：域分离前缀 **`0x00`–`0x04`**、账本前缀 `0x04`；**树的奇数处理与叶序未公布**
⇒ 「严格依托现有 SHA3-512 哈希树体系」这句话里，**"体系"其实不是同一个东西。**

本器做什么
──────────
取**同一份文件集**，穷举四个维度的口径组合，各算一次 root，把结果并排列出：
  ① 域分离：无 ／ `0x00`+`0x01`
  ② 奇数节点：复制末节点 ／ 上提末节点
  ③ 叶序：按路径 ／ 按哈希值
  ④ 叶归一：原字节 ／ CRLF→LF
**⇒ 用来回答一句话：口径不公布，root 就没有意义。**

用法：tree_ambiguity_demo.py <目录>
"""
from __future__ import annotations
import hashlib
import itertools
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_512(b).digest()


def leaf_hash(p: pathlib.Path, normalize: bool, prefix: bool) -> bytes:
    raw = p.read_bytes()
    if normalize:
        raw = raw.decode("latin1").replace("\r\n", "\n").encode("latin1")
    return sha3((b"\x00" + raw) if prefix else raw)


def root(hashes: list, dup_odd: bool, prefix: bool) -> str:
    L = list(hashes)
    while len(L) > 1:
        n = []
        for i in range(0, len(L), 2):
            if i + 1 < len(L):
                l, r = L[i], L[i + 1]
                n.append(sha3((b"\x01" + l + r) if prefix else (l + r)))
            else:
                n.append(L[i] if not dup_odd else sha3((b"\x01" + L[i] + L[i]) if prefix else (L[i] + L[i])))
        L = n
    return L[0].hex() if L else sha3(b"").hex()


def main():
    d = pathlib.Path(sys.argv[1])
    files = sorted([p for p in d.rglob("*") if p.is_file()], key=lambda p: p.relative_to(d).as_posix())
    print("═══ 同一份件、不同口径：root 会不会不同？ ═══")
    print("文件集：%s（%d 件）" % (d, len(files)))
    if not files:
        print("[ERR] 空目录"); return 2

    rows = {}
    for prefix, dup, norm in itertools.product((False, True), (True, False), (False, True)):
        hs_path = [leaf_hash(p, norm, prefix) for p in files]
        hs_hash = sorted(hs_path)
        rows[(prefix, dup, norm, "path")] = root(hs_path, dup, prefix)
        rows[(prefix, dup, norm, "hash")] = root(hs_hash, dup, prefix)

    uniq = sorted(set(rows.values()))
    print()
    print("%-8s %-10s %-10s %-6s %s" % ("域分离", "奇数", "叶归一", "叶序", "root（前 24 位）"))
    print("-" * 66)
    for (prefix, dup, norm, order), v in rows.items():
        print("%-8s %-10s %-10s %-6s %s…"
              % ("0x00/01" if prefix else "无",
                 "复制" if dup else "上提",
                 "CRLF→LF" if norm else "原字节",
                 "路径" if order == "path" else "哈希",
                 v[:24]))
    print()
    print("组合数 = %d ｜ ★不同 root 数 = %d" % (len(rows), len(uniq)))
    print("★结论：**口径不公布，root 就没有意义**——同一份件可产出 %d 个互不相同的 root，"
          "而第三方无从判断他看到的是哪一个。" % len(uniq))
    print("★故《可验证性三要件》之③（哈希树构建方案）不是学者的洁癖，是**互操作的硬前提**。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
