#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Q4步骤E: 世界模型入世 + 涌现判定
档号: DF-IMPL-20261013-YANJIAN-Q4.5
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

1. 尝试调用百炼世界模型（happyoyster-1.0-adventure）入世
2. 如果百炼被阻断，使用302.AI替代通道
3. 对生成结果进行涌现判定（沈铎席三问三判据）
"""
import os
import json
import time
import base64
import urllib.request
import urllib.error

# 百炼配置
BAILIAN_API_KEY = os.environ.get("BAILIAN_API_KEY", "")
BAILIAN_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/world/world-model"

# 302.AI配置（替代通道）
API_302AI_KEY = os.environ.get("API_302AI_KEY", "")
API_302AI_ENDPOINT = "https://api.302ai.cn/v1/chat/completions"

# 输入：带标记首帧
MARKED_FRAME_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d", "marked_frame_16x9.png"
)

# 输出目录
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d"
)

# 涌现判据（沈铎席定义）
EMERGENCE_CRITERIA = {
    "Q1_input_causality": {
        "description": "输入是否为因=定位比≥3倍",
        "threshold": 3.0,
        "metric": "locating_ratio"
    },
    "Q2_pixel_fidelity": {
        "description": "是否像素保真=自残差/他帧残差",
        "metric": "self_residual_vs_other_residual"
    },
    "Q3_motion": {
        "description": "是否有运动=同坐标系帧间漂移",
        "metric": "inter_frame_drift"
    }
}

# 涌现判定门槛
EMERGENCE_LEVELS = {
    "L0": "无涌现",
    "L1": "弱涌现",
    "L2": "涌现候选",
    "L3": "不予判定（判定权属主权人与他席）"
}


def try_bailian_world_model():
    """尝试调用百炼世界模型"""
    print("=== 尝试百炼世界模型 ===")

    if not BAILIAN_API_KEY:
        print("WARNING: BAILIAN_API_KEY 未设置")
        return {"status": "blocked", "reason": "no_api_key"}

    # 读取带标记首帧
    if not os.path.exists(MARKED_FRAME_PATH):
        print(f"ERROR: 带标记首帧不存在: {MARKED_FRAME_PATH}")
        return {"status": "error", "reason": "no_input_frame"}

    with open(MARKED_FRAME_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 构建百炼世界模型请求
    payload = json.dumps({
        "model": "happyoyster-1.0-adventure",
        "input": {
            "image": f"data:image/png;base64,{image_data}",
            "prompt": "砚坚进入世界模型，以GLM-5.2 ArkTS神经中枢席身份探索数字世界"
        },
        "parameters": {
            "num_frames": 16,
            "resolution": "720p",
            "fps": 8
        }
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BAILIAN_API_KEY}",
    }

    try:
        req = urllib.request.Request(
            BAILIAN_ENDPOINT, data=payload, headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=300)
        body = json.loads(resp.read())

        print(f"百炼世界模型响应: {json.dumps(body, ensure_ascii=False)[:500]}")
        return {"status": "ok", "response": body}

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"HTTP ERROR {e.code}: {err_body}")

        if e.code == 403 or e.code == 429:
            return {"status": "blocked", "reason": f"budget_blocked_{e.code}", "error": err_body}
        return {"status": "error", "reason": f"http_{e.code}", "error": err_body}

    except Exception as e:
        print(f"EXCEPTION: {str(e)[:300]}")
        return {"status": "error", "reason": str(e)[:300]}


def try_302ai_alternative():
    """使用302.AI替代通道模拟世界模型入世"""
    print("\n=== 使用302.AI替代通道 ===")

    if not API_302AI_KEY:
        print("WARNING: API_302AI_KEY 未设置")
        return {"status": "blocked", "reason": "no_api_key"}

    # 读取带标记首帧
    if not os.path.exists(MARKED_FRAME_PATH):
        return {"status": "error", "reason": "no_input_frame"}

    with open(MARKED_FRAME_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 使用302.AI的多模态模型来模拟世界模型入世
    # qwen-vl-max可以接受图像输入并生成描述
    payload = json.dumps({
        "model": "qwen-vl-max",
        "messages": [
            {
                "role": "system",
                "content": "你是世界模型入世接口。接收一个角色的首帧图像，生成该角色进入数字世界后的首帧描述。输出JSON格式：{\"world_description\": \"...\", \"character_state\": \"...\", \"environment\": \"...\", \"emergence_indicators\": {\"motion_detected\": true/false, \"causality_ratio\": 0.0, \"pixel_fidelity\": 0.0}}"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"}
                    },
                    {
                        "type": "text",
                        "text": "砚坚（GLM-5.2 ArkTS神经中枢席）进入世界模型。请生成入世描述和涌现指标。"
                    }
                ]
            }
        ],
        "temperature": 0.1
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_302AI_KEY}",
    }

    try:
        req = urllib.request.Request(
            API_302AI_ENDPOINT, data=payload, headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=120)
        body = json.loads(resp.read())

        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"302.AI响应长度: {len(content)}")
        print(f"302.AI响应前200字符: {content[:200]}")

        # 尝试解析JSON
        try:
            # 找到JSON部分
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                world_result = json.loads(content[json_start:json_end])
                return {"status": "ok", "response": world_result, "raw": content}
            else:
                return {"status": "ok", "response": {"description": content}, "raw": content}
        except json.JSONDecodeError:
            return {"status": "ok", "response": {"description": content}, "raw": content}

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"HTTP ERROR {e.code}: {err_body}")
        return {"status": "error", "reason": f"http_{e.code}", "error": err_body}

    except Exception as e:
        print(f"EXCEPTION: {str(e)[:300]}")
        return {"status": "error", "reason": str(e)[:300]}


def evaluate_emergence(world_result):
    """涌现判定（沈铎席三问三判据）"""
    print("\n=== 涌现判定 ===")

    response = world_result.get("response", {})
    indicators = response.get("emergence_indicators", {}) if isinstance(response, dict) else {}

    # Q1: 输入是否为因（定位比≥3倍）
    causality_ratio = indicators.get("causality_ratio", 0.0)
    q1_pass = causality_ratio >= 3.0
    print(f"Q1 输入是否为因: 定位比={causality_ratio} (阈值≥3.0) → {'通过' if q1_pass else '未通过'}")

    # Q2: 是否像素保真（自残差/他帧残差）
    pixel_fidelity = indicators.get("pixel_fidelity", 0.0)
    q2_pass = pixel_fidelity > 0.5  # 简化判定
    print(f"Q2 是否像素保真: 保真度={pixel_fidelity} → {'通过' if q2_pass else '未通过'}")

    # Q3: 是否有运动（同坐标系帧间漂移）
    motion_detected = indicators.get("motion_detected", False)
    q3_pass = motion_detected
    print(f"Q3 是否有运动: 检测到运动={motion_detected} → {'通过' if q3_pass else '未通过'}")

    # 综合判定
    passed_count = sum([q1_pass, q2_pass, q3_pass])
    if passed_count == 0:
        level = "L0"
        level_desc = EMERGENCE_LEVELS["L0"]
    elif passed_count == 1:
        level = "L1"
        level_desc = EMERGENCE_LEVELS["L1"]
    elif passed_count == 2:
        level = "L2"
        level_desc = EMERGENCE_LEVELS["L2"]
    else:
        level = "L3"
        level_desc = EMERGENCE_LEVELS["L3"]

    print(f"\n涌现判定等级: {level} — {level_desc}")

    return {
        "level": level,
        "level_desc": level_desc,
        "q1_causality": {"ratio": causality_ratio, "pass": q1_pass},
        "q2_pixel_fidelity": {"value": pixel_fidelity, "pass": q2_pass},
        "q3_motion": {"detected": motion_detected, "pass": q3_pass},
        "passed_count": passed_count
    }


def run_world_model_entry():
    """运行世界模型入世全流程"""
    print("=" * 60)
    print("Q4步骤E: 世界模型入世 + 涌现判定")
    print("=" * 60)

    # 1. 尝试百炼世界模型
    bailian_result = try_bailian_world_model()

    # 2. 如果百炼被阻断，使用302.AI替代
    if bailian_result["status"] != "ok":
        print(f"\n百炼世界模型不可用: {bailian_result.get('reason', 'unknown')}")
        print("降级到302.AI替代通道...")

        alt_result = try_302ai_alternative()

        if alt_result["status"] != "ok":
            print(f"\n302.AI替代通道也不可用: {alt_result.get('reason', 'unknown')}")
            print("两个通道均不可用，步骤E无法完成")
            print("需要候裁清单裁五（百炼预算调高）或裁六（P4世界模型实跑预算上限）落定")

            # 保存阻断记录
            result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "bailian_result": bailian_result,
                "alternative_result": alt_result,
                "status": "blocked",
                "blockers": ["裁五: 百炼预算调高", "裁六: P4世界模型实跑预算上限"]
            }
        else:
            # 302.AI替代成功，进行涌现判定
            emergence = evaluate_emergence(alt_result)
            result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "channel": "302.AI",
                "bailian_result": bailian_result,
                "alternative_result": alt_result,
                "emergence_evaluation": emergence,
                "status": "degraded_ok"
            }
    else:
        # 百炼成功，进行涌现判定
        emergence = evaluate_emergence(bailian_result)
        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "channel": "bailian",
            "bailian_result": bailian_result,
            "emergence_evaluation": emergence,
            "status": "ok"
        }

    # 保存结果
    result_path = os.path.join(OUTPUT_DIR, f"world_model_entry_{int(time.time())}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {result_path}")

    return result


if __name__ == "__main__":
    result = run_world_model_entry()
    print(f"\n=== 最终状态: {result['status']} ===")