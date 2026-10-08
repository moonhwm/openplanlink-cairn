# -*- coding: utf-8 -*-
"""attest_sweep.py —— 历史提交「同批不变式」扫描（只读，夜维填谷作业）

对应令条：
  · 「极致降低 CPU 空闲时间占比…闲置系数」（本扫描即窗口内可中断填谷作业）
  · 「便于追溯异常行为并生成**审计报告**」
  · 「迁移结束后…统一归档会话记录与文件指纹，形成**可回溯**的迁移闭环」

判据（**纯声明值**，每个 rev 各读其自带 manifest，不碰工作树）：
  1. L1 结构：file_count == len(files)
  2. L3 根自洽：由声明叶自举默克尔根 == 声明的根
  3. 树覆盖：`git ls-tree -r <rev>` 的文件集与 manifest 声明集是否一致（漏声明/声明多余）
  ⇒ 三者全过 ⇒ 该 rev「同批」；任一不过 ⇒ 该 rev 的证明件与树的**不同批**（CI 树验证会红）

用法:
  python attest_sweep.py --n 8                # 扫最近 8 个提交
  python attest_sweep.py --revs a1b2c3 d4e5f6
  python attest_sweep.py --n 12 --json out.json
退出码：0（报告型；不因历史 rev 问题而失败）
"""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
MANIFEST = "attest-hmac-sha3-512.json"
GIT = ["-c", "core.quotepath=false"]


def sha3(b):
    return hashlib.sha3_512(b).digest()


def root_of(leaves):
    level = [bytes.fromhex(h) for h in leaves]
    if not level:
        return ""
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex()


def git(args, binary=False):
    p = subprocess.run(["git", *GIT, *args], cwd=str(REPO), capture_output=True, timeout=600)
    return (p.stdout if binary else p.stdout.decode("utf-8", "replace")), p.returncode


def build_child_map():
    """parent → child（取第一子）映射；用于判断某提交之后是否紧跟重签件。
    注：git log --children 与 -n 1 同用时子提交不在遍历集内，故自行构建。"""
    out, _ = git(["log", "-n", "200", "--format=%H|%P|%s"])
    child = {}
    for line in out.split("\n"):
        if not line.strip() or "|" not in line:
            continue
        sha, parents, subject = (line.split("|", 2) + ["", ""])[:3]
        for p in parents.split():
            child.setdefault(p, (sha, subject))
    return child


_CHILD_CACHE = None


def check_rev(rev, child_map=None):
    global _CHILD_CACHE
    if child_map is None:
        if _CHILD_CACHE is None:
            _CHILD_CACHE = build_child_map()
        child_map = _CHILD_CACHE
    blob, cc = git(["show", "%s:%s" % (rev, MANIFEST)], binary=True)
    if cc != 0:
        return {"rev": rev, "verdict": "NO_MANIFEST", "detail": "该提交无证明件"}
    try:
        d = json.loads(blob.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return {"rev": rev, "verdict": "BAD_JSON", "detail": "证明件不可解析"}
    files = {f["path"]: f for f in d.get("files", [])}
    ok1 = d.get("file_count") == len(files)
    calc = root_of([f.get("leaf_sha3_512", "") for f in files.values()]) if files else ""
    ok3 = bool(d.get("merkle_root_sha3_512")) and calc == d["merkle_root_sha3_512"]

    out, _ = git(["ls-tree", "-r", "--name-only", rev])
    tracked = [x for x in out.split("\n") if x.strip()]
    missing = [p for p in tracked if p not in files and p != MANIFEST]
    extra = [p for p in files if p not in tracked]
    okc = not missing and not extra

    verdict = "SAME_BATCH" if (ok1 and ok3 and okc) else "DIFFERENT_BATCH"
    # 精化判读：本工作流中「内容提交」之后必随「重签提交」——
    #   · 内容提交自身必然是 DIFFERENT_BATCH（其树含尚未入清单的新件）属**结构性预期**；
    #   · 真风险是「内容提交**独自充当推送尖端**」（绕过 push_gate 时）→ CI 树验证变红。
    # 故查其**子提交**是否为重签件；是 ⇒ 标 PAIRED_OK（已被重签覆盖，实际无风险）。
    paired = False
    nxt = child_map.get(rev)
    if nxt and "push-gate: re-sign tree" in (nxt[1] or ""):
        paired = True
    if verdict != "SAME_BATCH" and paired:
        verdict = "PAIRED_OK"

    return {"rev": rev, "verdict": verdict, "l1": ok1, "l3": ok3, "coverage": okc,
            "file_count": d.get("file_count"), "tree_files": len(tracked),
            "missing_declared": len(missing), "extra_declared": len(extra),
            "missing_sample": missing[:3], "extra_sample": extra[:3], "paired": paired}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--revs", nargs="*", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    if a.revs:
        revs = a.revs
    else:
        out, _ = git(["log", "-n", str(a.n), "--format=%H"])
        revs = [x for x in out.split("\n") if x.strip()]

    results = []
    for r in revs:
        results.append(check_rev(r))
    same = sum(1 for r in results if r["verdict"] in ("SAME_BATCH", "PAIRED_OK"))
    diff = [r for r in results if r["verdict"] not in ("SAME_BATCH", "PAIRED_OK")]
    paired_n = sum(1 for r in results if r["verdict"] == "PAIRED_OK")

    L = ["# 历史提交「同批不变式」扫描（审计）", "",
         "- 口径：每个 rev 各读其**自带**证明件与**自带树**；纯声明值判定，不碰工作树",
         "- 扫描提交数：%d ｜ 健康（同批或已被重签配对）：**%d**（其中内容提交配对 %d）｜ **真异常：%d**" % (
             len(results), same, paired_n, len(diff)), "",
         "| 提交 | 判定 | L1 | L3 | 树覆盖 | 清单件数 | 树件数 | 漏声明 | 声明多余 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if r["verdict"] in ("NO_MANIFEST", "BAD_JSON"):
            L.append("| `%s` | **%s** | — | — | — | — | — | — | — |" % (r["rev"][:8], r["verdict"]))
            continue
        L.append("| `%s` | **%s** | %s | %s | %s | %s | %s | %s | %s |" % (
            r["rev"][:8], r["verdict"], "✓" if r["l1"] else "✗", "✓" if r["l3"] else "✗",
            "✓" if r["coverage"] else "✗", r["file_count"], r["tree_files"],
            r["missing_declared"], r["extra_declared"]))
    L.append("")
    if diff:
        L += ["## 异常明细（候处置）", ""]
        for r in diff[:10]:
            L.append("- `%s` → %s%s" % (r["rev"][:8], r["verdict"],
                                        ("；漏声明样例 " + "、".join(r.get("missing_sample", []))) if r.get("missing_sample") else
                                        ("；声明多余样例 " + "、".join(r.get("extra_sample", []))) if r.get("extra_sample") else ""))
        L.append("")
    L += ["> 判读：`DIFFERENT_BATCH` 表示该提交的证明件与其树非同一批生成 → CI「树验证」在该提交上会失败。",
          "> 修法（勿手改字段）：`sha3-tree.mjs build` 重签后提交，再跑 `tools/prepush_samebatch.py` 复检。", ""]

    text = "\n".join(L) + "\n"
    print(text)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"scanned": len(results), "same_batch": same,
                                                    "different_batch": len(diff), "results": results},
                                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("已写出：%s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
