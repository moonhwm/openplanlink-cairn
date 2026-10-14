#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
火山引擎ImageTo3D端点深入测试
1. 先用doubao-seedream-4-0生成砚坚角色图片
2. 再用doubao-seed3d-2-0-260328将图片转换为3D模型

SPDX-License-Identifier: AGPL-3.0
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-12
"""

import os
import sys
import json
import time
import base64
import requests
from typing import Dict, Any, Optional

# 火山引擎ARK API配置
ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3"

# 模型配置
IMAGE_MODEL = "doubao-seedream-4-0-20260415"
MODEL_3D = "doubao-seed3d-2-0-260328"

HEADERS = {
    "Authorization": f"Bearer {ARK_API_KEY}",
    "Content-Type": "application/json"
}

def step1_generate_image() -> Dict[str, Any]:
    """步骤1：用doubao-seedream-4-0生成砚坚角色图片"""
    print("\n" + "="*60)
    print("步骤1：生成砚坚角色图片")
    print("="*60)

    prompt = (
        "A 3D character concept art of a scholar named YanJian wearing a "
        "dark blue academic robe with silver cryptography badges, glowing "
        "data-stream eyes, holding an algorithm manual, standing in a virtual "
        "world with cryptography forest background, full body, front view, "
        "high detail, game character style"
    )

    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "size": "1024x1024",
        "response_format": "b64_json"
    }

    url = f"{ARK_ENDPOINT}/images/generations"
    print(f"POST {url}")
    print(f"模型: {IMAGE_MODEL}")
    print(f"Prompt: {prompt[:80]}...")

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print("✅ 图片生成成功")
            # 提取base64图片数据
            if "data" in data and len(data["data"]) > 0:
                image_data = data["data"][0]
                if "b64_json" in image_data:
                    b64 = image_data["b64_json"]
                    print(f"  图片格式: base64")
                    print(f"  base64长度: {len(b64)}")
                    return {"status": "success", "b64_image": b64, "raw_response": data}
                elif "url" in image_data:
                    img_url = image_data["url"]
                    print(f"  图片URL: {img_url[:80]}...")
                    return {"status": "success", "image_url": img_url, "raw_response": data}
            return {"status": "success", "raw_response": data}
        else:
            print(f"❌ 图片生成失败")
            print(f"  响应: {resp.text[:500]}")
            return {"status": "failed", "error": resp.text, "code": resp.status_code}

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"status": "error", "exception": str(e)}


def step2_image_to_3d(image_result: Dict[str, Any]) -> Dict[str, Any]:
    """步骤2：用doubao-seed3d-2-0-260328将图片转换为3D模型"""
    print("\n" + "="*60)
    print("步骤2：ImageTo3D转换")
    print("="*60)

    # 构建图片输入数据
    if "b64_image" in image_result:
        # 使用base64图片
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_result['b64_image']}"
            }
        }
        print("使用base64图片作为输入")
    elif "image_url" in image_result:
        # 使用URL图片
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": image_result["image_url"]
            }
        }
        print("使用URL图片作为输入")
    else:
        print("❌ 无可用图片数据")
        return {"status": "failed", "error": "no_image_data"}

    # 尝试多种API格式

    # 格式A：contents/generations（OpenAI兼容格式）
    print("\n--- 尝试格式A：contents/generations ---")
    payload_a = {
        "model": MODEL_3D,
        "content": [image_content]
    }
    url_a = f"{ARK_ENDPOINT}/contents/generations"
    result_a = _try_api(url_a, payload_a, "格式A")

    if result_a["status"] == "success":
        return result_a

    # 格式B：images/generations with image input
    print("\n--- 尝试格式B：images/generations（带图片输入） ---")
    payload_b = {
        "model": MODEL_3D,
        "image": image_content["image_url"]["url"],
        "response_format": "b64_json"
    }
    url_b = f"{ARK_ENDPOINT}/images/generations"
    result_b = _try_api(url_b, payload_b, "格式B")

    if result_b["status"] == "success":
        return result_b

    # 格式C：chat/completions with vision format
    print("\n--- 尝试格式C：chat/completions（视觉格式） ---")
    payload_c = {
        "model": MODEL_3D,
        "messages": [
            {
                "role": "user",
                "content": [
                    image_content,
                    {"type": "text", "text": "Convert this image to a 3D model."}
                ]
            }
        ]
    }
    url_c = f"{ARK_ENDPOINT}/chat/completions"
    result_c = _try_api(url_c, payload_c, "格式C")

    if result_c["status"] == "success":
        return result_c

    # 格式D：contents/generations with messages format
    print("\n--- 尝试格式D：contents/generations（messages格式） ---")
    payload_d = {
        "model": MODEL_3D,
        "messages": [
            {
                "role": "user",
                "content": [
                    image_content,
                    {"type": "text", "text": "Generate a 3D model from this image."}
                ]
            }
        ]
    }
    url_d = f"{ARK_ENDPOINT}/contents/generations"
    result_d = _try_api(url_d, payload_d, "格式D")

    return result_d


def _try_api(url: str, payload: Dict, label: str) -> Dict[str, Any]:
    """尝试调用API"""
    print(f"POST {url}")
    print(f"Payload keys: {list(payload.keys())}")

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=120)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ {label} 成功！")
            print(f"  响应keys: {list(data.keys())}")
            # 保存完整响应用于分析
            return {"status": "success", "api_format": label, "raw_response": data}
        else:
            print(f"❌ {label} 失败")
            print(f"  响应: {resp.text[:500]}")
            return {"status": "failed", "api_format": label, "error": resp.text, "code": resp.status_code}

    except Exception as e:
        print(f"❌ {label} 异常: {e}")
        return {"status": "error", "api_format": label, "exception": str(e)}


def step3_explore_3d_endpoints() -> Dict[str, Any]:
    """步骤3：探索其他3D生成端点"""
    print("\n" + "="*60)
    print("步骤3：探索其他3D生成端点")
    print("="*60)

    results = {}

    # 尝试hyper3d-gen2-260112
    print("\n--- hyper3d-gen2-260112 ---")
    payload = {
        "model": "hyper3d-gen2-260112",
        "prompt": "A 3D model of a scholar character with cryptography theme",
        "response_format": "b64_json"
    }

    for endpoint in ["/images/generations", "/contents/generations"]:
        url = f"{ARK_ENDPOINT}{endpoint}"
        print(f"\nPOST {url}")
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
            print(f"状态码: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ 成功！keys: {list(data.keys())}")
                results["hyper3d_gen2_" + endpoint] = {"status": "success", "raw_response": data}
            else:
                print(f"❌ 失败: {resp.text[:300]}")
                results["hyper3d_gen2_" + endpoint] = {"status": "failed", "code": resp.status_code, "error": resp.text[:300]}
        except Exception as e:
            print(f"❌ 异常: {e}")
            results["hyper3d_gen2_" + endpoint] = {"status": "error", "exception": str(e)}

    # 尝试hitem3d-2-0-251223
    print("\n--- hitem3d-2-0-251223 ---")
    payload2 = {
        "model": "hitem3d-2-0-251223",
        "prompt": "A 3D model of a scholar character with cryptography theme",
        "response_format": "b64_json"
    }

    for endpoint in ["/images/generations", "/contents/generations"]:
        url = f"{ARK_ENDPOINT}{endpoint}"
        print(f"\nPOST {url}")
        try:
            resp = requests.post(url, headers=HEADERS, json=payload2, timeout=60)
            print(f"状态码: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ 成功！keys: {list(data.keys())}")
                results["hitem3d_" + endpoint] = {"status": "success", "raw_response": data}
            else:
                print(f"❌ 失败: {resp.text[:300]}")
                results["hitem3d_" + endpoint] = {"status": "failed", "code": resp.status_code, "error": resp.text[:300]}
        except Exception as e:
            print(f"❌ 异常: {e}")
            results["hitem3d_" + endpoint] = {"status": "error", "exception": str(e)}

    return results


def main():
    print("="*60)
    print("火山引擎ImageTo3D端点深入测试")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {ARK_API_KEY[:20]}...")
    print("="*60)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": "volcengine_imageto3d_deep_test",
        "api_key_fingerprint": ARK_API_KEY[:20] + "..."
    }

    # 步骤1：生成图片
    image_result = step1_generate_image()
    all_results["step1_image_generation"] = image_result

    # 步骤2：ImageTo3D转换（仅在图片生成成功时）
    if image_result["status"] == "success":
        result_3d = step2_image_to_3d(image_result)
        all_results["step2_image_to_3d"] = result_3d
    else:
        print("\n⚠️ 图片生成失败，跳过ImageTo3D步骤")
        all_results["step2_image_to_3d"] = {"status": "skipped", "reason": "image_generation_failed"}

    # 步骤3：探索其他3D端点
    endpoint_results = step3_explore_3d_endpoints()
    all_results["step3_explore_endpoints"] = endpoint_results

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    step1_status = all_results["step1_image_generation"]["status"]
    step2_status = all_results.get("step2_image_to_3d", {}).get("status", "skipped")

    print(f"步骤1（图片生成）: {step1_status}")
    print(f"步骤2（ImageTo3D）: {step2_status}")

    for key, val in all_results.get("step3_explore_endpoints", {}).items():
        print(f"步骤3（{key}）: {val.get('status', 'unknown')}")

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "volcengine_imageto3d_deep_test_20261012.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {output_path}")

    return all_results


if __name__ == "__main__":
    main()