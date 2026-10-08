#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（探测仓库历史）。声明供 blast_radius.py 审计。
r"""
probe_opl_history.py —— 翻 Git 历史，判定存证对那 3 条不符项是【过期】还是【错】。 v1.0.0

问题
────
本席轮 48 对【线上真身】实测得：E=12 / N=0 / D=2 / M=1。不符的三条是：
    · data/shelf.json          （声明 982a6c75af25e764… ／ 线上磁盘 不符）
    · atlas/data/shelf.json    （同上，两条同声明值）
    · favicon.ico              （声明 50c88e368326161e… ／ 线上缺件）
★ 该三次不符，是【存证过期】还是【存证从来就错】？——**可用 Git 历史判定**：
    若某历史修订的 sha3-512 等于声明值 ⇒ 当年是对的 ⇒ **过期**；
    若全部历史修订都不等于声明值、且该文件从未存在 ⇒ **错**。

方法
────
走 GitHub REST API：列出该路径的全部提交 → 取每版内容 → 逐版算 sha3-512 → 比对声明值。
纯只读；不写仓库、不提交。

用法: probe_opl_history.py [--repo owner/name] [--branch main]
"""
from __future__ import annotations
import base64
import hashlib
import json
import sys
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
REPO = "moonhwm/openplanlink-mirror"
BRANCH = "main"

# 声明值（取自线上 attest.json；本席轮 48 实读）
DECLARED = {
    "data/shelf.json": "982a6c75af25e764",
    "atlas/data/shelf.json": "982a6c75af25e764",
    "favicon.ico": "50c88e368326161e",
}



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def api(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "cairn-dsh-probe", "Accept": "application/vnd.github+json"})
    with OPENER.open(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def sha3_512(b: bytes) -> str:
    return hashlib.sha3_512(b).digest().hex()


def main() -> int:
    print("═══ 翻 Git 历史：三条不符项是【过期】还是【错】 ═══")
    print("  仓库 =", REPO, "｜ 分支 =", BRANCH)
    print()
    for path, declared in DECLARED.items():
        print("▸ %s" % path)
        print("   声明值（前 16）= %s" % declared)
        try:
            commits = api("https://api.github.com/repos/%s/commits?sha=%s&path=%s&per_page=100"
                          % (REPO, BRANCH, urllib.parse.quote(path)))
        except Exception as e:
            print("   ★列提交失败：%s" % str(e)[:70]); print(); continue
        if not commits:
            print("   ★该路径【从未出现在提交历史中】 ⇒ 该件从未存在过")
            print("   ⇒ 判定：**存证记录了不存在的文件**（与其报告 12 的 C4 一致，但此处由历史判定）")
            print(); continue
        print("   提交数（该路径）= %d" % len(commits))
        hit = None
        seen = []
        for c in commits:
            sha = c["sha"]
            try:
                blob = api("https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, urllib.parse.quote(path), sha))
                content = base64.b64decode(blob["content"])
                h = sha3_512(content)
                seen.append((sha[:8], c["commit"]["committer"]["date"][:19], h[:16], len(content)))
                if h[:16] == declared:
                    hit = (sha[:8], c["commit"]["committer"]["date"][:19], h[:16])
                    break
            except Exception as e:
                seen.append((sha[:8], "err", str(e)[:20], 0))
        for s in seen[:8]:
            print("     %s  %s  sha3=%s  %d B" % s)
        if len(seen) > 8:
            print("     …（共 %d 版）" % len(seen))
        print()
        if hit:
            print("   ★★ 命中：提交 %s（%s）的 sha3-512 前 16 ＝ 声明值" % (hit[0], hit[1]))
            print("   ⇒ 判定：**该存证【当年是对的】，此后内容变更 ⇒ 属于【过期】，不是【错】**")
        else:
            print("   ★ 全部历史修订均不等于声明值")
            print("   ⇒ 判定：**在可得历史内，该声明值从未与任何真实版本相符** ⇒ 属【存证与内容不符】")
        print()
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
