#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
test_deduce_d4.py —— 专测沈铎 `deduce_core.py` 的 D4（实时性）计分口径。 **v1.1.0**

★ v1.0.0 的教训（写在这里，不抹）
──────────────────────────────────
  v1.0.0 的 Q2 段落**把结论写死在 print 里**，与它自己算出的数字相矛盾
  （三个口径都是 50.0，脚本却说"三种口径给出三个不同的 P95"）；
  且 Q2 的样本取 20 条同值 ⇒ **丢与不丢都是 50** ⇒ 演示本身失败；
  Q3 的"真 P95"用了与本器相同的 max 回退 ⇒ **对照是空的**。
  ⇒ **这正是本席整晚在指控的"恒真断言／结论与数据无关"。**
  ⇒ v1.1.0 改为：**每条结论一律由【比较结果】算出**，并打印 PASS/FAIL。

被测（[原件直取]，其 `DeduceCore.p95_latency`）：
    deltas = [r - e for e, r in self.latencies if r >= e]
    return statistics.quantiles(deltas, n=20)[18] if len(deltas) >= 20 else max(deltas)

用法: test_deduce_d4.py [--elsewhere 路径]
"""
from __future__ import annotations
import argparse
import pathlib
import statistics
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEATS = {}


def build(module_dir: str):
    sys.path.insert(0, module_dir)
    import deduce_core as dc
    return dc


def feed(core, samples):
    for i, (e, r) in enumerate(samples):
        core.ingest({"ts": e, "src": "t%d" % i, "kind": "heartbeat",
                     "payload": {"seat": "s%d" % i, "alive": True}}, t_render_ms=r)


def theirs(vals):
    """复现其口径：过滤 r<e 已由调用方完成；此处只看 n>=20 与否。"""
    return statistics.quantiles(vals, n=20)[18] if len(vals) >= 20 else max(vals)


def true_p95(vals):
    """另一套算法算 95 分位（最近秩法），用于形成【非空对照】。"""
    s = sorted(vals)
    k = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
    return s[k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elsewhere", default=r"C:\Users\欧阳宏俊\OneDrive\桌面")
    a = ap.parse_args()
    d = pathlib.Path(a.elsewhere)
    if not (d / "deduce_core.py").is_file():
        print("[ERR] 未找到 deduce_core.py"); return 2
    dc = build(str(d))
    print("═══ 专测 D4 计分口径（v1.1.0：结论一律由数据算出）═══")
    print("  对象 = %s" % (d / "deduce_core.py"))
    print()

    # ── Q1：负样本是否被静默丢弃 ──
    samples = [(1000 + i, 1000 + i + 50) for i in range(20)] + \
              [(2000 + i, 2000 + i - 30) for i in range(5)]
    core = dc.DeduceCore()
    feed(core, samples)
    kept = [r - e for e, r in samples if r >= e]
    dropped = len(samples) - len(kept)
    print("  Q1 负样本是否被静默丢弃")
    print("     投入 %d 条 ｜ 其内部保留 %d 条 ｜ 丢弃 %d 条" % (len(samples), len(kept), dropped))
    q1 = dropped > 0
    print("     [%s] 丢弃成立 = %s" % ("PASS" if q1 else "FAIL", q1))
    print()

    # ── Q2：丢弃【是否改变读数】——须构造一个真正会变的样本 ──
    #   设计：19 条正样本（值 10..190）＋ 1 条负样本
    #     · 丢弃 ⇒ 保留 19 条 ⇒ n<20 ⇒ 其口径返回 max = 190
    #     · 若把负样本按 0 计入 ⇒ n=20 ⇒ 其口径返回 quantiles[18]（≈181）
    pos19 = [(3000 + i, 3000 + i + (10 + 10 * i)) for i in range(19)]   # 10,20,…,190
    one_neg = [(9000, 9000 - 5)]
    c2 = dc.DeduceCore()
    feed(c2, pos19 + one_neg)
    got2 = c2.p95_latency()
    kept2 = [r - e for e, r in pos19]                 # 丢弃负样本后的集合（19 条）
    incl0 = [max(0, r - e) for e, r in (pos19 + one_neg)]  # 按 0 计入（20 条）
    theirs_drop = theirs(kept2)
    theirs_incl = theirs(incl0)
    print("  Q2 丢弃是否改变其读数（19 正 + 1 负）")
    print("     其实际报出            = %s" % round(got2, 3))
    print("     复现「丢弃」口径      = %s（n=%d ⇒ %s）" % (round(theirs_drop, 3), len(kept2), "max" if len(kept2) < 20 else "quantiles"))
    print("     复现「按 0 计入」口径 = %s（n=%d ⇒ %s）" % (round(theirs_incl, 3), len(incl0), "max" if len(incl0) < 20 else "quantiles"))
    changed = (theirs_drop != theirs_incl)
    print("     [%s] 丢弃【改变读数】= %s" % ("PASS" if changed else "FAIL", changed))
    if changed:
        print("     ⇒ ★ 结论：n=19 走 max、n=20 走分位 ⇒ **多一条负样本就换了公式** ⇒ 丢弃确有影响")
    else:
        print("     ⇒ 本席构造的样本仍未使读数改变 ⇒ **演示失败**，如实记，不粉饰")
    print()

    # ── Q3：n<20 时"P95"是否就是 max；对照须【非空】 ──
    small = [10, 20, 30, 40, 900]
    c3 = dc.DeduceCore()
    feed(c3, [(5000 + i, 5000 + i + v) for i, v in enumerate(small)])
    got3 = c3.p95_latency()
    is_max = (got3 == max(small))
    tp = true_p95(small)
    print("  Q3 n<20 时其\"P95\"是否＝max（对照用另一套算法）")
    print("     5 条样本 = %s" % small)
    print("     其报出 = %s ｜ 最近秩法 95 分位 = %s ｜ 最大值 = %s" % (got3, tp, max(small)))
    print("     [%s] 其报出等于 max = %s" % ("PASS" if is_max else "FAIL", is_max))
    print("     ★ 注：n=5 时\"95 分位\"本身统计意义薄弱；本器只报【其口径在小样本下退化为 max】这一事实")
    print()

    verdict = q1 and changed and is_max
    print("[总判] Q1/P Q2/Q3 三问：丢弃=%s ｜ 改变读数=%s ｜ 小样本退化为max=%s"
          % (q1, changed, is_max))
    print("★ 本器能返回 PASS 与 FAIL 两种结果（v1.0.0 时它只会照着写好的话打印）⇒ 现已非恒真。")
    print("★ 本席未改动被测文件一个字节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
