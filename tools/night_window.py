# -*- coding: utf-8 -*-
"""night_window.py —— 夜间运维窗口与折扣时段调度判定

对应本轮新增令条：
  · 「暂定**一般夜间运维默认为（峰谷或特定折扣定价）北京时间晚上 23 点到次日清晨 8 点**，
     时间临近时应该**妥善停止进一步规划并落盘**，具体细则有待 Agent to Agent 商榷」
  · 「特别是 **DeepSeek 股市开盘日进入北京时间晚上 20 点后**的可能峰谷时间**自我唤醒与集结**
     Agent to Agent 特定网络进行相关先行协同工作」
  · 「**Qwen 3.8 Max 在部分 Qoder CN 宿主应用为北京时间 22 点时有 4 折（×0.2 费率）优惠**，
     应也考虑在此时自动化拉入相关集会讨论中」

本工具**只读判定**：读当前时间，输出所处窗口、距边界剩余、今日待办时段与「临近落盘」提示；
可选 `--json` 输出机器可读结果，便于被总控台/会话提醒消费。

用法:
  python night_window.py                 # 人读报告
  python night_window.py --json out.json # 机器可读
  python night_window.py --lead 30       # 距边界 ≤30 分钟即提示「临近，须落盘停规划」
"""
import argparse
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")

TZ = ZoneInfo("Asia/Shanghai")
NIGHT_START = (23, 0)   # 夜间运维窗口起（默认，细则待商榷）
NIGHT_END = (8, 0)      # 夜间运维窗口止
EVENTS = [
    {"at": (20, 0), "name": "DeepSeek 峰谷协同（开盘日）",
     "note": "开盘日 20:00 后自我唤醒、集结 A2A 特定网络先行协同（候商榷：如何判定'开盘日'）"},
    {"at": (22, 0), "name": "Qwen 3.8 Max 折扣时段（×0.2 费率）",
     "note": "部分 Qoder CN 宿主 22:00 4 折——宜自动拉入集会讨论（候商榷：宿主/实例范围与核验方式）"},
    {"at": (23, 0), "name": "夜间运维窗口起（峰谷定价）",
     "note": "一般夜间运维默认窗口，23:00–08:00"},
    {"at": (8, 0), "name": "夜间运维窗口止",
     "note": "窗口结束，转入日间常规；临近边界须先落盘"},
]


def minutes(h, m):
    return h * 60 + m


def state(now, lead):
    cur = now.hour * 60 + now.minute
    ns, ne = minutes(*NIGHT_START), minutes(*NIGHT_END)
    in_night = (cur >= ns) or (cur < ne)          # 跨零点
    # 下一个边界
    bounds = [("夜间窗口止(08:00)", minutes(*NIGHT_END)), ("夜间窗口起(23:00)", minutes(*NIGHT_START))]
    for h, m in [(e["at"][0], e["at"][1]) for e in EVENTS]:
        bounds.append(("事件 %02d:%02d" % (h, m), minutes(h, m)))
    nxt = None
    for name, mm in bounds:
        delta = (mm - cur) % (24 * 60)
        if delta == 0:
            delta = 24 * 60
        if nxt is None or delta < nxt[1]:
            nxt = (name, delta)
    near = nxt[1] <= lead
    upcoming = []
    for e in EVENTS:
        mm = minutes(*e["at"])
        delta = (mm - cur) % (24 * 60)
        upcoming.append({"name": e["name"], "at": "%02d:%02d" % e["at"],
                         "in_minutes": delta, "today_passed": cur > mm, "note": e["note"]})
    return {"now": now.strftime("%Y-%m-%d %H:%M:%S"), "weekday": now.strftime("%A"),
            "in_night_window": in_night, "night_window": "23:00–08:00",
            "next_boundary": nxt[0], "next_in_minutes": nxt[1],
            "near_boundary": near, "lead_minutes": lead,
            "guidance": ("临近边界：**妥善停止进一步规划并落盘**（令条）" if near
                         else "距最近边界 %d 分钟，本窗口内可继续作业" % nxt[1]),
            "upcoming_events": upcoming}


def report(st):
    L = ["# 夜间运维窗口与折扣时段判定", "",
         "- 判定时刻：%s（%s，北京时间）" % (st["now"], st["weekday"]),
         "- 夜间运维窗口：**%s**（默认，细则待 A2A 商榷）" % st["night_window"],
         "- 当前是否处于夜间窗口：**%s**" % ("是" if st["in_night_window"] else "否"),
         "- 最近边界：**%s**（%d 分钟后）" % (st["next_boundary"], st["next_in_minutes"]),
         "- 处置指引：%s" % st["guidance"],
         "", "## 今日时段（按距当前时间）", "",
         "| 时段 | 名称 | 距当前 | 备注 |", "|---|---|---|---|"]
    for e in sorted(st["upcoming_events"], key=lambda x: x["in_minutes"]):
        L.append("| %s | %s | %d 分钟 | %s |" % (e["at"], e["name"], e["in_minutes"], e["note"]))
    L += ["", "> 本工具**只读判定**，不自动执行任何作业、不改任何配置；提醒/唤醒是否启用候 A2A 商榷。", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--lead", type=int, default=30)
    ap.add_argument("--at", default=None, help="以指定时刻判定（HH:MM，调试用）")
    a = ap.parse_args()

    now = dt.datetime.now(TZ)
    if a.at:
        hh, mm = a.at.split(":")
        now = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    st = state(now, a.lead)
    print(report(st))
    if a.json:
        import pathlib
        pathlib.Path(a.json).write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("已写出：%s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
