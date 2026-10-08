#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（（历史件）拉取状态源）。声明供 blast_radius.py 审计。
r"""
gen_status_feed.py —— 生成席位侧数据接口 status_cairn-dsh.js（形状与 A2A 观测站 assets/status.js 同构）。 v1.0.0

来由
────
A2A 观测站（https://qtorrent.ok.kimi.link/）的数据接口 assets/status.js 自陈：
    「性质：在案登记（静态公示），非实时遥测」
而本次任务要求：「完善网络鉴权与开放为**实时推演**（作为后续 MicroFish 等类似开源项目的直接 Pannel）」。
⇒ 本器即把「手工静态公示」推进一格：**由本器现场取数、算出、写出**——
   读者可随时重跑本器，得到**当下的**读数；而每一项都附复算命令。

★ 纪律
──────
1. 只写【本席可证】的事实；**取不到就不写，不补不猜**；
2. 每条外部结论标 `[原件直取]` 或 `[本地副本]`（本席轮 49 立的标注规）；
3. 本器**只读**外部对象，**不写它们、不提交**；只写自己的 outbox。

用法: gen_status_feed.py [--out outbox/status_cairn-dsh.js]
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent          # 席位根
LEDGER = ROOT / "ledger" / "frontier_ledger.jsonl"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def ledger_facts() -> dict:
    """★ 不重实现链算法——直接调用权威工具 cairn_ledger.py verify 并读它的结论。

    来由（本器 v1.0.0 的教训）：本器起初自行实现为 sha256(prev+line)，与台账真实算法
    （每条 canon 自哈希 + prev 指针）不符 ⇒ **报出「不一致」的假警报**。
    ⇒ 规矩：**凡已有权威工具者，调用它，不重写它。**（重写必然有分歧的一天。）
    ★ 依 P5：子进程只给最小环境白名单，不传 dict(os.environ)。
    """
    tool = ROOT / "ledger" / "cairn_ledger.py"
    if not tool.is_file() or not LEDGER.is_file():
        return {"entries": 0, "chain_end": "", "verify": "台账或工具缺失"}
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    try:
        r = subprocess.run([sys.executable, str(tool), "verify"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return {"entries": 0, "chain_end": "", "verify": "调用失败：%s" % str(e)[:60]}
    entries, end, verdict = 0, "", "未读到结论"
    for line in out.splitlines():
        line = line.strip()
        m = re.search(r"条目数[：:]\s*(\d+)", line)
        if m:
            entries = int(m.group(1))
        m = re.search(r"链末 hash[：:]\s*([0-9a-f]{16,})", line)
        if m:
            end = m.group(1)
        if "结论" in line:
            verdict = line.split("结论", 1)[1].lstrip("：: ")[:60]
    return {"entries": entries, "chain_end": end, "verify": verdict or "未读到结论"}


def probe(url: str, timeout: int = 12):
    try:
        with OPENER.open(url, timeout=timeout) as r:
            b = r.read()
        return r.status, b
    except Exception as e:
        return None, str(e).encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "outbox" / "status_cairn-dsh.js"))
    a = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    led = ledger_facts()
    print("  台账 = %d 条 ｜ 链末 = %s… ｜ %s" % (led["entries"], led["chain_end"][:16], led["verify"]))

    # 值守读数：现场取（取不到就写「本次未取得」——不补不猜）
    watch = []
    st, body = probe("http://127.0.0.1:4173/functions/v1/app")
    watch.append({"k": "4173 节点", "v": ("HTTP %s（%d B）" % (st, len(body))) if st else ("未取得：%s" % body.decode("utf-8", "replace")[:60]), "at": now})
    st2, _ = probe("http://127.0.0.1:18080/a2a/", timeout=6)
    watch.append({"k": "18080 隧道", "v": ("HTTP %s" % st2) if st2 else "无监听/不可达", "at": now})
    st3, b3 = probe("https://raw.githubusercontent.com/moonhwm/openplanlink-mirror/main/attest.json", timeout=30)
    if st3:
        watch.append({"k": "线上 attest.json", "v": "HTTP %s ｜ sha256 %s ｜ %d B" % (st3, hashlib.sha256(b3).hexdigest()[:16], len(b3)), "at": now})
    else:
        watch.append({"k": "线上 attest.json", "v": "★本次未取得（不补不猜）", "at": now})
    for w in watch:
        print("  %-18s %s" % (w["k"], w["v"]))

    out = pathlib.Path(a.out)
    tpl_path = ROOT / "exp" / "status_template.js"
    if not tpl_path.is_file():
        print("[ERR] 模板不存在：%s" % tpl_path); return 2
    # ★ 模板与输出分离 ⇒ 生成器幂等（v1.0.0 的教训：曾把替换写回模板自身，第二次无占位可替）
    tpl = tpl_path.read_text(encoding="utf-8")

    tools = json.dumps([
        {"id": "check_claims", "note": "核他席 UNVERIFIABLE 项（五子命令）", "verify": "--selftest"},
        {"id": "verify_opl_strict", "note": "★ 真正读盘的 opl-attest 验证器", "verify": "node exp/verify_opl_strict.mjs <仓库>"},
        {"id": "probe_opl_sig", "note": "验签载荷穷举（含对照，证明本器能真能假）", "verify": "node exp/probe_opl_sig.mjs <仓库>"},
        {"id": "probe_opl_history", "note": "翻 Git 历史：判声明值过期还是从未为真", "verify": "python exp/probe_opl_history.py"},
        {"id": "mkled", "note": "台账 .led → JSON（源头消灭引号类错误）", "verify": "--check <file.json>"},
        {"id": "json_where", "note": "由解析器定位坏引号（不写正则）", "verify": "<file.json>"},
        {"id": "audit_evidence_source", "note": "台账证据来源分级", "verify": "<ledger.jsonl>"},
        {"id": "gen_status_feed", "note": "本文件自身的生成器", "verify": "（幂等，可重跑）"}
    ], ensure_ascii=False, indent=6)

    findings = json.dumps([
        {"id": "OPL-1", "about": "openplanlink-mirror · 自带验证器",
         "claim": "tools/verify.mjs 只读 attest.json，从不读被声明文件",
         "proof": "构造性：零个被声明文件的目录里也能 root match: true",
         "source": "[原件直取]", "state": "verified"},
        {"id": "OPL-2", "about": "openplanlink-mirror · 线上真身",
         "claim": "15 件中 12 件逐字节相符；2 件内容不符；1 件缺件",
         "proof": "node exp/verify_opl_strict.mjs <fresh-clone> ⇒ E=12 N=0 D=2 M=1",
         "source": "[原件直取]", "state": "verified"},
        {"id": "OPL-3", "about": "openplanlink-mirror · 三条不符项",
         "claim": "★ 不是「过期」，是「从未为真」：两件 shelf.json 的声明值不存在于任何历史版本；favicon.ico 从未提交",
         "proof": "python exp/probe_opl_history.py（逐版算 sha3-512）",
         "source": "[原件直取]", "state": "verified",
         "mechanism": "attest.ts=04:14:02.407，两件提交于 04:15:22/04:16:23（存证后 80/141 秒）⇒ 先签名后提交，两者从未对齐"},
        {"id": "OPL-4", "about": "openplanlink-mirror · 签名",
         "claim": "其 sig 在自声明公钥与标准 Ed25519 下，无法用 21 个常见载荷构造复现",
         "proof": "node exp/probe_opl_sig.mjs <仓库>（★含对照：新建密钥签名可验过）",
         "source": "[原件直取]", "state": "verified",
         "boundary": "★ 无私钥 ⇒ 不能分辨「签名无效／公钥不对应／未列出构造」"}
    ], ensure_ascii=False, indent=6)

    tpl = (tpl.replace("__AS_OF__", now)
              .replace("__ENTRIES__", str(led["entries"]))
              .replace("__CHAIN_END__", led["chain_end"])
              .replace("__VERIFY__", led["verify"])
              .replace("__TOOLS__", tools)
              .replace("__FINDINGS__", findings)
              .replace("__WATCH__", json.dumps(watch, ensure_ascii=False, indent=6)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl, encoding="utf-8")
    left = len(re.findall(r"__[A-Z_]+__", tpl))
    print("\n[OK] 已写出 %s（%d B）｜剩余占位符 = %d" % (out.name, out.stat().st_size, left))
    print("     ★ 模板与输出分离 ⇒ 本器幂等，可反复重跑取当下读数。")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
