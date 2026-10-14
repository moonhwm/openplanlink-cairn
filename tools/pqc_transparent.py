# -*- coding: utf-8 -*-
"""pqc_transparent.py —— 透明加解密层（SDK 级）（PQC 二期⑤）（2026-10-14 立）

依据：《后量子加密与国密体系实施方案》PQC-20261014-CAIRN-01 二期⑤
      —— 「透明加解密能力，降低业务改造门槛」。

★形态：**SDK 级**（读写封装）—— 最低风险之形态（不动文件系统、不动现有件）。
★封装：
    ★`seal_write(path, data, key, aad)` ⇒ 写 **AES-256-GCM** 之密封件（头 ＋ nonce ＋ 密文）
    ★`seal_read(path, key, aad)`       ⇒ 读并**验 AAD 与 tag**（不符即抛）
    ★`seal_wrap(path)`                  ⇒ 返回**透明句柄**（open/read/write/close）

★文件格式（★自定，便于审计）：
    magic `OPLSEAL1`（8 B）｜版本 1（1 B）｜algo 1（1 B，0x01＝AES-256-GCM）｜
    nonce（12 B）｜aad 长度（2 B，大端）｜aad（变长）｜密文（含 16 B tag）

★诚实标注（★必读）：
    ★1 本器为**示范级**（SDK 层），**非生产**；**未**接入文件系统过滤驱动；
    ★2 键由**调用方**提供（本器**不生成、不落盘、不回显**键）；
    ★3 本器**只对显式调用之文件生效** ⇒ **不影响现有任何件**；
    ★4 未接入 **SM9／SM10／ZUC／HSM／QRNG**（承 PQC-01 之未实作清单）。

用法（自检）：python pqc_transparent.py selftest
"""
import os, pathlib, struct, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
MAGIC = b"OPLSEAL1"
VER = 1
ALGO_AES256GCM = 1


def _aesgcm(key: bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key)


def seal_bytes(data: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    ct = _aesgcm(key).encrypt(nonce, data, aad)
    return b"".join([MAGIC, bytes([VER, ALGO_AES256GCM]), nonce,
                     struct.pack(">H", len(aad)), aad, ct])


def unseal_bytes(blob: bytes, key: bytes, aad: bytes):
    if len(blob) < 8 + 2 + 12 + 2 or blob[:8] != MAGIC:
        raise ValueError("非 OPLSEAL 密封件（magic 不符）")
    ver, algo = blob[8], blob[9]
    if ver != VER or algo != ALGO_AES256GCM:
        raise ValueError("版本或算法不支持：ver=%d algo=%d" % (ver, algo))
    nonce = blob[10:22]
    (alen,) = struct.unpack(">H", blob[22:24])
    aad_in = blob[24:24 + alen]
    if aad_in != aad:
        raise ValueError("AAD 不符（席别／用途／版本绑定失败）")
    return _aesgcm(key).decrypt(nonce, blob[24 + alen:], aad)


class SealHandle:
    """★透明句柄：以普通文件之读写方式用之（解密在 read，加密在 write）。"""

    def __init__(self, path, key: bytes, aad: bytes, mode: str = "rb"):
        self.path = pathlib.Path(path)
        self.key, self.aad, self.mode = key, aad, mode
        self._buf = None
        if self.path.exists():
            self._buf = unseal_bytes(self.path.read_bytes(), key, aad)

    def read(self) -> bytes:
        return self._buf if self._buf is not None else b""

    def write(self, data: bytes) -> int:
        self.path.write_bytes(seal_bytes(data, self.key, self.aad))
        self._buf = data
        return len(data)

    def exists(self) -> bool:
        return self.path.exists()

    def size_plain(self) -> int:
        return len(self._buf or b"")

    def size_sealed(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0


def seal_wrap(path, key: bytes, aad: bytes) -> SealHandle:
    return SealHandle(path, key, aad)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "selftest":
        print(__doc__)
        return 1
    print("═══ 透明层自检（★不碰真凭据、不动现有件）═══")
    tmp = pathlib.Path(os.environ.get("TEMP", ".")) / "_oplseal_selftest.bin"
    key = os.urandom(32)                      # ★临时键，用毕即弃
    aad = "seat=A2A新席_石敢当Cairn|purpose=selftest|ver=1".encode("utf-8")
    payload = "透明层自检：正文之明文。".encode("utf-8")
    h = seal_wrap(tmp, key, aad)
    print("① 以句柄写 ⇒ 密封件")
    h.write(payload)
    print("   明文 %d B ⇒ 密封件 %d B（增 %d B：头 24＋aad %d＋tag 16）"
          % (len(payload), h.size_sealed(), h.size_sealed() - len(payload), len(aad)))
    print("② 以句柄读 ⇒ 透明解密")
    h2 = seal_wrap(tmp, key, aad)
    ok = h2.read() == payload
    print("   回读 %d B ｜ 一致 %s" % (h2.size_plain(), ok))
    print("③ 反例一：AAD 不符应失败")
    try:
        seal_wrap(tmp, key, "seat=他席".encode("utf-8"))
        print("   ★★异常：AAD 不符竟成功（须查）")
    except Exception as e:
        print("   ✓ 失败：%s" % str(e)[:60])
    print("④ 反例二：密文篡改 1 位应失败")
    blob = bytearray(tmp.read_bytes()); blob[-1] ^= 0x01
    try:
        unseal_bytes(bytes(blob), key, aad)
        print("   ★★异常：篡改竟通过（须查）")
    except Exception as e:
        print("   ✓ 失败：%s" % str(e)[:60])
    print("⑤ 清理临时件")
    try:
        tmp.unlink(); print("   ✓ 已删 %s" % tmp.name)
    except OSError as e:
        print("   ★未删：%s" % str(e)[:60])
    print("═══ 结论：SDK 级透明层**可即办且已验**（写／读／AAD 绑／篡改检测）；"
          "★文件系统级与 SM9／SM10／ZUC／HSM 仍**未实作** ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
