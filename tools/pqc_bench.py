# -*- coding: utf-8 -*-
"""pqc_bench.py —— 后量子/签名与审计链**延迟基线**（承令条：签名验证延迟控制在毫秒级）

令条相关要求（摘）：
    「算法采用 HMAC-SHA3-512 树、AES-256-GCM 及标识密码（IBC）等先进加密算法…
      架构上实行分层密钥派生与动态轮换，**在满足量子抗性前提下将签名验证延迟控制在毫秒级**，
      并**写入不可篡改审计链**。」

本器**只测本席现有能力**（不虚报未实现者）：
    A. **SSHSIG 验签延迟**（ed25519，n 次取 min/mean/max，**毫秒**）
    B. **HMAC-SHA3-512** 单次计算延迟（1 MiB 载荷，n 次）
    C. **SHA3-512** 单次摘要延迟（1 MiB）
    D. **台账链校验**延迟（全链，n=1；不可篡改审计链之现役实现）
    E. **事件链校验**延迟（全链，n=1）
    另：AES-256-GCM／IBC／SM9／SM10／ZUC／量子随机数／ABE／HSM —— **本席未实现 ⇒ 标"未实现"**（不测不报）。

纪律：私钥**不出、不录**；基准用**临时密钥**（HMAC）**不落盘**；取不到即标「未测」。
输出：表格 + JSON（`outbox/mem/pqc_bench.json`）。
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import statistics
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
OUT = SEAT / "outbox" / "mem" / "pqc_bench.json"
KEY = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing")
PUB = pathlib.Path(r"C:\Users\欧阳宏俊\.ssh\cairn-commit-signing.pub")


def timed(fn, n=5):
    xs = []
    ok = True
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception:  # noqa: BLE001
            ok = False
            break
        xs.append((time.perf_counter() - t0) * 1000.0)
    if not ok or not xs:
        return None
    return {"n": len(xs), "min_ms": round(min(xs), 3), "mean_ms": round(statistics.mean(xs), 3),
            "max_ms": round(max(xs), 3)}


def bench_sshsig(n):
    if not (KEY.exists() and PUB.exists()):
        return None, "密钥或公钥缺失"
    with tempfile.TemporaryDirectory() as d:
        msg = pathlib.Path(d) / "msg.txt"
        msg.write_bytes(b"cairn-pqc-bench: " + secrets.token_bytes(32))
        sig = pathlib.Path(str(msg) + ".sig")
        r = subprocess.run(["ssh-keygen", "-Y", "sign", "-n", "a2a-iurn-announce", "-f", str(KEY), "-"],
                           input=msg.read_bytes(), capture_output=True)
        if r.returncode != 0:
            return None, "签名步骤失败"
        sig.write_bytes(r.stdout)
        allowed = pathlib.Path(d) / "allowed"
        allowed.write_text("cairn %s\n" % PUB.read_text(encoding="utf-8").strip(), encoding="utf-8")

        def verify():
            p = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed),
                                "-I", "cairn", "-n", "a2a-iurn-announce", "-s", str(sig)],
                               capture_output=True, input=msg.read_bytes())
            if p.returncode != 0:
                raise RuntimeError("verify failed")
        return timed(verify, n), None


def bench_hmac_sha3(n):
    data = os.urandom(1 << 20)          # 1 MiB
    key = secrets.token_bytes(32)        # 临时密钥，不落盘
    return timed(lambda: hmac.new(key, data, hashlib.sha3_512).digest(), n), None


def bench_sha3(n):
    data = os.urandom(1 << 20)
    return timed(lambda: hashlib.sha3_512(data).digest(), n), None


def timed_cmd(cmd, cwd=None):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    el = (time.perf_counter() - t0) * 1000.0
    return {"rc": p.returncode, "ms": round(el, 1)}, (p.stdout or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5)
    a = ap.parse_args()
    res = {"generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
           "seat": "a2a-node-local", "samples": a.n, "rows": []}

    r, err = bench_sshsig(a.n)
    res["rows"].append({"op": "SSHSIG 验签(ed25519)", "result": r or "未测", "note": err or "本席现役宣告签名机制"})
    r, _ = bench_hmac_sha3(a.n)
    res["rows"].append({"op": "HMAC-SHA3-512(1 MiB)", "result": r or "未测", "note": "令条点名算法；本席用于 sha3 树"})
    r, _ = bench_sha3(a.n)
    res["rows"].append({"op": "SHA3-512 摘要(1 MiB)", "result": r or "未测", "note": "Merkle 叶哈希基元"})

    led = SEAT / "ledger" / "cairn_ledger.py"
    if led.exists():
        r, _ = timed_cmd([sys.executable, str(led), "verify"])
        res["rows"].append({"op": "台账链校验(全链)", "result": r, "note": "不可篡改审计链之现役实现"})
    ev = SEAT / "exp" / "ops_event.py"
    if ev.exists():
        r, _ = timed_cmd([sys.executable, str(ev), "verify"])
        res["rows"].append({"op": "事件链校验(全链)", "result": r, "note": "ops_event 链"})

    for op in ("AES-256-GCM", "IBC 标识密码", "SM9", "SM10/ZUC", "量子随机数熵源", "ABE 属性基加密", "HSM 密钥托管"):
        res["rows"].append({"op": op, "result": "未实现", "note": "本席未实现 ⇒ 不测不报（禁止以未测充已测）"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print("★ 后量子/签名与审计链延迟基线（%s｜n=%d｜北京时间）" % (res["generated_at"], a.n))
    print("  %-24s %-42s %s" % ("操作", "延迟(min/mean/max ms)", "备注"))
    for row in res["rows"]:
        if isinstance(row["result"], dict):
            r = row["result"]
            if "ms" in r:
                cell = "%.1f ms（单次）" % r["ms"]
            else:
                cell = "%.3f / %.3f / %.3f" % (r["min_ms"], r["mean_ms"], r["max_ms"])
        else:
            cell = row["result"]
        print("  %-24s %-42s %s" % (row["op"], cell, row["note"]))
    ms_rows = [x for x in res["rows"] if isinstance(x["result"], dict) and "mean_ms" in x["result"]]
    if ms_rows:
        worst = max(ms_rows, key=lambda x: x["result"]["mean_ms"])
        ok = worst["result"]["mean_ms"] < 1000.0
        print("  ⇒ 判读：本席**现役签名/哈希类**操作均值最大者＝%s（%.3f ms）⇒ 毫秒级要求：%s"
              % (worst["op"], worst["result"]["mean_ms"], "**满足**" if ok else "**不满足**"))
    print("  ⇒ **未实现项已逐条标「未实现」**（不以「未测」充数）")
    print("  JSON：%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
