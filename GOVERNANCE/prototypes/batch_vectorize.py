#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
批量向量化管线 — Phase 0
档号: DF-IMPL-20261014-YANJIAN-P0
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

功能:
  1. 扫描A2A台账目录(.md/.json) + GOVERNANCE目录(.md)
  2. 提取文本内容，分块处理
  3. 调用向量编码API (302.AI 3072维 + 硅基流动 1024维)
  4. 存储向量索引到JSON文件，支持增量恢复
  5. 构建检索管线: 查询→向量检索→重排序

凭据不落盘: 从环境变量读取
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# ============================================================
# 配置
# ============================================================

# 数据源目录
A2A_DIR = r"C:\Users\欧阳宏俊\WPS Cloud\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A共同体_总线指针与台账"
GOVERNANCE_DIR = r"C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app\GOVERNANCE"

# 输出目录
OUTPUT_DIR = r"C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app\GOVERNANCE\research\vector_index"

# 分块配置
CHUNK_SIZE = 800  # 每块约800字符
CHUNK_OVERLAP = 100  # 块间重叠100字符

# API配置
EMBEDDING_302AI = {
    "name": "302ai",
    "model": "text-embedding-3-large",
    "endpoint": "https://api.302ai.cn/v1/embeddings",
    "env_key": "API_302AI_KEY",
    "dim": 3072,
}

EMBEDDING_SILICONFLOW = {
    "name": "siliconflow",
    "model": "BAAI/bge-large-zh-v1.5",
    "endpoint": "https://api.siliconflow.cn/v1/embeddings",
    "env_key": "SILICONFLOW_API_KEY",
    "dim": 1024,
}

RERANK_SILICONFLOW = {
    "name": "siliconflow",
    "model": "BAAI/bge-reranker-v2-m3",
    "endpoint": "https://api.siliconflow.cn/v1/rerank",
    "env_key": "SILICONFLOW_API_KEY",
}

# 速率限制
API_DELAY = 0.3  # 每次API调用后延迟0.3秒
BATCH_SAVE_INTERVAL = 20  # 每处理20个文件保存一次进度


# ============================================================
# 文本提取与分块
# ============================================================

