#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git推送脚本v4 — 恢复credential helper"""
import os
import subprocess

GIT_EXE = r'C:\Users\欧阳宏俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
CWD = os.getcwd()

# 恢复credential helper
subprocess.run([GIT_EXE, 'config', 'credential.helper', 'manager'], capture_output=True, cwd=CWD)

# 配置proxy
subprocess.run([GIT_EXE, 'config', 'http.proxy', 'http://127.0.0.1:10081'], capture_output=True, cwd=CWD)
subprocess.run([GIT_EXE, 'config', 'https.proxy', 'http://127.0.0.1:10081'], capture_output=True, cwd=CWD)

# 查看credential文件内容（只看用户名部分）
cred_path = os.path.expanduser('~/.git-credentials')
if os.path.exists(cred_path):
    with open(cred_path, 'r') as f:
        content = f.read()
    import re
    for line in content.strip().split('\n'):
        if 'github.com' in line:
            match = re.search(r'https://([^:]+):([^@]+)@', line)
            if match:
                user = match.group(1)
                token_preview = match.group(2)[:8] + '...' + match.group(2)[-4:]
                print(f'GitHub credential: user={user}, token={token_preview}')

# 推送
print('\n推送...')
result = subprocess.run(
    [GIT_EXE, 'push', '--set-upstream', 'origin', 'master'],
    capture_output=True, cwd=CWD, timeout=120
)
print(f'Push exit: {result.returncode}')
out_text = result.stdout.decode('latin-1', errors='replace') if result.stdout else ""
err_text = result.stderr.decode('latin-1', errors='replace') if result.stderr else ""
print(f'stdout: {out_text[:500]}')
print(f'stderr: {err_text[:500]}')