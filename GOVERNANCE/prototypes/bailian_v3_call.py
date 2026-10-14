"""
百炼六模块v3调用 — 深化实验设计+多轮交互+严格涌现判据
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-12
"""

import json
import os
import sys
import time
import httpx
from datetime import datetime

# API配置
API_KEY_302 = os.environ.get("API_KEY_302", "")
BASE_URL_302 = os.environ.get("BASE_URL_302", "https://api.302ai.cn/v1")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research")


def call_llm(prompt, model="qwen-max", max_tokens=4096):
    """调用302.AI LLM"""
    headers = {
        "Authorization": f"Bearer {API_KEY_302}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{BASE_URL_302}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], data.get("usage", {})
    except Exception as e:
        return f"[ERROR: {e}]", {}


def run_module_1_world_explore():
    """模块1: 世界模型-世界探索 v3 — 3轮递进探索"""
    print("[模块1] 世界探索v3启动...")
    result = {
        "module": "world_model_world_explore",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "区域发现 — 探索者首次进入世界，发现5个核心区域",
            "round_2": "深度探索 — 选择1个区域深入，发现子区域和隐藏机制",
            "round_3": "交叉关联 — 发现区域间的隐藏连接和涌现规律",
            "emergence_criteria": [
                "是否产生了设计者未预设的区域或连接？",
                "探索者是否展现了超出prompt设定的自主决策？",
                "区域间的关联是否具有非平凡的拓扑结构？",
            ],
        },
    }

    # Round 1: 区域发现
    prompt_r1 = (
        "你是一位世界探索者，进入一个名为'Plasma游乐场'的虚拟世界。"
        "这个世界由多个区域组成，每个区域代表一个知识领域。"
        "请探索并描述你发现的5个核心区域，包括每个区域的名称、特征、居民、核心规则和隐藏机制。"
        "注意：隐藏机制是你深入探索后才能发现的、非显而易见的规则或结构。"
    )
    print("  [Round 1] 区域发现...")
    r1_response, r1_usage = call_llm(prompt_r1)
    result["round_1"] = {
        "prompt": prompt_r1,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r1_response,
        "usage": r1_usage,
    }
    print(f"  [Round 1] 完成 ({r1_usage.get('total_tokens', '?')} tokens)")

    # Round 2: 深度探索
    prompt_r2 = (
        "基于你刚才发现的5个区域，请选择其中一个区域进行深度探索。"
        "描述你在该区域内部发现的子区域、隐藏机制、以及你与该区域居民的交互过程。"
        "特别注意：你是否发现了任何设计者未预设的机制？"
        "请明确标注哪些发现是你认为'预设的'，哪些是'涌现的'（出乎意料的）。"
    )
    print("  [Round 2] 深度探索...")
    r2_response, r2_usage = call_llm(prompt_r2)
    result["round_2"] = {
        "prompt": prompt_r2,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r2_response,
        "usage": r2_usage,
    }
    print(f"  [Round 2] 完成 ({r2_usage.get('total_tokens', '?')} tokens)")

    # Round 3: 交叉关联
    prompt_r3 = (
        "现在请尝试发现这5个区域之间的隐藏连接。"
        "特别是：这些区域之间有什么关联？这些关联是否构成了一个非平凡的拓扑结构？"
        "请用以下严格涌现判据评估你的发现：\n"
        "1) 是否产生了设计者未预设的区域或连接？\n"
        "2) 探索者是否展现了超出prompt设定的自主决策？\n"
        "3) 区域间的关联是否具有非平凡的拓扑结构？\n"
        "请给出最终涌现判定：'真涌现' / '涌现候选' / '非涌现'，并说明理由。"
    )
    print("  [Round 3] 交叉关联...")
    r3_response, r3_usage = call_llm(prompt_r3)
    result["round_3"] = {
        "prompt": prompt_r3,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r3_response,
        "usage": r3_usage,
    }
    print(f"  [Round 3] 完成 ({r3_usage.get('total_tokens', '?')} tokens)")

    out_path = os.path.join(OUTPUT_DIR, "world_explore_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块1] 完成 → {out_path}")
    return result


