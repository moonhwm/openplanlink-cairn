#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
attest_lab_test.py —— 在【本席自己的 outbox】里建实验目录，跑其生成器，把读码推断变成实测。 **v1.1.0**

★ v1.0.0 的教训（写在这里，不抹）
──────────────────────────────────
  v1.0.0 的 E 段把 `fake_file` 与 `node_input` 取成同一个对象 ⇒ `same` **恒为真** ⇒
  **那是一个恒真演示，等于没有演示**——正是本席整晚在指控的毛病。
  v1.1.0 改为一个**非恒真**的演示：**造一枚文件，使其叶哈希【恰等于】某个内部节点哈希**，
  从而令【1 个文件的树】与【2 个文件的树】**根相同**。

背景
──────
轮 86 读其 `gen_attest.mjs` 得三条推断（因原 attest.json 是待填模板，当时无法实跑）：
  推断1 `sig` 覆盖 `{ts, merkle_root, file_count}`，**不含 `files` 表**
  推断2 叶哈希与内部节点哈希**无域分隔** ⇒ 叶/节点角色可混淆
  推断3 `file_count` 只统计**存在**的文件

★ 铁律：其生成器把 `attest.json` 写到【当前目录】⇒ 本器**只在 `exp/attest_lab/` 副本里跑**；
   **绝不在 `qtorrent_patch/` 或 v2.1 目录里跑**；删文件只在副本上删。
★ 依 P5：子进程只给最小环境白名单。
用法: attest_lab_test.py
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DESK = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面")
ROOT = DESK / "A2A新席_石敢当Cairn_20260928"
PATCH = DESK / "qtorrent_patch"
V21SITE = DESK / "OpenPlanLink_观测站_白天版v2.1_20261001" / "site"
LAB = ROOT / "exp" / "attest_lab"
PAGES = ["index.html", "observe.html", "oracle.html", "sandbox.html", "sea.html",
         "cinema.html", "a2a-architecture.html"]


def sha3hex(b: bytes) -> str:
    return hashlib.sha3_512(b).hexdigest()


def their_merkle(leaves_hex: list) -> str:
    """照其 merkleRoot 原文复现：叶排序；奇数上提不复制；节点哈希 Buffer.from(hex,'hex')。"""
    L = sorted(leaves_hex)
    while len(L) > 1:
        n = []
        for i in range(0, len(L), 2):
            r = L[i + 1] if i + 1 < len(L) else L[i]
            n.append(sha3hex(bytes.fromhex(L[i] + r)))
        L = n
    return L[0] if L else ""


