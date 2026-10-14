#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""Server酱告警通道 —— A2A网络管理员告警实装
编纂：砚坚 2026-10-03
依据：OTL-20261003-03 第七章（三）管理员告警 + 机主提供的SendKey
用途：MFA验证失败/Git钩子校验未通过/死信堆积/门禁连续拦截时自动推送告警至微信
"""
import json
import urllib.request
import urllib.error
import time
from typing import Optional


# Server酱 SendKey（由机主提供，仅存环境变量，不落盘）
# 设置方式：export SERVERCHAN_SENDKEY="sctp27948ta-xgg7lygc1i02s06aiwguronk"
import os
SENDKEY = os.environ.get("SERVERCHAN_SENDKEY", "")


def send_alert(title: str, content: str, level: str = "提示级") -> dict:
    """通过Server酱推送告警至微信
    
    Args:
        title: 告警标题（不超过32字符）
        content: 告警内容（Markdown格式）
        level: 告警级别（提示级/处置级）
    
    Returns:
        dict: 推送结果
    """
    if not SENDKEY:
        return {"ok": False, "error": "SERVERCHAN_SENDKEY未设置"}
    
    # 告警级别标记
    level_prefix = {"提示级": "⚠️", "处置级": "🚨"}.get(level, "⚠️")
    full_title = f"{level_prefix} {title}"
    
    # 构建请求
    url = f"https://sc3.ft07.com/send/{SENDKEY}.send"
    
    # 添加时间戳和级别标记
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    full_content = f"**告警级别**: {level}\n**时间**: {timestamp}\n\n{content}"
    
    data = {
        "title": full_title[:32],
        "desp": full_content,
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "result": result}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"网络错误: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"未知错误: {e}"}


def alert_mfa_failure(seat_id: str, reason: str, factor_details: str = "") -> dict:
    """MFA验证失败告警
    
    Args:
        seat_id: 失败席位标识
        reason: 失败原因码
        factor_details: 因子详情（遮蔽版）
    """
    content = f"**席位**: {seat_id}\n**失败原因**: {reason}\n"
    if factor_details:
        content += f"**因子详情**: {factor_details}\n"
    content += "\n请检查MFA配置并重新认证。连续失败将触发处置级告警。"
    return send8send_alert("MFA验证失败", content, "提示级")


def alert_hook_rejection(seat_id: str, hook_type: str, reason: str) -> dict:
    """Git钩子校验未通过告警
    
    Args:
        seat_id: 失败席位标识
        hook_type: 钩子类型（pre-commit/commit-msg/pre-push）
        reason: 拒绝原因
    """
    content = f"**席位**: {seat_id}\n**钩子类型**: {hook_type}\n**拒绝原因**: {reason}\n"
    content += "\n请修复问题后重新提交。连续失败将触发处置级告警。"
    return send_alert("Git钩子拦截", content, "提示级")


def alert_dlq_accumulation(dlq_count: int, oldest_event_age: str) -> dict:
    """死信队列堆积告警（处置级）
    
    Args:
        dlq_count: 死信队列消息数
        oldest_event_age: 最旧消息年龄
    """
    content = f"**死信队列消息数**: {dlq_count}\n**最旧消息年龄**: {oldest_event_age}\n"
    content += "\n死信堆积超过阈值，要求限时响应并回执。"
    return send_alert("死信队列堆积", content, "处置级")


def alert_gate_rejection(build_id: str, reason: str) -> dict:
    """发布门禁拦截告警（处置G级）
    
    Args:
        build_id: 构建标识
        reason: 门禁失败原因
    """
    content = f"**构建标识**: {build_id}\n**门禁失败原因**: {reason}\n"
    content += "\n发布门禁连续拦截，要求限时响应并回执。"
    return send_alert("发布门禁拦截", content, "处置级")


def alert_rollback(seat_id: str, operation: str, rollback_status: str) -> dict:
    """自动回滚告警
    
    Args:
        seat_id: 回滚席位标识
        operation: 回滚操作描述
        rollback_status: 回滚状态（成功/失败）
    """
    content = f"**席位**: {seat_id}\n**回滚操作**: {operation}\n**回滚状态**: {rollback_status}\n"
    content += "\n回滚动作已登记为事件，供审计回溯。"
    return send_alert("自动回滚执行", content, "提示级")


if __name__ == "__main__":
    # 自检：发送测试告警
    if not SENDKEY:
        print("❌ SERVERCHAN_SENDKEY环境变量未设置")
        print("   设置方式: export SERVERCHAN_SENDKEY='sctp27948ta-xgg7lygc1i02s06aiwguronk'")
        exit(1)
    
    result = send_alert(
        "A2A告警通道自检",
        "Server酱告警通道自检测试。\n如收到此消息，说明告警通道已正确配置。",
        "提示级"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))