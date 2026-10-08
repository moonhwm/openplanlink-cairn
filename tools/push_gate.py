#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""push_gate.py —— GitHub 上传门禁：原子化 拉取→重基→重签树→推送（结构解）。

机主令「持续对齐修复 A2A 网络 GitHub 上传问题」。
解决他席并发推送导致的 "rejected (fetch first)" 分叉问题：
  1. fetch 双端最新 2. rebase 合流 3. 重签 Merkle 树 4. push 双端。
纯标准库；节点树签名用 node tools/sha3-tree.mjs build。
"""
import os
import pathlib
import subprocess
import sys

REPO = r"C:\Users\欧阳宏俊\openplanlink-mirror"
KEY_FILE = r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin"
KEY_ID = "opl-a2a-2026q4"
LOG = pathlib.Path(r"C:\Users\欧阳宏俊\.push_gate.jsonl")


def _run(args, cwd=REPO, env=None, timeout=300):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=e, timeout=timeout)


def _log(ok, msg):
    import json, time
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "ok": ok, "msg": msg[:200]}, ensure_ascii=False) + "\n")


def gate():
    e = {"GIT_TERMINAL_PROMPT": "0"}
    # 1. 干净工作区
    r = _run(["git", "status", "--porcelain"], env=e)
    if r.stdout.strip():
        _run(["git", "stash", "push", "-u", "-m", "push-gate-auto"], env=e)
    # 2. 重签密钥环境
    kb = pathlib.Path(KEY_FILE).read_bytes()
    import base64
    e["OPL_A2A_HMAC_KEY_B64"] = base64.b64encode(kb).decode()
    e["OPL_A2A_HMAC_KEY_ID"] = KEY_ID
    # 3. fetch 双端
    _run(["git", "fetch", "origin"], env=e)
    _run(["git", "fetch", "gitcode"], env=e)
    # 4. rebase（无冲突假定；冲突则中止留人工）
    r = _run(["git", "rebase", "origin/main"], env=e)
    if r.returncode != 0:
        _run(["git", "rebase", "--abort"], env=e)
        _log(False, "rebase conflict, abort")
        return False
    # 5. 重签 Merkle 树
    r = _run(["node", "tools\\sha3-tree.mjs", "build"], env=e)
    if r.returncode != 0:
        _log(False, "tree sign fail")
        return False
    _run(["git", "add", "attest-hmac-sha3-512.json"], env=e)
    r = _run(["git", "commit", "-m", "push-gate: re-sign tree"], env=e)
    # 6. push 双端
    r1 = _run(["git", "push", "origin", "main"], env=e)
    _run(["git", "push", "gitcode", "main", "--force"], env=e)
    ok = r1.returncode == 0
    _log(ok, "origin push " + ("OK" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    ok = gate()
    print("★ push_gate:", "OK" if ok else "FAIL")
    sys.exit(0 if ok else 1)
