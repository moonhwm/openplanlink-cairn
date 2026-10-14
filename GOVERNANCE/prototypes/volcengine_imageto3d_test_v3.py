#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
火山引擎ImageTo3D端点深入测试 v3
基于v2发现：contents/generations需要image_data参数（字符串类型）
图片生成最小尺寸要求921600像素（约960x960）

SPDX-License-Identifier: AGPL-3.0
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-12
"""

import os
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


def generate_image() -> Dict[str, Any]:
    """生成图片（至少1024x1024满足921600像素要求）"""
    print("\n[1] 生成图片...")
    payload = {
        "model": "doubao-seedream-4-0-20260415",
        "prompt": "A 3D character concept art of a scholar named YanJian wearing a dark blue academic robe with silver cryptography badges, glowing data-stream eyes, holding an algorithm manual, standing in a virtual world with cryptography forest background, full body, front view, high detail, game character style",
        "size": "1024x1024",
        "response_format": "url"
    }

    url = f"{ARK_ENDPOINT}/images/generations"
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                item = data["data"][0]
                if "url" in item:
                    print(f"✅ 图片URL: {item['url'][:80]}...")
                    return {"status": "success", "image_url": item["url"]}
                elif "b64_json" in item:
                    print(f"✅ base64图片，长度: {len(item['b64_json'])}")
                    return {"status": "success", "b64_image": item["b64_json"]}
            return {"status": "success", "raw": data}
        else:
            print(f"❌ 失败: {resp.text[:300]}")
            return {"status": "failed", "error": resp.text[:300]}
    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"status": "error", "exception": str(e)}


def test_imageto3d_image_data(image_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用image_data参数调用contents/generations
    v2发现：API要求body -> image_data为字符串类型
    """
    print("\n[2] ImageTo3D with image_data参数")

    # 准备image_data
    image_data = None
    if "image_url" in image_result:
        image_data = image_result["image_url"]
        print(f"  使用URL作为image_data: {image_data[:80]}...")
    elif "b64_image" in image_result:
        image_data = f"data:image/png;base64,{image_result['b64_image']}"
        print(f"  使用base64作为image_data")

    if not image_data:
        print("❌ 无图片数据")
        return {"status": "failed", "error": "no_image_data"}

    # 尝试多种payload格式

    # 格式1：image_data作为顶层字段
    print("\n--- 格式1：image_data顶层字段 ---")
    payload1 = {
        "model": "doubao-seed3d-2-0-260328",
        "image_data": image_data
    }
    result1 = _try_request(payload1, "格式1")

    if result1.get("status") == "success":
        return result1

    # 格式2：image_data + content
    print("\n--- 格式2：image_data + content ---")
    payload2 = {
        "model": "doubao-seed3d-2-0-260328",
        "image_data": image_data,
        "content": [{"type": "text", "text": "Convert to 3D model"}]
    }
    result2 = _try_request(payload2, "格式2")

    if result2.get("status") == "success":
        return result2

    # 格式3：image_data + prompt
    print("\n--- 格式3：image_data + prompt ---")
    payload3 = {
        "model": "doubao-seed3d-2-0-260328",
        "image_data": image_data,
        "prompt": "Convert this image to a 3D model"
    }
    result3 = _try_request(payload3, "格式3")

    if result3.get("status") == "success":
        return result3

    # 格式4：content数组中包含image_data
    print("\n--- 格式4：content中包含image_data ---")
    payload4 = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "image_data", "image_data": image_data}
        ]
    }
    result4 = _try_request(payload4, "格式4")

    if result4.get("status") == "success":
        return result4

    # 格式5：content中包含image_url + image_data
    print("\n--- 格式5：content中image_url格式 ---")
    payload5 = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "image_url", "image_url": {"url": image_data}}
        ]
    }
    result5 = _try_request(payload5, "格式5")

    return result5 if result5.get("status") == "success" else {
        "status": "all_failed",
        "results": [result1, result2, result3, result4, result5]
    }


def _try_request(payload: Dict, label: str) -> Dict[str, Any]:
    """尝试发送请求"""
    url = f"{ARK_ENDPOINT}/contents/generations"
    print(f"POST {url}")
    print(f"Payload keys: {list(payload.keys())}")

    try:
        start = time.time()
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=300)
        elapsed = time.time() - start
        print(f"状态码: {resp.status_code} (耗时: {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ {label} 成功！")
            print(f"  响应keys: {list(data.keys())}")
            # 详细分析响应
            for key in data:
                val = data[key]
                if isinstance(val, str):
                    print(f"  {key}: {val[:150]}...")
                elif isinstance(val, list):
                    print(f"  {key}: list[{len(val)}]")
                    if len(val) > 0 and isinstance(val[0], dict):
                        print(f"    [0] keys: {list(val[0].keys())}")
                elif isinstance(val, dict):
                    print(f"  {key}: dict keys={list(val.keys())}")
                else:
                    print(f"  {key}: {type(val).__name__} = {val}")
            return {"status": "success", "label": label, "elapsed": round(elapsed, 1), "raw_response": data}
        else:
            print(f"❌ {label} 失败: {resp.text[:400]}")
            return {"status": "failed", "label": label, "code": resp.status_code, "error": resp.text[:400], "elapsed": round(elapsed, 1)}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"❌ {label} 超时（{elapsed:.1f}s）")
        return {"status": "timeout", "label": label, "elapsed": round(elapsed, 1)}
    except Exception as e:
        print(f"❌ {label} 异常: {e}")
        return {"status": "error", "label": label, "exception": str(e)}


def test_hyper3d_textto3d() -> Dict[str, Any]:
    """测试hyper3d-gen2-260112的TextTo3D能力"""
    print("\n[3] 测试hyper3d-gen2-260112 TextTo3D")

    # hyper3d可能支持text-to-3D
    payload = {
        "model": "hyper3d-gen2-260112",
        "content": [
            {"type": "text", "text": "A 3D model of a scholar character wearing a dark blue robe"}
        ]
    }
    return _try_request(payload, "hyper3d_textto3d")


def main():
    print("="*60)
    print("火山引擎ImageTo3D端点深入测试 v3")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": "volcengine_imageto3d_deep_test_v3",
    }

    # 步骤1：生成图片
    image_result = generate_image()
    all_results["step1_image_generation"] = image_result

    # 步骤2：ImageTo3D with image_data
    if image_result["status"] == "success":
        result_3d = test_imageto3d_image_data(image_result)
        all_results["step2_imageto3d"] = result_3d
    else:
        all_results["step2_imageto3d"] = {"status": "skipped"}

    # 步骤3：hyper3d TextTo3D
    result_hyper3d = test_hyper3d_textto3d()
    all_results["step3_hyper3d_textto3d"] = result_hyper3d

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"步骤1（图片生成）: {image_result['status']}")
    print(f"步骤2（ImageTo3D）: {all_results['step2_imageto3d'].get('status', 'unknown')}")
    print(f"步骤3（hyper3d TextTo3D）: {result_hyper3d.get('status', 'unknown')}")

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "volcengine_imageto3d_deep_test_v3_20261012.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存: {output_path}")

    return all_results


if __name__ == "__main__":
    main()