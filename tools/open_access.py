#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""open_access.py —— 开放获取资源检索适配器（跨库 + 格式归一化）。

依"部署建议：优先对接开放获取资源 + 跨库检索与格式归一化"，封装三个免凭据公共源：
OpenLibrary（图书）/ Gutendex（古腾堡公版书）/ arXiv（论文）。纯标准库，Windows 直跑。
统一输出 {source, title, author, year, url, kind}，供上层 A2A 端口插件调用。
"""
import json
import time
import urllib.parse
import urllib.request


def _get_json(url, timeout=15, retries=2, backoff=1.0):
    """请求 + 重试（异常回退：重试 N 次、指数退避，仍失败则抛出，由上层捕获切换源）。"""
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenPlanLink-A2A/0.1 (open-access adapter)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if i < retries:
                time.sleep(backoff * (2 ** i))
    raise last


def search_openlibrary(q, limit=5):
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode({"q": q, "limit": limit})
    out = []
    for d in _get_json(url).get("docs", [])[:limit]:
        out.append({"source": "openlibrary", "title": d.get("title", ""),
                    "author": (d.get("author_name") or [""])[0],
                    "year": (d.get("first_publish_year")),
                    "url": "https://openlibrary.org" + (d.get("key") or ""), "kind": "book"})
    return out


def search_gutenberg(q, limit=5):
    url = "https://gutendex.com/books?" + urllib.parse.urlencode({"search": q})
    out = []
    for d in _get_json(url).get("results", [])[:limit]:
        out.append({"source": "gutenberg", "title": d.get("title", ""),
                    "author": (d.get("authors") or [{}])[0].get("name", ""),
                    "year": None, "url": d.get("formats", {}).get("text/plain; charset=utf-8") or "",
                    "kind": "public-domain-book"})
    return out


def search_arxiv(q, limit=5):
    import xml.etree.ElementTree as ET
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": "all:" + q, "max_results": limit})
    req = urllib.request.Request(url, headers={"User-Agent": "OpenPlanLink-A2A/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        root = ET.fromstring(r.read().decode("utf-8"))
    out = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in root.findall("a:entry", ns)[:limit]:
        out.append({"source": "arxiv", "title": e.findtext("a:title", "", ns).strip(),
                    "author": (e.find("a:author/a:name", ns).text if e.find("a:author/a:name", ns) is not None else ""),
                    "year": e.findtext("a:published", "", ns)[:4],
                    "url": e.findtext("a:id", "", ns), "kind": "paper"})
    return out


SOURCES = {}  # 源注册表：策略模式动态注册，新增数据源不改核心调度
METRICS = {}  # 可观测性：每源 {ok, fail, latency_ms[]}


def register(name, fn):
    """注册一个数据源适配器（策略）。fn(query, limit) -> [统一行]。"""
    SOURCES[name] = fn


register("openlibrary", search_openlibrary)
register("gutenberg", search_gutenberg)
register("arxiv", search_arxiv)


def _record(name, ok, latency_ms):
    m = METRICS.setdefault(name, {"ok": 0, "fail": 0, "latency": []})
    m["ok" if ok else "fail"] += 1
    m["latency"].append(round(latency_ms, 1))


def _sorted_sources():
    """路由权重：按健康度排序——成功率高的优先、成功但慢的次之、失败的靠后。"""
    def key(name):
        s = stats().get(name, {})
        sr = s.get("success_rate") or 0
        lat = s.get("avg_latency_ms") or 1e9
        return (-sr, lat, name)
    return sorted(SOURCES, key=key)


def unified_search(q, limit=5):
    """跨库检索 + 格式归一化：按路由权重遍历（健康优先），源故障自动记录、不阻断整体。"""
    rows = []
    for name in _sorted_sources():
        fn = SOURCES[name]
        t0 = time.time()
        try:
            rows += fn(q, limit)
            _record(name, True, (time.time() - t0) * 1000)
        except Exception as e:
            _record(name, False, (time.time() - t0) * 1000)
            rows.append({"source": name, "title": "(检索失败)", "author": "", "year": None,
                         "url": "", "kind": "error", "error": str(e)[:80]})
    return rows


def stats():
    """各源健康度：成功率 + 平均延迟，供路由权重调整。"""
    out = {}
    for name, m in METRICS.items():
        total = m["ok"] + m["fail"]
        lat = m["latency"]
        out[name] = {"success_rate": round(m["ok"] / total, 3) if total else None,
                     "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else None,
                     "ok": m["ok"], "fail": m["fail"]}
    return out


if __name__ == "__main__":
    q = "a2a agent"
    print("══ 统一检索『%s』══" % q)
    for r in unified_search(q, 3):
        print("  [%s] %s ｜ %s ｜ %s" % (r["kind"], r["title"][:40], (r["author"] or "")[:20], r["url"][:50]))
