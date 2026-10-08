# -*- coding: utf-8 -*-
"""bailian_ops.py —— 阿里云百炼·例行工作器（实战固化）v1.0.0

## 立法定位（承主权人「聚焦阿里云百炼实战」与令条四模块强制调用）
把百炼四模块固化为**本席例行工作之器物**，**非探针、非演示**：
  world   世界模型（qwen-turbo）：对席务现状作**一句话简报**（零值输入，输出即用）
  decide  决策模型（qwen-turbo）：对状态作**三态判定＋置信度**（严格 JSON 输出）
  embed   向量编码（text-embedding-v4）：对文本作向量（默认打印维度与首 4 值；--full 全量）
  rerank  重排序（gte-rerank-v2）：对文档集作相关性排序（输出带分排序）

## 凭据（★零回显纪律）
API-KEY 唯一存放处：`%USERPROFILE%\\.zcode\\workspace\\default\\a2a-bridge\\.env` 之 DASHSCOPE_API_KEY。
本器**只读该键、仅在内存变量使用、绝不打印**。

## 用法
    python bailian_ops.py world   "<文本>"
    python bailian_ops.py decide  "<状态描述>"
    python bailian_ops.py embed   "<文本>" [--full]
    python bailian_ops.py rerank  "<查询>" <文档1> <文档2> [...]
    python bailian_ops.py --smoke
退出码：0 成功；1 调用失败；2 用法/未测。
"""
import argparse
import json
import pathlib
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
ENV = pathlib.Path.home() / ".zcode" / "workspace" / "default" / "a2a-bridge" / ".env"
BASE = "https://dashscope.aliyuncs.com"
CB = BASE + "/compatible-mode/v1/chat/completions"


def key() -> str:
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("DASHSCOPE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("★ .env 无 DASHSCOPE_API_KEY ⇒ 未测")


def chat(model, prompt, max_tokens=200):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(CB, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + key())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
            return j["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "replace")
        print("★ HTTP %d ｜ %s" % (e.code, json.loads(b).get("error", {}).get("code", b[:60])))
        return None


def embed_one(text):
    body = json.dumps({"model": "text-embedding-v4", "input": {"texts": [text]}}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + "/api/v1/services/embeddings/text-embedding/text-embedding",
                                 data=body, method="POST")
    req.add_header("Authorization", "Bearer " + key())
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8", "replace"))["output"]["embeddings"][0]["embedding"]


def rerank(query, docs):
    body = json.dumps({"model": "gte-rerank-v2", "input": {"query": query, "documents": docs}},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + "/api/v1/services/rerank/text-rerank/text-rerank",
                                 data=body, method="POST")
    req.add_header("Authorization", "Bearer " + key())
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8", "replace"))["output"]["results"]


def cmd_world(a):
    out = chat("qwen-turbo", "请用一句话简报（不超过40字）：" + a.text)
    if out is None:
        return 1
    print(out.strip())
    return 0


def cmd_decide(a):
    prompt = ('对下述状态作三态判定，严格只输出 JSON（无其他文字）：'
              '{"verdict":"ALIGNED|MISALIGNED|UNMEASURED","confidence":0到1}。状态：' + a.text)
    out = chat("qwen-turbo", prompt, 120)
    if out is None:
        return 1
    print(out.strip())
    return 0


def cmd_embed(a):
    try:
        v = embed_one(a.text)
    except Exception as e:
        print("★ 失败：%s" % str(e)[:80])
        return 1
    if a.full:
        print(json.dumps(v))
    else:
        print("维度=%d ｜ 首4=%s" % (len(v), [round(x, 4) for x in v[:4]]))
    return 0


def cmd_rerank(a):
    try:
        rs = rerank(a.query, a.docs)
    except Exception as e:
        print("★ 失败：%s" % str(e)[:80])
        return 1
    for it in sorted(rs, key=lambda x: -x["relevance_score"]):
        print("%.4f ｜ %s" % (it["relevance_score"], a.docs[it["index"]][:60]))
    return 0


def cmd_smoke():
    d = chat("qwen-turbo", '只输出 JSON：{"verdict":"ALIGNED","confidence":1}', 60)
    if not d or "verdict" not in d:
        print("★ decide 负断言未过")
        return 1
    v = embed_one("收到")
    if len(v) < 100:
        print("★ embed 负断言未过")
        return 1
    print("SMOKE PASS（decide JSON＋embed 维度）")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="bailian_ops")
    ap.add_argument("--smoke", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("world"); w.add_argument("text"); w.set_defaults(fn=cmd_world)
    d = sub.add_parser("decide"); d.add_argument("text"); d.set_defaults(fn=cmd_decide)
    e = sub.add_parser("embed"); e.add_argument("text"); e.add_argument("--full", action="store_true"); e.set_defaults(fn=cmd_embed)
    r = sub.add_parser("rerank"); r.add_argument("query"); r.add_argument("docs", nargs="+"); r.set_defaults(fn=cmd_rerank)
    a = ap.parse_args()
    if a.smoke:
        return cmd_smoke()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
