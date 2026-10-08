#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
fix_chain_signature.py —— 给快照链上签名：把"发现的病"做成"测过的药"。 v1.0.0

背景
──────
轮 77 实测其 `SnapshotChain.verify()`：**改结论并重算其后所有 digest ⇒ 链仍自洽 ⇒ 通过**。
其 §3.2 D3 只要求「hash 衔接、前驱在册」，**未覆盖"谁写的"**。
⇒ 本器做【修法】，并做【修前/修后对照】，全部用**其 §2.2 已设计的 ed25519**。

修法
──────
  ① 链头（或每条）digest 用【席位私钥】签一次，签名随链保存；
  ② 校验时：**先按原算法验衔接，再验签名** ⇒ 重写链需持有私钥，否则签名对不上。

三组对照（本器须能给出不同结论，否则作废）
  A 完好链 ＋ 有效签名            ⇒ **应通过**
  B 重写链（digest 全重算）＋ 旧签名 ⇒ ★ **应拦下**（这是修法带来的增量）
  C 重写链（digest 全重算）＋ 无签名 ⇒ **应通过**（复现轮 77 的病，作为"修前"基线）

★ 密钥纪律：**私钥只在内存、不落盘、不打印、不写入任何件**；用完即弃。
★ 本席未改其代码一个字节：**本器只复用其 `sha3`/`canon` 算法**。
用法: fix_chain_signature.py [--deduce 路径]
"""
from __future__ import annotations
import argparse
import copy
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deduce", default=r"C:\Users\欧阳宏俊\OneDrive\桌面")
    a = ap.parse_args()
    d = pathlib.Path(a.deduce)
    if not (d / "deduce_core.py").is_file():
        print("[ERR] 未找到 deduce_core.py"); return 2
    sys.path.insert(0, str(d))
    import deduce_core as dc

    # ★ 加密件：优先用 cryptography；无则用 node 亦可，但本器只依赖标准库可得的路径
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
    except Exception as e:
        print("[ERR] 缺 cryptography（本器需 ed25519）：%s" % e)
        print("      ★ 本席不为此安装任何东西；如需，请示机主。")
        return 3

    print("═══ 给快照链上签名：修前/修后对照 ═══")
    print("  对象算法复用 = %s（本席未改其代码）" % (d / "deduce_core.py"))
    print()

    # ── 造链（用其 DeduceCore 产真结论）──
    core = dc.DeduceCore()
    for e in [{"ts": 1000, "src": "s1", "kind": "cost", "payload": {"cost_yuan": 1.5}},
              {"ts": 1010, "src": "s2", "kind": "cost", "payload": {"cost_yuan": 2.5}},
              {"ts": 1020, "src": "s3", "kind": "bus_rows", "payload": {"rows": 100}}]:
        core.ingest(e)
    chain = core.chain.chain
    if not chain:
        print("[ERR] 链为空"); return 4
    print("  链长 = %d" % len(chain))

    # ── ★ 私钥只在内存 ──
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key()
    pk_raw = pk.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    print("  席位公钥（Raw，可外发） = %s…" % pk_raw.hex()[:24])
    print("  ★ 私钥：仅在内存生成、未落盘、未打印、未写入任何件；用完即弃。")
    print()

    def head_digest(ch):
        return ch[-1]["digest"]

    def sign_head(ch):
        return sk.sign(head_digest(ch).encode()).hex()

    def verify_signed(ch, sig_hex, pk_obj):
        """先验衔接（其算法），再验签名。"""
        prev, ok = "0" * 128, True
        for e in ch:
            exp = dc.sha3((prev + str(e["seq"]) + dc.sha3(dc.canon(e["conclusion"]))).encode())
            if exp != e["digest"] or e["prev"] != prev:
                ok = False
            prev = e["digest"]
        if not ok:
            return False, "衔接不符"
        try:
            pk_obj.verify(bytes.fromhex(sig_hex), head_digest(ch).encode())
            return True, "衔接符 ∧ 签名符"
        except Exception:
            return False, "衔接符，但★签名不符 ⇒ 链被重写"

    def rewrite(ch):
        """重写：改一条结论 + 按其算法重算其后全部 digest（轮 77 的攻法）。"""
        f = copy.deepcopy(ch)
        f[0]["conclusion"]["cost_yuan"] = 999.0
        prev = "0" * 128
        for i, e in enumerate(f):
            e["seq"] = i + 1
            e["prev"] = prev
            e["digest"] = dc.sha3((prev + str(e["seq"]) + dc.sha3(dc.canon(e["conclusion"]))).encode())
            prev = e["digest"]
        return f

    # 签名（在完好链上）
    good = copy.deepcopy(chain)
    sig = sign_head(good)
    forged = rewrite(chain)

    # ── A ──
    A_ok, A_why = verify_signed(good, sig, pk)
    print("  A 完好链 ＋ 有效签名              ⇒ %s ｜ %s（期望 通过）" % (A_ok, A_why))
    # ── B ──
    B_ok, B_why = verify_signed(forged, sig, pk)
    print("  B 重写链 ＋ 旧签名                ⇒ %s ｜ %s（期望 ★拦下）" % (B_ok, B_why))
    # ── C（修前基线）──
    C_ok = True
    prev = "0" * 128
    for e in forged:
        exp = dc.sha3((prev + str(e["seq"]) + dc.sha3(dc.canon(e["conclusion"]))).encode())
        if exp != e["digest"] or e["prev"] != prev:
            C_ok = False
        prev = e["digest"]
    print("  C 重写链 ＋ 无签名（修前基线）      ⇒ 其 verify 会通过 = %s（复现轮 77 之病）" % C_ok)

    print()
    ok = (A_ok is True) and (B_ok is False) and (C_ok is True)
    print("  ⇒ %s" % ("三组对照全部符合预期：**修法有效**——重写链在签名下被拦下，而修前通过"
                     if ok else "★有对照不符预期，见上"))
    print("  ⇒ 增量一句话：**同样一条被重写的链，修前通过、修后拦下。**")
    print("  ★ 本器能给出【通过】与【拦下】两种结果 ⇒ 非恒真。")
    print()
    print("  ★ 落地建议（承轮 77，仍复用其自家器具）：")
    print("     · 把「链头或每条 digest 的席位签名」并入其 §2.2 的 S1 验签流程；")
    print("     · 并把 D3 判据由「hash 衔接、前驱在册」改为「衔接 ∧ 可验签」。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
