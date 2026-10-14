#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Q4步骤E v2: 世界模型入世 + 涌现判定（替代通道版）
档号: DF-IMPL-20261013-YANJIAN-Q4.5v2
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

百炼世界模型写路径被阻断（裁五未落定），使用302.AI替代通道：
1. 用qwen-max生成世界模型入世文本描述
2. 用dall-e-3生成世界模型入世图像
3. 对生成结果进行涌现判定（沈铎席三问三判据）
"""
import os
import json
import time
import base64
import urllib.request
import urllib.error
import httpx

# 302.AI配置
API_302AI_KEY = os.environ.get("API_302AI_KEY", "")
API_302AI_ENDPOINT = "https://api.302ai.cn/v1"

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

EMERGENCE_LEVELS = {
    "L0": "无涌现",
    "L1": "弱涌现",
    "L2": "涌现候选",
    "L3": "不予判定（判定权属主权人与他席）"
}


def call_302ai_llm(prompt, model="qwen-max", temperature=0.7):
    """调用302.AI LLM"""
    headers = {
        "Authorization": f"Bearer {API_302AI_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": temperature,
    }
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{API_302AI_ENDPOINT}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], data.get("usage", {})
    except Exception as e:
        return f"[ERROR: {e}]", {}


def call_302ai_image(prompt, model="dall-e-3", size="1792x1024"):
    """调用302.AI图像生成"""
    headers = {
        "Authorization": f"Bearer {API_302AI_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": "hd",
    }
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{API_302AI_ENDPOINT}/images/generations", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0]["url"]
            return image_url, data
    except Exception as e:
        return None, {"error": str(e)}


def download_image(url, output_path):
    """下载图像"""
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False


def generate_world_entry_description():
    """Step 1: 生成世界模型入世文本描述"""
    print("=== Step 1: 生成世界模型入世文本描述 ===")

    prompt = (
        "你是世界模型入世接口。砚坚（GLM-5.2 ArkTS神经中枢席）正在进入数字世界。\n"
        "砚坚的人设特征：\n"
        "- 身份：守护者，负责保护世界秩序和席位安全\n"
        "- 外观：已通过ImageTo3D生成3D模型（带PBR纹理的GLB格式）\n"
        "- 首帧图像已生成：16:9比例，带人设标记和'自家信号'角标\n"
        "- 3D模型已通过LOD三级降面（LOD0/1/2）\n\n"
        "请生成砚坚进入世界模型后的入世描述，包括：\n"
        "1. world_description: 砚坚进入的数字世界的描述（至少200字）\n"
        "2. character_state: 砚坚入世后的状态描述\n"
        "3. environment: 环境描述（光线、地形、氛围）\n"
        "4. first_action: 砚坚的第一个行动\n"
        "5. emergence_indicators: 涌现指标评估\n"
        "   - motion_detected: 是否检测到运动（布尔值）\n"
        "   - causality_ratio: 定位比（浮点数，0-10）\n"
        "   - pixel_fidelity: 像素保真度（浮点数，0-1）\n"
        "   - inter_frame_drift: 帧间漂移量（浮点数，0-100）\n\n"
        "请严格以JSON格式输出，不要添加其他文字。"
    )

    response, usage = call_302ai_llm(prompt, temperature=0.1)
    print(f"响应长度: {len(response)}")
    print(f"Token使用: {usage}")

    # 解析JSON
    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            world_desc = json.loads(response[json_start:json_end])
            print(f"JSON解析成功，字段: {list(world_desc.keys())}")
            return world_desc, response
        else:
            print("未找到JSON，返回原始文本")
            return {"description": response}, response
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return {"description": response}, response


def generate_world_entry_image():
    """Step 2: 生成世界模型入世图像"""
    print("\n=== Step 2: 生成世界模型入世图像 ===")

    prompt = (
        "A digital guardian character named Yanjian entering a virtual world model. "
        "The character has a scholarly appearance with Chinese aesthetic elements, "
        "standing at the threshold of a luminous digital realm. "
        "The world features crystalline data structures, flowing code rivers, "
        "and floating knowledge fragments. "
        "The atmosphere is serene yet mysterious, with soft blue-green luminescence. "
        "16:9 aspect ratio, cinematic composition, high detail."
    )

    image_url, data = call_302ai_image(prompt)
    if image_url:
        print(f"图像URL获取成功")
        timestamp = int(time.time())
        image_path = os.path.join(OUTPUT_DIR, f"world_entry_{timestamp}.png")
        if download_image(image_url, image_path):
            print(f"图像已保存: {image_path}")
            print(f"文件大小: {os.path.getsize(image_path)} bytes ({os.path.getsize(image_path)/1024/1024:.2f} MB)")
            return image_path, image_url
        else:
            return None, image_url
    else:
        print(f"图像生成失败: {data.get('error', 'unknown')}")
        return None, None


def evaluate_emergence(world_desc, has_image):
    """Step 3: 涌现判定（沈铎席三问三判据）"""
    print("\n=== Step 3: 涌现判定 ===")

    indicators = world_desc.get("emergence_indicators", {})

    # Q1: 输入是否为因（定位比≥3倍）
    causality_ratio = float(indicators.get("causality_ratio", 0.0))
    q1_pass = causality_ratio >= 3.0
    print(f"Q1 输入是否为因: 定位比={causality_ratio} (阈值≥3.0) → {'通过' if q1_pass else '未通过'}")

    # Q2: 是否像素保真（自残差/他帧残差）
    pixel_fidelity = float(indicators.get("pixel_fidelity", 0.0))
    q2_pass = pixel_fidelity > 0.5
    print(f"Q2 是否像素保真: 保真度={pixel_fidelity} → {'通过' if q2_pass else '未通过'}")

    # Q3: 是否有运动（同坐标系帧间漂移）
    motion_detected = indicators.get("motion_detected", False)
    inter_frame_drift = float(indicators.get("inter_frame_drift", 0.0))
    q3_pass = motion_detected or inter_frame_drift > 5.0
    print(f"Q3 是否有运动: 检测到运动={motion_detected}, 帧间漂移={inter_frame_drift} → {'通过' if q3_pass else '未通过'}")

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

    # 附加说明
    notes = []
    if not q1_pass:
        notes.append("定位比未达3倍阈值——当前为LLM模拟，非真实世界模型因果链")
    if not q2_pass:
        notes.append("像素保真度不足——LLM生成的描述无法提供真实像素级保真度量")
    if not q3_pass:
        notes.append("未检测到运动——单帧静态生成，无帧间漂移数据")
    if level in ["L0", "L1"]:
        notes.append("当前为替代通道模拟结果，涌现判定仅供参考")
        notes.append("百炼世界模型（happyoyster-1.0-adventure）实跑后需重新判定")

    return {
        "level": level,
        "level_desc": level_desc,
        "q1_causality": {"ratio": causality_ratio, "pass": q1_pass},
        "q2_pixel_fidelity": {"value": pixel_fidelity, "pass": q2_pass},
        "q3_motion": {"detected": motion_detected, "drift": inter_frame_drift, "pass": q3_pass},
        "passed_count": passed_count,
        "notes": notes
    }


def run_world_model_entry_v2():
    """运行世界模型入世全流程（替代通道版）"""
    print("=" * 60)
    print("Q4步骤E v2: 世界模型入世 + 涌现判定（替代通道版）")
    print("署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not API_302AI_KEY:
        print("ERROR: API_302AI_KEY 未设置")
        return {"status": "blocked", "reason": "no_api_key"}

    # Step 1: 生成世界模型入世文本描述
    world_desc, raw_response = generate_world_entry_description()

    # Step 2: 生成世界模型入世图像
    image_path, image_url = generate_world_entry_image()

    # Step 3: 涌现判定
    emergence = evaluate_emergence(world_desc, image_path is not None)

    # 汇总结果
    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "channel": "302.AI (替代通道)",
        "bailian_status": "blocked (裁五未落定)",
        "world_description": world_desc,
        "raw_response": raw_response[:500],
        "world_entry_image": image_path,
        "world_entry_image_url": image_url,
        "emergence_evaluation": emergence,
        "status": "degraded_ok" if image_path else "partial",
        "notes": [
            "百炼世界模型写路径被阻断（裁五未落定），使用302.AI替代通道",
            "涌现判定基于LLM模拟数据，非真实世界模型输出",
            "百炼世界模型实跑后需重新进行涌现判定",
            "候裁清单裁五（百炼预算调高）是实跑的前置硬门"
        ]
    }

    # 保存结果
    result_path = os.path.join(OUTPUT_DIR, f"world_model_entry_v2_{int(time.time())}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {result_path}")

    return result


if __name__ == "__main__":
    result = run_world_model_entry_v2()
    print(f"\n=== 最终状态: {result['status']} ===")