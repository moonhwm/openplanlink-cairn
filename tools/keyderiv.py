# -*- coding: utf-8 -*-
"""keyderiv.py —— **分层密钥派生（HKDF-SHA3-512）＋ 密钥版本管理 ＋ 操作留痕**
（承令条后量子加密段：「架构上实行分层密钥派生与动态轮换」「健全密钥版本管理」
  「完整记录加解密操作，形成可追溯、可审计闭环」）

## 实现范围（**如实划界**）
本器用 **stdlib** 实现：
  1. **HKDF-SHA3-512**（RFC 5869 结构，哈希替换为 SHA3-512）——**extract + expand**；
  2. **分层派生**：主密钥 → **层-热／层-温／层-冷** 子密钥，及各**用途键**（`audit-sign`／`pack-mac`／`index-mac`）；
  3. **密钥版本管理**：`ops/key_registry.json` **只存** 键 ID／层级／用途／派生路径／**指纹（sha256 前16）**／版本／状态／轮换记录
     —— **绝不落任何密钥材料**；
  4. **动态轮换**：`rotate --tier X --purpose Y` 生成新版本、旧版置 `retired`、记轮换时点与原因；
  5. **加解密操作留痕**：`ops/key_ops.jsonl` **带 prev 哈希链**（append-only，篡改可检）。

**未实现（须外部库或主权人指定路径）**：AES-256-GCM、IBC、国密 SM9／SM10·ZUC、量子随机数、ABE、HSM 托管、透明加解密。
⇒ 本器**不声称**具备上述能力。

## 主密钥来源（**纪律**）
  - `--mode SELFTEST`：**临时生成**主密钥（**仅内存**，不落盘），用于自检与演示；
  - `--mode ENV`：从环境变量名读取（**只记变量名，不记值**）；**取值失败即"未测"**，不得以 SELFTEST 冒充。
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SEAT = os.path.abspath(SEAT)
REG = os.path.join(SEAT, "ops", "key_registry.json")
OPS = os.path.join(SEAT, "ops", "key_ops.jsonl")
ENV_NAME = "OPL_MASTER_KEY_B64"          # **变量名**（值不录）

TIERS = ["层-热", "层-温", "层-冷"]
PURPOSES = ["audit-sign", "pack-mac", "index-mac"]


def hkdf_sha3_512(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """RFC 5869 HKDF，哈希＝SHA3-512（输出长度上限 64*255）。"""
    if length > 64 * 255:
        raise ValueError("length too large")
    prk = hmac.new(salt, ikm, hashlib.sha3_512).digest()          # extract
    okm, t, i = b"", b"", 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha3_512).digest()   # expand
        okm += t
        i += 1
    return okm[:length]


def fp(key: bytes) -> str:
    """密钥**指纹**（可公开）：sha256 前 16 hex。**不可由指纹还原密钥**。"""
    return hashlib.sha256(key).hexdigest()[:16]


def master(mode):
    if mode == "SELFTEST":
        return secrets.token_bytes(32), "SELFTEST(临时，仅内存，未落盘)"
    v = os.environ.get(ENV_NAME)
    if not v:
        return None, "未测（环境变量 %s 未提供；**不以 SELFTEST 冒充**）" % ENV_NAME
    try:
        import base64
        return base64.b64decode(v), "ENV(%s；**值不录**)" % ENV_NAME
    except Exception:  # noqa: BLE001
        return None, "未测（环境变量存在但解码失败）"


def derive(mk, tier, purpose, version=1):
    info = ("opl/v1|%s|%s|v%d" % (tier, purpose, version)).encode("utf-8")
    salt = ("opl-salt|%s" % tier).encode("utf-8")
    return hkdf_sha3_512(mk, salt, info, 32)


def load_reg():
    if os.path.exists(REG):
        try:
            return json.load(open(REG, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"schema": "opl-keyregistry/1", "rows": [], "note": "**只存元数据与指纹，绝不存密钥材料**"}


def save_reg(r):
    os.makedirs(os.path.dirname(REG), exist_ok=True)
    with open(REG, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)


def ops_log(rec):
    """操作留痕：带 prev 哈希链（append-only）。"""
    prev = ""
    if os.path.exists(OPS):
        try:
            lines = [x for x in open(OPS, encoding="utf-8").read().splitlines() if x.strip()]
            if lines:
                prev = hashlib.sha256(lines[-1].encode()).hexdigest()[:16]
        except Exception:  # noqa: BLE001
            prev = "未测"
    rec = dict(rec); rec["ts"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"); rec["prev"] = prev
    line = json.dumps(rec, ensure_ascii=False)
    os.makedirs(os.path.dirname(OPS), exist_ok=True)
    with open(OPS, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return hashlib.sha256(line.encode()).hexdigest()[:16]


def selftest():
    mk = secrets.token_bytes(32)
    ok = []
    a = derive(mk, "层-热", "audit-sign", 1)
    b = derive(mk, "层-热", "audit-sign", 1)
    ok.append(("确定性（同输入同输出）", a == b))
    ok.append(("长度 32B", len(a) == 32))
    ok.append(("跨层独立", a != derive(mk, "层-温", "audit-sign", 1)))
    ok.append(("跨用途独立", a != derive(mk, "层-热", "pack-mac", 1)))
    ok.append(("跨版本独立", a != derive(mk, "层-热", "audit-sign", 2)))
    ok.append(("换主密钥即换输出", a != derive(secrets.token_bytes(32), "层-热", "audit-sign", 1)))
    long = hkdf_sha3_512(mk, b"s", b"i", 4096)
    ok.append(("长输出 4096B", len(long) == 4096))
    ok.append(("指纹可复算且不可还原", fp(a) == hashlib.sha256(a).hexdigest()[:16]
               and fp(a) != fp(derive(mk, "层-热", "audit-sign", 2))))
    bad = False
    try:
        hkdf_sha3_512(mk, b"s", b"i", 64 * 256)
    except ValueError:
        bad = True
    ok.append(("超长输出被拒（RFC 上限）", bad))
    for name, r in ok:
        print("  %-28s %s" % (name, "PASS" if r else "**FAIL**"))
    print("  ⇒ 自检：%d/%d PASS" % (sum(1 for _, r in ok if r), len(ok)))
    return 0 if all(r for _, r in ok) else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    d = sub.add_parser("derive"); d.add_argument("--tier", required=True)
    d.add_argument("--purpose", required=True); d.add_argument("--version", type=int, default=1)
    d.add_argument("--mode", default="SELFTEST")
    r = sub.add_parser("rotate"); r.add_argument("--tier", required=True)
    r.add_argument("--purpose", required=True); r.add_argument("--reason", default="定期轮换")
    r.add_argument("--mode", default="SELFTEST")
    sub.add_parser("status")
    a = ap.parse_args()

    if a.cmd == "selftest":
        return selftest()

    if a.cmd == "status":
        reg = load_reg()
        print("★ 密钥登记（%d 行；**只含元数据与指纹**）" % len(reg["rows"]))
        for row in reg["rows"][-12:]:
            print("  %-8s %-6s %-10s v%-2s %-9s fp=%s" % (row["tier"], row["purpose"], row["id"][:8],
                                                          row["version"], row["status"], row["fp"]))
        print("  登记文件：%s" % REG)
        print("  操作留痕：%s（行数 %d）" % (OPS, sum(1 for _ in open(OPS, encoding="utf-8")) if os.path.exists(OPS) else 0))
        return 0

    mk, src = master(a.mode)
    if mk is None:
        print("★ %s" % src)
        print("  ⇒ **未测**：不得以 SELFTEST 结果冒充真实派生（纪律：未知≠否，亦≠是）")
        return 1
    tier, purpose = a.tier, a.purpose
    reg = load_reg()

    if a.cmd == "derive":
        k = derive(mk, tier, purpose, a.version)
        row = {"id": "kd-%s-%s-v%d" % (tier, purpose, a.version), "tier": tier, "purpose": purpose,
               "version": a.version, "fp": fp(k), "path": "HKDF-SHA3-512(opl/v1|%s|%s|v%d)" % (tier, purpose, a.version),
               "status": "active", "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
               "master_source": src}
        reg["rows"] = [x for x in reg["rows"] if x["id"] != row["id"]] + [row]
        save_reg(reg)
        h = ops_log({"op": "derive", "id": row["id"], "fp": row["fp"], "master_source": src})
        print("★ 派生：%s ｜ 指纹=%s ｜ 主密钥来源=%s" % (row["id"], row["fp"], src))
        print("  （**密钥材料未落盘**；登记仅存指纹与派生路径）")
        print("  留痕哈希=%s" % h)
        return 0

    if a.cmd == "rotate":
        live = [x for x in reg["rows"] if x["tier"] == tier and x["purpose"] == purpose and x["status"] == "active"]
        nv = max([x["version"] for x in live] or [0]) + 1
        for x in live:
            x["status"] = "retired"
            x["retired_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08")
            x["retire_reason"] = a.reason
        k = derive(mk, tier, purpose, nv)
        row = {"id": "kd-%s-%s-v%d" % (tier, purpose, nv), "tier": tier, "purpose": purpose,
               "version": nv, "fp": fp(k), "path": "HKDF-SHA3-512(opl/v1|%s|%s|v%d)" % (tier, purpose, nv),
               "status": "active", "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
               "master_source": src, "rotated_from": [x["id"] for x in live]}
        reg["rows"].append(row)
        save_reg(reg)
        h = ops_log({"op": "rotate", "id": row["id"], "fp": row["fp"], "retired": [x["id"] for x in live],
                     "reason": a.reason, "master_source": src})
        print("★ 轮换：%s → **v%d**（指纹 %s）" % (tier + "/" + purpose, nv, row["fp"]))
        print("  退役 %d 个旧版；**密钥材料未落盘**；留痕哈希=%s" % (len(live), h))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
