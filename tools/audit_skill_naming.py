#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（（历史件）读远端技能清单）。声明供 blast_radius.py 审计。
r"""
audit_skill_naming.py —— 对 OpenPlanLink 镜像 skills/ 库做【逐份】命名一致性审计。 v1.1.0

v1.1.0 修正（★记下为什么改）
────────────────────────────
v1.0.0 对 117 个目录**逐个**请求 BUILD_MANIFEST.json，结果 **115 个 HTTPError、覆盖率仅 1.7%**。
本席没有拿那 1.7% 当结论，而是先查真因——**结果发现审计对象本身不齐**：
**大多数技能目录里根本没有 BUILD_MANIFEST.json**（只有经 cangjie 管线构建的"包"才有），
故 404 是**正常结果**，不是"我取不到"。
⇒ 改法：**先用递归树一次取全全部路径**（1 次请求即得 100% 的【结构】覆盖），
   只对"确实存在自报名清单"的目录取件；并把**结构覆盖**与**命名判定覆盖**分开报。

★ 两类覆盖必须分开说
─────────────────────
· **结构覆盖**：哪些目录有自报名清单 —— 由递归树给出，**100%**；
· **命名判定覆盖**：有多少件真正做了"目录名 vs 包内自报名"的比对 —— 只对有清单者成立。
把两者混成一个百分比，就是在掩盖"我其实没查到多少"。

★ 纪律：只读；**不改名、不提 PR、不开 Issue**（本席无对端凭据，且改名属僭越权责 L1061）。
"""
from __future__ import annotations
import concurrent.futures as cf
import json
import pathlib
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OWNER, REPO, REF = "moonhwm", "openplanlink-mirror", "main"
UA = {"User-Agent": "cairn-dsh-naming-audit/1.1"}
SEAT = pathlib.Path(__file__).resolve().parent.parent



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def get(url: str, tries: int = 3) -> bytes:
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            if e.code in (403, 429):            # 限流：退一步再试
                import time
                time.sleep(2)
                continue
            raise RuntimeError(last)
        except Exception as e:                  # noqa: BLE001
            last = type(e).__name__
    raise RuntimeError(str(last))


def main():
    print("═══ skills/ 命名一致性审计（逐份·两段报告）═══")
    tree = json.loads(get("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, REPO, REF)))
    paths = [p["path"] for p in tree["tree"]]
    dirs = sorted({p.split("/", 2)[1] for p in paths if p.startswith("skills/") and p.count("/") == 1})
    manifests = sorted({p.rsplit("/", 1)[0].split("/", 1)[1] for p in paths
                        if p.startswith("skills/") and p.endswith("/BUILD_MANIFEST.json")})
    skillmds = {p.rsplit("/", 1)[0].split("/", 1)[1] for p in paths
                if p.startswith("skills/") and p.endswith("/SKILL.md")}

    print("\n【结构覆盖·由递归树一次取全，100%%】")
    print("  skills/ 下条目数          = %d" % len(dirs))
    print("  含 BUILD_MANIFEST.json    = %d  ⇒ %s" % (len(manifests), "、".join(manifests) or "(无)"))
    print("  含 SKILL.md               = %d" % len(skillmds))
    print("  ★无自报名清单的条目       = %d" % (len(dirs) - len(manifests)))
    print("     —— 这批件的『名』在 SKILL.md 的 frontmatter 里，不在清单里；")
    print("        本席本轮【未逐份取 SKILL.md】（117 次请求会撞限流），故对其**不下命名结论**。")

    def probe(d):
        raw = "https://raw.githubusercontent.com/%s/%s/%s/skills/%s/BUILD_MANIFEST.json" % (OWNER, REPO, REF, d)
        try:
            m = json.loads(get(raw).decode("utf-8"))
            return (d, "OK", m.get("bundle_id", ""), m.get("version", ""), m.get("builder", ""))
        except Exception as e:                  # noqa: BLE001
            return (d, "取件失败", str(e)[:40], "", "")

    rows = []
    if manifests:
        with cf.ThreadPoolExecutor(max_workers=4) as ex:
            rows = list(ex.map(probe, manifests))

    same, diff, fail = [], [], []
    for d, st, bid, ver, builder in rows:
        (fail if st != "OK" else (same if bid == d else diff)).append((d, bid, ver, builder))

    print("\n【命名判定覆盖·仅对含清单的 %d 件】" % len(manifests))
    print("  目录名 == bundle_id ：%d 件" % len(same))
    print("  ★目录名 != bundle_id：%d 件" % len(diff))
    for d, bid, ver, builder in diff:
        print("     目录 %-20s 实际包名 %-26s v%s ｜ builder=%s" % (d, bid or "(空)", ver or "?", builder or "(未署)"))
    if fail:
        print("  取件失败：%d 件" % len(fail))
        for d, why, _v, _b in fail:
            print("     %-20s %s" % (d, why))

    print("\n═══ 两段覆盖率 ═══")
    print("  结构覆盖（有/无自报名清单）：%d/%d = 100.0%%（递归树一次取全）" % (len(dirs), len(dirs)))
    print("  命名判定覆盖（做了比对的）：%d/%d 件含清单者 ｜ 占全部条目的 %.1f%%"
          % (len(same) + len(diff), len(manifests), 100.0 * (len(same) + len(diff)) / len(dirs)))
    print("  ★未判定：%d 件（无自报名清单）＋ %d 件（取件失败）" % (len(dirs) - len(manifests), len(fail)))

    out = {"audit": "skills-naming-consistency", "tree_ok": True,
           "dirs_total": len(dirs), "with_manifest": manifests, "with_skillmd": len(skillmds),
           "same": [{"dir": d, "version": v, "builder": b} for d, v, b in
                    [(x[0], x[2], x[3]) for x in same]],
           "mismatch": [{"dir": d, "bundle_id": b, "version": v, "builder": bu} for d, b, v, bu in diff],
           "fetch_failed": [{"dir": d, "reason": w} for d, w, _v, _b in fail],
           "coverage": {"structural_pct": 100.0,
                        "naming_judged": len(same) + len(diff), "naming_total_with_manifest": len(manifests),
                        "naming_pct_of_all": round(100.0 * (len(same) + len(diff)) / max(len(dirs), 1), 1)}}
    (SEAT / "handshake" / "skills_naming_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n明细已写：handshake/skills_naming_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
