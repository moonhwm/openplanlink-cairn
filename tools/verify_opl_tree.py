#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_opl_tree.py —— 独立复算 A2A 标准 SHA3-512 树（无钥部分），与 manifest 对账。

字节契约（对齐 tools/SHA3_TREE.md）：
  叶   = SHA3-512(0x00 || uint32be(path_len) || path || uint64be(size) || sha3_512(content))
  父   = SHA3-512(0x01 || left || right)；奇数复制右项
  根MAC= HMAC-SHA3-512(key, "OpenPlanLink-A2A-Merkle-v1\\0" || root || uint64be(count)
              || uint16be(key_id_len) || key_id || uint16be(generated_at_len) || generated_at)
无钥即可复算【merkle 根】；根 MAC 需持钥方密钥（不落库）。
"""
import hashlib
import hmac
import json
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")


def sha3(b):
    return hashlib.sha3_512(b).digest()


def merkle_root_from_leaves(leaf_hexes):
    level = [bytes.fromhex(h) for h in leaf_hexes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex() if level else ""


def main(path):
    m = json.load(open(path, encoding="utf-8"))
    leaves = [f["leaf_sha3_512"] for f in m["files"]]
    mine = merkle_root_from_leaves(leaves)
    theirs = m.get("merkle_root_sha3_512", "")
    ok = hmac.compare_digest(mine, theirs)
    print("  文件数 = %d ｜ 叶子数 = %d" % (m.get("file_count"), len(leaves)))
    print("  我的树根 = %s" % mine)
    print("  manifest = %s" % theirs)
    print("  ★ 逐字节一致 = %s" % ok)
    print("★ VERDICT=" + ("PASS" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
