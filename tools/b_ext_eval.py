# -*- coding: utf-8 -*-
"""b_ext_eval.py —— 手写释义查询（扩充集）之评测：BM25 在该集上是否"能失败"（零外呼）
承接：retrieval_eval.py 之 B 组造法（手写问句 → 目标节标题子串）；本器评测★扩充集（b_spec_ext_20261012.json）
对照：A 组（已知项，取节正文中段 12 字）之 BM25 MRR —— 若 B 扩充集之 MRR ★显著低于 A ⇒ 证"该集能失败"
判据（可失败）：①每条查询皆解析出目标节；②两集皆可算分；③★B 扩充集与目标正文之重合低于 A 组
用法：python b_ext_eval.py --index <合规索引> --ext <扩充集json> [--json out]
（中文串一律用「」）
"""
import argparse, json, math, pathlib, re, sys, time

STOP = set("的 了 与 及 和 是 在 有 为 以 对 之 其 者 等 一 二 三 四 五 六 七 八 九 十 我 他 她 它 你 这 那 不 无 也 就 而 且 或 由 于 从 到 将 被 把 使 让 若 则 因 故 但 并 已 未 可 能 会 应 须 需 要 该 此 本".split())


def toks(t):
    t = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(t))
    out = []
    for w in t.split():
        if re.search(r"[\u4e00-\u9fff]", w):
            out += [w] if len(w) == 1 else [w[i:i+2] for i in range(len(w)-1)]
        else:
            out.append(w.lower())
    return [x for x in out if x and x not in STOP]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True)
    ap.add_argument("--ext", required=True); ap.add_argument("--k", type=int, default=5); ap.add_argument("--json", default="")
    a = ap.parse_args()
    idx = json.loads(pathlib.Path(a.index).read_text(encoding="utf-8-sig"))
    secs = idx.get("sections") or []; df = idx.get("df") or {}
    avgdl = idx.get("avgdl") or 1.0; N = idx.get("N") or len(secs)
    tf = []; dl = []
    for s in secs:
        t = s.get("tf") or {}
        tf.append(t); dl.append(sum(t.values()) if t else len(toks(s.get("body") or "")))
    ext = json.loads(pathlib.Path(a.ext).read_text(encoding="utf-8-sig"))["pairs"]

    def bm25_rank(q):
        qt = toks(q); sc = []
        for i in range(len(secs)):
            s = 0.0
            for w in qt:
                f = tf[i].get(w, 0)
                if not f: continue
                idf = math.log(1 + (N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
                s += idf * (f * (1.5 + 1)) / (f + 1.5 * (1 - 0.75 + 0.75 * dl[i] / avgdl))
            if s > 0: sc.append((s, i))
        sc.sort(key=lambda t: -t[0]); return [i for _, i in sc]

    # ★B 扩充集
    rows = []; miss = 0; caps = []
    for q, key in ext:
        tgt = [i for i, s in enumerate(secs) if key in (s.get("head") or "")]
        if not tgt: miss += 1; continue
        ti = tgt[0]; order = bm25_rank(q)
        rank = order.index(ti) + 1 if ti in order else None
        qt = set(toks(q)); bt = set(toks(secs[ti].get("body") or ""))
        cap = len(qt & bt) / max(1, len(qt))
        caps.append(cap)
        rows.append({"q": q, "key": key, "target": ti, "rank": rank, "cap_body": round(cap, 3)})
    n = len(rows)
    hit1 = sum(1 for r in rows if r["rank"] == 1)
    hit5 = sum(1 for r in rows if r["rank"] and r["rank"] <= a.k)
    mrr = sum((1.0/r["rank"]) if r["rank"] else 0.0 for r in rows)
    H1 = hit1/max(1, n); H5 = hit5/max(1, n); M = mrr/max(1, n)
    avg_cap = sum(caps)/max(1, len(caps))
    # ★A 组对照（取节正文中段 12 字 ⇒ 与正文重合近 1.0）
    A = []
    for i, s in enumerate(secs[:120]):
        b = re.sub(r"\s+", "", s.get("body") or "")
        if len(b) < 80: continue
        span = b[len(b)//2: len(b)//2+12]
        if len(span) < 8: continue
        order = bm25_rank(span)
        rank = order.index(i)+1 if i in order else None
        A.append(rank)
    a1 = sum(1 for r in A if r == 1); aM = sum((1.0/r) if r else 0.0 for r in A)
    AH1 = a1/max(1, len(A)); AM = aM/max(1, len(A))
    crit = {"①每条查询皆解析出目标节（未解析者 0）": miss == 0,
            "②两集皆可算分": n > 0 and len(A) > 0,
            "③★B 扩充集之正文重合低于 A 组": avg_cap < 0.9}
    print("  ═══ 手写释义（扩充集）之 BM25 ═══")
    print("   扩充集：%d 条（未解析 %d）｜索引节 %d" % (len(ext), miss, len(secs)))
    print("   ★B 扩充集：Hit@1 %.4f ｜ Hit@%d %.4f ｜ ★MRR %.4f ｜ 与目标正文重合 %.4f" % (H1, a.k, H5, M, avg_cap))
    print("   A 组（正文中段 12 字，N=%d）：Hit@1 %.4f ｜ ★MRR %.4f" % (len(A), AH1, AM))
    print("   ⇒ ★ΔMRR（B扩充 − A）＝ %+.4f ⇒ %s" % (M - AM, "★B 集更能失败（语义词面之外有空间）" if M < AM - 0.05 else "★B 集未能失败"))
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    print("   ── 样例（前 6 条，含名次）──")
    for r in rows[:6]:
        print("      rank=%-4s ｜ %-28s ⇒ %s" % (r["rank"], r["q"][:26], r["key"]))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
            "n": n, "B": {"hit1": round(H1, 4), "hit5": round(H5, 4), "mrr": round(M, 4), "cap_body": round(avg_cap, 4)},
            "A": {"n": len(A), "hit1": round(AH1, 4), "mrr": round(AM, 4)},
            "dmrr": round(M - AM, 4), "criteria": crit, "rows": rows}, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="\n")
    return 0 if all(crit.values()) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
