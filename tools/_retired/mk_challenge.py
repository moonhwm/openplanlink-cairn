# -*- coding: utf-8 -*-
"""mk_challenge.py —— 本席 challenge 应答端点（`file://` 形态，承 DF-IUR-NODE-…-HY4-01 §2.1）

规范原文：`challenge_ep: "file:///…/a2a/challenge.json"` —— 即 **challenge 是文件端点**，非 HTTP。
本席实现（**最小可核验**，不虚构能力）：
  · 落盘 `a2a/challenge.json`：含 seat_key、issued_at/expires_at、**nonce**（不可预测随机）、
    `answer_rule`（如何作答）、`verify_cmd`（**可复算命令**，承脱敏口径"登记命令而非值"）；
  · 作答方式：对 `nonce` 以本席 **Ed25519 签名密钥** 做 SSHSIG 签名（与宣告签名同一密钥与命名空间），
    验证者用宣告中的 `pubkey_fp` 对应公钥验签；
  · 🔴 **凭据纪律**：私钥**仅被使用、不被读取/回显**；challenge.json 内**不含任何密钥材料**、
    不含主机标识值、不含端口值（值只以"取数命令"指代）；
  · **时效**：nonce 随本件轮换（`--rotate` 重新生成），`expires_at_utc` 缺省 +24h；过期即视作答无效。

用法:
  python mk_challenge.py --out <目录>            # 生成/轮换 challenge.json
  python mk_challenge.py --out <目录> --show     # 同时打印可核验摘要（不含非ce 值以外的敏感信息）
退出码：0。
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import secrets
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEAT_KEY = "cairn-dsh"
SEAT_NAME = "石敢当Cairn"
KEY = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing")
NAMESPACE = "a2a-iurn-announce"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="落点目录（其下建 a2a/）")
    ap.add_argument("--ttl-hours", type=int, default=24)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()

    root = pathlib.Path(a.out) / "a2a"
    root.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    issued = now.strftime("%Y%m%dT%H%M%SZ")
    expires = (now + dt.timedelta(hours=a.ttl_hours)).strftime("%Y%m%dT%H%M%SZ")
    nonce = secrets.token_hex(16)

    doc = {
        "schema": "iurn-node-challenge/v0.1",
        "seat_key": SEAT_KEY,
        "seat_name": SEAT_NAME,
        "issued_at_utc": issued,
        "expires_at_utc": expires,
        "ttl_hours": a.ttl_hours,
        "nonce": nonce,
        "nonce_sha256": "sha256:" + hashlib.sha256(nonce.encode()).hexdigest(),
        "answer_rule": ("以本席 Ed25519 密钥对 nonce 做 SSHSIG 签名："
                        "ssh-keygen -Y sign -n %s -f <本席私钥> <含 nonce 的文件>；"
                        "验证者以宣告中 pubkey_fp 对应公钥验签，且要求签名件含同一 namespace" % NAMESPACE),
        "verify_cmd": [
            "# 记录命令而非值（承脱敏口径）；<nonce> 由本文件 nonce 字段取，<pub> 为宣告 pubkey_fp 对应公钥",
            "printf '%s' '<nonce>' > /tmp/chal.txt",
            "ssh-keygen -Y sign -n %s -f <本席私钥> /tmp/chal.txt" % NAMESPACE,
            "ssh-keygen -Y verify -n %s -f <pub> -I %s -s /tmp/chal.txt.sig < /tmp/chal.txt" % (NAMESPACE, SEAT_KEY),
        ],
        "key_material": "NONE（本文件不含任何公钥/私钥材料；公钥指纹见 announce_%s_*.md）" % SEAT_KEY,
        "value_discipline": "不含主机标识值/端口值；如需定位请用 verify_cmd",
        "rotation_note": "轮换：重跑本脚本（nonce 与 expires 同步更新；旧 nonce 作废）",
    }
    out = root / "challenge.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("★ challenge 端点：%s（%d B）" % (out, out.stat().st_size))
    print("★ seat_key=%s ｜ issued=%s ｜ expires=%s（TTL %dh）" % (SEAT_KEY, issued, expires, a.ttl_hours))
    print("★ nonce_sha256=%s（值本身仅在端点文件内）" % doc["nonce_sha256"])
    print("★ 凭据纪律：无密钥材料、无主机标识值、无端口值")
    if a.show:
        print("★ 可核验摘要：")
        for k in ("schema", "seat_key", "issued_at_utc", "expires_at_utc", "nonce_sha256", "answer_rule"):
            print("   %s: %s" % (k, doc[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
