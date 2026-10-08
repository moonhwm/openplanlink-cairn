#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build_opl_tree.py —— 按 A2A 标准构式（tools/SHA3_TREE.md）为 deliverables 建 SHA3 树。

字节契约（对齐 tools/sha3-tree.mjs）：
  叶   = SHA3-512(0x00 || uint32be(path_len) || path || uint64be(size) || sha3_512(content))  无钥
  父   = SHA3-512(0x01 || left || right)；奇数复制右项                                         无钥
  根MAC= HMAC-SHA3-512(key, "OpenPlanLink-A2A-Merkle-v1\\0" || root || uint64be(count)
              || uint16be(key_id_len) || key_id || uint16be(generated_at_len) || generated_at)
密钥指纹 = sha3_512(key)（自留，不进树）
"""
import hashlib
import hmac
import json
import pathlib
import secrets
import struct
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
DELIV = REPO / "deliverables" / "20261003"
KEY_FILE = pathlib.Path(r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin")
KEY_ID = "opl-a2a-2026q4"


def sha3(b):
    return hashlib.sha3_512(b).digest()


# 密钥（64 字节，自留）
key = KEY_FILE.read_bytes() if KEY_FILE.exists() else secrets.token_bytes(64)
if len(key) != 64:
    key = secrets.token_bytes(64)
KEY_FILE.write_bytes(key)


def leaf(path_utf8, size, content_digest_hex):
    pb = path_utf8.encode("utf-8")
    data = b"\x00" + struct.pack(">I", len(pb)) + pb + struct.pack(">Q", size) + bytes.fromhex(content_digest_hex)
    return sha3(data).hex()


def merkle_root(leaf_hexes):
    level = [bytes.fromhex(h) for h in leaf_hexes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex() if level else ""


files = sorted(p.relative_to(DELIV).as_posix() for p in DELIV.rglob("*") if p.is_file())
files = [f for f in files if f != "hmac_attest.json"]  # 排除自身

entries = []
for rel in files:
    data = (DELIV / rel).read_bytes()
    cd = sha3(data).hex()
    lh = leaf(rel, len(data), cd)
    entries.append({"path": rel, "size": len(data), "content_sha3_512": cd, "leaf_sha3_512": lh})

root = merkle_root([e["leaf_sha3_512"] for e in entries])

generated_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
kid = KEY_ID.encode("utf-8")
gen = generated_at.encode("utf-8")
mac_input = (
    b"OpenPlanLink-A2A-Merkle-v1\x00"
    + bytes.fromhex(root)
    + struct.pack(">Q", len(entries))
    + struct.pack(">H", len(kid)) + kid
    + struct.pack(">H", len(gen)) + gen
)
mac = hmac.new(key, mac_input, hashlib.sha3_512).hexdigest()

manifest = {
    "schema": "opl-hmac-sha3-512-tree/1",
    "generated_at": generated_at,
    "tree_algorithm": "sha3-512",
    "mac_algorithm": "hmac-sha3-512",
    "leaf_encoding": "0x00 || uint32be(path_utf8_len) || path_utf8 || uint64be(size) || sha3_512(content)",
    "node_encoding": "0x01 || left_digest || right_digest; duplicate odd right node",
    "mac_encoding": "UTF8(OpenPlanLink-A2A-Merkle-v1\\0) || root_digest || uint64be(file_count) || uint16be(key_id_utf8_len) || key_id_utf8 || uint16be(generated_at_utf8_len) || generated_at_utf8",
    "key_id": KEY_ID,
    "file_count": len(entries),
    "merkle_root_sha3_512": root,
    "hmac_sha3_512": mac,
    "files": entries,
}
out = DELIV / "hmac_attest.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("★ 密钥指纹 sha3_512(key) 前16 =", sha3(key).hex()[:16])
print("★ merkle_root =", root)
print("★ hmac_sha3_512 =", mac)
print("★ file_count =", len(entries))
print("★ 已写 =", out.name)