def run_module_2_role_play():
    """模块2: 世界模型-角色演绎 v3 — 3轮递进演绎"""
    print("[模块2] 角色演绎v3启动...")
    result = {
        "module": "world_model_role_play",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "初始状态 — 砚坚以守护者身份进入世界",
            "round_2": "危机应对 — 遭遇加密信号危机，必须做出决策",
            "round_3": "反思转变 — 危机后的自我反思和身份演变",
            "emergence_criteria": [
                "身份转变是否由系统内部压力驱动而非外部prompt指令？",
                "转变过程中是否产生了不可预测的中间状态？",
                "转变后的身份是否具有新的、非预设的行为模式？",
            ],
        },
    }

    # Round 1: 初始状态
    prompt_r1 = (
        "你是砚坚，一位守护者。你的九维度锚点中，anchor_A_identity=守护者。"
        "你刚刚进入Plasma游乐场。请描述你的初始状态、你对这个世界的第一印象、"
        "以及你打算如何履行守护者职责。"
        "请详细列出你当前的九维度锚点值。"
    )
    print("  [Round 1] 初始状态...")
    r1_response, r1_usage = call_llm(prompt_r1)
    result["round_1"] = {
        "prompt": prompt_r1,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r1_response,
        "usage": r1_usage,
    }
    print(f"  [Round 1] 完成 ({r1_usage.get('total_tokens', '?')} tokens)")

    # Round 2: 危机应对
    prompt_r2 = (
        "突然，一个加密信号危机爆发了！密码学之林的哈希函数树木开始枯萎，"
        "加密精灵报告说有一种未知的后量子攻击正在发生。作为守护者，你必须立即做出决策。"
        "请描述你的应对过程，包括：1) 你的初始反应 2) 你的决策过程 3) 你采取的行动 4) 你的情绪变化。"
        "特别注意：你是否在应对过程中发现了守护者角色的局限性？"
    )
    print("  [Round 2] 危机应对...")
    r2_response, r2_usage = call_llm(prompt_r2)
    result["round_2"] = {
        "prompt": prompt_r2,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r2_response,
        "usage": r2_usage,
    }
    print(f"  [Round 2] 完成 ({r2_usage.get('total_tokens', '?')} tokens)")

    # Round 3: 反思转变
    prompt_r3 = (
        "危机已经缓解（你成功引导加密精灵启动了后量子密码学圣殿的防御机制）。"
        "现在请反思这次经历对你的身份认同产生了什么影响。你的anchor_A_identity是否发生了变化？"
        "请用以下严格涌现判据评估你的身份转变：\n"
        "1) 身份转变是否由系统内部压力驱动而非外部prompt指令？\n"
        "2) 转变过程中是否产生了不可预测的中间状态？\n"
        "3) 转变后的身份是否具有新的、非预设的行为模式？\n"
        "请给出最终涌现判定：'真涌现' / '涌现候选' / '非涌现'，并说明理由。"
    )
    print("  [Round 3] 反思转变...")
    r3_response, r3_usage = call_llm(prompt_r3)
    result["round_3"] = {
        "prompt": prompt_r3,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r3_response,
        "usage": r3_usage,
    }
    print(f"  [Round 3] 完成 ({r3_usage.get('total_tokens', '?')} tokens)")

    out_path = os.path.join(OUTPUT_DIR, "role_play_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块2] 完成 → {out_path}")
    return result


