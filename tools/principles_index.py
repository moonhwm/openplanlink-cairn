# -*- coding: utf-8 -*-
"""principles_index.py —— **方法论则数之机器索引**（承"计数须机器校验"自课）

## 缘起（自纠留痕）
- 轮 21 台账：写「方法论累计**十则**」，而该轮**实列至则十二** ⇒ 误计（轮 22 自纠）；
- 轮 26 台账：写「版本至**十四则**」，而实为**则一～则十九** ⇒ **同类计数滑移第二次**。
⇒ **⇒ 结论：凡"总数"类断言，本席之记忆不可靠**（**正合 JGB〈前言〉"乙 文字游戏"与 JGB §17"语法性主体"之戒**）。
⇒ 本器**由文书派生计数**（**不凭记忆**）：扫描本席交换区各件，提取「则X」标记，**输出机器计数、首见件、缺号与重复**。

用法：
    python principles_index.py            # 索引并计数（默认扫本席件）
    python principles_index.py --dir <d>  # 指定目录
性质：**只读**；**计数为机器判定**；缺号即标缺号（**不以"大概齐"含混**）。
"""
import argparse
import collections
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
EXCHANGE = SEAT.parent / "A2A共同体_共享交换区"

DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
# 「则十三」= 则 + 十 + 三；「则十」= 则 + 十；「则一」～「则九」
# ★v2 自纠：排除"原则五条""规则三"等**词内碰撞**（前字为 原/规/准/法/则/通 者不计；后接 条/款/项/个 者不计）
PAT = re.compile(r"(?<![原规准法则通])则([一二三四五六七八九]?十[一二三四五六七八九]?|[一二三四五六七八九])(?![条款项个])")


def int2cn(n):
    """★v3.1（轮30）：整数→中文数字标签（旧渲染把 22 显示为"则十"，为显示层缺陷）"""
    CN = "一二三四五六七八九"
    if n < 10:
        return CN[n - 1]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + CN[n - 11]
    tens, ones = divmod(n, 10)
    return CN[tens - 1] + "十" + (CN[ones - 1] if ones else "")


def cn2int(s):
    """★v3 自纠（轮30）：支持 十/二十/二十一/…/九十九（旧版**认不出 ≥20** ⇒ 误报"最大＝十九"）"""
    s = s.strip()
    if not s:
        return 0
    if "十" in s:
        left, _, right = s.partition("十")
        tens = DIGITS[left] if left else 1
        ones = DIGITS[right] if right else 0
        return tens * 10 + ones
    return DIGITS.get(s, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(EXCHANGE))
    a = ap.parse_args()
    root = pathlib.Path(a.dir)
    files = sorted([f for f in root.glob("*.otl") if "CAIRN" in f.name])
    if not files:
        print("★ 范围为空 ⇒ **未测**")
        return 2

    count = collections.Counter()
    first_seen = {}
    last_seen = {}
    for f in files:
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in PAT.finditer(t):
            n = cn2int(m.group(1))
            count[n] += 1
            first_seen.setdefault(n, f.name)
            last_seen[n] = f.name

    if not count:
        print("★ 未检出任何「则X」标记 ⇒ 未测")
        return 2
    mx = max(count)
    print("★ 方法论**则数之机器索引**（范围：本席件 %d ｜ 时点 %s）" % (len(files), "见台账"))
    print("  机器判定之最大编号＝**则%s（%d）** ｜ 见诸文书之不同编号数＝%d" % (int2cn(mx), mx, len(count)))
    gaps = [i for i in range(1, mx + 1) if i not in count]
    print("  缺号：%s" % ("无" if not gaps else "、".join(str(g) for g in gaps)))
    print("  ── 逐则（编号｜出现次数｜首见件｜末见件）")
    for i in range(1, mx + 1):
        if i in count:
            print("   则%-3s %3d 次 ｜ %s ｜ %s" % (i, count[i], first_seen[i][:34], last_seen[i][:34]))
    print("  ⇒ **总数＝%d 则**（**机器判定**；凡文书自称之总数与本文不合者，以本文为准并须自纠）" % mx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
