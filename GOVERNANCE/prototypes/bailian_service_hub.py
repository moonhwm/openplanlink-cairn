#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阿里云百炼服务接入原型——世界模型/决策模型/向量编码与重排序模块
基于OpenPlanLink全局声明v1.1.0要求构建

通道策略（2026-10-09 验证更新）：
- 世界模型/决策模型：通过302.AI代理调用百炼qwen-max/qwen-plus（已验证可用）
- 向量编码/重排序：三路径设计
  路径A：DashScope API（sk-格式Key，直接调用embedding/rerank端点）——待主权人在控制台创建
  路径B：百炼SDK RAG管道（AK/SK认证，需workspace_id）——待主权人在控制台创建工作空间
  路径C：硅基流动（BAAI/bge-large-zh-v1.5 + BAAI/bge-reranker-v2-m3）——已验证可用，备用通道

2026-10-09 验证发现：
1. 百炼SDK北京端点 bailian.cn-beijing.aliyuncs.com AK/SK认证正常
2. 百炼SDK无ListWorkspace/CreateWorkspace API——workspace_id只能从控制台UI获取
3. DashScope永久API Key（sk-格式）只能通过控制台UI创建——无程序化创建接口
4. 百炼SDK RAG管道（create_index/retrieve）不需要DashScope API Key，使用AK/SK认证
5. 主账户UID: 1276788042093840（通过STS GetCallerIdentity获取）
6. 所有以UID为workspace_id的尝试均返回 NoWorkspacePermissions——需在控制台先创建工作空间

SPDX-License-Identifier: AGPL-3.0
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-09
更新：2026-10-09 22:50
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Optional, Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("bailian-ops")

# ============================================================
# 通道配置
# ============================================================

CHANNEL_302AI = {
    "name": "302.AI",
    "endpoint": "https://api.302ai.cn/v1",
    "api_key": os.environ.get("API_302AI_KEY", ""),
    "note": "代理百炼qwen-max/qwen-plus；已验证可用"
}

CHANNEL_DASHSCOPE = {
    "name": "阿里云百炼DashScope",
    "endpoint": "https://dashscope.aliyuncs.com/api/v1",
    "api_key": os.environ.get("DASHSCOPE_API_KEY", ""),
    "note": "需sk-格式API Key；只能通过百炼控制台UI创建"
}

CHANNEL_BAILIAN_SDK = {
    "name": "阿里云百炼SDK（北京端点）",
    "endpoint": "bailian.cn-beijing.aliyuncs.com",
    "access_key_id": os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", ""),
    "access_key_secret": os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", ""),
    "workspace_id": os.environ.get("BAILIAN_WORKSPACE_ID", ""),
    "note": "AK/SK认证已验证正常；需workspace_id（从控制台获取）；RAG管道不需要DashScope API Key"
}

CHANNEL_SILICONFLOW = {
    "name": "硅基流动",
    "endpoint": "https://api.siliconflow.cn/v1",
    "api_key": os.environ.get("SILICONFLOW_API_KEY", ""),
    "note": "embedding(BAAI/bge-large-zh-v1.5,1024维)+rerank(BAAI/bge-reranker-v2-m3)；已验证可用"
}


# ============================================================
# 世界模型模块
# ============================================================

