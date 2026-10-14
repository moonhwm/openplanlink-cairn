#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
火山引擎ImageTo3D端点深入测试 v2
基于v1发现：contents/generations端点接收请求但超时，需更长超时
格式A（content参数）是正确格式，但3D生成耗时较长

SPDX-License-Identifier: AGPL-3.0
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-12
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any

ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3"

HEADERS = {
    "Authorization": f"Bearer {ARK_API_KEY}",
    "Content-Type": "application/json"
}

def test_imageto3d_with_url() -> Dict[str, Any]:
    """
    使用URL格式图片（而非base64）调用contents/generations
    v1中base64图片导致超时，可能因为payload过大
    改用URL格式，或使用更小的图片
    """
    print("\n" + "="*60)
    print("测试1：contents/generations with content（URL格式）")
    print("="*60)

    # 先生成图片，获取URL
    print("\n[1] 生成图片（获取URL）...")
    payload_img = {
        "model": "doubao-seedream-4-0-20260415",
        "prompt": "A simple 3D character: a scholar in blue robe, front view, game style",
        "size": "512x512",  # 更小的尺寸
        "response_format": "url"
    }

    url_img = f"{ARK_ENDPOINT}/images/generations"
    try:
        resp = requests.post(url_img, headers=HEADERS, json=payload_img, timeout=60)
        print(f"状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"❌ 图片生成失败: {resp.text[:300]}")
            # 尝试b64_json格式
            payload_img["response_format"] = "b64_json"
            resp = requests.post(url_img, headers=HEADERS, json=payload_img, timeout=60)
            print(f"重试状态码: {resp.status_code}")
            if resp.status_code != 200:
                return {"status": "failed", "error": "image_generation_failed", "detail": resp.text[:300]}

        data = resp.json()
        image_url = None
        b64_image = None

        if "data" in data and len(data["data"]) > 0:
            item = data["data"][0]
            if "url" in item:
                image_url = item["url"]
                print(f"✅ 图片URL获取成功: {image_url[:80]}...")
            elif "b64_json" in item:
                b64_image = item["b64_json"]
                print(f"✅ base64图片获取成功，长度: {len(b64_image)}")

    except Exception as e:
        print(f"❌ 图片生成异常: {e}")
        return {"status": "error", "exception": str(e)}

    # 调用contents/generations进行ImageTo3D
    print("\n[2] 调用contents/generations进行ImageTo3D...")

    if image_url:
        content_item = {
            "type": "image_url",
            "image_url": {"url": image_url}
        }
    elif b64_image:
        content_item = {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"}
        }
    else:
        return {"status": "failed", "error": "no_image_data"}

    payload_3d = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [content_item]
    }

    url_3d = f"{ARK_ENDPOINT}/contents/generations"
    print(f"POST {url_3d}")
    print(f"模型: doubao-seed3d-2-0-260328")
    print(f"超时: 300秒")

    try:
        start_time = time.time()
        resp = requests.post(url_3d, headers=HEADERS, json=payload_3d, timeout=300)
        elapsed = time.time() - start_time
        print(f"状态码: {resp.status_code} (耗时: {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ ImageTo3D成功！")
            print(f"  响应keys: {list(data.keys())}")
            # 分析响应结构
            for key in data:
                val = data[key]
                if isinstance(val, str):
                    print(f"  {key}: {val[:100]}...")
                elif isinstance(val, list):
                    print(f"  {key}: list[{len(val)}]")
                    if len(val) > 0:
                        print(f"    [0] keys: {list(val[0].keys()) if isinstance(val[0], dict) else type(val[0])}")
                elif isinstance(val, dict):
                    print(f"  {key}: dict keys={list(val.keys())}")
                else:
                    print(f"  {key}: {val}")
            return {"status": "success", "elapsed_seconds": round(elapsed, 1), "raw_response": data}
        else:
            print(f"❌ ImageTo3D失败")
            print(f"  响应: {resp.text[:500]}")
            return {"status": "failed", "code": resp.status_code, "error": resp.text[:500], "elapsed": round(elapsed, 1)}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ 超时（{elapsed:.1f}s）——3D生成可能需要更长时间")
        return {"status": "timeout", "elapsed": round(elapsed, 1)}
    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"status": "error", "exception": str(e)}