def extract_text_from_md(filepath: str) -> str:
    """从Markdown文件提取文本"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠ 读取MD失败 {filepath}: {e}")
        return ""


def extract_text_from_json(filepath: str) -> str:
    """从JSON文件提取文本字段"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 递归提取所有字符串值
        texts = []
        def _extract(obj):
            if isinstance(obj, str) and len(obj) > 10:
                texts.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    _extract(item)
        _extract(data)
        return "\n".join(texts)
    except Exception as e:
        print(f"  ⚠ 读取JSON失败 {filepath}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """将长文本分块，带重叠"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap  # 重叠
    return chunks


def content_hash(text: str) -> str:
    """计算文本的SHA3-512哈希"""
    return hashlib.sha3_512(text.encode("utf-8")).hexdigest()[:32]


# ============================================================
# 向量编码API调用
# ============================================================

def call_embedding_api(channel: Dict, text: str) -> Tuple[bool, Dict]:
    """调用向量编码API"""
    api_key = os.environ.get(channel["env_key"])
    if not api_key:
        return False, {"error": f"环境变量 {channel['env_key']} 未设置"}

    payload = json.dumps({
        "model": channel["model"],
        "input": text[:8000],  # 截断超长文本
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib.request.Request(
            channel["endpoint"], data=payload, headers=headers, method="POST"
        )
        start_time = time.time()
        resp = urllib.request.urlopen(req, timeout=60)
        latency_ms = int((time.time() - start_time) * 1000)
        body = json.loads(resp.read())

        if "data" in body and len(body["data"]) > 0:
            embedding = body["data"][0].get("embedding", [])
            if embedding:
                return True, {
                    "embedding": embedding,
                    "dim": len(embedding),
                    "latency_ms": latency_ms,
                }
        return False, {"error": f"响应格式异常: {str(body)[:200]}"}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:300]
        return False, {"error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return False, {"error": str(e)[:300]}


def call_rerank_api(query: str, documents: List[str]) -> Tuple[bool, Dict]:
    """调用重排序API"""
    api_key = os.environ.get(RERANK_SILICONFLOW["env_key"])
    if not api_key:
        return False, {"error": f"环境变量 {RERANK_SILICONFLOW['env_key']} 未设置"}

    payload = json.dumps({
        "model": RERANK_SILICONFLOW["model"],
        "query": query,
        "documents": documents,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib.request.Request(
            RERANK_SILICONFLOW["endpoint"], data=payload, headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read())
        if "results" in body:
            results = sorted(body["results"], key=lambda x: x.get("relevance_score", 0), reverse=True)
            return True, {"results": results}
        return False, {"error": f"响应格式异常: {str(body)[:200]}"}
    except Exception as e:
        return False, {"error": str(e)[:300]}


# ============================================================
# 文件扫描
# ============================================================

def scan_a2a_directory() -> List[Dict]:
    """扫描A2A台账目录"""
    files = []
    if not os.path.exists(A2A_DIR):
        print(f"  ⚠ A2A目录不存在: {A2A_DIR}")
        return files

    for root, dirs, filenames in os.walk(A2A_DIR):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".md", ".json"]:
                rel_path = os.path.relpath(fpath, A2A_DIR)
                files.append({
                    "source": "a2a",
                    "path": fpath,
                    "rel_path": rel_path,
                    "filename": fname,
                    "ext": ext,
                })
    return files


def scan_governance_directory() -> List[Dict]:
    """扫描GOVERNANCE目录"""
    files = []
    if not os.path.exists(GOVERNANCE_DIR):
        print(f"  ⚠ GOVERNANCE目录不存在: {GOVERNANCE_DIR}")
        return files

    for root, dirs, filenames in os.walk(GOVERNANCE_DIR):
        # 跳过external目录（外部仓库克隆）
        if "external" in root:
            continue
        for fname in filenames:
            if fname.endswith(".md"):
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, GOVERNANCE_DIR)
                files.append({
                    "source": "governance",
                    "path": fpath,
                    "rel_path": rel_path,
                    "filename": fname,
                    "ext": ".md",
                })
    return files


# ============================================================
# 向量索引构建
# ============================================================

def load_progress(progress_file: str) -> Dict:
    """加载进度文件"""
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"processed_files": [], "total_chunks": 0, "total_vectors": 0}


def save_progress(progress_file: str, progress: Dict):
    """保存进度文件"""
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def save_vector_batch(vector_file: str, vectors: List[Dict]):
    """保存向量批次到文件（追加模式）"""
    # 读取已有向量
    existing = []
    if os.path.exists(vector_file):
        try:
            with open(vector_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            existing = []
    
    existing.extend(vectors)
    
    with open(vector_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)


def build_vector_index():
    """构建向量索引 — 主流程"""
    print("=" * 70)
    print("Phase 0: 批量向量化管线")
    print("署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)")
    print("档号: DF-IMPL-20261014-YANJIAN-P0")
    print("=" * 70)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 扫描文件
    print("\n[1/5] 扫描数据源...")
    a2a_files = scan_a2a_directory()
    gov_files = scan_governance_directory()
    all_files = a2a_files + gov_files
    print(f"  A2A台账: {len(a2a_files)} 个文件")
    print(f"  GOVERNANCE: {len(gov_files)} 个文件")
    print(f"  总计: {len(all_files)} 个文件")

    # 加载进度
    progress_file = os.path.join(OUTPUT_DIR, "progress.json")
    progress = load_progress(progress_file)
    processed_set = set(progress["processed_files"])
    print(f"  已处理: {len(processed_set)} 个文件（增量恢复）")

    # 准备通道
    # A2A台账用硅基流动(中文优化, 1024维)
    # GOVERNANCE用302.AI(3072维, 更详细)
    a2a_channel = EMBEDDING_SILICONFLOW
    gov_channel = EMBEDDING_302AI

    # 检查API Key
    for ch in [a2a_channel, gov_channel]:
        key = os.environ.get(ch["env_key"])
        if not key:
            print(f"  ⚠ 环境变量 {ch['env_key']} 未设置，跳过通道 {ch['name']}")
        else:
            print(f"  ✓ 通道 {ch['name']} ({ch['model']}) 凭据已就绪")

    # 向量索引文件
    a2a_vector_file = os.path.join(OUTPUT_DIR, "a2a_vectors.json")
    gov_vector_file = os.path.join(OUTPUT_DIR, "governance_vectors.json")

    # 统计
    stats = {
        "a2a": {"files": 0, "chunks": 0, "vectors": 0, "errors": 0},
        "governance": {"files": 0, "chunks": 0, "vectors": 0, "errors": 0},
    }

    # 处理文件
    print(f"\n[2/5] 开始向量化处理...")
    pending_files = [f for f in all_files if f["path"] not in processed_set]
    print(f"  待处理: {len(pending_files)} 个文件")

    a2a_batch = []
    gov_batch = []
    file_count = 0

    for file_info in pending_files:
        file_count += 1
        source = file_info["source"]
        fpath = file_info["path"]
        fname = file_info["filename"]

        # 提取文本
        if file_info["ext"] == ".md":
            text = extract_text_from_md(fpath)
        elif file_info["ext"] == ".json":
            text = extract_text_from_json(fpath)
        else:
            continue

        if not text or not text.strip():
            processed_set.add(fpath)
            continue

        # 分块
        chunks = chunk_text(text)
        if not chunks:
            processed_set.add(fpath)
            continue

        # 选择通道
        channel = a2a_channel if source == "a2a" else gov_channel
        api_key = os.environ.get(channel["env_key"])
        if not api_key:
            print(f"  ⚠ 跳过 {fname} — 通道 {channel['name']} 无凭据")
            continue

        # 向量化每个块
        for chunk_idx, chunk in enumerate(chunks):
            success, result = call_embedding_api(channel, chunk)
            time.sleep(API_DELAY)

            if success:
                vector_entry = {
                    "source": source,
                    "file": file_info["rel_path"],
                    "filename": fname,
                    "chunk_idx": chunk_idx,
                    "total_chunks": len(chunks),
                    "text_preview": chunk[:200],
                    "content_hash": content_hash(chunk),
                    "embedding": result["embedding"],
                    "dim": result["dim"],
                    "model": channel["model"],
                    "provider": channel["name"],
                    "timestamp": int(time.time()),
                }

                if source == "a2a":
                    a2a_batch.append(vector_entry)
                else:
                    gov_batch.append(vector_entry)

                stats[source]["vectors"] += 1
            else:
                print(f"  ⚠ 向量化失败 {fname} chunk#{chunk_idx}: {result['error'][:80]}")
                stats[source]["errors"] += 1
                # 失败后等待更长时间
                time.sleep(1.0)

        stats[source]["files"] += 1
        stats[source]["chunks"] += len(chunks)
        processed_set.add(fpath)

        # 定期保存
        if file_count % BATCH_SAVE_INTERVAL == 0:
            print(f"  [{file_count}/{len(pending_files)}] 保存进度...")
            if a2a_batch:
                save_vector_batch(a2a_vector_file, a2a_batch)
                a2a_batch = []
            if gov_batch:
                save_vector_batch(gov_vector_file, gov_batch)
                gov_batch = []
            progress["processed_files"] = list(processed_set)
            progress["total_chunks"] = stats["a2a"]["chunks"] + stats["governance"]["chunks"]
            progress["total_vectors"] = stats["a2a"]["vectors"] + stats["governance"]["vectors"]
            save_progress(progress_file, progress)

        # 每100个文件打印进度
        if file_count % 100 == 0:
            print(f"  [{file_count}/{len(pending_files)}] A2A:{stats['a2a']['vectors']}向量 GOV:{stats['governance']['vectors']}向量")

    # 保存剩余批次
    print(f"\n[3/5] 保存最终批次...")
    if a2a_batch:
        save_vector_batch(a2a_vector_file, a2a_batch)
    if gov_batch:
        save_vector_batch(gov_vector_file, gov_batch)

    # 保存进度
    progress["processed_files"] = list(processed_set)
    progress["total_chunks"] = stats["a2a"]["chunks"] + stats["governance"]["chunks"]
    progress["total_vectors"] = stats["a2a"]["vectors"] + stats["governance"]["vectors"]
    save_progress(progress_file, progress)

    # 统计报告
    print(f"\n[4/5] 向量化统计:")
    print(f"  A2A台账: {stats['a2a']['files']}文件 / {stats['a2a']['chunks']}块 / {stats['a2a']['vectors']}向量 / {stats['a2a']['errors']}错误")
    print(f"  GOVERNANCE: {stats['governance']['files']}文件 / {stats['governance']['chunks']}块 / {stats['governance']['vectors']}向量 / {stats['governance']['errors']}错误")
    print(f"  总计: {stats['a2a']['vectors'] + stats['governance']['vectors']}向量")

    # 构建检索索引摘要
    print(f"\n[5/5] 构建检索索引摘要...")
    index_summary = {
        "timestamp": int(time.time()),
        "a2a": {
            "files": stats["a2a"]["files"],
            "vectors": stats["a2a"]["vectors"],
            "dim": a2a_channel["dim"],
            "model": a2a_channel["model"],
            "vector_file": "a2a_vectors.json",
        },
        "governance": {
            "files": stats["governance"]["files"],
            "vectors": stats["governance"]["vectors"],
            "dim": gov_channel["dim"],
            "model": gov_channel["model"],
            "vector_file": "governance_vectors.json",
        },
        "total_vectors": stats["a2a"]["vectors"] + stats["governance"]["vectors"],
    }
    summary_file = os.path.join(OUTPUT_DIR, "index_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(index_summary, f, ensure_ascii=False, indent=2)
    print(f"  索引摘要已保存: {summary_file}")

    return stats


# ============================================================
# 检索管线
# ============================================================

def vector_search(query: str, top_k: int = 10, source: str = "all") -> List[Dict]:
    """
    向量检索: query → 向量化 → 余弦相似度 → top_k结果
    """
    import math

    # 选择通道
    if source == "a2a":
        channel = EMBEDDING_SILICONFLOW
        vector_file = os.path.join(OUTPUT_DIR, "a2a_vectors.json")
    elif source == "governance":
        channel = EMBEDDING_302AI
        vector_file = os.path.join(OUTPUT_DIR, "governance_vectors.json")
    else:
        # 搜索两个索引
        results_a2a = vector_search(query, top_k, "a2a")
        results_gov = vector_search(query, top_k, "governance")
        combined = results_a2a + results_gov
        combined.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return combined[:top_k]

    # 向量化查询
    success, result = call_embedding_api(channel, query)
    if not success:
        print(f"  ⚠ 查询向量化失败: {result['error']}")
        return []

    query_vec = result["embedding"]

    # 加载向量索引
    if not os.path.exists(vector_file):
        print(f"  ⚠ 向量索引文件不存在: {vector_file}")
        return []

    with open(vector_file, "r", encoding="utf-8") as f:
        vectors = json.load(f)

    # 计算余弦相似度
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)

    scored = []
    for v in vectors:
        sim = cosine_sim(query_vec, v["embedding"])
        scored.append({
            "file": v["file"],
            "filename": v["filename"],
            "chunk_idx": v["chunk_idx"],
            "text_preview": v["text_preview"],
            "similarity": sim,
            "source": v["source"],
            "model": v["model"],
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def search_with_rerank(query: str, top_k: int = 5) -> List[Dict]:
    """
    检索+重排序管线: query → 向量检索top20 → 重排序top5
    """
    # 第一步: 向量检索获取top20
    print(f"  [检索] 查询: {query}")
    candidates = vector_search(query, top_k=20, source="all")
    if not candidates:
        print("  [检索] 无结果")
        return []

    print(f"  [检索] 向量检索返回 {len(candidates)} 个候选")

    # 第二步: 重排序
    documents = [c["text_preview"] for c in candidates]
    success, result = call_rerank_api(query, documents)

    if success:
        print(f"  [重排序] 重排序完成，返回 {len(result['results'])} 个结果")
        reranked = []
        for r in result["results"]:
            idx = r["index"]
            if idx < len(candidates):
                entry = candidates[idx].copy()
                entry["rerank_score"] = r["relevance_score"]
                reranked.append(entry)
        return reranked[:top_k]
    else:
        print(f"  [重排序] 重排序失败: {result['error'][:80]}，使用向量检索结果")
        return candidates[:top_k]


# ============================================================
# 主入口
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="批量向量化管线")
    parser.add_argument("--build", action="store_true", help="构建向量索引")
    parser.add_argument("--search", type=str, help="搜索查询")
    parser.add_argument("--rerank", action="store_true", help="搜索时使用重排序")
    parser.add_argument("--source", type=str, default="all", choices=["all", "a2a", "governance"])
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.build:
        stats = build_vector_index()
        print("\n✅ 向量索引构建完成")
        # 保存统计到JSON
        stats_file = os.path.join(OUTPUT_DIR, "build_stats.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"  统计报告: {stats_file}")

    elif args.search:
        if args.rerank:
            results = search_with_rerank(args.search, top_k=args.top_k)
        else:
            results = vector_search(args.search, top_k=args.top_k, source=args.source)

        print(f"\n{'='*70}")
        print(f"检索结果 (top {len(results)})")
        print(f"{'='*70}")
        for i, r in enumerate(results):
            score = r.get("rerank_score", r.get("similarity", 0))
            score_type = "rerank" if "rerank_score" in r else "cosine"
            print(f"\n  [{i+1}] {r['filename']} (chunk#{r['chunk_idx']}) [{r['source']}]")
            print(f"      {score_type}={score:.4f}")
            print(f"      {r['text_preview'][:120]}...")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()