#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只读核验器算哈希，写一个 .led；不触网。
r"""emit_lockpin.py —— 现算核验器哈希，写出 LOCKPIN 的 .led（★ 不许凭记忆写签名串）。 v1.0.0

为什么单独一件器
──────────────────
台账条目的 subject 里要放**核验器当前的真实 sha256**。
★ 若手写，就有抄错/抄旧的风险 —— 而本席的规矩是【预期签名必须从真实输出取】。
故：先算，再写，且把「算出来的」与「写进去的」当场回读比对。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
CHK = SEAT / "exp" / "verify_seat_location.py"
LEDGER = SEAT / "ledger" / "frontier_ledger.jsonl"
OUT = SEAT / "exp" / "led_224_lockpin.led"


def chain_head() -> str:
    """★ 轮 99 加：**现取链末**，不再写死。

    缘由（轮 99 实证）：本器原先把"本条目之前的链末"【硬写】成一个常量
      （dd9fddff2d90b71d…）。★ 而它自己的 docstring 写着「不许凭记忆写签名串」——
      ⇒ ★ 同一件器、一条规矩、一处违反：**它凭记忆写了一个链末**。
      ⇒ 故改为【现取】：读台账最后一条的 hash。
    ★ 本器的原意（"先算再写、当场回读比对"）在这一处【也要照办】。
    """
    if not LEDGER.is_file():
        return "（台账不在，无法现取）"
    last = ""
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line
    try:
        return json.loads(last).get("hash", "（末条无 hash）")
    except Exception:
        return "（末条解析失败）"


def main() -> int:
    if not CHK.is_file():
        print("ERR 核验器不在：%s" % CHK)
        return 2
    h = hashlib.sha256(CHK.read_bytes()).hexdigest()
    print("═══ 现算链上钉 ═══")
    print("  核验器 = exp\\%s" % CHK.name)
    print("  sha256 = %s" % h)

    subject = ("★链上钉（LOCKPIN）· 核验器 exp\\verify_seat_location.py 的整file sha256 ＝ "
               + h
               + " ；本条把钉移进【只能追加的链】，用于补【第五环：谁验钉？】")
    detail = (
        "★ 病：声明里的版本钉（核验器第⑤条）与核验器【同出一席】⇒ 同握两把钥匙 ⇒ "
        "合法改器时【同时】更新声明里的钉，两处一致 ⇒ ⑤ 全程绿灯 ⇒ ⑤ 只防【单点】篡改，不防【双点】篡改。"
        "★ 药：把钉移进【只能追加的台账链】⇒ 双点篡改（改器 ＋ 改声明钉）之后，"
        "链上这条旧钉【依然在】⇒ 与现行器哈希不符 ⇒ 核验器第⑥条必红；"
        "要消掉⑥只能【再追加一条新钉】，而那是【看得见的追加】，不是【无声的改写】。"
        "★ 诚实边界：链也是本席写的 ⇒ 这买到的仍是【改动可见】，不是【改动不可能】，更不是【独立】；"
        "真正的破环需要【第二个不同席位独立复算并联署】，本席【没有】。"
    )
    evidence = ("追加时刻核验器实测 sha256 ＝ %s（由 exp\\emit_lockpin.py 现算并回读比对）；"
                "核验器第⑥条逐次比对【链上最新 LOCKPIN】与【现行器哈希】；"
                "本条目之前的链末为 %s（★ 轮 99 起：此值【现取】，不再写死）"
                % (h, chain_head()))

    text = ("ev_type: LOCKPIN\n"
            "subject: %s\n"
            "detail: %s\n"
            "evidence: %s\n"
            "seal_files:\n"
            "  - exp/verify_seat_location.py\n" % (subject, detail, evidence))
    OUT.write_text(text, encoding="utf-8", newline="\n")

    # ★ 回读比对：写进去的哈希 == 现算的哈希
    back = OUT.read_text(encoding="utf-8")
    ok = h in back and "PLACEHOLDER" not in back
    print("  已写 = exp\\%s（%d B）" % (OUT.name, OUT.stat().st_size))
    print("  回读比对：%s" % ("★ 一致（且无占位符）" if ok else "★★ 不一致 —— 停手"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
