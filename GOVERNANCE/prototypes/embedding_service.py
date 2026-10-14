#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
向量编码服务层 — 多通道降级链
档号: DF-IMPL-20261012-YANJIAN-Q1.1
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

降级链: 百炼text-embedding-v4 → 302.AI text-embedding-3-large → 硅基流动 bge-large-zh-v1.5
凭据不落盘: 从环境变量读取
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
import hashlib


class EmbeddingService:
    """向量编码服务 — 三通道降级链"""

    # 通道配置（凭据从环境变量读取，不落盘）
    CHANNELS = [
        {
            "name": "bailian",
            "model": "text-embedding-v4",
            "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
            "env_key": "DASHSCOPE_API_KEY",
            "dim": 1024,
            "priority": 1,
        },
        {
            "name": "302ai",
            "model": "text-embedding-3-large",
            "endpoint": "https://api.302ai.cn/v1/embeddings",
            "env_key": "API_302AI_KEY",
            "dim": 3072,
            "priority": 2,
        },
        {
            "name": "siliconflow",
            "model": "BAAI/bge-large-zh-v1.5",
            "endpoint": "https://api.siliconflow.cn/v1/embeddings",
            "env_key": "SILICONFLOW_API_KEY",
            "dim": 1024,
            "priority": 3,
        },
    ]

    def __init__(self, preferred_channel: Optional[str] = None):
        """
        Args:
            preferred_channel: 指定首选通道名称 ("bailian"/"302ai"/"siliconflow")
                              None则按优先级自动降级
        """
        self.preferred_channel = preferred_channel
        self._channel_order = self._resolve_channel_order()

    def _resolve_channel_order(self) -> List[Dict]:
        """解析通道顺序：首选通道优先，其余按priority排序"""
        if self.preferred_channel:
            preferred = [c for c in self.CHANNELS if c["name"] == self.preferred_channel]
            others = sorted(
                [c for c in self.CHANNELS if c["name"] != self.preferred_channel],
                key=lambda x: x["priority"],
            )
            return preferred + others
        return sorted(self.CHANNELS, key=lambda x: x["priority"])

    def _get_api_key(self, env_key: str) -> Optional[str]:
        """从环境变量读取API Key，不落盘"""
        return os.environ.get(env_key)

    def _call_channel(self, channel: Dict, text: str) -> Tuple[bool, Dict]:
        """调用单个通道，返回 (success, result)"""
        api_key = self._get_api_key(channel["env_key"])
        if not api_key:
            return False, {"error": f"环境变量 {channel['env_key']} 未设置", "channel": channel["name"]}

        payload = json.dumps({
            "model": channel["model"],
            "input": text,
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

            if "data" in body and len(body["data"]) > 0:
                embedding = body["data"][0].get("embedding", [])
                if embedding and all(isinstance(x, (int, float)) for x in embedding):
                    return True, {
                        "embedding": embedding,
                        "dim": len(embedding),
                        "model": channel["model"],
                        "provider": channel["name"],
                        "latency_ms": latency_ms,
                    }
                else:
                    return False, {"error": "embedding为空或含非数值", "channel": channel["name"]}
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

    def embed(self, text: str) -> Dict:
        """
        向量化文本 — 按降级链尝试所有通道

        Returns:
            {
                "embedding": List[float],
                "dim": int,
                "model": str,
                "provider": str,
                "latency_ms": int,
                "fallback_used": bool,  # 是否使用了非首选通道
            }
        """
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")

        errors = []
        for i, channel in enumerate(self._channel_order):
            success, result = self._call_channel(channel, text)
            if success:
                result["fallback_used"] = i > 0
                return result
            else:
                errors.append(result)
                continue

        # 所有通道都失败
        raise RuntimeError(
            f"所有向量编码通道均失败。错误链: " +
            " → ".join([f"{e.get('channel', '?')}: {e.get('error', '?')[:80]}" for e in errors])
        )

    def embed_batch(self, texts: List[str]) -> List[Dict]:
        """批量向量化"""
        return [self.embed(t) for t in texts]

    def health_check(self) -> Dict:
        """健康检查 — 测试各通道可用性"""
        results = {}
        test_text = "向量编码通道健康检查"
        for channel in self.CHANNELS:
            api_key = self._get_api_key(channel["env_key"])
            if not api_key:
                results[channel["name"]] = {"status": "no_key", "detail": f"环境变量 {channel['env_key']} 未设置"}
                continue
            success, result = self._call_channel(channel, test_text)
            if success:
                results[channel["name"]] = {
                    "status": "ok",
                    "dim": result["dim"],
                    "latency_ms": result["latency_ms"],
                }
            else:
                results[channel["name"]] = {
                    "status": "error",
                    "detail": result.get("error", "")[:150],
                }
        return results


# ===== 测试 =====
if __name__ == "__main__":
    import sys

    # 设置环境变量（从全局声明中的凭据，不落盘到文件）
    # 注意：百炼DashScope API Key需要主权人在控制台生成，此处仅测试替代通道
    # 凭据从环境变量读取，不落盘
    # 请设置: API_302AI_KEY, SILICONFLOW_API_KEY
    if not os.environ.get("API_302AI_KEY") and not os.environ.get("SILICONFLOW_API_KEY"):
        print("⚠ 请先设置环境变量 API_302AI_KEY 和 SILICONFLOW_API_KEY")
        sys.exit(1)

    service = EmbeddingService()

    print("=" * 60)
    print("向量编码服务层 — 健康检查")
    print("=" * 60)
    health = service.health_check()
    for name, info in health.items():
        print(f"  [{name}] {info['status']}", end="")
        if info["status"] == "ok":
            print(f" — dim={info['dim']}, latency={info['latency_ms']}ms")
        elif info["status"] == "error":
            print(f" — {info.get('detail', '')[:80]}")
        else:
            print(f" — {info.get('detail', '')[:80]}")

    print()
    print("=" * 60)
    print("向量编码测试 — 单条文本")
    print("=" * 60)
    try:
        result = service.embed("Graphiti时序知识图谱是A2A网络记忆持久化的核心组件")
        print(f"  provider: {result['provider']}")
        print(f"  model: {result['model']}")
        print(f"  dim: {result['dim']}")
        print(f"  latency: {result['latency_ms']}ms")
        print(f"  fallback_used: {result['fallback_used']}")
        print(f"  embedding[:5]: {result['embedding'][:5]}")
        print(f"  all_finite: {all(isinstance(x, (int, float)) for x in result['embedding'])}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("=" * 60)
    print("向量编码测试 — 批量")
    print("=" * 60)
    try:
        texts = [
            "世界模型支持实时交互的开放式世界探索",
            "决策模型面向高频业务判断的结构化输出",
            "向量编码与重排序模块提升检索精度",
        ]
        results = service.embed_batch(texts)
        for i, r in enumerate(results):
            print(f"  [{i}] provider={r['provider']}, dim={r['dim']}, latency={r['latency_ms']}ms")
    except Exception as e:
        print(f"  ERROR: {e}")