#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在临时目录里造一条【伪造但自洽】的链；不触网、不碰真实台账。
r"""forge_demo.py —— 证明「PASS ≠ 真」：一条【完全伪造】的链，能否骗过本席的 verify？ v1.0.0

为什么做它
────────────
本席一切结论都挂在一条哈希链上；而该链的 verify 只核三件事：
  ① 自哈希相符  ② 前向指针不断  ③ signed 是否为 False
★ 而链上每条 entry 自己就写着「未签发席位密钥；本链只证一致，不证作者（哈希链≠签名）」。
⇒ 故可推知：【任何被一致地生成的链都会 PASS】。本器把这个推论【做出来】，看它是否成立。

★ 本器【绝不碰真实台账】：它在临时目录里造一个【席位形状】的迷你目录，
   把真实的 `cairn_ledger.py` 复制进去，再写一条【伪造】的链，然后跑真实的 verify。

若 verify 报 PASS ⇒ ★ 结论成立：PASS 只证【自洽】，不证【真】。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LEDGER_PY = SEAT / "ledger" / "cairn_ledger.py"
ZERO = "0" * 64


def canon(core: dict) -> bytes:
    return json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def entry_hash(core: dict) -> str:
    return hashlib.sha256(canon(core)).hexdigest()


def forge(n: int, claim: str) -> list[dict]:
    """造一条【自洽的伪造链】——一个本席从未做过的事。"""
    rows, prev = [], ZERO
    for i in range(n):
        core = {
            "ts": "2026-10-02T00:00:%02d+08:00" % i,
            "seat": "cairn-dsh",
            "instance": "forged",
            "ev_type": "CLAIM",
            "subject": "%s（第 %d 条）" % (claim, i + 1),
            "detail": "★ 这一条【完全是伪造的】：本席从未做过此事。",
            "evidence": "（伪造）",
            "prev": prev,
            "signed": False,
            "sig": None,
            "sig_note": "未签发席位密钥；本链只证一致，不证作者（哈希链≠签名）",
        }
        core["hash"] = entry_hash(core)
        rows.append(core)
        prev = core["hash"]
    return rows


def main() -> int:
    print("═══ 伪造链对照（只在临时目录）═══")
    if not LEDGER_PY.is_file():
        print("ERR 找不到真实器：%s ⇒ ★ 器具故障" % LEDGER_PY)
        return 2

    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td) / "seat"
        # ★ 2026-10-03 轮 65 加：**可复用断言**（承轮 64 的边界）。
        #   缘由：本器声明「只在临时目录里造链」，★ 而此前【没有一行核过它】。
        #   ⇒ 一行装上（见 exp\tempguard.py）；不成立即抛 OutsideSeat、拒绝继续。
        try:
            from tempguard import assert_outside_seat
        except ImportError:
            import sys as _sys
            _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
            from tempguard import assert_outside_seat
        assert_outside_seat(lab, SEAT)
        (lab / "ledger").mkdir(parents=True)
        shutil.copy2(LEDGER_PY, lab / "ledger" / "cairn_ledger.py")

        claim = "★ 本条宣称：本席已于 2026-10-02 完成对外推送并取得回执"
        rows = forge(3, claim)
        chain = lab / "ledger" / "frontier_ledger.jsonl"
        chain.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n",
                         encoding="utf-8")
        print("  伪造链已写入临时目录：%d 条" % len(rows))
        print("  伪造的宣称 = %s" % claim)
        print("  链末 hash = %s…" % rows[-1]["hash"][:32])
        print("  ★ 注意：这条链由【一个没有本席密钥的人】（其实是我自己随手）生成。")

        r = subprocess.run([sys.executable, str(lab / "ledger" / "cairn_ledger.py"), "verify"],
                           capture_output=True, text=True, encoding="utf-8", cwd=str(lab))
        out = (r.stdout or "") + (r.stderr or "")
        print("\n  ── 真实 verify 器对这条【伪造链】的判词 ──")
        for line in out.splitlines():
            if any(k in line for k in ("条目数", "链末", "结论", "签名状态")):
                print("     " + line.strip())
        passed = "结论：PASS" in out

    print()
    if passed:
        print("  ⇒ ★★ 结论成立：verify 对【完全伪造的链】报 PASS。")
        print("     ⇒ 故 PASS 只证【自洽】，不证【作者】，也不证【内容为真】。")
        print("  ⇒ ★ 由此可判：一个【外部见证】（把链末记在本席控制不到的地方）会带来【新的可检出差异】——")
        print("     有它，则【整链一致改写】可被检出；没有它，则不可。")
        print("  ⇒ ★★ 故本席上一轮立的【停规】「下一层不再提供新差异时就停」——【被本器证伪】：第六层提供。")
        # ★ 2026-10-03 轮 76 加：机器可读判词行（★ 承轮 72–75：本器在配方里、每轮被收尾块跑）。
        print("★ VERDICT=PASS")
        return 0
    print("  ⇒ ★ verify 对伪造链报 FAIL ⇒ 则本席链的强度【高于】我此前的判断，须改写结论。")
    # ★ 轮 76：另一条返回路也要印。
    print("★ VERDICT=BAD")
    return 1


if __name__ == "__main__":
    sys.exit(main())
