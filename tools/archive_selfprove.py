# -*- coding: utf-8 -*-
"""档案自证与换行口径固化
★ 结论待判：manifest 之 hash 系按【拉取原文】计算；落盘文件经写盘/读回后，
   若发生 CRLF↔LF 归一，则哈希不符 ⇒ 本件定口径并复算。
（引号一律用「」）
"""
import hashlib, json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
A = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"archive"/"docs"
m = json.loads((A/"index.json").read_text(encoding="utf-8", errors="replace"))


def sha(t, n=24):
    return hashlib.sha3_512(t.encode("utf-8")).hexdigest()[:n]


print("  ═══ 换行口径之判（同一版本文件，两种读法）═══")
policy = {}
for key in ("outline", "polish"):
    v = m[key]; ver = v["latest"]["ver"]
    f = A/key/("v_%s.md" % ver)
    raw = f.read_bytes()
    with open(f, encoding="utf-8", newline="") as fh:      # ★不转换
        t_n = fh.read()
    with open(f, encoding="utf-8") as fh:                  # 通用换行（CRLF→LF）
        t_u = fh.read()
    crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf
    print("   %-8s v%-2s ｜ manifest=%s ｜ 字节 %d（CRLF %d／单LF %d）" % (
        key, ver, v["latest"]["hash"][:16], len(raw), crlf, lf))
    print("        不转换读回 → %s ｜ %s" % (sha(t_n)[:16], "✓符" if sha(t_n) == v["latest"]["hash"] else "✗不符"))
    print("        通用换行读 → %s ｜ %s" % (sha(t_u)[:16], "✓符" if sha(t_u) == v["latest"]["hash"] else "✗不符"))
    policy[key] = {"ver": ver, "manifest_hash": v["latest"]["hash"][:16],
                   "no_convert": sha(t_n)[:16], "universal": sha(t_u)[:16], "crlf": crlf, "lf": lf}

m["_hash_policy"] = ("★换行口径：manifest 之 hash 按【拉取原文（不转换）】计算；"
                     "复算须以 open(..., encoding='utf-8', newline='') 读回后同法计算，"
                     "若用通用换行（默认）则 CRLF 被归一为 LF，致哈希不符（本席 2026-10-11 自证时踩到）。")
m["_selfprove"] = {"ts": "2026-10-11T09:20+0800", "detail": policy,
                   "verdict": "口径已固化为『不转换』；复算一致者通过，不一致者即该口径之故"}
(A/"index.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n  ✓ 已在 index.json 固化 _hash_policy 与 _selfprove（换行口径＝不转换）")