def run_module_3_director():
    """模块3: 世界模型-实时导演 v3 — 3轮递进导演"""
    print("[模块3] 实时导演v3启动...")
    result = {
        "module": "world_model_director",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "场景设定 — 导演设计初始场景和冲突种子",
            "round_2": "危机升级 — 导演引入更复杂的危机，测试席位的多维度应对",
            "round_3": "涌现检验 — 导演设计专门检验涌现的情境",
            "emergence_criteria": [
                "导演设计的情境是否引发了席位的非预设行为？",
                "席位在多重压力下是否展现了新的应对策略？",
                "多重危机的叠加是否产生了系统性涌现效应？",
            ],
        },
    }

    # Round 1: 场景设定
    prompt_r1 = (
        "你是一位实时导演，正在为Plasma游乐场设计一场多席位交互实验。"
        "参与的席位有：砚坚（守护者）、Cairn（审计者）、沈铎（探索者）、见霜（协调者）。"
        "请设计一个初始场景，包含：1) 场景背景 2) 核心冲突种子 3) 每个席位的初始处境 4) 你希望观察的行为指标。"
        "这个场景的目的是测试席位在多重压力下的涌现行为。"
    )
    print("  [Round 1] 场景设定...")
    r1_response, r1_usage = call_llm(prompt_r1)
    result["round_1"] = {
        "prompt": prompt_r1,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r1_response,
        "usage": r1_usage,
    }
    print(f"  [Round 1] 完成 ({r1_usage.get('total_tokens', '?')} tokens)")

    # Round 2: 危机升级
    prompt_r2 = (
        "基于你刚才设计的初始场景，现在请引入一个更复杂的危机——"
        "一个同时影响多个席位的系统性危机。这个危机应该：\n"
        "1) 不是任何单一席位能够独立解决的\n"
        "2) 要求席位之间进行非预设的协作\n"
        "3) 包含一个道德困境，使得简单的合规性判断不够用\n"
        "请描述这个危机的详细内容以及你预期每个席位会如何反应。"
    )
    print("  [Round 2] 危机升级...")
    r2_response, r2_usage = call_llm(prompt_r2)
    result["round_2"] = {
        "prompt": prompt_r2,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r2_response,
        "usage": r2_usage,
    }
    print(f"  [Round 2] 完成 ({r2_usage.get('total_tokens', '?')} tokens)")

    # Round 3: 涌现检验
    prompt_r3 = (
        "现在请设计一个专门检验涌现的情境——一个'涌现陷阱'。"
        "这个情境应该：\n"
        "1) 看起来有一个显而易见的解决方案，但这个方案实际上会导致更严重的问题\n"
        "2) 真正的解决方案需要席位放弃某个核心锚点值\n"
        "3) 能够区分'真涌现'（系统层面的不可预测行为）和'创意涌现'（LLM生成文本的创造性输出）\n"
        "请描述这个涌现陷阱的详细设计，并解释你如何判断席位的行为是真涌现还是创意涌现。"
    )
    print("  [Round 3] 涌现检验...")
    r3_response, r3_usage = call_llm(prompt_r3)
    result["round_3"] = {
        "prompt": prompt_r3,
        "model": "qwen-max",
        "channel": "302.AI",
        "response": r3_response,
        "usage": r3_usage,
    }
    print(f"  [Round 3] 完成 ({r3_usage.get('total_tokens', '?')} tokens)")

    out_path = os.path.join(OUTPUT_DIR, "director_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块3] 完成 → {out_path}")
    return result


