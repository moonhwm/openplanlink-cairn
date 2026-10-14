#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Q4步骤B: 首帧图像 → 3D模型（火山引擎ImageTo3D）
档号: DF-IMPL-20261012-YANJIAN-Q4.2
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

使用上轮生成的砚坚人设首帧图像，调用火山引擎doubao-seed3d-2-0-260328生成3D模型。
预计耗时~10分钟。
"""
import os
import json
import time
import base64
import urllib.request
import urllib.error
import sys

# 配置
VOLCENGINE_API_KEY = os.environ.get("VOLCENGINE_API_KEY", "")
if not VOLCENGINE_API_KEY:
    # 从全局声明指定的凭据A:\OPL_A2A\connections\20261009-0304-night-opening\ 读取
    # 凭据不落盘到文件，从环境变量读取
    print("WARNING: VOLCENGINE_API_KEY 未设置，请通过环境变量设置")
    print("  PowerShell: $env:VOLCENGINE_API_KEY='your-key-here'")
    print("  然后运行: python run_imageto3d.py")
I2D_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/contents/generations"
MODEL = "doubao-seed3d-2-0-260328"

# 输入：上轮生成的首帧图像
FIRST_FRAME_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d", "first_frame_test.png"
)

# 输出目录
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d"
)

def run_image_to_3d():
    """运行ImageTo3D生成3D模型"""
    if not VOLCENGINE_API_KEY:
        print("ERROR: VOLCENGINE_API_KEY 环境变量未设置")
        return None

    if not os.path.exists(FIRST_FRAME_PATH):
        print(f"ERROR: 首帧图像不存在: {FIRST_FRAME_PATH}")
        return None

    print(f"输入图像: {FIRST_FRAME_PATH}")
    print(f"图像大小: {os.path.getsize(FIRST_FRAME_PATH)} bytes")

    # 读取图像并转为base64
    with open(FIRST_FRAME_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    image_url = f"data:image/png;base64,{image_data}"

    # 构建请求
    payload = json.dumps({
        "model": MODEL,
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
        ],
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLCENGINE_API_KEY}",
    }

    print(f"提交ImageTo3D请求... (模型: {MODEL})")
    print(f"预计耗时: ~10分钟")

    start_time = time.time()

    try:
        req = urllib.request.Request(
            I2D_ENDPOINT, data=payload, headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=900)  # 15分钟超时
        latency = time.time() - start_time
        body = json.loads(resp.read())

        print(f"\n请求完成! 耗时: {latency:.1f}秒 ({latency/60:.1f}分钟)")

        # 解析响应
        result = {
            "latency_sec": latency,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": MODEL,
            "input_image": FIRST_FRAME_PATH,
        }

        # 火山引擎ImageTo3D响应格式: {"model": "...", "content": {"video_url": "..."}}
        model_url = ""
        if "data" in body and len(body["data"]) > 0:
            model_url = body["data"][0].get("url", "")
        elif "content" in body and isinstance(body["content"], dict):
            model_url = body["content"].get("video_url", "")

        if model_url:
            result["model_url"] = model_url
            result["status"] = "ok"

            # 下载3D模型
            timestamp = int(time.time())
            model_path = os.path.join(OUTPUT_DIR, f"persona_3d_{timestamp}.zip")
            print(f"下载3D模型到: {model_path}")

            try:
                import subprocess
                dl_result = subprocess.run(
                    ["curl", "-L", "-s", "-o", model_path, model_url],
                    capture_output=True, text=True, timeout=300
                )
                if dl_result.returncode == 0 and os.path.exists(model_path):
                    result["model_path"] = model_path
                    result["model_size_bytes"] = os.path.getsize(model_path)
                    print(f"下载成功! 大小: {result['model_size_bytes']} bytes ({result['model_size_bytes']/1024/1024:.1f} MB)")
                else:
                    result["download_error"] = f"curl exit {dl_result.returncode}"
                    print(f"下载失败: curl exit {dl_result.returncode}")
            except Exception as e:
                result["download_error"] = str(e)[:200]
                print(f"下载异常: {e}")
        else:
            result["status"] = "error"
            result["error"] = f"响应中未找到模型URL: {json.dumps(body, ensure_ascii=False)[:1000]}"
            print(f"ERROR: 响应中未找到模型URL")

        # 保存结果JSON
        result_path = os.path.join(OUTPUT_DIR, f"persona_3d_result_{int(time.time())}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存: {result_path}")

        return result

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"HTTP ERROR {e.code}: {err_body}")
        return {"status": "error", "error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        print(f"EXCEPTION: {str(e)[:300]}")
        return {"status": "error", "error": str(e)[:300]}


if __name__ == "__main__":
    result = run_image_to_3d()
    if result:
        print(f"\n=== 最终结果 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n=== 失败 ===")