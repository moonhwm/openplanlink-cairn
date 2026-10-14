#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Q4步骤B runner — 设置环境变量后调用run_imageto3d.py
凭据从环境变量读取，不落盘到文件。
"""
import os
import sys

# 设置环境变量（凭据不落盘到文件，仅在此运行时设置）
# 火山引擎API Key
os.environ["VOLCENGINE_API_KEY"] = os.environ.get("VOLCENGINE_API_KEY", "")
if not os.environ["VOLCENGINE_API_KEY"]:
    print("ERROR: 请先设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)

# 导入并运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_imageto3d import run_image_to_3d

result = run_image_to_3d()
if result:
    print(f"\n=== 最终结果 ===")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print("\n=== 失败 ===")