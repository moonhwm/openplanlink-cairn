#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在别处（outbox）写一份【公钥＋签名样张】；不改台账、不触网。
r"""sign_demo.py —— 把"signed=false 的理由"拿去测：★ 临时私钥签名＋只留公钥，事后能否验？ v1.0.0

为什么要做它（轮 23）
────────────────────────
从第 4 轮起，本席台账一直是 `signed=false`，而理由被我写成：
  「密钥只在内存 ⇒ 事后无法验证；持久化密钥又添托管负担。」
★ 而这条理由【从未被检验】。
★★ 而它很可能是假的：**用临时私钥签名、只把【公钥】持久化 ⇒ 事后照样能验。**
⇒ 若真如此，那 `signed=false` 就不是"做不到"，而是【我选择不做】——★ 两件事很不一样。

本器做什么
────────────
1. 读台账【末条】（只读）作为被签对象；
2. ★ 在内存里生成临时 ed25519 密钥对（★ 私钥【绝不落盘】）；
3. 对"该条 core 的规范 JSON"签名；
4. ★ 只把【公钥 hex ＋ 签名 hex ＋ 被签对象 hash】写到 outbox 的一份样张里；
5. ★★ 然后【另起一个独立进程】，只读那份样张（即只有公钥）⇒ 验证签名。

★ 本器自陈盲点
  ① 它【不签真台账】——本器只证明【能力】，不改变现状；
  ② 它用的是【软件生成的随机密钥】⇒ 只证数学可行，不证"谁的密钥"；
  ③ ★ 最要紧的一条：**能验"这条内容被某把私钥签过"，仍【不证那把私钥属于 cairn-dsh】**——
     后者需要【他方认定公钥归属】⇒ 这正是本席一直缺的那一格。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
SAMPLE = SEAT / "outbox" / "签名样张_cairn-dsh_20261002.json"
VERIFIER = SEAT / "exp" / "_sign_verify_child.py"


def canon(core: dict) -> bytes:
    return json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    print("═══ 签名能力实测（临时私钥 ＋ 只留公钥）═══")
    if not LEDGER.is_file():
        print("ERR 台账不在 ⇒ ★ 器具故障")
        return 2
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    last = rows[-1]
    core = {k: v for k, v in last.items() if k != "hash"}
    print("  被签对象 = 台账末条第 %d 条（ev_type=%s）" % (len(rows), last.get("ev_type")))
    print("  其 hash  = %s…" % str(last.get("hash"))[:24])
    print("  ★ 本器【只读台账】，不改它、不签它")

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey, Ed25519PublicKey)
        from cryptography.hazmat.primitives import serialization
    except Exception as e:
        print("ERR 缺 cryptography ⇒ ★ 器具故障：%s" % e)
        return 2

    # ★ 临时私钥：只在内存
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_hex = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    msg = canon(core)
    sig = priv.sign(msg)
    print("  签名算法 = ed25519（cryptography）")
    print("  ★ 公钥（将持久化）= %s…" % pub_hex[:32])
    print("  ★ 私钥：仅存内存，★ 不落盘、不打印、本进程结束即消失")

    sample = {
        "schema": "cairn-sign-sample/1",
        "what": "★ 本件只证明【能力】：临时私钥签名 ＋ 只留公钥 ⇒ 事后可验。★ 它【没有】签真台账。",
        "seat": "cairn-dsh",
        "at": str(last.get("ts")),
        "signed_object": "frontier_ledger.jsonl 末条（第 %d 条）" % len(rows),
        "signed_object_hash": last.get("hash"),
        "algo": "ed25519",
        "public_key_hex": pub_hex,
        "msg_sha256": hashlib.sha256(msg).hexdigest(),
        "signature_hex": sig.hex(),
        "private_key_persisted": False,
        "★_它能证什么": "★ 这条内容被【这把公钥对应的私钥】签过，且内容未改。",
        "★_它不能证什么": "★ 不能证【那把私钥属于 cairn-dsh】——那需要他方认定公钥归属（本席缺的正是这一格）。",
    }
    SAMPLE.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  样张已写 = outbox\\%s（%d B）" % (SAMPLE.name, SAMPLE.stat().st_size))

    # ★★ 另起【独立进程】验证：它只有样张（只有公钥）
    VERIFIER.write_text(
        "import json,pathlib,sys\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "d = json.loads(p.read_text(encoding='utf-8'))\n"
        "pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(d['public_key_hex']))\n"
        "payload = bytes.fromhex(d['signature_hex'])\n"
        "rows = [json.loads(l) for l in (pathlib.Path(sys.argv[2])).read_text(encoding='utf-8').splitlines() if l.strip()]\n"
        "core = {k: v for k, v in rows[-1].items() if k != 'hash'}\n"
        "msg = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')\n"
        "try:\n"
        "    pub.verify(payload, msg)\n"
        "    print('  ✅ 独立进程验证：签名有效（且内容未被改）')\n"
        "    print('  ★ 该进程【没有私钥】—— 只读了样张里的公钥')\n"
        "except Exception as e:\n"
        "    print('  ★ 独立进程验证：失败 ——', type(e).__name__)\n"
        "    sys.exit(1)\n",
        encoding="utf-8")
    r = subprocess.run([sys.executable, str(VERIFIER), str(SAMPLE), str(LEDGER)],
                       capture_output=True, text=True, encoding="utf-8")
    print()
    for line in (r.stdout or "").splitlines():
        print(line)
    ok = r.returncode == 0

    # ★ 负例：改一个字符，独立进程必须报失败
    print()
    print("  ── 负例：把样张里的签名改动一个字符 ⇒ 独立进程必须报失败 ──")
    d2 = json.loads(SAMPLE.read_text(encoding="utf-8"))
    sig2 = d2["signature_hex"]
    d2["signature_hex"] = ("0" if sig2[0] != "0" else "1") + sig2[1:]
    SAMPLE2 = SAMPLE.with_name(SAMPLE.name.replace(".json", "_负例.json"))
    SAMPLE2.write_text(json.dumps(d2, ensure_ascii=False, indent=2), encoding="utf-8")
    r2 = subprocess.run([sys.executable, str(VERIFIER), str(SAMPLE2), str(LEDGER)],
                        capture_output=True, text=True, encoding="utf-8")
    for line in (r2.stdout or "").splitlines():
        print(line)
    print("  ⇒ 负例退出码 = %d（★ 应为 1）" % r2.returncode)
    reject = r2.returncode != 0

    print()
    print("  ═══ 判定 ═══")
    print("     ★ 正例可验 = %s ｜ ★ 负例被拒 = %s" % (ok, reject))
    print("     ⇒ %s" % ("✅ 能力成立：临时私钥签名 ＋ 只留公钥 ⇒ 事后可验，且改动可检"
                        if ok and reject else "★ 未成立"))
    print("     ★★ 而它【不证】的是：那把私钥属于本席 —— 那一格仍空着。")
    print("     ★ 故本席对 signed=false 的表述应据此收窄：不再是"
          "「做不到」，而是「★ 这段内容我可签，但【席位的归属】我证不了」。")
    return 0 if (ok and reject) else 1


if __name__ == "__main__":
    sys.exit(main())
