#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ignition_gate.py —— 石敢当席「点火闸」：燃烧申请去重与台账。  v1.0.0

来由
────
机主 2026-09-29 19:59 令：**一切燃烧须先与见霜/石敢当讨论再点火，且做好控制不重复操作。**
本工具把"不重复操作"从口头纪律变成**可机检的闸**：
  key       算去重键 = sha256(题面 ‖ 模型id ‖ 提示词模板)[:16]
  check     查台账：键已存在即【拒】（FOUND / NOT-FOUND）
  register  登记一条窑（只增不改）；★键重复即拒登
  verify    复算台账：行数 + 逐行键重算（证未被改动）

七件申请单（缺件不受理）
────────────────────────
  task 题面 / stove 灶(池) / model 模型id / template 提示词模板
  budget 预算上限 / criterion 判据 / deadline 死线
（申请人、登记时刻由工具自动补）

v1.1.0（2026-10-01）
   · 增 reconcile 档：为既有登记行【追加】一条对账记录（原行一字不动）。
     来由：第 1 批执行完毕需核收时才发现，本闸只有「登记」没有「对账」——
     登记与对账是两种态，缺了这一档就只能改原行，而原行不可改。
   · verify 区分申请行与对账行：对账须挂得上键、须有 verdict
     （记账齐而不判，等于没核收）。
   · 兼容旧行：加 ev_type 字段之前写入的行没有该字段，按 APPLICATION 对待。
     （★此坑是现实踩出来的：加字段后三条核收被自家闸误拒。）
   · 强制 UTF-8 输出（GBK 控制台下中文全乱码）。

零第三方依赖。台账为 JSONL，**只增不改**。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
import time

# ★ UTF-8 输出（2026-10-01 连坐普检补）：GBK 控制台下中文全乱码。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = SEAT / "ledger" / "ignition_registry.jsonl"
REQUIRED = ["task", "stove", "model", "template", "budget", "criterion", "deadline"]


def now_cst() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def h16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def dedup_key(task: str, model: str, template: str) -> str:
    """去重键：题面 ‖ 模型id ‖ 模板 三者归一后取 sha256 前 16 位。"""
    norm = "|".join(x.strip().replace("\r\n", "\n") for x in (task, model, template))
    return h16(norm)


def load() -> list:
    if not LEDGER.exists():
        return []
    rows = []
    for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print("[ERR] 台账第 %d 行非法 JSON：%s" % (i, e))
                sys.exit(2)
    return rows


def cmd_key(args):
    if len(args) < 3:
        print("用法：ignition_gate.py key <题面> <模型id> <提示词模板>")
        return 2
    k = dedup_key(args[0], args[1], args[2])
    print("去重键 = %s" % k)
    print("  题面sha256[:16]    = %s" % h16(args[0]))
    print("  模型id             = %s" % args[1])
    print("  模板sha256[:16]    = %s" % h16(args[2]))
    return 0


def cmd_check(args):
    if not args:
        print("用法：ignition_gate.py check <去重键>")
        return 2
    k = args[0]
    rows = load()
    hit = [r for r in rows if r.get("key") == k]
    if hit:
        r = hit[0]
        print("[拒] FOUND —— 该键已在台账（第 %d 条）" % (rows.index(r) + 1))
        print("   题面摘要：%s" % (r.get("task", "")[:60]))
        print("   灶/模型：%s / %s ｜ 登记于 %s" % (r.get("stove"), r.get("model"), r.get("ts")))
        print("   ★ 不得「再跑一遍看看」——重复燃烧即违机主 19:59 令。")
        return 1
    print("[准] NOT-FOUND —— 台账无此键，可进入申请闸七件校验")
    return 0


