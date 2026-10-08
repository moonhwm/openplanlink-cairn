#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
verify_opl_attest.py —— 独立复算 OpenPlanLink 幻16 桥接节点的 SHA3-512 存证。

定位
────
节点在生态通告第 5 条自己写了：
  「身份核验严格依托 SHA3-512 哈希树多重验证，**不得仅以键名/席位名为唯一依据**」。
本工具就是照这条办事：**不采信任何标签，全部自己算**。

三件事
──────
① **逐件复算**：对 attest.json 所列每个文件算 sha3-512，与声明值逐字符比对。
② **验签**：用 attest.json 给的 Ed25519 公钥（SPKI DER）验签，逐个试候选被签消息，
   并**如实报告"试了哪些、哪个通过"**——不做"看起来没问题"的含糊判断。
③ **Merkle 重算**：在**未获知构建方案**的前提下，穷举若干常见组合试算 root，
   匹配则报匹配，**不匹配则如实说"方案不可从公开数据复原"**——这是缺口，不是失败。

诚实边界
────────
· 本工具**只读**本地已取回的件，不联网。
· 未被取回的文件**计入"未取回"**，不计入相符——**覆盖率必须如实报**。
· 签名通过**只证"该 root 由该公钥签发"**，**不证"root 对应的内容就是好内容"**。
"""
from __future__ import annotations
import base64
import hashlib
import itertools
import json
import pathlib
import sys

# ★ UTF-8 输出（建立时即带）：本席既有 8 个工具都补过这一块，新工具必须同规格，
#   否则「⇒」这类字符在 GBK 控制台下直接 UnicodeEncodeError。
#   ★首次运行确实炸在这里——**上轮刚立的『连坐』教训，自己隔一轮就犯**，
#   故本轮另建 tool_hygiene.py 把这条做成机检，不再靠记忆。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIRROR = ROOT / "handshake" / "openplanlink-mirror"
ATTEST = MIRROR / "attest.json"


def sha3_hex(b: bytes) -> str:
    return hashlib.sha3_512(b).hexdigest()


def part1_piecewise(att: dict):
    files = att["files"]
    print("── ① 逐件复算（sha3-512）──")
    print("   schema=%s ｜ ts=%s ｜ sig_alg=%s" % (att["schema"], att["ts"], att["sig_alg"]))
    print("   声明文件数=%d ｜ file_count 字段=%d ⇒ %s"
          % (len(files), att["file_count"], "一致" if len(files) == att["file_count"] else "★不一致"))
    ok, bad, miss = 0, [], []
    for rel, want in sorted(files.items()):
        p = MIRROR / rel
        if not p.exists():
            miss.append(rel)
            continue
        got = sha3_hex(p.read_bytes())
        if got == want:
            ok += 1
            print("   [相符] %-32s %s…" % (rel, got[:20]))
        else:
            bad.append(rel)
            print("   ★[不符] %s\n           存证 %s\n           实算 %s" % (rel, want, got))
    total = len(files)
    print("\n   相符 %d ｜ 不符 %d ｜ 未取回 %d ／ 声明 %d" % (ok, len(bad), len(miss), total))
    print("   ★复算覆盖率 = %.1f%%（已相符/声明）" % (100.0 * ok / total))
    if miss:
        print("   未取回明细：%s" % "、".join(miss))
    return ok, bad, miss


def part2_signature(att: dict):
    print("\n── ② 验签（Ed25519）──")
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
    except Exception as e:
        print("   [SKIP] 无 cryptography 库：%s" % e)
        return None
    der = base64.b64decode(att["pubkey"])
    pub = load_der_public_key(der)
    sig = base64.b64decode(att["sig"])
    print("   公钥算法=%s ｜ 签名长度=%d 字节 ｜ 公钥 DER=%d 字节"
          % (type(pub).__name__, len(sig), len(der)))

    root_hex = att["merkle_root"]
    base = {k: v for k, v in att.items() if k not in ("sig", "pubkey")}
    cands = [
        ("merkle_root 的 utf-8 字节", root_hex.encode()),
        ("merkle_root 的 hex 解码字节", bytes.fromhex(root_hex)),
        ("files 的规范 JSON（sort_keys）", json.dumps(att["files"], ensure_ascii=False, sort_keys=True).encode()),
        ("去掉 sig/pubkey 的规范 JSON", json.dumps(base, ensure_ascii=False, sort_keys=True).encode()),
        ("去掉 sig/pubkey 的紧凑 JSON", json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
        ("merkle_root+file_count", ("%s%d" % (root_hex, att["file_count"])).encode()),
    ]
    hit = None
    for name, msg in cands:
        try:
            pub.verify(sig, msg)
            print("   ★[验签通过] 被签消息 = %s（%d 字节）" % (name, len(msg)))
            hit = name
            break
        except Exception:
            print("   [未通过] %s" % name)
    if not hit:
        print("   ⇒ 结论：**六种候选消息无一验签通过**。")
        print("     本席不据此断言「存证是伪造的」——只断言「**所签消息的内容未在公开数据中说明**」，")
        print("     故**第三方无法独立完成验签**。这是一处**可验证性缺口**，须由节点方公布签名口径。")
    return hit


def mroot(leaves: list, sort: bool, dup_odd: bool, prefix: bool) -> str:
    h = [bytes.fromhex(x) for x in leaves]
    if sort:
        h.sort()
    if prefix:
        h = [b"\x00" + x for x in h]
    while len(h) > 1:
        if len(h) % 2 == 1:
            if dup_odd:
                h = h + [h[-1]]
            else:
                carry = h[-1]
                h = h[:-1]
                nxt = []
                for i in range(0, len(h), 2):
                    nxt.append(hashlib.sha3_512((b"\x01" if prefix else b"") + h[i] + h[i + 1]).digest())
                nxt.append(carry)
                h = nxt
                continue
        nxt = []
        for i in range(0, len(h), 2):
            nxt.append(hashlib.sha3_512((b"\x01" if prefix else b"") + h[i] + h[i + 1]).digest())
        h = nxt
    return h[0].hex()


def part3_merkle(att: dict):
    print("\n── ③ Merkle root 重算（构建方案未公布，穷举常见组合）──")
    want = att["merkle_root"]
    print("   声明 root = %s…" % want[:24])
    leaves = list(att["files"].values())
    tried = 0
    for sort, dup, pre in itertools.product((True, False), (True, False), (True, False)):
        got = mroot(leaves, sort, dup, pre)
        tried += 1
        tag = "排序" if sort else "原序"
        if got == want:
            print("   ★[匹配] 组合：%s／奇数叶重复=%s／叶节点前缀=%s" % (tag, dup, pre))
            return (sort, dup, pre)
    print("   试算 %d 种组合，**无一匹配**。" % tried)
    print("   ⇒ 结论：**Merkle root 的构建方案无法从公开数据复原**（叶序／奇偶处理／前缀／")
    print("     域分隔符均未公布）。故**第三方无法独立验证 root 本身**，只能验证各叶哈希。")
    print("     ★这是一处**可验证性缺口**，不是「存证造假」的证据——两者必须分开说。")
    return None


def main():
    if not ATTEST.exists():
        print("[ERR] 未找到 %s" % ATTEST)
        return 2
    att = json.loads(ATTEST.read_text(encoding="utf-8"))
    print("═══ 独立复算：OpenPlanLink 幻16 桥接节点存证 ═══")
    print("（本席不采信任何标签；以下全部为本机现算）\n")
    ok, bad, miss = part1_piecewise(att)
    sig = part2_signature(att)
    mk = part3_merkle(att)
    print("\n═══ 汇总 ═══")
    print("逐件相符：%d ｜ 不符：%d ｜ 未取回：%d" % (ok, len(bad), len(miss)))
    print("验签：%s" % ("通过（消息＝%s）" % sig if sig else "**未通过／口径未公布**"))
    print("Merkle 重算：%s" % ("匹配" if mk else "**方案未公布，无法复原**"))
    print("\n★ 判读纪律：以上三项**互相独立**。逐件相符只证「这些字节与声明一致」；")
    print("  验签只证「该消息由该公钥签发」；root 复算只证「叶集能拼出该 root」。")
    print("  **任何一项通过，都不等于「内容可信」**——那是第四件事，须另论。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
