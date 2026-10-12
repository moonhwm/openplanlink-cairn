# -*- coding: utf-8 -*-
"""ports_triage.py —— 裸「名:端口」候选三分类甄别（**不回显值**）

背景：`disclosure_scan.py` 精化后全仓仍有 81 处「裸名称:端口」**候选**（轮20 实测）。
本工具把候选**按结构分组**并三分类，供人工/网络裁定，避免"候选数＝披露面"的误解。

分类规则（**结构判据，不看语义**）：
  · **A 疑似真端口**：端口 ∈ 常见服务端口集（3000/4173/5432/6379/8000/8080/8791/8792/9200/11434 等）
    或名称形如 `<字母串><可选数字>` 且不含 `_`（服务名常见形态）
  · **B 他形文本**：名称含 `_`、或以 `--`/数字结尾、或为已知非端口词（如 css/单位/协议前缀）
  · **C 待人工判**：其余

纪律：**只打印掩码（前 2 字符 + ***）**；不打印原值（承"复述即再披露"）。
用法:
  python ports_triage.py [--repo <路径>] [--limit 40]
"""
import argparse
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PAT = re.compile(
    r"\b(?!font-weight|font-size|font-family|line-height|letter-spacing|min-width|max-width"
    r"|min-height|max-height|border-radius|border-width|z-index|text-align|background-color"
    r"|width|height|margin|padding|border|top|left|right|bottom|gap|flex|grid|color|opacity"
    r"|transition|transform|scale|rotate|delay|duration|content|order|columns|rows)\b"
    r"([a-zA-Z][a-zA-Z0-9_\-]{2,})[:：]([1-9]\d{3,4})\b", re.I)

COMMON_PORTS = {"3000", "3001", "4173", "433", "443", "5432", "6379", "8000", "8080", "8443",
                "8791", "8792", "8888", "9000", "9200", "11434", "1024", "1080", "1081"}
NOT_PORT_WORDS = {"css", "px", "em", "rem", "vh", "vw", "pt", "ms", "s", "fr", "deg", "http",
                  "https", "file", "data", "utf", "iso", "sha", "md", "json", "yaml",
                  # ↓ v0.2：引文/文献类前缀（arXiv:<编号值不录> 一类为本轮实证的主要误报源）
                  "arxiv", "doi", "isbn", "issn", "vol", "no", "pp", "ch", "sec", "fig", "tab",
                  "eq", "ref", "refs", "ver", "rev", "chapter", "section", "line", "id"}
SERVICE_NAMES = {"localhost", "proxy", "a2a", "relay", "server", "api", "host", "node", "port",
                 "ws", "wss", "rpc", "db", "sql", "redis", "postgres", "supabase", "bridge",
                 "gateway", "worker", "daemon", "bus", "endpoint", "health"}
CONTEXT_RX = re.compile(r"(?i)(listen|端口|port\b|bind|服务端|监听|本机服务|服务名)")


def mask(v: str) -> str:
    return (v[:2] + "***") if len(v) > 2 else "***"


def git(args, binary=True):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, timeout=300)
    return (p.stdout if binary else p.stdout.decode("utf-8", "replace")), p.returncode


def classify(name: str, port: str, line: str = ""):
    """v0.2：先排文本类（含引文前缀），再以服务名白名单/语境闸判真端口，其余待人工。"""
    n = name.lower()
    if n in NOT_PORT_WORDS or re.match(r"^[a-z]{1,3}$", n):
        return "B 他形文本"
    if n in SERVICE_NAMES:
        return "A 疑似真端口"
    if port in COMMON_PORTS:
        return "A 疑似真端口"
    if CONTEXT_RX.search(line or ""):
        return "A 疑似真端口"
    if "_" in name or re.search(r"\d$", name) or name.endswith("--"):
        return "B 他形文本"
    if re.match(r"^[a-z][a-z\-]{2,}$", n):
        return "C 待人工判"
    return "C 待人工判"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\欧阳宏俊\openplanlink-mirror")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    global REPO
    REPO = pathlib.Path(a.repo)

    files, _ = git(["ls-files"], binary=False)
    rows = []
    for f in files.split("\n"):
        f = f.strip()
        if not f or f == "attest-hmac-sha3-512.json":
            continue
        if pathlib.Path(f).suffix.lower() not in {".md", ".otl", ".txt", ".json", ".jsonl", ".py",
                                                 ".mjs", ".js", ".yml", ".yaml", ".sh", ".ps1",
                                                 ".led", ".csv", ".ini", ".cfg", ".toml", ".html"}:
            continue
        blob, code = git(["show", "HEAD:%s" % f])
        if code != 0:
            continue
        try:
            txt = blob.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for m in PAT.finditer(txt):
            nm, pt = m.group(1), m.group(2)
            rows.append((classify(nm, pt, txt[max(0,m.start()-60):m.end()+60]), nm.lower(), pt, f))

    print("★ 裸「名:端口」候选三分类甄别（**不回显值**，仅掩码）")
    print("★ 总候选：%d 处" % len(rows))
    from collections import Counter
    cnt = Counter(r[0] for r in rows)
    print("")
    print("| 分类 | 命中数 | 占比 |")
    print("|---|---|---|")
    for k in sorted(cnt):
        print("| %s | %d | %.0f%% |" % (k, cnt[k], 100.0 * cnt[k] / max(1, len(rows))))
    print("")
    print("| 分类 | 名称掩码 | 端口位数 | 文件（前 %d 条） |" % a.limit)
    print("|---|---|---|---|")
    for cls, nm, pt, f in rows[: a.limit]:
        print("| %s | `%s` | %d 位 | `%s` |" % (cls, mask(nm), len(pt), f))
    if len(rows) > a.limit:
        print("| … | … | … | （余 %d 条略） |" % (len(rows) - a.limit))
    print("")
    print("判读：A 类应优先按披露口径处置（改类别名或取数命令）；B 类属同形文本可排除；C 类逐项人工确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
