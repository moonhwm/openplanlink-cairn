#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
火山引擎ImageTo3D端点深入测试 v4
基于v3发现：
- 格式5（content中image_url格式）超时300秒——API接受了请求但3D生成耗时长
- 需要更长超时或异步轮询方式
- hyper3d-gen2-260112返回ModelLoading——需稍后重试

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


def generate_image_url() -> str:
    """生成图片并返回URL"""
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
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                img_url = data["data"][0].get("url")
                if img_url:
                    print(f"✅ 图片URL: {img_url[:80]}...")
                    return img_url
        print(f"❌ 图片生成失败: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ 异常: {e}")
    return ""


def test_imageto3d_long_timeout(image_url: str) -> Dict[str, Any]:
    """
    使用格式5（content中image_url格式）但超时设为600秒
    v3中超时300秒，这次给更长时间
    """
    print("\n[2] ImageTo3D（超时600秒）")

    payload = {
        "model": "doubao-seed3d-2-0-260328",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    }

    url = f"{ARK_ENDPOINT}/contents/generations"
    print(f"POST {url}")
    print(f"超时: 600秒")

    try:
        start = time.time()
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=600)
        elapsed = time.time() - start
        print(f"状态码: {resp.status_code} (耗时: {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ ImageTo3D成功！耗时{elapsed:.1f}s")
            print(f"  响应keys: {list(data.keys())}")
            for key in data:
                val = data[key]
                if isinstance(val, str):
                    print(f"  {key}: {val[:200]}...")
                elif isinstance(val, list):
                    print(f"  {key}: list[{len(val)}]")
                    if len(val) > 0 and isinstance(val[0], dict):
                        print(f"    [0] keys: {list(val[0].keys())}")
                        for k2, v2 in val[0].items():
                            if isinstance(v2, str):
                                print(f"      {k2}: {v2[:150]}...")
                            else:
                                print(f"      {k2}: {type(v2).__name__}")
                elif isinstance(val, dict):
                    print(f"  {key}: dict keys={list(val.keys())}")
                else:
                    print(f"  {key}: {type(val).__name__} = {val}")
            return {"status": "success", "elapsed": round(elapsed, 1), "raw_response": data}
        else:
            print(f"❌ 失败: {resp.text[:500]}")
            return {"status": "failed", "code": resp.status_code, "error": resp.text[:500], "elapsed": round(elapsed, 1)}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"❌ 超时（{elapsed:.1f}s）——3D生成可能需要超过10分钟")
        return {"status": "timeout", "elapsed": round(elapsed, 1)}
    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"status": "error", "exception": str(e)}


def test_async_endpoints(image_url: str) -> Dict[str, Any]:
    """
    探索异步API端点
    火山引擎可能支持任务提交+轮询模式
    """
    print("\n[3] 探索异步API端点")

    results = {}

    # 尝试tasks端点
    for endpoint in ["/contents/tasks", "/tasks", "/contents/async/generations"]:
        url = f"{ARK_ENDPOINT}{endpoint}"
        payload = {
            "model": "doubao-seed3d-2-0-260328",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
        print(f"\nPOST {url}")
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
            print(f"状态码: {resp.status_code}")
            results[endpoint] = {"code": resp.status_code, "response": resp.text[:300]}
        except Exception as e:
            print(f"❌ 异常: {e}")
            results[endpoint] = {"status": "error", "exception": str(e)}

    # 尝试GET /contents/tasks/{id}
    print("\n--- 探索GET端点 ---")
    for endpoint in ["/contents/tasks", "/tasks"]:
        url = f"{ARK_ENDPOINT}{endpoint}"
        print(f"\nGET {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            print(f"状态码: {resp.status_code}")
            results["GET_" + endpoint] = {"code": resp.status_code, "response": resp.text[:300]}
        except Exception as e:
            results["GET_" + endpoint] = {"status": "error", "exception": str(e)}

    return results


def test_hyper3d_retry() -> Dict[str, Any]:
    """重试hyper3d-gen2-260112"""
    print("\n[4] 重试hyper3d-gen2-260112")

    payload = {
        "model": "hyper3d-gen2-260112",
        "content": [
            {"type": "text", "text": "A 3D model of a scholar character wearing a dark blue robe"}
        ]
    }

    url = f"{ARK_ENDPOINT}/contents/generations"
    print(f"POST {url}")
    print(f"超时: 120秒")

    try:
        start = time.time()
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=120)
        elapsed = time.time() - start
        print(f"状态码: {resp.status_code} (耗时: {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ hyper3d成功！")
            print(f"  响应keys: {list(data.keys())}")
            return {"status": "success", "elapsed": round(elapsed, 1), "raw_response": data}
        else:
            print(f"❌ 失败: {resp.text[:500]}")
            return {"status": "failed", "code": resp.status_code, "error": resp.text[:500], "elapsed": round(elapsed, 1)}

    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"status": "error", "exception": str(e)}


def main():
    print("="*60)
    print("火山引擎ImageTo3D端点深入测试 v4")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": "volcengine_imageto3d_deep_test_v4",
    }

    # 步骤1：生成图片
    image_url = generate_image_url()
    all_results["step1_image_url"] = image_url[:100] if image_url else ""

    if not image_url:
        print("\n⚠️ 图片生成失败，无法继续测试")
        all_results["status"] = "blocked"
        _save_results(all_results)
        return

    # 步骤2：ImageTo3D长超时测试
    result_3d = test_imageto3d_long_timeout(image_url)
    all_results["step2_imageto3d_long_timeout"] = result_3d

    # 步骤3：探索异步端点
    async_results = test_async_endpoints(image_url)
    all_results["step3_async_endpoints"] = async_results

    # 步骤4：重试hyper3d
    hyper3d_result = test_hyper3d_retry()
    all_results["step4_hyper3d_retry"] = hyper3d_result

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"步骤2（ImageTo3D 600s超时）: {result_3d.get('status', 'unknown')} (耗时: {result_3d.get('elapsed', '?')}s)")
    print(f"步骤3（异步端点探索）: {len(async_results)}个端点测试")
    print(f"步骤4（hyper3d重试）: {hyper3d_result.get('status', 'unknown')}")

    _save_results(all_results)
    return all_results


def _save_results(results: Dict[str, Any]):
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "volcengine_imageto3d_deep_test_v4_20261012.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存: {output_path}")


if __name__ == "__main__":
    main()