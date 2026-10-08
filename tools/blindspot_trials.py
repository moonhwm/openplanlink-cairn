#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在临时目录做试验；不触网、不改动真实席位与真实台账。
r"""blindspot_trials.py —— 把【强度表里那七条盲点】逐条【展出来】。 v1.0.0

为什么做它
────────────
轮 12 我出了一张「各条强度与其盲点」表。★ 而那七条盲点【是我声称的】。
⇒ 按本席轮 5–12 的教训：凡我对自己东西的声明，都要【拿去测】，不能只写。
⇒ ★ 展不出来的"盲点"，本身就是装饰。

三项新展出（其余已展过，本器给出指针）
────────────────────────────────────────
  T1 ①「只证路径可达，不证该路径就是应然的正本」
     ⇒ 做法：把声明的 canonical 指向【另一处确实存在的目录】⇒ 看 ① 是否照样绿。
  T6 ⑥「再追加一条新钉即可消掉它」
     ⇒ 做法：在【临时台账】里，先改核验器副本、再【追加一条新 LOCKPIN】⇒ 看 ⑥ 是否转绿。
  T7 ⑦「只核类别是否被写明，不核判得对不对」
     ⇒ 做法：把一条【其实是"选择"的限制】标成"给定"⇒ 看 ⑦ 是否照样绿。

已展过（引用，不重做）
────────────────────────
  T2 ② 「不证链此后未被整体重建」⇒ exp\forge_demo.py（伪造链令 verify 报 PASS）
  T5 ⑤ 「双点篡改下照样绿」      ⇒ exp\neg_control_seat_location.py 对照五（⑤绿而⑥红）
  T4 ④ 「只核环是否被写明」      ⇒ 同上 对照三（摘掉 self_reference ⇒ 红）
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
DECL = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
CHK = SEAT / "exp" / "verify_seat_location.py"


def run(chk: pathlib.Path, decl: pathlib.Path, cwd: pathlib.Path):
    r = subprocess.run([sys.executable, str(chk), str(decl)],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def clause_green(out: str, mark: str) -> bool:
    for line in out.splitlines():
        if mark in line and "✅" in line:
            return True
    return False


def main() -> int:
    # ★ 轮 43：原表头为「═══ 盲点展出（全在临时目录）═══」——★ 那句「全在临时目录」是不准确的
    #   （T1 会读一处领地外的真实目录）⇒ 已改为下面那两行（临时目录 ＋ 只读真实路径），
    #   ★ 且【不再保留旧句】：让旧声明留在旁边，等于没改。
    if not DECL.is_file() or not CHK.is_file():
        print("ERR 缺声明或核验器 ⇒ ★ 器具故障")
        return 2
    results = []

    with tempfile.TemporaryDirectory() as td:
        lab = pathlib.Path(td)
        # ★ 2026-10-02 轮 43 补：把【读 vs 写】分开，并加断言。
        #   缘由：本器头注写「只在临时目录里造正/负例」，★ 而 T1 会【读】一处真实目录
        #     （SEAT.parent / "_石敢当席"）——★ 读是无害的，但声明若不分开说，
        #     读者会以为本器连读都没读真实目录。
        #   ⇒ 故此处：① 断言【工作目录不在本席领地内】；② 打印【本次会读到的真实路径清单】。
        lab_r, seat_r = lab.resolve(), SEAT.resolve()
        inside = (seat_r == lab_r) or (seat_r in lab_r.parents)
        print("═══ 盲点展出（临时目录 ＋ 只读真实路径）═══")
        print("  ★ 工作目录 = %s" % lab_r)
        print("  ★ 本席领地 = %s" % seat_r)
        print("  ★ 断言：工作目录不在领地内 ⇒ %s" % ("✅ 成立" if not inside else "★★ 不成立！"))
        if inside:
            print("  ★★ 断言失败 ⇒ 拒绝继续")
            return 2
        print("  ── ★ 本次【会读到】的真实路径（★ 只读，绝不写）──")
        for p in (SEAT / "exp" / "verify_seat_location.py",
                  SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json",
                  SEAT.parent / "_石敢当席"):
            print("     [只读] %s" % p)
        print("  ── ★ 本次【会写到】的路径 ⇒ 全部在临时目录内 ──")
        print("     [仅写] %s" % lab_r)

        # 复制核验器（声明仍指向真席位，但 ① 的试验要另造声明）
        chk = lab / "chk.py"
        shutil.copy2(CHK, chk)

        # ── T1：把 canonical 指向【另一处确实存在的目录】──
        print("\n  ── T1 · 展出 ① 的盲点：把 canonical 指向另一处【存在的】目录 ──")
        d1 = json.loads(DECL.read_text(encoding="utf-8"))
        other = SEAT.parent / "_石敢当席"          # 另一处真实存在的目录
        if other.is_dir():
            d1["canonical"]["path"] = str(other)
            (lab / "decl_other.json").write_text(json.dumps(d1, ensure_ascii=False), encoding="utf-8")
            rc, out = run(chk, lab / "decl_other.json", lab)
            g = clause_green(out, "①")
            print("     canonical 指向 = %s" % other.name)
            print("     ★ ① 仍然绿 = %s ⇒ 盲点【展出来了】：① 只证路径可达" % g)
            results.append(("T1 ① 指错正本仍绿", g))
        else:
            print("     （另一处目录不存在，跳过）")
            results.append(("T1 ① 指错正本仍绿", None))

        # ── T7：把一条【其实是"选择"】的限制标成"给定" ──
        print("\n  ── T7 · 展出 ⑦ 的盲点：把【其实是选择】的限制标成「给定」──")
        d7 = json.loads(DECL.read_text(encoding="utf-8"))
        for it in d7["limit_taxonomy"]["items"]:
            if "signed=false" in it.get("limit", ""):
                it["class"] = "给定"            # ★ 故意标错
        (lab / "decl_mislabel.json").write_text(json.dumps(d7, ensure_ascii=False), encoding="utf-8")
        rc, out = run(chk, lab / "decl_mislabel.json", lab)
        g = clause_green(out, "⑦")
        print("     把『signed=false』由【选择】改标为【给定】")
        print("     ★ ⑦ 仍然绿 = %s ⇒ 盲点【展出来了】：⑦ 只核『类别是否被写明』" % g)
        results.append(("T7 ⑦ 标签写错仍绿", g))

        # ── T6：改器 + 【追加一条新钉】⇒ ⑥ 是否转绿 ──
        print("\n  ── T6 · 展出 ⑥ 的盲点：改器 + 【追加一条新 LOCKPIN】⇒ ⑥ 是否转绿 ──")
        labseat = lab / "seat"
        (labseat / "ledger").mkdir(parents=True)
        (labseat / "outbox").mkdir(parents=True)
        (labseat / "exp").mkdir(parents=True)
        # 改器：加一行注释（哈希必变）
        tampered = CHK.read_text(encoding="utf-8") + "\n# (T6：改器一行)\n"
        chk2 = labseat / "exp" / "chk2.py"
        chk2.write_text(tampered, encoding="utf-8")
        new_h = hashlib.sha256(chk2.read_bytes()).hexdigest()
        # 造临时台账：先放一条【旧钉】，再【追加一条新钉】＝新值
        def ent(h):
            core = {"ts": "2026-10-02T22:00:00+08:00", "seat": "cairn-dsh", "instance": "lab",
                    "ev_type": "LOCKPIN", "subject": "★链上钉 · sha256 ＝ " + h,
                    "detail": "（T6 试验）", "evidence": "（试验）", "prev": "0" * 64,
                    "signed": False, "sig": None, "sig_note": "未签发"}
            core["hash"] = hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True,
                                                     separators=(",", ":")).encode()).hexdigest()
            return core
        old_h = hashlib.sha256(CHK.read_bytes()).hexdigest()
        ledger_rows = [ent(old_h), ent(new_h)]          # ★ 旧钉在前、新钉在后
        (labseat / "ledger" / "frontier_ledger.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in ledger_rows) + "\n",
            encoding="utf-8")
        # 声明：canonical 指向 labseat；副本指向真实副本（存在）；钉指向新哈希
        d6 = json.loads(DECL.read_text(encoding="utf-8"))
        d6["canonical"]["path"] = str(labseat)
        d6["verifier_pin"]["sha256"] = new_h
        d6["ledger"]["path"] = "ledger/frontier_ledger.jsonl"
        d6["ledger"]["entries_at_declaration"] = 2
        d6["ledger"]["chain_head_at_declaration"] = ledger_rows[1]["hash"]
        (labseat / "decl6.json").write_text(json.dumps(d6, ensure_ascii=False), encoding="utf-8")
        rc, out = run(chk2, labseat / "decl6.json", labseat)
        g = clause_green(out, "⑥")
        for line in out.splitlines():
            if "⑥" in line:
                print("     " + line.strip()[:96])
        print("     ⇒ ★ ⑥ 在【改器并追加新钉】后仍然绿 = %s ⇒ 盲点【展出来了】：改器后可追加新钉消掉它" % g)
        results.append(("T6 ⑥ 追加新钉即绿", g))

        # ── 已展过的：只引用 ──
        print("\n  ── 已展过（本器不重做，只给指针）──")
        print("     T2 ② 不证链未被整体重建   ⇒ exp\\forge_demo.py（伪造链令 verify 报 PASS）")
        print("     T5 ⑤ 双点篡改下照样绿     ⇒ exp\\neg_control_seat_location.py 对照五")
        print("     T4 ④ 只核环是否被写明     ⇒ 同上 对照三（摘掉 self_reference ⇒ 红）")

    print("\n  ═══ 汇总 ═══")
    shown = [n for n, g in results if g is True]
    unshown = [n for n, g in results if g is not True]
    for n, g in results:
        print("     %-24s %s" % (n, "★ 已展出" if g is True else "★ 未能展出"))
    print("     ⇒ ★ 本轮新展出 %d 条；未能展出 %d 条" % (len(shown), len(unshown)))
    print("     ★ 本器局限：只展【能构造出来的】盲点；构造不出的不等于不存在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