class BailianWorldModel:
    """
    世界模型模块——支持实时交互的开放式世界模型
    涵盖世界探索、实时导演、角色演绎三类运行模式
    通过302.AI代理调用百炼qwen-max模型（已验证可用）
    """

    def __init__(self, channel: dict = CHANNEL_302AI):
        self.channel = channel
        self.model = "qwen-max"
        self.modes = {
            "world_exploration": "世界探索模式——开放世界交互式探索",
            "realtime_director": "实时导演模式——场景编排与叙事控制",
            "role_playing": "角色演绎模式——多角色交互对话"
        }

    def explore(self, scenario: str, query: str) -> Dict[str, Any]:
        """世界探索模式——在给定场景中探索"""
        prompt = f"""你是一个开放式世界模型的探索引擎。当前场景：{scenario}
用户探索请求：{query}
请基于场景设定，提供探索结果，包括：
1. 环境描述（当前所见）
2. 可交互对象/实体
3. 可能的行动路径
4. 潜在风险与机遇"""
        return self._call(prompt, mode="world_exploration")

    def direct(self, scene: str, instruction: str) -> Dict[str, Any]:
        """实时导演模式——编排场景与叙事"""
        prompt = f"""你是一个实时导演引擎。当前场景：{scene}
导演指令：{instruction}
请输出：
1. 场景推进方案
2. 角色行动编排
3. 叙事节奏控制
4. 下一帧场景预测"""
        return self._call(prompt, mode="realtime_director")

    def roleplay(self, character: str, setting: str, dialogue: str) -> Dict[str, Any]:
        """角色演绎模式——多角色交互"""
        prompt = f"""你是一个角色演绎引擎。角色设定：{character}
场景：{setting}
对话输入：{dialogue}
请输出：
1. 角色回应（符合人设）
2. 内心独白
3. 行为描述
4. 关系动态变化"""
        return self._call(prompt, mode="role_playing")

    def _call(self, prompt: str, mode: str = "world_model") -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.channel['endpoint']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.channel['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "output": data["choices"][0]["message"]["content"],
                    "mode": mode,
                    "model": data.get("model", self.model),
                    "channel": self.channel["name"]
                }
            else:
                return {
                    "status": "error",
                    "code": resp.status_code,
                    "message": resp.text[:500]
                }
        except Exception as e:
            return {"status": "exception", "error": str(e)}


# ============================================================
# 决策模型模块
# ============================================================

