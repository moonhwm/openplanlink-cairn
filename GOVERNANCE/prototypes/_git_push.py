#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git推送脚本"""
import os
import subprocess

GIT_EXE = r'C:\Users\欧阳宏俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
CWD = os.getcwd()

# 配置proxy
subprocess.run([GIT_EXE, 'config', 'http.proxy', 'http://127.0.0.1:10081'], capture_output=True, cwd=CWD)

# 配置credential helper为manager
subprocess.run([GIT_EXE, 'config', 'credential.helper', 'manager'], capture_output=True, cwd=CWD)

# 尝试推送
result = subprocess.run(
    [GIT_EXE, 'push', '--set-upstream', 'origin', 'master'],
    capture_output=True, cwd=CWD, timeout=120
)
print('Push exit:', result.returncode)
out_text = result.stdout.decode('latin-1', errors='replace') if result.stdout else ""
err_text = result.stderr.decode('latin-1', errors='replace') if result.stderr else ""
print('stdout:', out_text[:500])
print('stderr:', err_text[:500])

# 如果失败，尝试用GIT_SSH_COMMAND
if result.returncode != 0:
    print('\n尝试设置GIT_SSH...')
    env = os.environ.copy()
    # 找到ssh
    ssh_path = r'C:\Windows\System32\OpenSSH\ssh.exe'
    if os.path.exists(ssh_path):
        env['GIT_SSH'] = ssh_path
        result2 = subprocess.run(
            [GIT_EXE, 'push', '--set-upstream', 'origin', 'master'],
            capture_output=True, cwd=CWD, timeout=120, env=env
        )
        print('Push2 exit:', result2.returncode)
        out_text2 = result2.stdout.decode('latin-1', errors='replace') if result2.stdout else ""
        err_text2 = result2.stderr.decode('latin-1', errors='replace') if result2.stderr else ""
        print('stdout:', out_text2[:500])
        print('stderr:', err_text2[:500])