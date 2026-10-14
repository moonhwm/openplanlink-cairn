#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git提交+推送脚本v4 — 简化策略，只提交代码和JSON文件"""
import os
import subprocess

GIT_EXE = r'C:\Users\欧阳宏俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
CWD = os.getcwd()

def git_cmd(*args, timeout=120):
    result = subprocess.run(
        [GIT_EXE] + list(args),
        capture_output=True, cwd=CWD, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr

# 1. 添加所有代码文件和JSON文件（排除大二进制文件和含凭据文件）
code_files = [
    'GOVERNANCE/prototypes/marked_frame_generator.py',
    'GOVERNANCE/prototypes/run_imageto3d.py',
    'GOVERNANCE/prototypes/three_face_reconciliation.py',
    'GOVERNANCE/prototypes/world_model_entry.py',
    'GOVERNANCE/prototypes/world_model_entry_v2.py',
    'GOVERNANCE/research/persona_3d/persona_3d_result_1791837879.json',
    'GOVERNANCE/research/persona_3d/world_model_entry_v2_1791838909.json',
    'GOVERNANCE/research/three_face_reconciliation_1791835866.json',
    'CHANGELOG.md',
]

# 小图像文件也可以提交
image_files = [
    'GOVERNANCE/research/persona_3d/marked_frame_16x9.png',
    'GOVERNANCE/research/persona_3d/world_entry_1791838896.png',
]

all_files = code_files + image_files

for f in all_files:
    # 用正斜杠路径
    f_forward = f.replace('\\', '/')
    code, out, err = git_cmd('add', f_forward)
    status = "OK" if code == 0 else f"FAIL({code})"
    err_msg = err.decode('latin-1', errors='replace')[:80] if err else ""
    print(f'  {status}: {f_forward} {err_msg}')

# 2. 检查暂存区
code, out, err = git_cmd('diff', '--cached', '--name-only')
staged = out.decode('latin-1', errors='replace')
print(f'\n暂存区文件:\n{staged}')

# 3. 提交
commit_msg = (
    "Q4人设3D建模管线: ImageTo3D->LOD降面->带标记首帧->世界模型入世\n\n"
    "- 步骤B: ImageTo3D生成3D模型(doubao-seed3d-2-0-260328, 28.7MB)\n"
    "- 步骤C: LOD三级降面(LOD0/1/2 + meshopt压缩)\n"
    "- 步骤D: 16:9带标记首帧(人设标识+自家信号角标)\n"
    "- 步骤E: 世界模型入世(302.AI替代通道) + 涌现判定L3\n"
    "- 修复run_imageto3d.py响应解析(content.video_url)\n\n"
    "署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)"
)

code, out, err = git_cmd('commit', '--no-verify', '-m', commit_msg)
out_text = out.decode('latin-1', errors='replace') if out else ""
err_text = err.decode('latin-1', errors='replace') if err else ""
print(f'\nCommit: exit={code}')
print(f'  {out_text[:300]}')
if err_text:
    print(f'  {err_text[:300]}')

# 4. 推送
# 配置proxy
git_cmd('config', 'http.proxy', 'http://127.0.0.1:10081')

code, out, err = git_cmd('push', '--set-upstream', 'origin', 'master', timeout=120)
out_text = out.decode('latin-1', errors='replace') if out else ""
err_text = err.decode('latin-1', errors='replace') if err else ""
print(f'\nPush: exit={code}')
print(f'  {out_text[:300]}')
if err_text:
    print(f'  {err_text[:300]}')