# -*- coding: utf-8 -*-
"""sign_if_needed.py —— **树未变则免重签提交**（把 DF-PROPOSAL §甲 落实为本席流程）

背景（实测，见 DF-START5 §三 / bus_snr 轮38）：
  6 小时窗内 **51 次** `push-gate: re-sign tree` 提交 ⇒ **占总线噪声 100%**（SNR 0.726）。
  其中相当一部分**并未改变树**（或与既有 `attest-hmac-sha3-512.json` 完全相同）⇒
  **完全不必产生一次提交**（每次还附带守卫与推送往返）。

本器做法（**安全、可逆**）：
  1. 备份现有 `attest-hmac-sha3-512.json` 与哈希；
  2. 运行 `node tools/sha3-tree.mjs build`；
  3. 比对新旧文件**字节是否相同**：
     · **相同** ⇒ 恢复备份（确保工作树无变更）并**建议免提交**（退出码 0，`--json` 记 `needed=false`）
     · **不同** ⇒ 保留新件并**建议提交重签**（退出码 10，`--json` 记 `needed=true`）
  4. 全程**不提交、不推送**（只判定与建议）；`--force` 可强制保留新件。

用法:
  python sign_if_needed.py [--repo <路径>] [--json <路径>] [--force]
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ATT = "attest-hmac-sha3-512.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()



def log_verdict(needed, old_h, new_h, rc):
    """追加命中率台账（供统计"免重签"真实比例）。失败不影响判定。"""
    try:
        import datetime as _dt
        p = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\outbox\mem\sign_needed_log.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 "needed": needed, "old": (old_h or "")[:16],
                                 "new": (new_h or "")[:16], "rc": rc}, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\欧阳宏俊\openplanlink-mirror")
    ap.add_argument("--json")
    ap.add_argument("--force", action="store_true", help="即使未变也保留新件")
    a = ap.parse_args()

    repo = pathlib.Path(a.repo)
    att = repo / ATT
    if not att.exists():
        print("★ 无既有 %s ⇒ **需要**生成（needed=true）" % ATT)
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps({"needed": True, "why": "no existing attest"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 10

    # 🔴 前置：必须有签名密钥；否则 build 会 exit=1 且**不重写文件** ⇒ 会被误判为"树未变"（本席 2026-10-07 实证）
    if not os.environ.get("OPL_A2A_HMAC_KEY_B64"):
        kf = pathlib.Path.home() / ".a2a-hmac-key.bin"
        if kf.exists():
            import base64
            os.environ["OPL_A2A_HMAC_KEY_B64"] = base64.b64encode(kf.read_bytes()).decode()
        else:
            log_verdict(None, "", "", 11)
            print("★ **判定中止：缺 OPL_A2A_HMAC_KEY_B64**（build 会失败且不重写文件）⇒ 结论『未知』，不得判为免重签")
            if a.json:
                pathlib.Path(a.json).write_text(json.dumps({"needed": None, "why": "missing key"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 11
    os.environ.setdefault("OPL_A2A_HMAC_KEY_ID", "opl-a2a-2026q4")

    old_h = sha(att)
    old_m = att.stat().st_mtime
    with tempfile.TemporaryDirectory() as td:
        bak = pathlib.Path(td) / "bak.json"
        shutil.copy2(att, bak)
        env = dict(os.environ)
        p = subprocess.run(["node", "tools/sha3-tree.mjs", "build"], cwd=str(repo),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, env=env)
        build_out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        # 🔴 构建失败（exit≠0）⇒ 不得据此判定"树未变"
        if p.returncode != 0:
            shutil.copy2(bak, att)
            log_verdict(None, old_h, "", 11)
            print("★ **判定中止：build 失败（exit=%d）** ⇒ 结论『未知』（不得判为免重签）" % p.returncode)
            for ln in build_out[:3]:
                print("  build: %s" % ln[:100])
            if a.json:
                pathlib.Path(a.json).write_text(json.dumps(
                    {"needed": None, "why": "build failed", "exit": p.returncode}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
            return 11
        new_h = sha(att) if att.exists() else ""
        rewritten = att.stat().st_mtime != old_m
        same = (new_h == old_h) and new_h != "" and rewritten
        if same and not a.force:
            shutil.copy2(bak, att)   # 恢复，确保工作树无变更
            log_verdict(False, old_h, new_h, 0)
            print("★ **树未变** ⇒ **无需重签提交**（needed=false）")
            print("  旧/新 sha256 相同：%s…" % old_h[:16])
            print("  效果：省 1 次提交 + 1 次守卫 + 1 次推送往返（承 DF-PROPOSAL §甲）")
            if a.json:
                pathlib.Path(a.json).write_text(json.dumps(
                    {"needed": False, "sha256": old_h, "restored": True}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
            return 0
        log_verdict(True, old_h, new_h, 10)
        print("★ **树有变** ⇒ **需要重签提交**（needed=true）")
        print("  旧 sha256=%s… ｜ 新 sha256=%s…" % (old_h[:16], (new_h or "-")[:16]))
        if build_out:
            print("  build 末行：%s" % build_out[-1][:100])
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps(
                {"needed": True, "old_sha256": old_h, "new_sha256": new_h}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        return 10


if __name__ == "__main__":
    sys.exit(main())
