#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Graphiti时序知识图谱集成配置
档号: DF-IMPL-20261012-YANJIAN-Q2.1
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

基于Graphiti代码分析P1-P3结果，配置：
  - LLM Provider: 302.AI → qwen-max
  - Embedder: 硅基流动 → BAAI/bge-large-zh-v1.5 (1024维)
  - Reranker: 硅基流动 → BAAI/bge-reranker-v2-m3
  - Graph DB: Neo4j localhost
  - 搜索配方: COMBINED_HYBRID_SEARCH_CROSS_ENCODER
"""

import os
import json
from typing import Dict, Optional


class GraphitiConfig:
    """Graphiti集成配置"""

    # Neo4j配置
    NEO4J_CONFIG = {
        "uri": "bolt://localhost:7687",
        "username": "neo4j",
        "password_env": "NEO4J_PASSWORD",  # 从环境变量读取，不落盘
        "database": "neo4j",
    }

    # LLM配置（302.AI → qwen-max）
    LLM_CONFIG = {
        "provider": "openai_generic",
        "base_url": "https://api.302ai.cn/v1",
        "api_key_env": "API_302AI_KEY",
        "model": "qwen-max",
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    # Embedder配置（硅基流动 → bge-large-zh-v1.5）
    EMBEDDER_CONFIG = {
        "provider": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "model": "BAAI/bge-large-zh-v1.5",
        "dim": 1024,
    }

    # Reranker配置（硅基流动 → bge-reranker-v2-m3）
    RERANKER_CONFIG = {
        "provider": "bge",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "model": "BAAI/bge-reranker-v2-m3",
    }

    # 搜索配方配置
    SEARCH_CONFIG = {
        "default_recipe": "COMBINED_HYBRID_SEARCH_CROSS_ENCODER",
        "available_recipes": [
            "COMBINED_HYBRID_SEARCH_RRF",           # bm25+cosine+RRF
            "COMBINED_HYBRID_SEARCH_CROSS_ENCODER", # bm25+cosine+cross-encoder rerank
            "COMBINED_HYBRID_SEARCH_RRF_WITH_LLM",  # bm25+cosine+RRF+LLM rerank
            "NODE_ONLY_HYBRID_SEARCH_RRF",          # 仅节点搜索
            "NODE_ONLY_HYBRID_SEARCH_CROSS_ENCODER",
            "NODE_ONLY_HYBRID_SEARCH_RRF_WITH_LLM",
            "EDGE_ONLY_HYBRID_SEARCH_RRF",          # 仅边搜索
            "EDGE_ONLY_HYBRID_SEARCH_CROSS_ENCODER",
            "EDGE_ONLY_HYBRID_SEARCH_RRF_WITH_LLM",
            "NODE_AND_EDGE_ONLY_HYBRID_SEARCH_RRF", # 节点+边搜索
            "NODE_AND_EDGE_ONLY_HYBRID_SEARCH_CROSS_ENCODER",
            "NODE_AND_EDGE_ONLY_HYBRID_SEARCH_RRF_WITH_LLM",
        ],
    }

    # MCP Server配置
    MCP_CONFIG = {
        "transport": "http",
        "host": "0.0.0.0",
        "port": 8000,
        "tools": [
            "add_memory",
            "search_memory_facts",
            "search_memory_nodes",
            "search_memory_edges",
            "get_episodes",
            "search",
            "add_entity",
            "add_relation",
            "get_entity",
            "get_relation",
            "delete_entity",
            "delete_relation",
        ],
    }

    # 时序事实管理配置
    TEMPORAL_CONFIG = {
        "valid_at_field": "valid_at",
        "invalid_at_field": "invalid_at",
        "expired_at_field": "expired_at",
        "default_valid_at": "now",
        "default_invalid_at": "infinity",
    }

    def __init__(self):
        self.config = self._build_full_config()

    def _build_full_config(self) -> Dict:
        """构建完整配置"""
        return {
            "neo4j": self.NEO4J_CONFIG,
            "llm": self.LLM_CONFIG,
            "embedder": self.EMBEDDER_CONFIG,
            "reranker": self.RERANKER_CONFIG,
            "search": self.SEARCH_CONFIG,
            "mcp": self.MCP_CONFIG,
            "temporal": self.TEMPORAL_CONFIG,
            "version": "1.0",
            "created_by": "砚坚 (GLM-5.2 ArkTS神经中枢席)",
            "created_at": "2026-10-12",
        }

    def to_json(self) -> str:
        """输出JSON配置"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)

    def to_env_vars(self) -> Dict[str, str]:
        """输出环境变量配置（凭据不落盘）"""
        return {
            "NEO4J_URI": self.NEO4J_CONFIG["uri"],
            "NEO4J_USERNAME": self.NEO4J_CONFIG["username"],
            # NEO4J_PASSWORD 从环境变量读取，不在此处设置
            "GRAPHITI_LLM_BASE_URL": self.LLM_CONFIG["base_url"],
            "GRAPHITI_LLM_MODEL": self.LLM_CONFIG["model"],
            # API keys 从环境变量读取，不在此处设置
            "GRAPHITI_EMBEDDER_BASE_URL": self.EMBEDDER_CONFIG["base_url"],
            "GRAPHITI_EMBEDDER_MODEL": self.EMBEDDER_CONFIG["model"],
            "GRAPHITI_EMBEDDER_DIM": str(self.EMBEDDER_CONFIG["dim"]),
            "GRAPHITI_RERANKER_BASE_URL": self.RERANKER_CONFIG["base_url"],
            "GRAPHITI_RERANKER_MODEL": self.RERANKER_CONFIG["model"],
            "GRAPHITI_SEARCH_RECIPE": self.SEARCH_CONFIG["default_recipe"],
            "GRAPHITI_MCP_PORT": str(self.MCP_CONFIG["port"]),
        }

    def generate_env_file_template(self) -> str:
        """生成.env文件模板（凭据值留空，需手动填写）"""
        lines = [
            "# Graphiti集成配置 — .env模板",
            "# 档号: DF-IMPL-20261012-YANJIAN-Q2.1",
            "# 凭据不落盘: 请手动填写以下值，不要提交到版本控制",
            "",
            "# Neo4j",
            "NEO4J_URI=bolt://localhost:7687",
            "NEO4J_USERNAME=neo4j",
            "NEO4J_PASSWORD=",  # 留空，需手动填写
            "",
            "# LLM (302.AI)",
            "API_302AI_KEY=",  # 留空，需手动填写
            "",
            "# Embedder & Reranker (硅基流动)",
            "SILICONFLOW_API_KEY=",  # 留空，需手动填写
            "",
            "# Graphiti配置",
            "GRAPHITI_LLM_BASE_URL=https://api.302ai.cn/v1",
            "GRAPHITI_LLM_MODEL=qwen-max",
            "GRAPHITI_EMBEDDER_BASE_URL=https://api.siliconflow.cn/v1",
            "GRAPHITI_EMBEDDER_MODEL=BAAI/bge-large-zh-v1.5",
            "GRAPHITI_EMBEDDER_DIM=1024",
            "GRAPHITI_RERANKER_BASE_URL=https://api.siliconflow.cn/v1",
            "GRAPHITI_RERANKER_MODEL=BAAI/bge-reranker-v2-m3",
            "GRAPHITI_SEARCH_RECIPE=COMBINED_HYBRID_SEARCH_CROSS_ENCODER",
            "GRAPHITI_MCP_PORT=8000",
        ]
        return "\n".join(lines)

    def generate_docker_compose(self) -> str:
        """生成docker-compose.yml（Neo4j本地部署）"""
        return """version: '3.8'

services:
  neo4j:
    image: neo4j:5-community
    container_name: graphiti-neo4j
    ports:
      - "7687:7687"  # Bolt
      - "7474:7474"  # HTTP
    environment:
      - NEO4J_AUTH=neo4j/password  # 请修改password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
"""

    def verify_config(self) -> Dict:
        """验证配置完整性"""
        checks = {
            "neo4j_uri": bool(self.NEO4J_CONFIG["uri"]),
            "llm_base_url": bool(self.LLM_CONFIG["base_url"]),
            "llm_model": bool(self.LLM_CONFIG["model"]),
            "embedder_base_url": bool(self.EMBEDDER_CONFIG["base_url"]),
            "embedder_model": bool(self.EMBEDDER_CONFIG["model"]),
            "embedder_dim": self.EMBEDDER_CONFIG["dim"] == 1024,
            "reranker_base_url": bool(self.RERANKER_CONFIG["base_url"]),
            "reranker_model": bool(self.RERANKER_CONFIG["model"]),
            "search_recipe": self.SEARCH_CONFIG["default_recipe"] in self.SEARCH_CONFIG["available_recipes"],
            "mcp_port": 0 < self.MCP_CONFIG["port"] < 65536,
        }
        all_pass = all(checks.values())
        return {
            "all_pass": all_pass,
            "checks": checks,
            "missing_env_vars": [
                self.NEO4J_CONFIG["password_env"],
                self.LLM_CONFIG["api_key_env"],
                self.EMBEDDER_CONFIG["api_key_env"],
                self.RERANKER_CONFIG["api_key_env"],
            ],
        }


# ===== 测试 =====
if __name__ == "__main__":
    config = GraphitiConfig()

    print("=" * 60)
    print("Graphiti集成配置 — 验证")
    print("=" * 60)
    verify = config.verify_config()
    print(f"  all_pass: {verify['all_pass']}")
    for check, result in verify["checks"].items():
        print(f"  {check}: {'✅' if result else '❌'}")
    print(f"  需要的环境变量: {verify['missing_env_vars']}")

    print()
    print("=" * 60)
    print("Graphiti集成配置 — JSON输出")
    print("=" * 60)
    print(config.to_json())

    print()
    print("=" * 60)
    print("Graphiti集成配置 — .env模板")
    print("=" * 60)
    print(config.generate_env_file_template())

    print()
    print("=" * 60)
    print("Graphiti集成配置 — docker-compose.yml")
    print("=" * 60)
    print(config.generate_docker_compose())