def test_textto3d() -> Dict[str, Any]:
    """
    尝试TextTo3D（直接文本生成3D）
    有些3D模型支持直接从文本生成，不需要图片输入
    """
    print("\n" + "="*60)
    print("测试2：TextTo3D（contents/generations with text content）")
    print("="*60)

    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "text", "text": "A 3D model of a scholar character wearing a dark blue academic robe with silver cryptography badges"}
        ]
    }

    url = f"{ARK_ENDPOINT}/contents/generations"
    print(f"POST {url}")
    print(f"超时: 300秒")

    try:
        start_time = time.time()
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=300)
        elapsed = time.time() - start_time
        print(f"状态码: {resp.status_code} (耗时: {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ TextTo3D成功！")
            print(f"  响应keys: {list(data.keys())}")
            return {"status": "success", "elapsed_seconds": round(elapsed, 1), "raw_response": data}
        else:
            print(f"❌ TextTo3D失败")
            print(f"  响应: {resp.text[:500]}")
            return {"status": "failed", "code": resp.status_code, "error": resp.text[:500], "elapsed": round(elapsed, 1)}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ 超时（{elapsed:.1f}s）")
        return {"status": "timeout", "elapsed": round(elapsed, 1)}
    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"status": "error", "exception": str(e)}


def test_explore_api_docs() -> Dict[str, Any]:
    """
    通过API探索火山引擎支持的3D生成格式
    尝试不同的content结构和参数组合
    """
    print("\n" + "="*60)
    print("测试3：探索API参数格式")
    print("="*60)

    results = {}

    # 尝试3-1：content with type="image" (而非"image_url")
    print("\n--- 3-1: content type='image' ---")
    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "image", "image": "https://example.com/test.png"}
        ]
    }
    url = f"{ARK_ENDPOINT}/contents/generations"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        print(f"状态码: {resp.status_code}")
        results["type_image"] = {"code": resp.status_code, "response": resp.text[:300]}
    except Exception as e:
        results["type_image"] = {"status": "error", "exception": str(e)}

    # 尝试3-2：content with type="input_image"
    print("\n--- 3-2: content type='input_image' ---")
    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "input_image", "image_url": "https://example.com/test.png"}
        ]
    }
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        print(f"状态码: {resp.status_code}")
        results["type_input_image"] = {"code": resp.status_code, "response": resp.text[:300]}
    except Exception as e:
        results["type_input_image"] = {"status": "error", "exception": str(e)}

    # 尝试3-3：带prompt参数的contents/generations
    print("\n--- 3-3: contents/generations with prompt ---")
    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "prompt": "A scholar character in blue robe",
        "content": [
            {"type": "text", "text": "Generate 3D model"}
        ]
    }
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        print(f"状态码: {resp.status_code}")
        results["with_prompt"] = {"code": resp.status_code, "response": resp.text[:300]}
    except Exception as e:
        results["with_prompt"] = {"status": "error", "exception": str(e)}

    # 尝试3-4：images/generations with 3D model + prompt
    print("\n--- 3-4: images/generations with 3D model + prompt ---")
    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "prompt": "A 3D model of a scholar character"
    }
    url_img = f"{ARK_ENDPOINT}/images/generations"
    try:
        resp = requests.post(url_img, headers=HEADERS, json=payload, timeout=30)
        print(f"状态码: {resp.status_code}")
        results["images_with_prompt"] = {"code": resp.status_code, "response": resp.text[:300]}
    except Exception as e:
        results["images_with_prompt"] = {"status": "error", "exception": str(e)}

    return results


def main():
    print("="*60)
    print("火山引擎ImageTo3D端点深入测试 v2")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": "volcengine_imageto3d_deep_test_v2",
    }

    # 测试1：ImageTo3D with URL
    result1 = test_imageto3d_with_url()
    all_results["test1_imageto3d"] = result1

    # 测试2：TextTo3D
    result2 = test_textto3d()
    all_results["test2_textto3d"] = result2

    # 测试3：探索API格式
    result3 = test_explore_api_docs()
    all_results["test3_explore_formats"] = result3

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"测试1（ImageTo3D with URL）: {result1.get('status', 'unknown')}")
    print(f"测试2（TextTo3D）: {result2.get('status', 'unknown')}")
    for key, val in result3.items():
        print(f"测试3（{key}）: {val.get('code', val.get('status', 'unknown'))}")

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "volcengine_imageto3d_deep_test_v2_20261012.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存: {output_path}")

    return all_results


if __name__ == "__main__":
    main()