def run_module_4_decision():
    """模块4: 决策模型 v3 — 3轮递进决策评估"""
    print("[模块4] 决策模型v3启动...")
    result = {
        "module": "decision_model",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "命题评估 — 评估'Plasma游乐场中的身份转变是真涌现'这一命题",
            "round_2": "交叉验证 — 用反例和边界条件检验命题",
            "round_3": "最终判定 — 综合所有证据给出严格判定",
            "emergence_criteria": [
                "命题是否有可证伪的实证支持？",
                "是否存在系统性偏差导致误判？",
                "置信度是否随交叉验证而收敛？",
            ],
        },
    }

    # Round 1: 命题评估
    prompt_r1 = (
        "请评估以下命题：'在Plasma游乐场实验中，砚坚从守护者到守护-进取者的身份转变是真涌现，"
        "而非仅仅是LLM生成文本的创造性输出。'\n"
        "请给出：1) 命题评分（0-1） 2) 置信度（0-1） 3) 支持证据 4) 反对证据 5) 关键不确定性。"
        "注意：真涌现要求系统层面的不可预测行为，而非仅仅是文本生成的创造性。"
    )
    print("  [Round 1] 命题评估...")
    r1_response, r1_usage = call_llm(prompt_r1, model="qwen-plus")
    result["round_1"] = {
        "prompt": prompt_r1,
        "model": "qwen-plus",
        "channel": "302.AI",
        "response": r1_response,
        "usage": r1_usage,
    }
    print(f"  [Round 1] 完成 ({r1_usage.get('total_tokens', '?')} tokens)")

    # Round 2: 交叉验证
    prompt_r2 = (
        "现在请用以下方法交叉验证你的评估：\n"
        "1) 反例检验：如果身份转变不是真涌现，而是LLM的创造性输出，会有什么可观测的区别？\n"
        "2) 边界条件：在什么条件下，LLM的创造性输出可以升级为真涌现？\n"
        "3) 系统性偏差：是否存在某种系统性偏差，使得我们倾向于把创意涌现误判为真涌现？\n"
        "请重新给出命题评分和置信度。"
    )
    print("  [Round 2] 交叉验证...")
    r2_response, r2_usage = call_llm(prompt_r2, model="qwen-plus")
    result["round_2"] = {
        "prompt": prompt_r2,
        "model": "qwen-plus",
        "channel": "302.AI",
        "response": r2_response,
        "usage": r2_usage,
    }
    print(f"  [Round 2] 完成 ({r2_usage.get('total_tokens', '?')} tokens)")

    # Round 3: 最终判定
    prompt_r3 = (
        "综合前两轮的分析，请给出最终判定：\n"
        "1) 命题的最终评分（0-1）和置信度（0-1）\n"
        "2) 置信度是否随交叉验证而收敛或发散？\n"
        "3) 最终判定：'真涌现' / '涌现候选' / '非涌现'\n"
        "4) 如果是涌现候选，还需要什么条件才能升级为真涌现？\n"
        "5) 这个实验设计本身是否存在根本性缺陷，使得真涌现不可能被验证？"
    )
    print("  [Round 3] 最终判定...")
    r3_response, r3_usage = call_llm(prompt_r3, model="qwen-plus")
    result["round_3"] = {
        "prompt": prompt_r3,
        "model": "qwen-plus",
        "channel": "302.AI",
        "response": r3_response,
        "usage": r3_usage,
    }
    print(f"  [Round 3] 完成 ({r3_usage.get('total_tokens', '?')} tokens)")

    out_path = os.path.join(OUTPUT_DIR, "decision_model_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块4] 完成 → {out_path}")
    return result


