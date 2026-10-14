#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WPS云盘文档检查 + K3集群技能检查 + 本地技能目录检查
"""
import os
import json
import time
import requests

results = {}

# ========== 1. WPS云盘关键目录检查 ==========
print("=" * 70)
print("[1/3] WPS云盘关键目录检查")
print("=" * 70)

wps_base = r"C:\Users\欧阳宏俊\WPS Cloud\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场"

key_dirs = [
    "Plan提示词工程",
    "Plan提示词工程\\Re0",
    "Plan提示词工程\\openplanlink-docx",
    "A2A共同体_公约与议会",
    "A2A共同体_总线指针与台账",
    "Kimi skill归总",
    "Loop 工程",
    "Harness 工程",
    "KI 人设及建模",
    "init",
    "k3-main-archive",
]

for d in key_dirs:
    full_path = os.path.join(wps_base, d)
    if os.path.exists(full_path):
        try:
            items = os.listdir(full_path)
            file_count = len(items)
            print(f"  ✅ {d}: {file_count}个文件/目录")
            # 列出前5个文件名
            for item in items[:5]:
                print(f"     - {item}")
            if file_count > 5:
                print(f"     ... 还有{file_count - 5}个")
            results[f"wps_{d.replace(chr(92), '_')}"] = {"status": "OK", "count": file_count, "items": items[:10]}
        except Exception as e:
            print(f"  ❌ {d}: 读取失败: {e}")
            results[f"wps_{d.replace(chr(92), '_')}"] = {"status": "ERROR", "msg": str(e)}
    else:
        print(f"  ❌ {d}: 不存在")
        results[f"wps_{d.replace(chr(92), '_')}"] = {"status": "NOT_FOUND"}

# ========== 2. K3集群自建技能检查 ==========
print()
print("=" * 70)
print("[2/3] K3集群自建技能检查（GitHub + 本地）")
print("=" * 70)

k3_skills = [
    "quota-guard-ops",
    "quota-ledger-ops",
    "seat-naming-ops",
    "persona-iteration-loop-ops",
    "k3-territory-studies",
    "iteration-convergence-ops",
    "diffusion-dynamics-extension",
    "quant-frontier-lab",
    "registry-knowledge-ops",
    "extpool-furnace-ops",
    "fusion-cast-op",
    "github-mirror-sync-ops",
    "govdoc-compliance-ops",
    "otl-format-ops",
    "quad-ops-umbrella",
    "glb-observatory-ops",
    "dcc-mcp-umbrella",
    "remotion-video-forge",
    "compshare-cli",
    "moonforge-ops",
    "moongate-craft",
    "v2fun-ops",
    "hyper3d-rodin-mcp",
    "star-owner-ops",
    "video-seer",
    "vector-verdict-ops",
    "tongtu-hub",
    "ima-skil",
]

# 2.1 检查GitHub qoder-skills-hub仓库
print("\n--- 2.1 GitHub qoder-skills-hub仓库技能检查 ---")
try:
    # 获取仓库根目录内容
    resp = requests.get(
        "https://api.github.com/repos/moonhwm/qoder-skills-hub/contents/",
        timeout=30,
        headers={"Accept": "application/vnd.github.v3+json"}
    )
    if resp.status_code == 200:
        root_items = resp.json()
        root_dirs = [item["name"] for item in root_items if item["type"] == "dir"]
        print(f"  根目录: {len(root_dirs)}个目录")
        
        # 检查每个K3技能是否存在于仓库中
        found_in_github = []
        not_found_in_github = []
        for skill in k3_skills:
            if skill in root_dirs:
                found_in_github.append(skill)
            else:
                # 尝试模糊匹配
                matches = [d for d in root_dirs if skill.lower() in d.lower() or d.lower() in skill.lower()]
                if matches:
                    found_in_github.append(f"{skill} → {matches[0]}")
                else:
                    not_found_in_github.append(skill)
        
        print(f"  ✅ 在GitHub中找到: {len(found_in_github)}")
        for s in found_in_github:
            print(f"     - {s}")
        print(f"  ❌ 在GitHub中未找到: {len(not_found_in_github)}")
        for s in not_found_in_github:
            print(f"     - {s}")
        
        results["k3_skills_github"] = {
            "found": found_in_github,
            "not_found": not_found_in_github,
            "total_dirs": len(root_dirs),
            "root_dirs": root_dirs[:20]
        }
    else:
        print(f"  ❌ GitHub API返回: {resp.status_code}")
        results["k3_skills_github"] = {"status": "FAIL", "code": resp.status_code}
except Exception as e:
    print(f"  ❌ GitHub检查失败: {e}")
    results["k3_skills_github"] = {"status": "ERROR", "msg": str(e)}

# 2.2 检查本地GOVERNANCE/skills目录
print("\n--- 2.2 本地GOVERNANCE/skills目录检查 ---")
local_skills_path = os.path.join(os.path.dirname(__file__), "..", "skills")
if os.path.exists(local_skills_path):
    local_items = os.listdir(local_skills_path)
    print(f"  本地skills目录: {len(local_items)}个文件/目录")
    for item in local_items[:20]:
        print(f"     - {item}")
    results["local_skills"] = {"status": "OK", "count": len(local_items), "items": local_items}
else:
    print(f"  ❌ 本地skills目录不存在: {local_skills_path}")
    results["local_skills"] = {"status": "NOT_FOUND"}

# ========== 3. 本地GOVERNANCE目录完整结构 ==========
print()
print("=" * 70)
print("[3/3] 本地GOVERNANCE目录完整结构")
print("=" * 70)

gov_path = os.path.join(os.path.dirname(__file__), "..")
if os.path.exists(gov_path):
    all_files = []
    for root, dirs, files in os.walk(gov_path):
        # 排除external目录（外部仓库）
        if "external" in root:
            continue
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), gov_path)
            all_files.append(rel_path)
    
    # 按类型分类
    md_files = [f for f in all_files if f.endswith(".md")]
    py_files = [f for f in all_files if f.endswith(".py")]
    json_files = [f for f in all_files if f.endswith(".json")]
    js_files = [f for f in all_files if f.endswith(".js") or f.endswith(".mjs")]
    ets_files = [f for f in all_files if f.endswith(".ets")]
    other_files = [f for f in all_files if not any(f.endswith(ext) for ext in [".md", ".py", ".json", ".js", ".mjs", ".ets"])]
    
    print(f"  总文件数: {len(all_files)}")
    print(f"  Markdown: {len(md_files)}")
    print(f"  Python: {len(py_files)}")
    print(f"  JSON: {len(json_files)}")
    print(f"  JavaScript: {len(js_files)}")
    print(f"  ArkTS: {len(ets_files)}")
    print(f"  其他: {len(other_files)}")
    
    # 列出所有.md文件
    print(f"\n  Markdown文件列表:")
    for f in sorted(md_files):
        print(f"     - {f}")
    
    # 列出所有.py文件
    print(f"\n  Python文件列表:")
    for f in sorted(py_files):
        print(f"     - {f}")
    
    results["local_governance"] = {
        "total": len(all_files),
        "md": len(md_files),
        "py": len(py_files),
        "json": len(json_files),
        "js": len(js_files),
        "ets": len(ets_files),
        "other": len(other_files),
        "md_files": sorted(md_files),
        "py_files": sorted(py_files)
    }

# ========== 汇总 ==========
print()
print("=" * 70)
print("汇总")
print("=" * 70)

wps_ok = sum(1 for k, v in results.items() if k.startswith("wps_") and v.get("status") == "OK")
wps_total = sum(1 for k in results if k.startswith("wps_"))
print(f"WPS云盘目录: {wps_ok}/{wps_total} 存在")

k3_found = len(results.get("k3_skills_github", {}).get("found", []))
k3_total = len(k3_skills)
print(f"K3集群技能(GitHub): {k3_found}/{k3_total} 找到")

local_skills_count = results.get("local_skills", {}).get("count", 0)
print(f"本地skills目录: {local_skills_count}个文件")

gov_total = results.get("local_governance", {}).get("total", 0)
print(f"本地GOVERNANCE文件总数: {gov_total}")

# 保存结果
output_path = os.path.join(os.path.dirname(__file__), "..", "research", f"wps_skills_check_{int(time.time())}.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: {output_path}")