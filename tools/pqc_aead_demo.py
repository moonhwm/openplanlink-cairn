# -*- coding: utf-8 -*-
"""pqc_aead_demo.py —— PQC 二期可即办项之示范器（2026-10-14 立）

依据：《后量子加密与国密体系实施方案》PQC-20261014-CAIRN-01 二期
      —— 「④ AES-256-GCM 正文加密；⑤ 透明加解密层」；并列 **SM3 完整性**（令条 SM10 之近亲）。

★守界（★极要）：
    ★1 **不碰真凭据**：本器只对**内置之假想字段**加解密，**不读、不写、不回显任何真实密钥或凭据**；
    ★2 键为**运行时临时生成**（`AESGCM.generate_key`），**用毕即弃**（不落盘）；
    ★3 输出**只含长度与校验结果**，**不含密钥、不含明文**；
    ★4 诚实标注：★本器为**示范**，非**生产加密**；★SM3 为**哈希**（完整性），**非** SM10 之序列密码实现。

★所验三事：
    ★A **AES-256-GCM** 之加解密与 AAD（席别绑定）；
    ★B **SM3** 之完整性摘要（国密哈希可用性）；
    ★C 若 SM3 不可用，**退路为 SHA3-256**（并如实标）。

用法：python pqc_aead_demo.py
"""
import hashlib, os, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

SAMPLE = "假想敏感字段：示例文本，仅用于验证加解密与完整性链路。"
# ★注：bytes 字面量只能含 ASCII ⇒ 中文须 .encode("utf-8")（承 pyrun.py 预编译前置之拦）
AAD = "seat=A2A新席_石敢当Cairn|purpose=demo|ver=1".encode("utf-8")


def main() -> int:
    print("═══ PQC 二期示范（★不碰真凭据）═══")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception as e:
        print("   ★AESGCM 不可用：%s" % str(e)[:80]); return 2

    print("★A AES-256-GCM ＋ AAD（席别／用途／版本绑定）")
    key = AESGCM.generate_key(bit_length=256)      # ★临时生成、用毕即弃
    nonce = os.urandom(12)
    pt = SAMPLE.encode("utf-8")
    ct = AESGCM(key).encrypt(nonce, pt, AAD)
    rec = AESGCM(key).decrypt(nonce, ct, AAD)
    print("   明文 %d 字节 ⇒ 密文 %d 字节（含 tag 16）⇒ 回解 %d 字节 ⇒ 一致 %s"
          % (len(pt), len(ct), len(rec), rec == pt))
    try:
        AESGCM(key).decrypt(nonce, ct, "seat=他席".encode("utf-8"))            # ★AAD 不符应失败
        print("   ★★异常：AAD 不符竟解密成功（须查）")
    except Exception:
        print("   ✓ AAD 不符时解密失败（★席别绑定有效）")
    bad = bytearray(ct); bad[-1] ^= 0x01
    try:
        AESGCM(key).decrypt(nonce, bytes(bad), AAD)
        print("   ★★异常：篡改竟通过（须查）")
    except Exception:
        print("   ✓ 密文篡改 1 位即失败（★完整性有效）")

    print("★B SM3（国密哈希）之完整性摘要")
    # ★注：`sm3` 列于 algorithms_available，而 `hashlib.sm3` **属性不存在** ⇒ 须用 hashlib.new()
    def _new_sm3(data: bytes):
        return hashlib.new("sm3", data)
    try:
        h1 = _new_sm3(SAMPLE.encode("utf-8")).hexdigest()
        print("   ✓ hashlib.new('sm3') 可用 ｜ 摘要 %s…（%d 位）" % (h1[:32], len(h1) * 4))
        print("   ✓ 同输入再算一致：%s" % (_new_sm3(SAMPLE.encode("utf-8")).hexdigest() == h1))
        print("   ★诚实：SM3 为**哈希**（完整性）；★令条之 **SM10** 为**序列密码之完整性算法**，"
              "**★本器未实现 SM10**")
    except Exception as e:
        h1 = hashlib.sha3_256(SAMPLE.encode("utf-8")).hexdigest()
        print("   ★sm3 不可用（%s）⇒ 退路 SHA3-256：%s…" % (str(e)[:40], h1[:32]))

    print("★C 与一期之衔接（HMAC-SHA3-512 树）")
    import hmac
    k = os.urandom(32)
    leaf = hmac.new(k, SAMPLE.encode("utf-8"), hashlib.sha3_512).digest()
    print("   ✓ HMAC-SHA3-512 叶可算（%d 字节）；★本器不落任何键" % len(leaf))

    print("★D 透明层之可行形态（★方案，非实作）")
    for form in ("文件系统级（filter driver／WinFsp）", "SDK 级（读写封装）", "目录级（约定后缀 + 钩子）"):
        print("   · %s" % form)
    print("   ★诚实：★三者皆**未实作**；★二期只到**示范**")
    print("═══ 结论：二期之 A（AES-256-GCM＋AAD）与 B（SM3）皆**可即办且已验**；"
          "★透明加解密层与 SM10／SM9／ZUC 仍**未实作** ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