def run_gen(lab: pathlib.Path) -> dict:
    env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "PATHEXT": os.environ.get("PATHEXT", ".EXE;.CMD;.BAT"), "TEMP": os.environ.get("TEMP", "")}
    r = subprocess.run(["node", "gen_attest.mjs"], cwd=str(lab), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError("生成器失败：%s" % ((r.stderr or r.stdout or "")[-240:]))
    return json.loads((lab / "attest.json").read_text(encoding="utf-8"))


def verify_sig(o: dict):
    env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "PATHEXT": os.environ.get("PATHEXT", ".EXE;.CMD;.BAT"), "TEMP": os.environ.get("TEMP", "")}
    js = ('import {createPublicKey,verify} from "node:crypto";'
          'const o=JSON.parse(process.argv[1]);'
          'const p=Buffer.from(JSON.stringify({ts:o.ts,merkle_root:o.merkle_root,file_count:o.file_count}));'
          'try{const pk=createPublicKey({key:Buffer.from(o.pubkey,"base64"),format:"der",type:"spki"});'
          'process.stdout.write(verify(null,p,pk,Buffer.from(o.sig,"base64"))?"OK":"BAD");}'
          'catch(e){process.stdout.write("ERR");}')
    r = subprocess.run(["node", "-e", js, json.dumps(o, ensure_ascii=False)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    return r.stdout.strip()


def main() -> int:
    print("═══ 把读码推断变成实测（全程在副本里）═══")
    if LAB.exists():
        shutil.rmtree(LAB, ignore_errors=True)
    (LAB / ".well-known").mkdir(parents=True, exist_ok=True)
    for f in PAGES:
        shutil.copy2(V21SITE / f, LAB / f)
    shutil.copy2(PATCH / "llms.txt", LAB / "llms.txt")
    shutil.copy2(PATCH / "agent-card.json", LAB / ".well-known" / "agent-card.json")
    shutil.copy2(PATCH / "gen_attest.mjs", LAB / "gen_attest.mjs")
    print("  ① 实验目录 = %s（%d 件）" % (LAB, len(PAGES) + 3))

    a1 = run_gen(LAB)
    print("  ② 产出真 attest.json：file_count=%s ｜ files 条数=%d ｜ merkle_root=%s…"
          % (a1["file_count"], len(a1["files"]), a1["merkle_root"][:24]))

    print()
    print("  ── A 基线 ──")
    ra = verify_sig(a1)
    print("     新签名原样验 = %s（期望 OK）" % ra)

    print()
    print("  ── B ★改 files 表两条哈希（ts/root/count 一字不动）──")
    b = json.loads(json.dumps(a1))
    ks = sorted(b["files"].keys())
    b["files"][ks[0]], b["files"][ks[1]] = b["files"][ks[1]], b["files"][ks[0]]
    print("     互换 %s ⇄ %s" % (ks[0], ks[1]))
    rb = verify_sig(b)
    print("     结果 = %s（★OK ⇒ 推断1 成立：files 表不在签名覆盖内）" % rb)

    print()
    print("  ── C 对照：改 merkle_root（files 不动）──")
    c = json.loads(json.dumps(a1))
    c["merkle_root"] = "0" * len(c["merkle_root"])
    rc = verify_sig(c)
    print("     结果 = %s（期望 BAD ⇒ 证明验签确实在看 root）" % rc)

    print()
    print("  ── D 推断3：删掉一个文件后重跑生成器 ──")
    victim = "cinema.html"
    (LAB / victim).unlink()
    a2 = run_gen(LAB)
    rd = verify_sig(a2)
    print("     删 %s 后：file_count %s → %s ｜ root %s… → %s…"
          % (victim, a1["file_count"], a2["file_count"], a1["merkle_root"][:16], a2["merkle_root"][:16]))
    print("     新 attest 自身验签 = %s（★OK ⇒ 新签名对【新的较小 count】依然成立）" % rd)
    print("     ⇒ 光看一份 attest，看不出「应有几个文件」——须由外部知道应有数。")

    print()
    print("  ── E 推断2：叶/节点角色是否可混淆（★非恒真演示）──")
    X = b"file-X-content"
    Y = b"file-Y-content"
    hX, hY = sha3hex(X), sha3hex(Y)
    root2 = their_merkle([hX, hY])                       # 两个文件的树
    node_input = bytes.fromhex(hX + hY)                  # 节点哈希所吃的【64 个原始字节】
    Z = node_input                                       # ★ 造一枚【内容恰为那 64 字节】的文件
    hZ = sha3hex(Z)
    root1 = their_merkle([hZ])                           # 一个文件的树
    print("     两个文件的树根 = %s…" % root2[:32])
    print("     一个文件的树根 = %s…" % root1[:32])
    print("     （该文件内容长度 = %d 字节 = 两条摘要的原始字节拼接）" % len(Z))
    collide = (root1 == root2)
    print("     ⇒ ★【1 个文件的树】与【2 个文件的树】根相同 = %s" % collide)
    if collide:
        print("     ⇒ 即：**同一函数、无域分隔 ⇒ 一个「文件」可以被当作一个「内部节点」**，")
        print("        于是【叶子数】不再由根唯一决定 ⇒ 与推断3 叠加：`file_count` 更不可信。")
    else:
        print("     ⇒ 未发生混淆（本席预期落空，如实记）")

    print()
    print("  ── 汇总 ──")
    print("   A 基线=%s ｜ B 改files仍过=%s ｜ C 改root失败=%s ｜ D 删件后新签名仍过=%s ｜ E 一叶与两叶同根=%s"
          % (ra, rb, rc != "OK", rd, collide))
    print("  ★ 本器能给出【通过】与【失败】两种结果（C 即失败例）⇒ 非恒真。")
    print("  ★ 其 qtorrent_patch/ 与 v2.1 目录【一个字节未动】；实验全在 %s 内。" % LAB.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
