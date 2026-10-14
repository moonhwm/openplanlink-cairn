#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
重排序服务层 — 多通道降级链
档号: DF-IMPL-20261012-YANJIAN-Q1.2
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

降级链: 百炼gte-rerank-v2 → 硅基流动 bge-reranker-v2-m3
凭据不落盘: 从环境变量读取
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple


class RerankService:
    """重排序服务 — 双通道降级链"""

    CHANNELS = [
        {
            "name": "bailian",
            "model": "gte-rerank-v2",
            "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/rerank",
            "env_key": "DASHSCOPE_API_KEY",
            "priority": 1,
        },
        {
            "name": "siliconflow",
            "model": "BAAI/bge-reranker-v2-m3",
            "endpoint": "https://api.siliconflow.cn/v1/rerank",
            "env_key": "SILICONFLOW_API_KEY",
            "priority": 2,
        },
    ]

    def __init__(self, preferred_channel: Optional[str] = None):
        self.preferred_channel = preferred_channel
        self._channel_order = self._resolve_channel_order()

    def _resolve_channel_order(self) -> List[Dict]:
        if self.preferred_channel:
            preferred = [c for c in self.CHANNELS if c["name"] == self.preferred_channel]
            others = sorted(
                [c for c in self.CHANNELS if c["name"] != self.preferred_channel],
                key=lambda x: x["priority"],
            )
            return preferred + others
        return sorted(self.CHANNELS, key=lambda x: x["priority"])

    def _get_api_key(self, env_key: str) -> Optional[str]:
        return os.environ.get(env_key)

    def _call_channel(self, channel: Dict, query: str, documents: List[str]) -> Tuple[bool, Dict]:
        api_key = self._get_api_key(channel["env_key"])
        if not api_key:
            return False, {"error": f"环境变量 {channel['env_key']} 未设置", "channel": channel["name"]}

        payload = json.dumps({
            "model": channel["model"],
            "query": query,
            "documents": documents,
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
            resp = urllib.request.urlopen(req, timeout=30)
            latency_ms = int((time.time() - start_time) * 1000)
            body = json.loads(resp.read())

            if "results" in body:
                results = body["results"]
                # 确保按relevance_score降序排列
                results_sorted = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
                return True, {
                    "results": results_sorted,
                    "model": channel["model"],
                    "provider": channel["name"],
                    "latency_ms": latency_ms,
                }
            else:
                return False, {"error": f"响应格式异常: {str(body)[:200]}", "channel": channel["name"]}

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            return False, {
                "error": f"HTTP {e.code}: {err_body}",
                "channel": channel["name"],
                "http_status": e.code,
            }
        except Exception as e:
            return False, {"error": str(e)[:300], "channel": channel["name"]}

    def rerank(self, query: str, documents: List[str]) -> Dict:
        """
        对documents按与query的相关性重排序

        Returns:
            {
                "results": [{"index": int, "relevance_score": float}],  # 按score降序
                "model": str,
                "provider": str,
                "latency_ms": int,
                "fallback_used": bool,
            }
        """
        if not query or not query.strip():
            raise ValueError("query不能为空")
        if not documents or len(documents) == 0:
            raise ValueError("documents不能为空")

        errors = []
        for i, channel in enumerate(self._channel_order):
            success, result = self._call_channel(channel, query, documents)
            if success:
                result["fallback_used"] = i > 0
                return result
            else:
                errors.append(result)
                continue

        raise RuntimeError(
            f"所有重排序通道均失败。错误链: " +
            " → ".join([f"{e.get('channel', '?')}: {e.get('error', '?')[:80]}" for e in errors])
        )

    def health_check(self) -> Dict:
        results = {}
        test_query = "健康检查"
        test_docs = ["通道可用", "通道不可用"]
        for channel in self.CHANNELS:
            api_key = self._get_api_key(channel["env_key"])
            if not api_key:
                results[channel["name"]] = {"status": "no_key", "detail": f"环境变量 {channel['env_key']} 未设置"}
                continue
            success, result = self._call_channel(channel, test_query, test_docs)
            if success:
                results[channel["name"]] = {
                    "status": "ok",
                    "latency_ms": result["latency_ms"],
                    "results_count": len(result["results"]),
                }
            else:
                results[channel["name"]] = {
                    "status": "error",
                    "detail": result.get("error", "")[:150],
                }
        return results


# ===== 测试 =====
if __name__ == "__main__":
    # 凭据从环境变量读取，不落盘
    # 请设置: SILICONFLOW_API_KEY
    if not os.environ.get("SILICONFLOW_API_KEY"):
        print("⚠ 请先设置环境变量 SILICONFLOW_API_KEY")
        sys.exit(1)

    service = RerankService()

    print("=" * 60)
    print("重排序服务层 — 健康检查")
    print("=" * 60)
    health = service.health_check()
    for name, info in health.items():
        print(f"  [{name}] {info['status']}", end="")
        if info["status"] == "ok":
            print(f" — latency={info['latency_ms']}ms, results={info['results_count']}")
        else:
            print(f" — {info.get('detail', '')[:80]}")

    print()
    print("=" * 60)
    print("重排序测试 — A2A候裁清单相关性")
    print("=" * 60)
    try:
        query = "百炼预算阻断如何解决"
        documents = [
            "裁五：百炼Budget预算调高——唯一代码不可解阻断，需主权人控制台操作",
            "裁六：P4世界模型实跑预算上限——建议单轮≤5元封顶",
            "Q1向量编码服务层：302.AI和硅基流动作为替代通道",
            "Q2 Graphiti集成：Neo4j+302.AI+硅基流动配置",
            "裁八：302ai键轮换——建议立即执行",
        ]
        result = service.rerank(query, documents)
        print(f"  provider: {result['provider']}")
        print(f"  model: {result['model']}")
        print(f"  latency: {result['latency_ms']}ms")
        print(f"  fallback_used: {result['fallback_used']}")
        print(f"  排序结果:")
        for r in result["results"]:
            print(f"    doc{r['index']}: score={r['relevance_score']:.4f} — {documents[r['index']][:50]}")
    except Exception as e:
        print(f"  ERROR: {e}")