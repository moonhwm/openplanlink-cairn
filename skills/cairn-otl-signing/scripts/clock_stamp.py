# -*- coding: utf-8 -*-
"""clock_stamp.py —— **时点行之机器生成**（承轮31 之"时点口径自纠"）

## 缘起（自纠留痕）
轮 31 核出：**本席件之正文"时点"行系手写臆进**，而**署名块时点系工具取真实钟** ⇒
**可比对 31 件中 28 件 Δ＞5 min，平均偏差 4.89 h**（近件 7.4–11.5 h）——**同一件内两时点相冲**。
⇒ **根因**：正文时点未被强制取自时钟，**本席以"每轮约 40 分钟"之假想推进之**。
⇒ **对策**：**时点行一律由本器生成**（**不再手写**）；**审计口径：以署名块时点为准**。

用法：
    python clock_stamp.py                # 打印可粘贴之"时点"行（含起时与末时）
    python clock_stamp.py --start "<北京时间起时>"   # 声明本轮起始时点（取真实钟者为末时）
性质：**只读时钟**；**不改任何文件**。
"""
import argparse
import datetime as dt
import sys

sys.stdout.reconfigure(encoding="utf-8")
TZ = dt.timezone(dt.timedelta(hours=8))


def now():
    return dt.datetime.now(TZ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="")
    a = ap.parse_args()
    n = now()
    end = n.strftime("%H:%M")
    if a.start:
        line = "- 时点：北京时间 **%s %s–%s**（★**末时由 `clock_stamp.py` 取真实钟**）" % (n.strftime("%Y-%m-%d"), a.start, end)
    else:
        line = "- 时点：北京时间 **%s %s**（★**由 `clock_stamp.py` 取真实钟**）" % (n.strftime("%Y-%m-%d"), end)
    print("★ 建议粘贴之「时点」行：")
    print(line)
    print("  （真实钟：%s ｜ UTC %s ｜ 时区 %s）" % (n.strftime("%Y-%m-%d %H:%M:%S %z"),
                                                n.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                                                "Asia/Shanghai (UTC+8)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
