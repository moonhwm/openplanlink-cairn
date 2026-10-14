#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
决策模型服务层 — 多通道降级链 + nn_deep适配
档号: DF-IMPL-20261012-YANJIAN-Q3.1
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

降级链: 百炼decision-model-preview → 302.AI qwen-max(结构化prompt)
输出契约: {class, verdict, score, prob_distribution, confidence}
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
import hashlib


class DecisionService:
    """决策模型服务 — 双通道降级链"""

    # 百炼决策模型通道
    BAILIAN_CHANNEL = {
        "name": "bailian",
        "model": "decision-model-preview",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "env_key": "DASHSCOPE_API_KEY",
        "priority": 1,
    }

    # 302.AI LLM决策通道（结构化prompt→JSON输出）
    CHANNEL_302AI = {
        "name": "302ai",
        "model": "qwen-max",
        "endpoint": "https://api.302ai.cn/v1/chat/completions",
        "env_key": "API_302AI_KEY",
        "priority": 2,
    }

    # 决策prompt模板
    DECISION_PROMPT_TEMPLATE = """你是一个结构化决策模型。请对以下事项做出判断，输出严格的JSON格式。

事项: {item}
描述: {description}

请输出以下JSON结构（不要输出其他内容）:
{{
  "class": "分类标签（如: 预算/技术/治理/安全/运营）",
  "verdict": true/false（是否应该执行）,
  "score": 0.0-1.0（执行紧迫度评分）,
  "prob_distribution": [0.0-1.0, 0.0-1.0]（[执行概率, 不执行概率]，和为1.0）,
  "confidence": 0.0-1.0（置信度）
}}"""

    def __init__(self, preferred_channel: Optional[str] = None):
        self.preferred_channel = preferred_channel
        if preferred_channel == "bailian":
            self._channel_order = [self.BAILIAN_CHANNEL, self.CHANNEL_302AI]
        elif preferred_channel == "302ai":
            self._channel_order = [self.CHANNEL_302AI, self.BAILIAN_CHANNEL]
        else:
            self._channel_order = [self.BAILIAN_CHANNEL, self.CHANNEL_302AI]

    def _get_api_key(self, env_key: str) -> Optional[str]:
        return os.environ.get(env_key)

    def _call_bailian_decision(self, item: str, description: str) -> Tuple[bool, Dict]:
        """调用百炼decision-model-preview"""
        channel = self.BAILIAN_CHANNEL
        api_key = self._get_api_key(channel["env_key"])
        if not api_key:
            return False, {"error": f"环境变量 {channel['env_key']} 未设置", "channel": channel["name"]}

        # 百炼decision-model-preview使用特殊的API格式
        payload = json.dumps({
            "model": channel["model"],
            "input": {
                "item": item,
                "description": description,
            },
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

            # 解析百炼决策模型输出
            output = body.get("output", {})
            return True, {
                "class": output.get("class", ""),
                "verdict": output.get("verdict", False),
                "score": float(output.get("score", 0.0)),
                "prob_distribution": output.get("prob_distribution", [0.5, 0.5]),
                "confidence": float(output.get("confidence", 0.0)),
                "model": channel["model"],
                "provider": channel["name"],
                "latency_ms": latency_ms,
            }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            return False, {
                "error": f"HTTP {e.code}: {err_body}",
                "channel": channel["name"],
                "http_status": e.code,
            }
        except Exception as e:
            return False, {"error": str(e)[:300], "channel": channel["name"]}

    def _call_302ai_decision(self, item: str, description: str) -> Tuple[bool, Dict]:
        """调用302.AI qwen-max做结构化决策"""
        channel = self.CHANNEL_302AI
        api_key = self._get_api_key(channel["env_key"])
        if not api_key:
            return False, {"error": f"环境变量 {channel['env_key']} 未设置", "channel": channel["name"]}

        prompt = self.DECISION_PROMPT_TEMPLATE.format(item=item, description=description)

        payload = json.dumps({
            "model": channel["model"],
            "messages": [
                {"role": "system", "content": "你是一个结构化决策模型，只输出JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,  # 低温度确保确定性
            "max_tokens": 200,
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

            # 从LLM响应中提取JSON
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            decision = self._parse_decision_json(content)

            if decision:
                decision["model"] = channel["model"]
                decision["provider"] = channel["name"]
                decision["latency_ms"] = latency_ms
                return True, decision
            else:
                return False, {"error": f"JSON解析失败: {content[:200]}", "channel": channel["name"]}

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            return False, {
                "error": f"HTTP {e.code}: {err_body}",
                "channel": channel["name"],
                "http_status": e.code,
            }
        except Exception as e:
            return False, {"error": str(e)[:300], "channel": channel["name"]}

    def _parse_decision_json(self, content: str) -> Optional[Dict]:
        """从LLM输出中解析决策JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON块
        import re
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 尝试提取```json```块
        json_block = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except json.JSONDecodeError:
                pass

        return None

    def decide(self, item: str, description: str = "") -> Dict:
        """
        对事项做出结构化决策

        Returns:
            {
                "class": str,          # 分类标签
                "verdict": bool,       # 是否应该执行
                "score": float,        # 紧迫度评分 0.0-1.0
                "prob_distribution": List[float],  # [执行概率, 不执行概率]
                "confidence": float,   # 置信度 0.0-1.0
                "model": str,
                "provider": str,
                "latency_ms": int,
                "fallback_used": bool,
            }
        """
        if not item or not item.strip():
            raise ValueError("item不能为空")

        errors = []
        for i, channel in enumerate(self._channel_order):
            if channel["name"] == "bailian":
                success, result = self._call_bailian_decision(item, description)
            else:
                success, result = self._call_302ai_decision(item, description)

            if success:
                result["fallback_used"] = i > 0
                # 验证输出契约完整性
                required = ["class", "verdict", "score", "prob_distribution", "confidence"]
                for field in required:
                    if field not in result:
                        result[field] = None  # 缺失字段填None
                return result
            else:
                errors.append(result)
                continue

        raise RuntimeError(
            f"所有决策模型通道均失败。错误链: " +
            " → ".join([f"{e.get('channel', '?')}: {e.get('error', '?')[:80]}" for e in errors])
        )

    def decide_batch(self, items: List[Dict]) -> List[Dict]:
        """批量决策 — items为[{item, description}, ...]"""
        return [self.decide(item["item"], item.get("description", "")) for item in items]

    def verify_determinism(self, item: str, description: str = "", n: int = 3) -> Dict:
        """验证确定性 — 同输入n次，检查输出是否逐字节相同"""
        results = []
        for _ in range(n):
            r = self.decide(item, description)
            # 只比较决策字段（不含latency_ms等运行时字段）
            decision_fields = {
                "class": r.get("class"),
                "verdict": r.get("verdict"),
                "score": r.get("score"),
                "prob_distribution": r.get("prob_distribution"),
                "confidence": r.get("confidence"),
            }
            results.append(json.dumps(decision_fields, sort_keys=True))

        all_same = len(set(results)) == 1
        return {
            "deterministic": all_same,
            "n_runs": n,
            "unique_outputs": len(set(results)),
            "results": results,
        }


# ===== 候裁清单 =====
CANDIDATE_DECISIONS = [
    {"item": "裁五：百炼Budget预算调高", "description": "唯一代码不可解阻断，需主权人在百炼控制台操作Budget Management调高预算"},
    {"item": "裁六：P4世界模型实跑预算上限", "description": "建议单轮≤5元封顶，超限即停"},
    {"item": "裁七：Sites MCP恢复后补publish_site", "description": "同意，复三面一致"},
    {"item": "裁八：302ai键轮换（第三次暴露）", "description": "建议立即执行轮换"},
    {"item": "裁九：纲要云端凭据区块+1增长", "description": "建议升级脱敏工单为本周执行项"},
    {"item": "裁十：P2试点200节用量预估<0.5元/轮", "description": "建议准按此边界执行"},
    {"item": "裁十一：Neo4j Desktop安装授权", "description": "Graphiti集成前置条件，免费本地版"},
    {"item": "裁十二：Q4人设3D建模使用已有10个ready世界", "description": "建议先用已有世界试跑，免建世费"},
]


# ===== 测试 =====
if __name__ == "__main__":
    # 凭据从环境变量读取，不落盘
    # 请设置: API_302AI_KEY
    if not os.environ.get("API_302AI_KEY"):
        print("⚠ 请先设置环境变量 API_302AI_KEY")
        sys.exit(1)

    service = DecisionService()

    print("=" * 60)
    print("决策模型服务层 — 候裁清单批量决策")
    print("=" * 60)

    for item in CANDIDATE_DECISIONS:
        try:
            result = service.decide(item["item"], item["description"])
            print(f"\n  [{result['provider']}] {item['item']}")
            print(f"    class: {result.get('class', '?')}")
            print(f"    verdict: {result.get('verdict', '?')}")
            print(f"    score: {result.get('score', '?')}")
            print(f"    prob_distribution: {result.get('prob_distribution', '?')}")
            print(f"    confidence: {result.get('confidence', '?')}")
            print(f"    latency: {result.get('latency_ms', '?')}ms")
        except Exception as e:
            print(f"\n  ERROR [{item['item']}]: {e}")

    print()
    print("=" * 60)
    print("确定性验证 — 同输入3次")
    print("=" * 60)
    try:
        det = service.verify_determinism("裁五：百炼Budget预算调高", "唯一代码不可解阻断", n=3)
        print(f"  deterministic: {det['deterministic']}")
        print(f"  unique_outputs: {det['unique_outputs']}/{det['n_runs']}")
        if not det['deterministic']:
            print(f"  ⚠ 非确定性 — LLM通道温度不为0时输出可能变化")
            for i, r in enumerate(det['results']):
                print(f"    run{i}: {r[:100]}")
    except Exception as e:
        print(f"  ERROR: {e}")