def cmd_register(args):
    if not args:
        print("用法：ignition_gate.py register <申请单.json>")
        return 2
    p = pathlib.Path(args[0])
    if not p.is_file():
        print("[ERR] 申请单不存在：%s" % p)
        return 2
    spec = json.loads(p.read_text(encoding="utf-8"))

    missing = [f for f in REQUIRED if not str(spec.get(f, "")).strip()]
    if missing:
        print("[拒] 申请闸未过：缺 %d 件 —— %s" % (len(missing), "、".join(missing)))
        print("     七件为：%s" % "／".join(REQUIRED))
        return 1

    k = dedup_key(spec["task"], spec["model"], spec["template"])
    rows = load()
    if any(r.get("key") == k for r in rows):
        print("[拒] 去重闸未过：键 %s 已在台账（重复题面×模型×模板）" % k)
        return 1

    row = {
        "ts": now_cst(),
        "key": k,
        "task": spec["task"], "task_h": h16(spec["task"]),
        "stove": spec["stove"], "model": spec["model"],
        "template": spec["template"], "template_h": h16(spec["template"]),
        "budget": spec["budget"], "criterion": spec["criterion"],
        "deadline": spec["deadline"],
        "applicant": spec.get("applicant", "(未署)"),
        "ev_type": "APPLICATION",
        "gate": "PASS-申请闸+去重闸",
        "status": "REGISTERED-AWAITING-IGNITION",
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    # 先写后读回比对
    back = load()
    if not back or back[-1].get("key") != k:
        print("[ERR] 写入回读比对失败")
        return 1
    print("[准] 已登记第 %d 条（只增不改）｜ 键 %s" % (len(back), k))
    print("   灶=%s ｜ 模型=%s ｜ 预算=%s ｜ 死线=%s" % (row["stove"], row["model"], row["budget"], row["deadline"]))
    print("   ★ 登记≠点火：点火仍须见霜/机主执行，且批后须回执对账（每窑 ev/tokens/cost/ts）。")
    return 0


def cmd_reconcile(args):
    """对账核收：为既有登记行【追加】一条 RECONCILE 记录（原行一字不动）。

    用法：ignition_gate.py reconcile <键> <对账.json>
    对账 JSON 字段：usage（逐窑记账）/ verdict（核收判定）/ note / evidence
    ★ 立此档的来由：第 1 批执行完毕需核收时，本席发现闸只有『登记』没有『对账』——
      登记与对账不同态，缺档就只能改原行，而原行不可改。故补此档，仍守只增不改。
    """
    if len(args) < 2:
        print("用法：ignition_gate.py reconcile <键> <对账.json>")
        return 2
    key = args[0]
    rows = load()
    # ★ 版本迁移兼容：加 ev_type 字段之前写入的旧行没有该字段，按 APPLICATION 对待。
    #   实证：本闸首跑 reconcile 时三条核收全被拒（『台账无此键的登记行』）——
    #   原因是旧行缺 ev_type，属本席自造的迁移不兼容，已修。
    app = [r for r in rows
           if r.get("ev_type", "APPLICATION") == "APPLICATION" and r.get("key") == key]
    if not app:
        print("[拒] 台账无此键的登记行：%s —— 未登记不得对账" % key)
        return 1
    p = pathlib.Path(args[1])
    if not p.is_file():
        print("[ERR] 对账件不存在：%s" % p)
        return 2
    spec = json.loads(p.read_text(encoding="utf-8"))
    if not str(spec.get("verdict", "")).strip():
        print("[拒] 对账缺 verdict（核收判定）——记账齐而不判，等于没核收")
        return 1

    row = {
        "ts": now_cst(),
        "ev_type": "RECONCILE",
        "ref_key": key,
        "usage": spec.get("usage", "(未报)"),
        "verdict": spec["verdict"],
        "note": spec.get("note", ""),
        "evidence": spec.get("evidence", ""),
        "reconciler": spec.get("reconciler", "cairn-dsh"),
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    back = load()
    if not back or back[-1].get("ref_key") != key:
        print("[ERR] 写入回读比对失败")
        return 1
    print("[OK] 已核收第 %d 条 ｜ 键 %s ｜ 判定：%s" % (len(back), key, row["verdict"]))
    return 0


def cmd_verify(args):
    rows = load()
    if not rows:
        print("[--] 台账为空或不存在：%s" % LEDGER)
        return 0
    bad = 0
    seen = set()
    app_keys = set()
    n_app = n_rec = 0
    for i, r in enumerate(rows, 1):
        if r.get("ev_type") == "RECONCILE":
            n_rec += 1
            if r.get("ref_key") not in app_keys:
                print("★第 %d 条：对账指向的键无登记行（%s）" % (i, r.get("ref_key")))
                bad += 1
            if not str(r.get("verdict", "")).strip():
                print("★第 %d 条：对账缺 verdict" % i)
                bad += 1
            continue
        n_app += 1
        k = dedup_key(r.get("task", ""), r.get("model", ""), r.get("template", ""))
        if k != r.get("key"):
            print("★第 %d 条：键不可复算（记录 %s／实算 %s）" % (i, r.get("key"), k))
            bad += 1
        if r.get("key") in seen:
            print("★第 %d 条：键重复出现 —— 去重闸被绕过" % i)
            bad += 1
        seen.add(r.get("key"))
        app_keys.add(r.get("key"))
    print("═══ 点火台账校验 ═══")
    print("条目数：%d ｜ 申请 %d ｜ 对账 %d ｜ 唯一键 %d ｜ 异常：%d"
          % (len(rows), n_app, n_rec, len(seen), bad))
    print("结论：%s" % ("PASS —— 键皆可复算、无重复登记、对账皆挂得上键" if bad == 0 else "FAIL"))
    return 0 if bad == 0 else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "key":
        return cmd_key(sys.argv[2:])
    if cmd == "check":
        return cmd_check(sys.argv[2:])
    if cmd == "register":
        return cmd_register(sys.argv[2:])
    if cmd == "reconcile":
        return cmd_reconcile(sys.argv[2:])
    if cmd == "verify":
        return cmd_verify(sys.argv[2:])
    print("用法：ignition_gate.py {key|check|register|verify} …")
    return 2


if __name__ == "__main__":
    sys.exit(main())
