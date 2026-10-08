#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 只在临时目录里造正/负例；不触网、不碰任何席位的真实件。
r"""neg_control_seat_location.py —— 用【合成样本】证明 verify_seat_location.py 会红也会绿。 v1.0.0

为什么必须做
──────────────
我修了"活文件分叉"的判据之后，**原来那个负例因为选错文件被跳过** ⇒
**"不会失败的检查，等于没有检查"** ⇒ 必须补一个【必然触发】的负例。

★ 且**不去改守藏席的副本**（那是别席的产出）⇒ 在临时目录里合成一对 A/B：
   正例：A、B 逐字节相同（外加一个活文件差异）⇒ 期望 OK
   负例：A、B 有一个【预期外】的非活文件差异 ⇒ 期望 BAD
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = SEAT / "exp" / "verify_seat_location.py"


def build(tmp: pathlib.Path, surprise: bool):
    """造 A/B 一对；surprise=True 时制造一个【预期外】差异。"""
    a = tmp / "A"
    b = tmp / "B"
    for d in (a, b):
        (d / "ledger").mkdir(parents=True, exist_ok=True)
        (d / "outbox").mkdir(parents=True, exist_ok=True)
        (d / "exp").mkdir(parents=True, exist_ok=True)
    # 冻结件：两处相同
    for d in (a, b):
        (d / "exp" / "tool.py").write_text("print(1)\n", encoding="utf-8")
        (d / "outbox" / "state_x.json").write_text('{"n":1}\n', encoding="utf-8")
    # 活文件：两处【故意不同】（台账，预期分叉）
    (a / "ledger" / "frontier_ledger.jsonl").write_text('{"hash":"AAA"}\n{"hash":"BBB"}\n', encoding="utf-8")
    (b / "ledger" / "frontier_ledger.jsonl").write_text('{"hash":"AAA"}\n', encoding="utf-8")
    # 预期外差异：非活文件
    (a / "exp" / "tool.py").write_text("print(2)\n" if surprise else "print(1)\n", encoding="utf-8")
    decl = {
        "schema": "a2a/seat-location/1", "seat_id": "neg-control",
        "canonical": {"path": str(a), "role": "正本"},
        "replicas": [{"path": str(b), "role": "副本",
                      "verified": {"shared_files": 3, "byte_identical": 2,
                                   "byte_differing": 1, "only_in_canonical": 0, "only_in_replica": 0}}],
        "ledger": {"path": "ledger/frontier_ledger.jsonl", "entries_at_declaration": 1,
                   "chain_head_at_declaration": "AAA", "signed": False},
        # ★ 合成样本也须含自指段（否则 ④ 会把"正例"判红——那正是对照一 首跑不符期望的原因）
        "self_reference": {
            "why_this_section_exists": "合成样本：用于证明核验器会红也会绿。",
            "loops": {
                "R1": {"status": "★ 成立（合成）"},
                "R2": {"status": "★ 成立（合成）"},
                "R3": {"status": "★ 成立（合成）"},
            },
        },
        # ★ 合成样本【不钉】verifier_pin ⇒ ⑤ 应报「未检（整条未执行）」而非失败 —— 这正是要验的
    }
    p = tmp / ("decl_surprise.json" if surprise else "decl_ok.json")
    p.write_text(json.dumps(decl, ensure_ascii=False), encoding="utf-8")
    return p


def run(p: pathlib.Path):
    r = subprocess.run([sys.executable, str(CHECKER), str(p)], capture_output=True, text=True, encoding="utf-8")
    verdict = "OK" if "判词：OK" in (r.stdout or "") else ("BAD" if "判词：BAD" in (r.stdout or "") else "ERR")
    return r.returncode, verdict, (r.stdout or "")


def main() -> int:
    print("═══ 合成负例对照（不碰任何席位的真实件）═══")
    results = []
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        # ★ 2026-10-02 轮 42 加：**给这句声明加一条断言，并打印实据**。
        #   缘由：本器第 3 行 BLAST 头与上一行输出都写着「不碰任何席位的真实件」，
        #   ★ 而此前【没有任何一行检查过它】——★ 声明无凭据。
        #   ⇒ 故此处当场断言：工作目录【不在本席领地内】，并把两者都打出来。
        tmp_r = tmp.resolve()
        seat_r = SEAT.resolve()
        inside = (seat_r == tmp_r) or (seat_r in tmp_r.parents)
        print("  ★ 工作目录 = %s" % tmp_r)
        print("  ★ 本席领地 = %s" % seat_r)
        print("  ★ 断言：工作目录【不在本席领地内】⇒ %s" % ("✅ 成立" if not inside else "★★ 不成立！"))
        if inside:
            print("  ★★ 断言失败 ⇒ 拒绝继续（否则可能碰真实件）")
            return 2
        # ★ 轮 42 注：此处【不往 results 里塞东西】——results 后面按四元组解包，
        #   我第一版塞了个字符串进去 ⇒ ValueError: too many values to unpack（当场被实跑抓住）。
        rc1, v1, out1 = run(build(tmp, surprise=False))
        print("\n  ── 对照一 · 正例（只有活文件分叉）⇒ 期望 OK ──")
        for line in out1.splitlines():
            if any(k in line for k in ("③", "④", "判词", "核过")):
                print("     " + line.strip())
        print("     实测：判词 %s ／ 退出码 %d" % (v1, rc1))
        results.append(("对照一 正例", v1 == "OK" and rc1 == 0, v1, rc1))

        rc2, v2, out2 = run(build(tmp, surprise=True))
        print("\n  ── 对照二 · 负例（非活文件差异）⇒ 期望 BAD ──")
        for line in out2.splitlines():
            if any(k in line for k in ("③", "④", "判词", "核过", "预期外")):
                print("     " + line.strip())
        print("     实测：判词 %s ／ 退出码 %d" % (v2, rc2))
        results.append(("对照二 预期外差异", v2 == "BAD" and rc2 == 1, v2, rc2))

    # ★ 对照三：把声明里的 self_reference 段【摘掉】⇒ 期望 BAD
    print("\n  ── 对照三 · 把声明的 self_reference 段摘掉 ⇒ 期望 BAD ──")
    real = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        d = json.loads(real.read_text(encoding="utf-8"))
        d.pop("self_reference", None)
        p = tmp / "decl_no_selfref.json"
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        rc3, v3, out3 = run(p)
        for line in out3.splitlines():
            if any(k in line for k in ("④", "判词", "核过")):
                print("     " + line.strip())
        print("     实测：判词 %s ／ 退出码 %d" % (v3, rc3))
        results.append(("对照三 缺自指段", v3 == "BAD" and rc3 == 1, v3, rc3))

    # ★★ 对照四（最尖）：把核验器【自己源码】里的免责句删掉 ⇒ 期望 BAD
    print("\n  ── 对照四 · 删掉核验器【自己判词】里的免责句 ⇒ 期望 BAD ──")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        src = CHECKER.read_text(encoding="utf-8")
        damaged = src.replace("只证自洽，不证正确", "（已删）")
        assert damaged != src, "★ 免责句没找到 ⇒ 本对照无效，须先修"
        chk2 = tmp / "verify_seat_location_stripped.py"
        chk2.write_text(damaged, encoding="utf-8")
        r = subprocess.run([sys.executable, str(chk2), str(real)],
                           capture_output=True, text=True, encoding="utf-8")
        o = r.stdout or ""
        v4 = "OK" if "判词：OK" in o else ("BAD" if "判词：BAD" in o else "ERR")
        for line in o.splitlines():
            if any(k in line for k in ("④", "判词", "核过")):
                print("     " + line.strip())
        print("     实测：判词 %s ／ 退出码 %d" % (v4, r.returncode))
        results.append(("对照四 删免责句", v4 == "BAD" and r.returncode == 1, v4, r.returncode))

    # ★★ 对照五（第五环 · 判决性）：模拟【双点篡改】——改核验器 ＋ 只改声明里的钉，【不动链】
    #    期望：⑤ 绿（因为声明钉被同步改了）★ 但 ⑥ 必红（因为链上那枚旧钉改不掉）⇒ 判词 BAD。
    #    ⇒ 这一条就是"⑤ 只防单点、⑤+⑥ 才防双点"的判决。
    print("\n  ── 对照五 · 双点篡改（改器＋改声明钉，不动链）⇒ 期望 BAD（⑥ 必红）──")
    real_decl = SEAT / "outbox" / "SEAT_LOCATION_cairn-dsh_20261002.json"
    # 前置：真实声明里必须有钉，否则本对照无意义 ⇒ 报 ERR 而不是假装通过
    try:
        _d0 = json.loads(real_decl.read_text(encoding="utf-8"))
        if "sha256" not in (_d0.get("verifier_pin") or {}):
            print("     ERR 真实声明无 verifier_pin ⇒ ★ 本对照【未执行】（器具前提不足）")
            results.append(("对照五 双点篡改", False, "ERR", -1))
        else:
            with tempfile.TemporaryDirectory() as td:
                tmp = pathlib.Path(td)
                # 改器：加一行注释（哈希必变）
                src = CHECKER.read_text(encoding="utf-8")
                forged = src + "\n# (双点篡改演示：加一行即改哈希)\n"
                fake_chk = tmp / "verify_forged.py"
                fake_chk.write_text(forged, encoding="utf-8")
                fake_h = hashlib.sha256(fake_chk.read_bytes()).hexdigest()
                # 改声明钉：同步成被改器的哈希（模拟"一个人改两处"）
                d2 = json.loads(real_decl.read_text(encoding="utf-8"))
                d2["verifier_pin"]["sha256"] = fake_h
                fake_decl = tmp / "decl_forged.json"
                fake_decl.write_text(json.dumps(d2, ensure_ascii=False), encoding="utf-8")
                # 用【被改的器】跑【被改的声明】——注意它仍会读【真实台账】
                r = subprocess.run([sys.executable, str(fake_chk), str(fake_decl)],
                                   capture_output=True, text=True, encoding="utf-8")
                o = r.stdout or ""
                v5 = "OK" if "判词：OK" in o else ("BAD" if "判词：BAD" in o else "ERR")
                for line in o.splitlines():
                    if any(k in line for k in ("⑤", "⑥", "判词", "核过")):
                        print("     " + line.strip())
                print("     实测：判词 %s ／ 退出码 %d" % (v5, r.returncode))
                results.append(("对照五 双点篡改", v5 == "BAD" and r.returncode == 1, v5, r.returncode))
    except Exception as e:
        print("     ERR 对照五无法执行：%s ⇒ ★ 未执行（不是通过）" % e)
        results.append(("对照五 双点篡改", False, "ERR", -1))

    print("\n  ═══ 五对照汇总 ═══")
    allok = True
    for name, ok, v, rc in results:
        print("     %-22s 判词 %-3s 退出码 %d  %s" % (name, v, rc, "✅" if ok else "★不符期望"))
        allok = allok and ok
    print("  ⇒ %s" % ("★ 五个方向全部按期望（检查会红也会绿，含对【它自己的诚实】的检查、以及对【双点篡改】的检查）"
                    if allok else "★ 有对照不符期望 —— 判据仍有问题"))
    # ★ 2026-10-03 轮 76 加：机器可读判词行（★ 承轮 72–75：本器在配方里、每轮被收尾块跑）。
    print("★ VERDICT=%s" % ("PASS" if allok else "BAD"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
