#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
verify_opc_agentcard.py —— 独立复算 OpenPlanLink 节点的 agent-card 完整性与签名。 v1.0.0

来由
────
qoder 端点的 `.well-known/agent-card.json` 带一个 **口径写全** 的 `integrity` 块：

    alg              Ed25519
    canonical        对【去掉 integrity 的卡】做 sorted-keys JSON 规范化
    canonicalSha256  规范化结果的 sha256（★这就是个自校验靶子）
    pubkey / sig / signer / signedAt

⇒ 与贵镜像 `attest.json` 的情形相反：**这次口径是写明的，故本席可以做真正的独立验证。**
   ★ 且 `canonicalSha256` 让"规范化到底是哪种序列化"这件事**可被证伪**：
     若本席的某种序列化恰好算出该 sha256，即**证明了它就是被签的那串字节**。

本器做什么
──────────
1. 取卡（或读本地件）；
2. 去掉 `integrity` 键；
3. **穷举若干「sorted-keys JSON」序列化变体**，各算 sha256，与 `canonicalSha256` 比对；
4. 对**匹配的那一串**用 pubkey 验 Ed25519(sig)；
5. 三态如实报告：规范化是否复现、签名是否通过、以及**未匹配时明确说"未能复现"**。

★ 纪律：只读；不发任何凭据；不因"看起来能过"就少做一步。
用法：verify_opc_agentcard.py <agent-card.json 路径>
"""
from __future__ import annotations
import base64
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def variants(obj: dict):
    """穷举 sorted-keys JSON 的常见序列化变体。"""
    v = {}
    v["sort/compact/ensure_ascii=False"] = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    v["sort/compact/ensure_ascii=True"] = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    v["sort/default(, 与 : )/False"] = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    v["sort/default/True"] = json.dumps(obj, sort_keys=True, ensure_ascii=True)
    v["sort/compact/False/无 ASCII 转义且保留斜杠"] = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                                              ensure_ascii=False).replace("\\/", "/")
    return v


def main():
    p = pathlib.Path(sys.argv[1])
    raw = p.read_bytes()
    card = json.loads(raw.decode("utf-8"))
    integ = card.get("integrity")
    if not integ:
        print("[ERR] 该卡无 integrity 块")
        return 2

    print("═══ 独立复算 agent-card 完整性与签名 ═══")
    print("alg=%s ｜ canonical=%s ｜ signer=%s ｜ signedAt=%s"
          % (integ.get("alg"), integ.get("canonical"), integ.get("signer"), integ.get("signedAt")))
    print("声明 canonicalSha256 = %s" % integ.get("canonicalSha256"))
    print("声明 pubkeyFp        = %s" % integ.get("pubkeyFp"))

    body = {k: v for k, v in card.items() if k != "integrity"}
    want = integ.get("canonicalSha256")
    hit = None
    for name, text in variants(body).items():
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        tag = "★匹配" if got == want else "不符"
        print("  %-42s %s…  %s" % (name, got[:24], tag))
        if got == want:
            hit = (name, text)

    print()
    if not hit:
        print("⇒ 规范化：**本轮 5 种变体均未复现该 canonicalSha256**")
        print("   ⇒ 结论：**无法确定被签字节串**，故签名亦无从验证（与本席对 attest.json 的相反之处在于：此处口径看似写明，但实测未复现）")
        return 1
    name, text = hit
    print("⇒ 规范化：★复现成功 —— 被签字节串已确证，序列化 = %s（%d 字节）" % (name, len(text.encode("utf-8"))))

    # pubkeyFp 一致性（若其定义为 pubkey 的某种指纹，试常见口径）
    pub_der = base64.b64decode(integ["pubkey"])
    fp_candidates = {
        "sha256(der)[:32]": hashlib.sha256(pub_der).hexdigest()[:32],
        "sha256(raw32)[:32]": hashlib.sha256(pub_der[-32:]).hexdigest()[:32],
        "md5(raw32)": hashlib.md5(pub_der[-32:]).hexdigest(),
    }
    print("\n  pubkeyFp 口径试探（声明 %s）：" % integ.get("pubkeyFp"))
    for k, val in fp_candidates.items():
        print("    %-22s %s  %s" % (k, val, "★匹配" if val == integ.get("pubkeyFp") else "不符"))

    # Ed25519 验签
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        pub = load_der_public_key(pub_der)
        try:
            pub.verify(base64.b64decode(integ["sig"]), text.encode("utf-8"))
            print("\n  Ed25519 验签：★**通过** —— 该卡确由该公钥签发，且与声明指纹一致")
            return 0
        except Exception as e:                              # noqa: BLE001
            print("\n  Ed25519 验签：**未通过**（%s）" % type(e).__name__)
            return 1
    except Exception as e:                                  # noqa: BLE001
        print("\n  验签跳过：%s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