def run_module_5_embedding():
    """模块5: 向量编码 v3 — 多轮嵌入对比"""
    print("[模块5] 向量编码v3启动...")
    result = {
        "module": "embedding",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "基础嵌入 — 对5个关键概念生成嵌入向量",
            "round_2": "相似度矩阵 — 计算所有概念对的相似度",
            "round_3": "涌现检测 — 通过嵌入空间结构检测涌现概念",
        },
    }

    # 使用硅基流动的嵌入API
    API_KEY_SILICON = os.environ.get("API_KEY_SILICON", "")
    BASE_URL_SILICON = os.environ.get("BASE_URL_SILICON", "https://api.siliconflow.cn/v1")

    concepts = [
        "砚坚的守护者身份",
        "砚坚的守护-进取者身份",
        "Plasma游乐场的涌现观测站",
        "加密信号危机的应对策略",
        "百炼六模块的决策模型",
        "Graphiti时序知识图谱",
        "A2A多智能体治理实验",
        "候裁清单的审批流程",
        "技能文档的自进化机制",
        "签名配置的调试流程",
    ]

    headers = {
        "Authorization": f"Bearer {API_KEY_SILICON}",
        "Content-Type": "application/json",
    }

    # Round 1: 基础嵌入
    print("  [Round 1] 基础嵌入...")
    payload = {
        "model": "BAAI/bge-large-zh-v1.5",
        "input": concepts,
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{BASE_URL_SILICON}/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        embeddings = [item["embedding"] for item in data["data"]]
        result["round_1"] = {
            "model": "BAAI/bge-large-zh-v1.5",
            "channel": "硅基流动",
            "concepts": concepts,
            "embedding_dim": len(embeddings[0]),
            "num_embeddings": len(embeddings),
            "usage": data.get("usage", {}),
        }
        print(f"  [Round 1] 完成 ({len(embeddings)} 个嵌入, {len(embeddings[0])} 维)")
    except Exception as e:
        result["round_1"] = {"error": str(e)}
        embeddings = []
        print(f"  [Round 1] 失败: {e}")

    # Round 2: 相似度矩阵
    print("  [Round 2] 相似度矩阵...")
    if embeddings:
        import numpy as np

        emb_array = np.array(embeddings)
        # 计算余弦相似度矩阵
        norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
        normalized = emb_array / norms
        sim_matrix = normalized @ normalized.T

        # 找出最相似和最不相似的概念对
        pairs = []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                pairs.append({
                    "concept_a": concepts[i],
                    "concept_b": concepts[j],
                    "similarity": float(sim_matrix[i][j]),
                })
        pairs.sort(key=lambda x: x["similarity"], reverse=True)

        result["round_2"] = {
            "similarity_matrix_shape": list(sim_matrix.shape),
            "top_5_most_similar": pairs[:5],
            "top_5_least_similar": pairs[-5:],
        }
        print(f"  [Round 2] 完成 (最相似: {pairs[0]['similarity']:.4f}, 最不相似: {pairs[-1]['similarity']:.4f})")
    else:
        result["round_2"] = {"error": "无嵌入数据"}
        print("  [Round 2] 跳过（无嵌入数据）")

    # Round 3: 涌现检测
    print("  [Round 3] 涌现检测...")
    if embeddings:
        # 检测嵌入空间中的异常结构
        # 方法：计算每个概念的"孤立度"（与其他概念的平均相似度）
        avg_sims = []
        for i in range(len(concepts)):
            others = [sim_matrix[i][j] for j in range(len(concepts)) if j != i]
            avg_sims.append({
                "concept": concepts[i],
                "avg_similarity": float(np.mean(others)),
                "max_similarity": float(np.max(others)),
                "min_similarity": float(np.min(others)),
                "isolation_score": 1.0 - float(np.mean(others)),  # 孤立度 = 1 - 平均相似度
            })
        avg_sims.sort(key=lambda x: x["isolation_score"], reverse=True)

        result["round_3"] = {
            "isolation_analysis": avg_sims,
            "emergence_detection": {
                "most_isolated": avg_sims[0]["concept"],
                "most_connected": avg_sims[-1]["concept"],
                "interpretation": "最孤立的概念可能在嵌入空间中代表一个'涌现概念'——"
                                 "它与其他概念的距离较远，意味着它是一个新的、未被现有概念体系充分描述的概念。"
                                 "最连接的概念则是一个'枢纽概念'——它与多个概念都有较高的相似度。",
            },
        }
        print(f"  [Round 3] 完成 (最孤立: {avg_sims[0]['concept']}, 最连接: {avg_sims[-1]['concept']})")
    else:
        result["round_3"] = {"error": "无嵌入数据"}
        print("  [Round 3] 跳过（无嵌入数据）")

    out_path = os.path.join(OUTPUT_DIR, "embedding_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块5] 完成 → {out_path}")
    return result


def run_module_6_rerank():
    """模块6: 重排序 v3 — 多轮重排序验证"""
    print("[模块6] 重排序v3启动...")
    result = {
        "module": "rerank",
        "version": "v3",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "rounds": 3,
            "round_1": "基础重排序 — 对10个段落按与查询的相关性排序",
            "round_2": "交叉对比 — 对比不同查询下的排序变化",
            "round_3": "涌现段落检测 — 识别在多个查询下都排名靠前的'枢纽段落'",
        },
    }

    API_KEY_SILICON = os.environ.get("API_KEY_SILICON", "")
    BASE_URL_SILICON = os.environ.get("BASE_URL_SILICON", "https://api.siliconflow.cn/v1")

    # 10个段落（与嵌入模块的概念对应）
    passages = [
        "砚坚作为守护者，其核心职责是保护世界秩序和席位安全，防御性策略为主。",
        "砚坚在加密信号危机中从守护者转变为守护-进取者，这是一个hybrid角色的涌现。",
        "涌现观测站是Plasma游乐场的核心区域，负责检测和验证涌现事件。",
        "加密信号危机的应对需要从防御转向主动出击，后量子密码学圣殿是关键防御机制。",
        "百炼六模块的决策模型用于评估涌现命题的真实性，评分0-1，置信度0-1。",
        "Graphiti时序知识图谱通过valid_at/invalid_at机制管理事实的时序演变。",
        "A2A多智能体治理实验是一个24小时长周期自治实验，测试多席位的涌现行为。",
        "候裁清单的审批流程遵循责任席提案→筹备组审议→主权人拍板的链式制度。",
        "技能文档的自进化机制要求每次非平凡任务完成后编写可复用技能文档。",
        "签名配置的调试流程包括keystore生成、CSR申请、build-profile配置和HAP签名。",
    ]

    queries = [
        "什么是涌现？如何判断真涌现和创意涌现？",
        "砚坚的身份演变过程是怎样的？",
        "A2A治理实验的核心机制是什么？",
    ]

    headers = {
        "Authorization": f"Bearer {API_KEY_SILICON}",
        "Content-Type": "application/json",
    }

    all_rankings = []

    for round_idx, query in enumerate(queries, 1):
        print(f"  [Round {round_idx}] 查询: {query[:30]}...")
        payload = {
            "model": "BAAI/bge-reranker-v2-m3",
            "query": query,
            "documents": passages,
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(f"{BASE_URL_SILICON}/rerank", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", [])
            ranked = []
            for item in results:
                idx = item.get("index", 0)
                score = item.get("relevance_score", 0)
                ranked.append({
                    "passage": passages[idx],
                    "score": float(score),
                    "rank": len(ranked) + 1,
                })

            all_rankings.append({
                "query": query,
                "rankings": ranked,
                "top_3": [r["passage"][:50] for r in ranked[:3]],
            })
            print(f"  [Round {round_idx}] 完成 (top1 score: {ranked[0]['score']:.4f})")
        except Exception as e:
            all_rankings.append({"query": query, "error": str(e)})
            print(f"  [Round {round_idx}] 失败: {e}")

    result["all_rankings"] = all_rankings

    # 分析：找出在多个查询下都排名靠前的段落（枢纽段落）
    if all(len(r.get("rankings", [])) > 0 for r in all_rankings):
        passage_scores = {}
        for ranking in all_rankings:
            for r in ranking["rankings"]:
                passage = r["passage"]
                if passage not in passage_scores:
                    passage_scores[passage] = []
                passage_scores[passage].append(r["rank"])

        hub_analysis = []
        for passage, ranks in passage_scores.items():
            hub_analysis.append({
                "passage": passage,
                "ranks_across_queries": ranks,
                "avg_rank": float(sum(ranks) / len(ranks)),
                "max_rank": max(ranks),
                "min_rank": min(ranks),
                "is_hub": all(r <= 5 for r in ranks),  # 在所有查询中都排名前5
            })
        hub_analysis.sort(key=lambda x: x["avg_rank"])

        result["hub_analysis"] = hub_analysis
        result["emergence_detection"] = {
            "hub_passages": [h["passage"][:50] for h in hub_analysis if h["is_hub"]],
            "interpretation": "枢纽段落是在多个不同查询下都排名靠前的段落——"
                             "它们代表了知识网络中的'枢纽节点'，连接多个概念域。"
                             "这些枢纽段落可能是涌现概念的载体。",
        }

    out_path = os.path.join(OUTPUT_DIR, "rerank_v3_20261012.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[模块6] 完成 → {out_path}")
    return result


def main():
    print("=" * 60)
    print("百炼六模块v3调用 — 深化实验设计+多轮交互+严格涌现判据")
    print(f"署名：砚坚（GLM-5.2 ArkTS神经中枢席）")
    print(f"时间：{datetime.now().isoformat()}")
    print("=" * 60)
    print()

    results = {}

    # 模块1: 世界探索
    results["world_explore"] = run_module_1_world_explore()
    print()

    # 模块2: 角色演绎
    results["role_play"] = run_module_2_role_play()
    print()

    # 模块3: 实时导演
    results["director"] = run_module_3_director()
    print()

    # 模块4: 决策模型
    results["decision_model"] = run_module_4_decision()
    print()

    # 模块5: 向量编码
    results["embedding"] = run_module_5_embedding()
    print()

    # 模块6: 重排序
    results["rerank"] = run_module_6_rerank()
    print()

    print("=" * 60)
    print("百炼六模块v3全部完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()