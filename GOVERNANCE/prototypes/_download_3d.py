#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本：从ImageTo3D结果JSON中提取URL并下载3D模型"""
import json
import os
import re
import subprocess
import time

result_file = "GOVERNANCE/research/persona_3d/persona_3d_result_1791837289.json"
d = json.load(open(result_file, "r", encoding="utf-8"))

err_str = d["error"]
match = re.search(r"video_url': '([^']+)'", err_str)
if match:
    url = match.group(1)
    print(f"URL长度: {len(url)}")
    print(f"URL前80字符: {url[:80]}")
    print(f"URL后80字符: {url[-80:]}")

    ts = int(time.time())
    model_path = f"GOVERNANCE/research/persona_3d/persona_3d_{ts}.zip"
    print(f"下载到: {model_path}")

    result = subprocess.run(
        ["curl", "-L", "-s", "-o", model_path, url],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0 and os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"下载成功! 大小: {size} bytes ({size/1024/1024:.1f} MB)")
    else:
        print(f"下载失败: curl exit {result.returncode}")
        print(f"stderr: {result.stderr[:300]}")
else:
    print("未找到video_url")
    print(f"error字段完整内容: {err_str}")