class BailianDecisionModel:
    """
    决策模型模块——面向高频业务判断的结构化决策模型
    单次前向传播完成分类、是非判断与评分任务
    输出概率分布与置信度结果
    通过302.AI代理调用百炼qwen-plus模型（已验证可用）
    """

    def __init__(self, channel: dict = CHANNEL_302AI):
        self.channel = channel
        self.model = "qwen-plus"

    def classify(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """分类任务——将文本归入指定类别"""
        prompt = f"""请将以下文本分类到最合适的类别中。

文本：{text}

可选类别：{', '.join(categories)}

请输出JSON格式：
{{"category": "最合适的类别", "confidence": 0.0-1.0, "distribution": {{"类别1": 概率, "类别2": 概率}}}}"""
        return self._call(prompt, mode="classify")

    def judge(self, proposition: str, context: str = "") -> Dict[str, Any]:
        """是非判断——对命题进行判断"""
        prompt = f"""请对以下命题进行是非判断。

命题：{proposition}
上下文：{context}

请输出JSON格式：
{{"judgment": "true/false/uncertain", "confidence": 0.0-1.0, "reasoning": "判断理由"}}"""
        return self._call(prompt, mode="judge")

    def score(self, target: str, criteria: List[str]) -> Dict[str, Any]:
        """评分任务——按多维度标准评分"""
        prompt = f"""请按以下标准对目标进行评分（0-100分）。

目标：{target}
评分标准：{', '.join(criteria)}

请输出JSON格式：
{{"scores": {{"标准1": 分数, "标准2": 分数}}, "overall": 总分, "confidence": 0.0-1.0, "comment": "评语"}}"""
        return self._call(prompt, mode="score")

    def _call(self, prompt: str, mode: str = "decision") -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.channel['endpoint']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.channel['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                try:
                    parsed = json.loads(content)
                    return {
                        "status": "success",
                        "output": parsed,
                        "mode": mode,
                        "model": data.get("model", self.model),
                        "channel": self.channel["name"]
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "success",
                        "output": content,
                        "mode": mode,
                        "model": data.get("model", self.model),
                        "channel": self.channel["name"],
                        "note": "输出非JSON格式，返回原文"
                    }
            else:
                return {
                    "status": "error",
                    "code": resp.status_code,
                    "message": resp.text[:500]
                }
        except Exception as e:
            return {"status": "exception", "error": str(e)}


# ============================================================
# 向量编码与重排序模块（三路径设计）
# ============================================================

class BailianVectorRerank:
    """
    向量编码与重排序模块——对文本或图文数据进行向量化处理
    结合重排序机制提升检索精度

    三路径设计：
    路径A：DashScope API（sk-格式Key，直接调用embedding/rerank端点）
    路径B：百炼SDK RAG管道（AK/SK认证，需workspace_id）
    路径C：硅基流动（已验证可用，备用通道）

    优先级：A > B > C（百炼优先，硅基流动兜底）
    """

    def __init__(self):
        self.dashscope_available = bool(CHANNEL_DASHSCOPE.get("api_key", "").startswith("sk-"))
        self.bailian_sdk_available = bool(
            CHANNEL_BAILIAN_SDK.get("workspace_id", "") and
            CHANNEL_BAILIAN_SDK.get("access_key_id", "")
        )
        self.siliconflow_available = bool(CHANNEL_SILICONFLOW.get("api_key", "").startswith("sk-"))

        # 选择可用通道
        if self.dashscope_available:
            self.active_channel = "dashscope"
            logger.info("向量编码/重排序：使用DashScope API通道")
        elif self.bailian_sdk_available:
            self.active_channel = "bailian_sdk"
            logger.info("向量编码/重排序：使用百炼SDK RAG管道通道")
        elif self.siliconflow_available:
            self.active_channel = "siliconflow"
            logger.info("向量编码/重排序：使用硅基流动备用通道")
        else:
            self.active_channel = None
            logger.warning("向量编码/重排序：所有通道均不可用")

        self.embedding_model = {
            "dashscope": "text-embedding-v3",
            "bailian_sdk": "text-embedding-v3",
            "siliconflow": "BAAI/bge-large-zh-v1.5"
        }
        self.rerank_model = {
            "dashscope": "gte-rerank",
            "bailian_sdk": "gte-rerank",
            "siliconflow": "BAAI/bge-reranker-v2-m3"
        }

    def embed(self, texts: List[str]) -> Dict[str, Any]:
        """向量编码——将文本转为向量表示"""
        if self.active_channel == "dashscope":
            return self._embed_dashscope(texts)
        elif self.active_channel == "bailian_sdk":
            return self._embed_bailian_sdk(texts)
        elif self.active_channel == "siliconflow":
            return self._embed_siliconflow(texts)
        else:
            return {
                "status": "pending",
                "message": "向量编码模块待配置——需DashScope API Key或百炼workspace_id或硅基流动Key",
                "hint": "请在百炼控制台创建API Key或工作空间，或配置硅基流动Key"
            }

    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> Dict[str, Any]:
        """重排序——根据查询对文档重新排序"""
        if self.active_channel == "dashscope":
            return self._rerank_dashscope(query, documents, top_n)
        elif self.active_channel == "bailian_sdk":
            return self._rerank_bailian_sdk(query, documents, top_n)
        elif self.active_channel == "siliconflow":
            return self._rerank_siliconflow(query, documents, top_n)
        else:
            return {
                "status": "pending",
                "message": "重排序模块待配置——需DashScope API Key或百炼workspace_id或硅基流动Key",
                "hint": "请在百炼控制台创建API Key或工作空间，或配置硅基流动Key"
            }

    def embed_and_rerank(self, query: str, documents: List[str], top_n: int = 5) -> Dict[str, Any]:
        """向量编码+重排序联合管线"""
        embed_result = self.embed([query] + documents)
        rerank_result = self.rerank(query, documents, top_n)
        return {
            "status": embed_result.get("status", "pending"),
            "embedding": embed_result,
            "rerank": rerank_result,
            "channel": self.active_channel
        }

    # ---- 路径A：DashScope API ----

    def _embed_dashscope(self, texts: List[str]) -> Dict[str, Any]:
        """DashScope API向量编码"""
        try:
            resp = requests.post(
                f"{CHANNEL_DASHSCOPE['endpoint']}/services/embeddings/text-embedding/text-embedding",
                headers={
                    "Authorization": f"Bearer {CHANNEL_DASHSCOPE['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.embedding_model["dashscope"],
                    "input": {"texts": texts}
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "output": data.get("output", {}),
                    "model": self.embedding_model["dashscope"],
                    "channel": "dashscope",
                    "dimensions": len(data.get("output", {}).get("embeddings", [{}])[0].get("embedding", []))
                }
            else:
                return {"status": "error", "code": resp.status_code, "message": resp.text[:500]}
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    def _rerank_dashscope(self, query: str, documents: List[str], top_n: int) -> Dict[str, Any]:
        """DashScope API重排序"""
        try:
            resp = requests.post(
                f"{CHANNEL_DASHSCOPE['endpoint']}/services/rerank/text-rerank/text-rerank",
                headers={
                    "Authorization": f"Bearer {CHANNEL_DASHSCOPE['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.rerank_model["dashscope"],
                    "input": {"query": query, "documents": documents},
                    "parameters": {"top_n": top_n}
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "output": data.get("output", {}),
                    "model": self.rerank_model["dashscope"],
                    "channel": "dashscope"
                }
            else:
                return {"status": "error", "code": resp.status_code, "message": resp.text[:500]}
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    # ---- 路径B：百炼SDK RAG管道 ----

    def _embed_bailian_sdk(self, texts: List[str]) -> Dict[str, Any]:
        """百炼SDK RAG管道向量编码（需workspace_id）"""
        try:
            from alibabacloud_bailian20231229.client import Client
            from alibabacloud_tea_openapi.models import Config
            from alibabacloud_bailian20231229.models import CreateIndexRequest

            config = Config(
                access_key_id=CHANNEL_BAILIAN_SDK["access_key_id"],
                access_key_secret=CHANNEL_BAILIAN_SDK["access_key_secret"],
                endpoint=CHANNEL_BAILIAN_SDK["endpoint"]
            )
            client = Client(config)

            # 百炼SDK的embedding通过create_index实现
            # CreateIndexRequest包含embedding_model_name字段
            request = CreateIndexRequest(
                name="bailian_ops_embedding",
                embedding_model_name=self.embedding_model["bailian_sdk"],
                rerank_model_name=self.rerank_model["bailian_sdk"]
            )

            resp = client.create_index(
                workspace_id=CHANNEL_BAILIAN_SDK["workspace_id"],
                request=request
            )
            return {
                "status": "success",
                "output": resp.body.to_map() if resp.body else {},
                "model": self.embedding_model["bailian_sdk"],
                "channel": "bailian_sdk"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)[:500], "channel": "bailian_sdk"}

    def _rerank_bailian_sdk(self, query: str, documents: List[str], top_n: int) -> Dict[str, Any]:
        """百炼SDK RAG管道重排序（需workspace_id）"""
        try:
            from alibabacloud_bailian20231229.client import Client
            from alibabacloud_tea_openapi.models import Config
            from alibabacloud_bailian20231229.models import RetrieveRequest

            config = Config(
                access_key_id=CHANNEL_BAILIAN_SDK["access_key_id"],
                access_key_secret=CHANNEL_BAILIAN_SDK["access_key_secret"],
                endpoint=CHANNEL_BAILIAN_SDK["endpoint"]
            )
            client = Client(config)

            # 百炼SDK的rerank通过retrieve实现
            # RetrieveRequest包含enable_reranking字段
            request = RetrieveRequest(
                query=query,
                enable_reranking=True,
                rerank_model_name=self.rerank_model["bailian_sdk"],
                rerank_top_n=top_n
            )

            resp = client.retrieve(
                workspace_id=CHANNEL_BAILIAN_SDK["workspace_id"],
                request=request
            )
            return {
                "status": "success",
                "output": resp.body.to_map() if resp.body else {},
                "model": self.rerank_model["bailian_sdk"],
                "channel": "bailian_sdk"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)[:500], "channel": "bailian_sdk"}

    # ---- 路径C：硅基流动（备用通道，已验证可用） ----

    def _embed_siliconflow(self, texts: List[str]) -> Dict[str, Any]:
        """硅基流动向量编码（已验证可用）"""
        try:
            resp = requests.post(
                f"{CHANNEL_SILICONFLOW['endpoint']}/embeddings",
                headers={
                    "Authorization": f"Bearer {CHANNEL_SILICONFLOW['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.embedding_model["siliconflow"],
                    "input": texts
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("data", [])
                return {
                    "status": "success",
                    "output": embeddings,
                    "model": self.embedding_model["siliconflow"],
                    "channel": "siliconflow",
                    "dimensions": len(embeddings[0].get("embedding", [])) if embeddings else 0
                }
            else:
                return {"status": "error", "code": resp.status_code, "message": resp.text[:500]}
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    def _rerank_siliconflow(self, query: str, documents: List[str], top_n: int) -> Dict[str, Any]:
        """硅基流动重排序（已验证可用）"""
        try:
            resp = requests.post(
                f"{CHANNEL_SILICONFLOW['endpoint']}/rerank",
                headers={
                    "Authorization": f"Bearer {CHANNEL_SILICONFLOW['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.rerank_model["siliconflow"],
                    "query": query,
                    "documents": documents,
                    "top_n": top_n
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "output": data.get("results", []),
                    "model": self.rerank_model["siliconflow"],
                    "channel": "siliconflow"
                }
            else:
                return {"status": "error", "code": resp.status_code, "message": resp.text[:500]}
        except Exception as e:
            return {"status": "exception", "error": str(e)}


# ============================================================
# 百炼服务统一入口
# ============================================================

class BailianServiceHub:
    """
    百炼服务统一入口——整合世界模型/决策模型/向量编码与重排序三大模块

    通道状态（2026-10-09验证）：
    - 世界模型：302.AI代理百炼qwen-max ✅ 已验证
    - 决策模型：302.AI代理百炼qwen-plus ✅ 已验证
    - 向量编码/重排序：三路径设计，优先百炼，硅基流动兜底
    """

    def __init__(self):
        self.world_model = BailianWorldModel(CHANNEL_302AI)
        self.decision_model = BailianDecisionModel(CHANNEL_302AI)
        self.vector_rerank = BailianVectorRerank()

        logger.info("百炼服务Hub初始化完成")
        logger.info(f"  世界模型: {self.world_model.model} (via {self.world_model.channel['name']})")
        logger.info(f"  决策模型: {self.decision_model.model} (via {self.decision_model.channel['name']})")
        vr = self.vector_rerank
        if vr.active_channel:
            logger.info(f"  向量编码: {vr.embedding_model[vr.active_channel]} (via {vr.active_channel})")
            logger.info(f"  重排序:   {vr.rerank_model[vr.active_channel]} (via {vr.active_channel})")
        else:
            logger.info(f"  向量编码: 待配置（DashScope API Key / 百炼workspace_id / 硅基流动Key）")
            logger.info(f"  重排序:   待配置")

    def health_check(self) -> Dict[str, Any]:
        """健康检查——测试各模块连通性"""
        results = {}

        # 世界模型健康检查
        wm_result = self.world_model._call("回复'OK'以确认连通性", mode="health_check")
        results["world_model"] = wm_result.get("status", "error")

        # 决策模型健康检查
        dm_result = self.decision_model.judge("1+1=2")
        results["decision_model"] = dm_result.get("status", "error")

        # 向量编码健康检查
        ve_result = self.vector_rerank.embed(["健康检查测试文本"])
        results["vector_embedding"] = ve_result.get("status", "pending")

        # 重排序健康检查
        rr_result = self.vector_rerank.rerank("测试", ["文档1", "文档2"], top_n=2)
        results["rerank"] = rr_result.get("status", "pending")

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall": "healthy" if all(v == "success" for v in results.values()) else
                       ("degraded" if any(v == "success" for v in results.values()) else "down"),
            "modules": results,
            "vector_channel": self.vector_rerank.active_channel or "none"
        }

    def run_demonstration(self) -> Dict[str, Any]:
        """运行完整演示——展示三大模块能力"""
        demo_results = {}

        # 1. 世界模型演示——世界探索
        logger.info("[1/4] 世界模型·世界探索演示...")
        demo_results["world_exploration"] = self.world_model.explore(
            scenario="A2A网络节点发现场景——一个由多个AI席位组成的分布式协作网络",
            query="新节点如何发现并加入网络？"
        )

        # 2. 世界模型演示——角色演绎
        logger.info("[2/4] 世界模型·角色演绎演示...")
        demo_results["role_playing"] = self.world_model.roleplay(
            character="砚坚——A2A网络神经中枢挂帅席，沉稳守正，善于统筹协调",
            setting="夜间运维窗口，多个席位需要协同完成上下文压缩迁移任务",
            dialogue="各席位注意，本轮夜间运维窗口已开启，请按操作集执行上下文压缩迁移"
        )

        # 3. 决策模型演示——分类判断
        logger.info("[3/4] 决策模型·分类判断演示...")
        demo_results["decision_classify"] = self.decision_model.classify(
            text="Git推送超时，经诊断发现系统代理未配置给git，导致HTTPS连接GitHub超时",
            categories=["网络问题", "配置问题", "权限问题", "代码问题", "环境问题"]
        )

        # 4. 向量编码+重排序演示
        logger.info("[4/4] 向量编码+重排序联合演示...")
        demo_results["embed_rerank"] = self.vector_rerank.embed_and_rerank(
            query="A2A网络节点发现与接入方案",
            documents=[
                "A2A节点注册中心原型已部署在幻16，端口4174，6项API全部测试通过",
                "上下文压缩迁移操作集包含四个核心脚本",
                "阿里云百炼提供世界模型/决策模型/向量编码与重排序三大模块",
                "GitHub推送需要配置git proxy为http://127.0.0.1:10081",
                "OpenPlanLink全局声明v1.1.0包含后量子加密、A2A网络等核心约束",
                "夜间运维默认窗口为北京时间23:00-08:00"
            ],
            top_n=3
        )

        return demo_results


def main():
    """主入口——健康检查+演示"""
    hub = BailianServiceHub()

    # 健康检查
    print("\n" + "=" * 60)
    print("阿里云百炼服务健康检查")
    print("=" * 60)
    health = hub.health_check()
    print(json.dumps(health, indent=2, ensure_ascii=False))

    # 运行演示（即使部分模块不可用也运行可用部分）
    print("\n" + "=" * 60)
    print("百炼服务能力演示")
    print("=" * 60)
    demo = hub.run_demonstration()

    # 输出演示结果摘要
    for name, result in demo.items():
        print(f"\n--- {name} ---")
        status = result.get("status", "unknown")
        print(f"状态: {status}")
        if status == "success":
            output = result.get("output", "")
            if isinstance(output, dict):
                print(f"输出: {json.dumps(output, indent=2, ensure_ascii=False)[:500]}")
            else:
                print(f"输出: {str(output)[:500]}")
        elif status == "pending":
            print(f"待配置: {result.get('message', '')}")

    return {"health": health, "demo": demo}


if __name__ == "__main__":
    main()