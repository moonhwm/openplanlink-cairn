#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
line_tails.py —— 读取「超长行被截断的尾部」，输出过掩码。  v1.0.0

来由
────
附录段1 读件员如实报出：11 行超 2000 字符，read 工具按行截断，**尾部未读**，
并指出「read 工具无法给出，需要其它读取手段」。本席补此手段。

纪律
────
· 输出**必经掩码**（复用 scan_secrets.mask_line：模式表掩码 ＋ 长 token 兜底掩码），
  以免把尾部里可能存在的凭据打进上下文。
· 只读，不改任何文件。
· 先报长度，再报尾巴；长度超阈值可只报摘要（--head 控制）。

用法：line_tails.py <文件> <行号>[,<行号>…] [从第几字符开始=2000]
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scan_secrets import mask_line  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    p = pathlib.Path(sys.argv[1])
    if not p.is_file():
        print("[ERR] 不是文件：%s" % p)
        return 2
    nums = [int(x) for x in sys.argv[2].split(",") if x.strip()]
    cut = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

    print("文件：%s（共 %d 行）｜ 从第 %d 字符起显示尾部（已掩码）\n" % (p.name, len(lines), cut))
    for n in nums:
        if not (1 <= n <= len(lines)):
            print("L%-6d (超范围)" % n)
            continue
        s = lines[n - 1]
        tail = s[cut:]
        print("═══ L%d ═══ 全长=%d 字符 ｜ 2000 字内已由读件员读过 ｜ 尾部=%d 字符"
              % (n, len(s), len(tail)))
        print(mask_line(tail) if tail.strip() else "(尾部为空)")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
