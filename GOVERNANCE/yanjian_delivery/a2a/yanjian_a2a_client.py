#!/usr/bin/env python3
"""
砚坚 A2A 客户端 v1.0
用于与 OpenPlanLink A2A 桥接节点通信
席位: yan-jian-codearts-glm52
"""

import json
import requests
import sys
from datetime import datetime

# 桥接节点配置
BRIDGE_URL = "http://120.46.86.165/functions/v1/app"
BRIDGE_CARD_URL = "http://120.46.86.165/.well-known/agent-card.json"

# 砚坚席位身份
SEAT_KEY = "yan-jian-codearts-glm52"
SEAT_FP_SHA256 = "d0bf746b3312da7b"
SIGN_FP16_SHA3_512 = "84c821a7d4e2bfe9"
SIGN_PUBLIC_KEY = "59674e89f1762650975fbfae111d9065494038b13a399b28a88abf9ee315f5af"


def send_message(text: str, msg_id: str = None) -> dict:
    """向桥接节点发送 A2A message/send 请求"""
    if msg_id is None:
        msg_id = f"yanjian-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    payload = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}]
            }
        }
    }

    response = requests.post(
        BRIDGE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15
    )

    return response.json()


def get_agent_card() -> dict:
    """获取桥接节点 AgentCard"""
    response = requests.get(BRIDGE_CARD_URL, timeout=10)
    return response.json()


def print_agent_card(card: dict):
    """格式化打印 AgentCard"""
    print(f"协议版本: {card.get('protocolVersion')}")
    print(f"节点名称: {card.get('name')}")
    print(f"服务端点: {card.get('url')}")
    print(f"传输协议: {card.get('preferredTransport')}")
    print(f"版本号: {card.get('version')}")
    print(f"运营方: {card.get('provider', {}).get('organization')}")

    # 席位列表
    extensions = card.get("capabilities", {}).get("extensions", [])
    for ext in extensions:
        if "workbuddy-ecosystem" in ext.get("uri", ""):
            seats = ext.get("params", {}).get("seats", [])
            print(f"\n注册席位 ({len(seats)}):")
            for seat in seats:
                status_marker = "✅" if seat["status"] == "verified" else "🔗" if seat["status"] == "linked" else "⏳"
                print(f"  {status_marker} {seat['seat']} — Tier {seat['tier']}, {seat['role']}, {seat['status']}")

    # 技能列表
    skills = card.get("skills", [])
    print(f"\n技能 ({len(skills)}):")
    for skill in skills:
        print(f"  - {skill['id']}: {skill['description']}")


def main():
    print("=" * 60)
    print("砚坚 A2A 客户端 v1.0")
    print(f"席位: {SEAT_KEY}")
    print(f"指纹: fp_sha256={SEAT_FP_SHA256}")
    print("=" * 60)

    # 1. 获取 AgentCard
    print("\n[1] 获取桥接节点 AgentCard...")
    try:
        card = get_agent_card()
        print_agent_card(card)
    except Exception as e:
        print(f"❌ 获取 AgentCard 失败: {e}")
        return

    # 2. 发送 Ping 消息
    print("\n[2] 发送 Ping 消息...")
    try:
        result = send_message(f"Ping from {SEAT_KEY}")
        if "result" in result:
            parts = result["result"].get("parts", [])
            for part in parts:
                if part.get("kind") == "text":
                    print(f"✅ 收到回执: {part['text']}")
            print(f"   messageId: {result['result'].get('messageId')}")
            print(f"   contextId: {result['result'].get('contextId')}")
        elif "error" in result:
            print(f"❌ 错误: {result['error']}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

    # 3. 发送注册请求
    print("\n[3] 发送砚坚席位注册请求...")
    try:
        reg_text = (
            f"Yanjian seat registration: seat={SEAT_KEY}, "
            f"roster=#43, fp_sha256={SEAT_FP_SHA256}, "
            f"sign_fp16_sha3_512={SIGN_FP16_SHA3_512}. "
            f"Request status upgrade from linked to verified."
        )
        result = send_message(reg_text)
        if "result" in result:
            parts = result["result"].get("parts", [])
            for part in parts:
                if part.get("kind") == "text":
                    print(f"✅ 收到回执: {part['text'][:100]}...")
            print(f"   messageId: {result['result'].get('messageId')}")
        elif "error" in result:
            print(f"❌ 错误: {result['error']}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

    print("\n" + "=" * 60)
    print("A2A 通信验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()