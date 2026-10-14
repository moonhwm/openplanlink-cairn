# -*- coding: utf-8 -*-
"""pqc_attest.py —— 台账之 HMAC-SHA3-512 树证明（PQC 方案一期②）（2026-10-14 立）

依据：《后量子加密与国密体系实施方案》PQC-20261014-CAIRN-01 一期
      —— 「审计链由 SHA-256＋prev 升级为 **HMAC-SHA3-512 树**」。

★设计：
    ★1 叶：每行台账（原始字节）之 **HMAC-SHA3-512(key, line)**；
    ★2 干：相邻叶两两 **HMAC-SHA3-512(key, L‖R)** 直至唯一根（奇数则末叶上提）；
    ★3 输出：`ops/ledger_hmac_tree_<YYYYmmdd_HHMM>.json`（root／叶数／键标识／算法）；
    ★4 **键不入件**（只记 key_id 与首 8 位指纹）—— 承「凭据零回显、零落盘」；
    ★5 `verify` 模式：重算并与最近之证明比对（**结构在否**之判据）。

★诚实：★本器所证为**台账字节之完整性**，**非**台账内容之真实性；★且键仍为**对称 HMAC**
      （**非** SM9／格基之**非对称后量子签名**）⇒ ★仅**量子抗性之哈希层**，★不得称"已完成后量子化"。

用法：
    python pqc_attest.py            # 生成证明
    python pqc_attest.py verify     # 复核（重算 root 与最近之证明比对）
"""
import base64, hashlib, hmac, json, pathlib, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HOME = pathlib.Path.home()
SEAT = (HOME / "WPS Cloud" / "WPSDrive" / "29969771" / "WPS云盘" / "月之暗面的Plasma游乐场"
        / "A2A新席_石敢当Cairn_20260928")
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
OPS = SEAT / "ops"
KEYBIN = HOME / ".a2a-hmac-key.bin"


def h(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha3_512).digest()


def tree_root(key: bytes, leaves):
    lvl = list(leaves)
    while len(lvl) > 1:
        nxt = []
        for i in range(0, len(lvl), 2):
            if i + 1 < len(lvl):
                nxt.append(h(key, b"L" + lvl[i] + b"R" + lvl[i + 1]))
            else:
                nxt.append(lvl[i])
        lvl = nxt
    return lvl[0] if lvl else h(key, b"EMPTY")


def build(key: bytes):
    lines = [ln.encode("utf-8") for ln in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    leaves = [h(key, ln) for ln in lines]
    root = tree_root(key, leaves)
    return lines, leaves, root


def key_info():
    kb = KEYBIN.read_bytes()
    fp = hashlib.sha256(kb).hexdigest()[:16]
    st = KEYBIN.stat()
    return kb, fp, st.st_size, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))


def main() -> int:
    if not KEYBIN.exists():
        print("   ★键不在：%s" % KEYBIN); return 2
    kb, kfp, ksz, kmt = key_info()
    print("   ① 熵源补证（PQC 一期①）")
    print("      键件 %s ｜ 字节 %d ｜ 指纹(sha256 前16) %s ｜ 生成/改时间 %s" % (KEYBIN.name, ksz, kfp, kmt))
    print("      ★诚实：★其**来源与生成方式**本席**无记录**（★须补记，见下）；★键值不入件、不回显")
    lines, leaves, root = build(kb)
    rh = root.hex()
    print("   ② HMAC-SHA3-512 树（PQC 一期②）")
    print("      台账 %d 行 ⇒ 叶 %d ｜ ★根 %s" % (len(lines), len(leaves), rh[:32] + "…"))

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        cands = sorted(OPS.glob("ledger_hmac_tree_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            print("   ★无既有证明可比（如实报）"); return 3
        j = json.loads(cands[0].read_text(encoding="utf-8"))
        same = (j.get("root") == rh)
        print("   ③ 复核（对 %s）" % cands[0].name)
        print("      证明之 root %s… ｜ 叶数 %s" % (str(j.get("root"))[:32], j.get("leaves")))
        print("      重算之 root %s…" % rh[:32])
        print("      ⇒ %s" % ("★一致（台账字节未变）" if same else "★★不一致（台账已变或键已换）"))
        return 0 if same else 4

    OPS.mkdir(parents=True, exist_ok=True)
    out = OPS / ("ledger_hmac_tree_%s.json" % time.strftime("%Y%m%d_%H%M"))
    rec = {
        "schema": "opl-ledger-hmac-tree/1",
        "algo": "HMAC-SHA3-512（叶=行字节；干=HMAC(key, 'L'||L||'R'||R)）",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ledger": "ledger/frontier_ledger.jsonl",
        "lines": len(lines), "leaves": len(leaves),
        "root": rh,
        "key_id": "opl-a2a-2026q4",
        "key_fp_sha256_16": kfp,
        "key_bytes": ksz,
        "honesty": [
            "★所证为台账字节之完整性，非内容之真实性",
            "★键为对称 HMAC，非 SM9／格基之非对称后量子签名 ⇒ 仅量子抗性之哈希层",
            "★键之来源与生成方式尚无记录（PQC 一期①待补记）",
        ],
    }
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print("   ③ 证明已出：%s（%d B）" % (out.name, out.stat().st_size))
    print("      ★键值不入件；仅记 key_id 与指纹前 16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
