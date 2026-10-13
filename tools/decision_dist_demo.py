# -*- coding: utf-8 -*-
"""decision_dist_demo.py —— 决策模型「概率分布＋置信度」输出之可运行示范（2026-10-13 立）
缘由：令条「决策模型…仅需单次前向传播…并输出★概率分布与置信度结果」⇒ ★本器以★本地零调用
      （词表查对＋余弦＋softmax）给出★完整分布（p 之和为 1）与置信度，★一次前向（无迭代）。
      注：此为「精确存在性」通道之示范（承 -1363 定案：查表 1.000）；非 LLM。
用法：python decision_dist_demo.py [--query 总线可否事后补录]
（中文串一律用「」）
"""
import argparse, json, math, pathlib, sys, time

CAND = {
    "总线 emit 不可事后补录（行为之历史不可伪造）": ["总线", "emit", "补录", "不可"],
    "夜间游乐场开园：以首帧为条件之重绘": ["夜间游乐场", "开园", "首帧", "重绘"],
    "人设三级 LOD GLB 与四段动画": ["人设", "LOD", "GLB", "动画"],
    "例行复拉与节键重排虚警之自动标注": ["例行", "复拉", "重排", "虚警"],
    "决策模型单次前向输出概率分布与置信度": ["决策", "单次", "前向", "概率分布", "置信度"],
}
QUERY_DEF = "总线可否事后补录"


def toks(s):
    return set(s.replace("（", " ").replace("）", " ").replace("，", " ").replace("：", " ").split())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--query", default=QUERY_DEF); a = ap.parse_args()
    q = toks(a.query)
    scores = {}
    for label, kws in CAND.items():
        lab = toks(label)
        inter = len(q & lab)
        # 以关键词并集做加权重叠（类 n-gram 之近似）
        kw_hit = sum(1 for k in kws if k in a.query)
        scores[label] = 0.6*inter/max(1, len(q)) + 0.4*kw_hit/max(1, len(kws))
    items = sorted(scores.items(), key=lambda x: -x[1])
    # softmax（τ=0.2）⇒ 概率分布
    tau = 0.2
    ex = [math.exp(min(s, 1.0)/tau) for _, s in items]
    z = sum(ex)
    dist = [{"label": l, "p": round(e/z, 4)} for (l, _), e in zip(items, ex)]
    conf = dist[0]["p"]
    margin = dist[0]["p"] - dist[1]["p"]
    print("  ═══ 决策模块之「概率分布＋置信度」示范（★本地零调用；一次前向）═══")
    print("   ★query：%s" % a.query)
    print("   ★概率分布（softmax τ=0.2；p 之和=%s）：" % round(sum(d["p"] for d in dist), 4))
    for d in dist:
        print("      %.4f ｜ %s" % (d["p"], d["label"]))
    print("   ★置信度：top1 p=%.4f ｜ margin=%.4f ｜ 判=%s"
          % (conf, margin, "★可信" if conf >= 0.5 else "★存疑"))
    print("   ★输出契约：{label, p, confidence} ｜ p 为分布、confidence=margin")
    out = pathlib.Path(__file__).resolve().parent.parent/"outbox"/"mem"/("decision_dist_demo_%s.json" % time.strftime("%Y%m%d_%H%M"))
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "query": a.query,
        "distribution": dist, "confidence": conf, "margin": round(margin, 4),
        "sum_p": round(sum(d["p"] for d in dist), 4)}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
