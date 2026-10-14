#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only AND SSPL-1.0
"""Server酱推送模块——砚坚席微信IM智慧互联通道
实装版本：将方案设计落地为可执行脚本
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 频率控制记录文件
_RATE_LIMIT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "GOVERNANCE", "audit_logs", "serverchan_rate.json"
)


def _load_rate_limit():
    """加载频率控制记录"""
    try:
        with open(_RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rate_limit(data):
    """保存频率控制记录"""
    os.makedirs(os.path.dirname(_RATE_LIMIT_FILE), exist_ok=True)
    with open(_RATE_LIMIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _check_rate_limit(category, event_key=None):
    """
    检查频率限制
    category: CRITICAL(1h) / WARNING(1h) / INFO(4h)
    event_key: 同一事件的唯一标识，用于去重
    """
    limits = {
        "CRITICAL": 3600,   # 1小时
        "WARNING": 3600,    # 1小时
        "INFO": 14400,      # 4小时
    }
    window = limits.get(category, 3600)
    now = time.time()
    rate_data = _load_rate_limit()

    key = f"{category}:{event_key}" if event_key else category

    if key in rate_data:
        elapsed = now - rate_data[key]
        if elapsed < window:
            return False, int(window - elapsed)

    rate_data[key] = now
    _save_rate_limit(rate_data)
    return True, 0


def push(title, desp, category="INFO", event_key=None):
    """
    通过Server酱推送消息到机主微信

    参数：
        title: 标题（最多32字）
        desp: 正文（支持Markdown）
        category: CRITICAL/WARNING/INFO/DEBUG
        event_key: 事件唯一标识（用于去重）

    返回：
        (success: bool, message: str)
    """
    if category == "DEBUG":
        return True, "DEBUG级别不推送"

    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        print(f"[Server酱] SERVERCHAN_SENDKEY未设置，跳过推送", file=sys.stderr)
        return False, "SENDKEY未设置"

    allowed, remaining = _check_rate_limit(category, event_key)
    if not allowed:
        return False, f"频率限制，{remaining}秒后可再次推送"

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({
        "title": title[:32],
        "desp": desp
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("code") == 0 and result.get("errno") == 0:
            pushid = result.get("data", {}).get("pushid", "unknown")
            return True, f"推送成功 pushid={pushid}"
        else:
            return False, f"推送失败: {result}"
    except Exception as e:
        return False, f"推送异常: {e}"


def push_alert(event_type, details, impact="", action=""):
    """推送告警消息（CRITICAL级别，1h内同一事件不重复）"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## 🚨 {event_type}

- **时间**：{now}
- **席位**：砚坚（码道·GLM-5.2）
- **详情**：{details}
- **影响**：{impact}
- **处置**：{action}"""
    return push(f"告警：{event_type}", desp, "CRITICAL", event_key=event_type)


def push_warning(event_type, details, impact="", action=""):
    """推送警告消息（WARNING级别，1h内同一事件不重复）"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## ⚠️ {event_type}

- **时间**：{now}
- **席位**：砚坚（码道·GLM-5.2）
- **详情**：{details}
- **影响**：{impact}
- **处置**：{action}"""
    return push(f"警告：{event_type}", desp, "WARNING", event_key=event_type)


def push_report(completed, in_progress, pending, over_window=""):
    """推送状态汇报（INFO级别，4h内不重复）"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## 📊 砚坚席工作摘要

- **时间**：{now}
- **完成**：{completed}
- **进行**：{in_progress}
- **待办**：{pending}"""
    if over_window:
        desp += f"\n- **越窗**：{over_window}"
    return push("砚坚席工作摘要", desp, "INFO")


def push_negotiation(direction, topic, peer, result=""):
    """推送协商通知（INFO级别）"""
    desp = f"""## 🤝 A2A协商通知

- **方向**：{direction}
- **命题**：{topic}
- **对端**：{peer}
- **结果**：{result}"""
    return push(f"协商通知：{topic}", desp, "INFO", event_key=f"negotiation_{topic}")


def push_over_window(task_description, window_end):
    """推送越窗报告（WARNING级别）"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## ⏰ 越窗报告

- **时间**：{now}
- **任务**：{task_description}
- **指令窗口截止**：{window_end}
- **处置**：按"继续推进+如实报越窗"原则执行"""
    return push(f"越窗报告：{task_description[:20]}", desp, "WARNING", event_key="over_window")


# ============ 自检 ============

def self_test():
    """Server酱推送模块自检"""
    print("=" * 60)
    print("Server酱推送模块自检")
    print("=" * 60)

    # 检查环境变量
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        print("\n[跳过] SERVERCHAN_SENDKEY未设置，无法测试推送")
        print("  请先设置环境变量：")
        print('  PowerShell: $env:SERVERCHAN_SENDKEY="sctp27948ta-xgg7lygc1i02s06aiwguronk"')
        return

    # 测试1：推送INFO级别消息
    print("\n[测试1] 推送INFO级别消息...")
    ok, msg = push("自检测试", "这是砚坚席Server酱推送模块的自检消息", "INFO")
    print(f"  结果: ok={ok}, msg={msg}")

    # 测试2：频率控制——立即重复推送应被拦截
    print("\n[测试2] 频率控制——立即重复推送...")
    ok2, msg2 = push("自检测试", "这是重复消息，应被频率控制拦截", "INFO")
    print(f"  结果: ok={ok2}, msg={msg2}")

    # 测试3：推送CRITICAL级别告警
    print("\n[测试3] 推送CRITICAL级别告警...")
    ok3, msg3 = push_alert(
        event_type="自检告警",
        details="这是自检测试告警消息",
        impact="无实际影响",
        action="自检完成"
    )
    print(f"  结果: ok={ok3}, msg={msg3}")

    print("\n" + "=" * 60)
    print("自检完成")
    print("=" * 60)


if __name__ == "__main__":
    self_test()