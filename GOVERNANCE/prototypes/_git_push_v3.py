#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git推送脚本v3 — 用HTTPS带凭据推送"""
import os
import subprocess
import urllib.parse

GIT_EXE = r'C:\Users\欧阳宏俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
CWD = os.getcwd()

# GitHub凭据
GH_USER = '454461837@qq.com'
GH_PASS = 'CH3CH2OH@hy3'

# URL编码密码
GH_PASS_ENCODED = urllib.parse.quote(GH_PASS, safe='')
GH_USER_ENCODED = urllib.parse.quote(GH_USER, safe='')

# 构建带凭据的URL
REMOTE_URL = f'https://{GH_USER_ENCODED}:{GH_PASS_ENCODED}@github.com/moonhwm/openplanlink-mirror.git'

print(f'设置remote URL（凭据已编码）...')

# 配置proxy
subprocess.run([GIT_EXE, 'config', 'http.proxy', 'http://127.0.0.1:10081'], capture_output=True, cwd=CWD)

# 设置remote URL
result = subprocess.run(
    [GIT_EXE, 'remote', 'set-url', 'origin', REMOTE_URL],
    capture_output=True, cwd=CWD
)
print(f'set-url exit: {result.returncode}')

# 推送
print('推送...')
result = subprocess.run(
    [GIT_EXE, 'push', '--set-upstream', 'origin', 'master'],
    capture_output=True, cwd=CWD, timeout=120
)
print(f'Push exit: {result.returncode}')
out_text = result.stdout.decode('latin-1', errors='replace') if result.stdout else ""
err_text = result.stderr.decode('latin-1', errors='replace') if result.stderr else ""
print(f'stdout: {out_text[:500]}')
print(f'stderr: {err_text[:500]}')

# 恢复remote URL（移除凭据）
CLEAN_URL = 'https://github.com/moonhwm/openplanlink-mirror.git'
subprocess.run([GIT_EXE, 'remote', 'set-url', 'origin', CLEAN_URL], capture_output=True, cwd=CWD)
print('Remote URL已恢复（移除凭据）')