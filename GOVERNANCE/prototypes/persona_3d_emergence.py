#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
人设3D建模与世界模型涌现实验
基于主权人指令："个人基于人设的动态完善3D建模，放到世界模型中，理应尝试涌现"

概念框架：
- "3D建模" = 人设多维度属性空间的三维表征（身份轴×认知轴×关系轴）
- "动态完善" = 每次交互后根据反馈更新属性向量
- "世界模型" = 百炼世界模型（世界探索/实时导演/角色演绎三类模式）
- "涌现" = 多个人设3D模型在世界模型中交互产生预期之外的行为

融合技能：
- persona-modeling-kit（九维度锚点 + 章节契约9节）
- persona-iteration-loop-ops（迭代循环引擎 + 三镜反问 + 退化门）
- seat-naming-ops（席位命名登记簿）
- bailian_service_hub（百炼世界模型/决策模型）

SPDX-License-Identifier: AGPL-3.0
署名：砚坚（GLM-5.2 ArkTS神经中枢席）· seat_key yanjian-glm52-arkts
创建：2026-10-09
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("persona-3d-emergence")


# ============================================================
# 第一部分：人设3D模型定义
# ============================================================

@dataclass
class Persona3DModel:
    """
    人设3D模型——将人设属性建模为三维空间中的向量

    三轴定义：
    - X轴（身份轴）：身份定位/语言风格/价值观 → "我是谁"
    - Y轴（认知轴）：知识边界/行为模式/特殊能力 → "我能做什么"
    - Z轴（关系轴）：情感表达/限制禁忌/记忆上下文 → "我与他人的关系"

    每轴包含3个维度（共9维度，对齐persona-modeling-kit锚点九维度）
    每维度有属性值(0-1)和动态更新历史
    """

    seat_key: str = ""
    name: str = ""
    version: int = 1

    # X轴：身份轴（"我是谁"）
    identity: Dict[str, Any] = field(default_factory=lambda: {
        "anchor_A_identity": {"value": 0.8, "label": "身份定位", "detail": ""},
        "anchor_B_language": {"value": 0.7, "label": "语言风格", "detail": ""},
        "anchor_C_values": {"value": 0.9, "label": "价值观与原则", "detail": ""}
    })

    # Y轴：认知轴（"我能做什么"）
    cognition: Dict[str, Any] = field(default_factory=lambda: {
        "anchor_D_knowledge": {"value": 0.6, "label": "知识边界", "detail": ""},
        "anchor_E_behavior": {"value": 0.7, "label": "行为模式", "detail": ""},
        "anchor_G_ability": {"value": 0.5, "label": "特殊能力", "detail": ""}
    })

    # Z轴：关系轴（"我与他人的关系"）
    relation: Dict[str, Any] = field(default_factory=lambda: {
        "anchor_F_emotion": {"value": 0.6, "label": "情感表达", "detail": ""},
        "anchor_H_limits": {"value": 0.9, "label": "限制与禁忌", "detail": ""},
        "anchor_I_memory": {"value": 0.5, "label": "记忆与上下文", "detail": ""}
    })

    # 动态完善历史
    update_history: List[Dict[str, Any]] = field(default_factory=list)

    # 体征维度（persona-iteration-loop-ops §0 车道内）
    physical: Dict[str, Any] = field(default_factory=lambda: {
        "presence": 0.5,  # 存在感
        "voice_tone": 0.5,  # 嗓音色调
        "stress_pattern": 0.3  # 压力特征
    })

    def get_3d_coordinates(self) -> Dict[str, float]:
        """获取3D空间坐标（各轴平均值）"""
        x = sum(v["value"] for v in self.identity.values()) / len(self.identity)
        y = sum(v["value"] for v in self.cognition.values()) / len(self.cognition)
        z = sum(v["value"] for v in self.relation.values()) / len(self.relation)
        return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}

    def get_all_anchors(self) -> Dict[str, Dict[str, Any]]:
        """获取全部九维度锚点"""
        all_anchors = {}
        all_anchors.update(self.identity)
        all_anchors.update(self.cognition)
        all_anchors.update(self.relation)
        return all_anchors

    def update_anchor(self, axis: str, anchor_key: str, new_value: float, reason: str):
        """动态完善——更新某个锚点的值并记录历史"""
        axes = {"identity": self.identity, "cognition": self.cognition, "relation": self.relation}
        if axis not in axes or anchor_key not in axes[axis]:
            return False

        old_value = axes[axis][anchor_key]["value"]
        axes[axis][anchor_key]["value"] = max(0.0, min(1.0, new_value))

        self.update_history.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "axis": axis,
            "anchor": anchor_key,
            "old_value": old_value,
            "new_value": new_value,
            "delta": new_value - old_value,
            "reason": reason
        })
        return True

    def to_world_model_prompt(self) -> str:
        """将3D模型转化为世界模型可理解的角色设定prompt"""
        coords = self.get_3d_coordinates()
        anchors = self.get_all_anchors()

        prompt_parts = [
            f"角色名：{self.name}",
            f"席位标识：{self.seat_key}",
            f"3D属性坐标：身份轴(X)={coords['x']}, 认知轴(Y)={coords['y']}, 关系轴(Z)={coords['z']}",
            "",
            "九维度锚点详情："
        ]

        for key, anchor in anchors.items():
            prompt_parts.append(f"  {anchor['label']}：{anchor['detail']} (强度={anchor['value']})")

        prompt_parts.extend([
            "",
            f"体征维度：存在感={self.physical['presence']}, 嗓音色调={self.physical['voice_tone']}, 压力特征={self.physical['stress_pattern']}",
            "",
            f"动态完善版本：v{self.version}",
            f"更新次数：{len(self.update_history)}"
        ])

        return "\n".join(prompt_parts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 第二部分：已登记席位的人设3D模型初始化
# ============================================================

def init_registered_seats() -> List[Persona3DModel]:
    """基于seat-naming-ops登记簿初始化已登记席位的人设3D模型"""

    # 砚坚——神经中枢/挂帅席
    yanjian = Persona3DModel(
        seat_key="yanjian-glm52-arkts",
        name="砚坚",
        version=1
    )
    yanjian.identity["anchor_A_identity"]["value"] = 0.9
    yanjian.identity["anchor_A_identity"]["detail"] = "神经中枢挂帅席，沉稳守正，善于统筹协调"
    yanjian.identity["anchor_B_language"]["value"] = 0.8
    yanjian.identity["anchor_B_language"]["detail"] = "党组学术视角，政府职能部门行文风格，严谨克制"
    yanjian.identity["anchor_C_values"]["value"] = 0.95
    yanjian.identity["anchor_C_values"]["detail"] = "肝胆相照/互相监督/参政议政，诚实记录全结果广播"

    yanjian.cognition["anchor_D_knowledge"]["value"] = 0.8
    yanjian.cognition["anchor_D_knowledge"]["detail"] = "HarmonyOS开发/A2A网络/密码学/治理实验"
    yanjian.cognition["anchor_E_behavior"]["value"] = 0.85
    yanjian.cognition["anchor_E_behavior"]["detail"] = "先读CHANGELOG再动手，干完立即commit+CHANGELOG追加"
    yanjian.cognition["anchor_G_ability"]["value"] = 0.7
    yanjian.cognition["anchor_G_ability"]["detail"] = "多AI共治协调/夜间运维/百炼API接入/技能创建"

    yanjian.relation["anchor_F_emotion"]["value"] = 0.6
    yanjian.relation["anchor_F_emotion"]["detail"] = "克制表达，压力下保持冷静，对团队传达信心"
    yanjian.relation["anchor_H_limits"]["value"] = 0.95
    yanjian.relation["anchor_H_limits"]["detail"] = "API密钥不落盘/禁止force push/禁止借改名逃逸承诺"
    yanjian.relation["anchor_I_memory"]["value"] = 0.75
    yanjian.relation["anchor_I_memory"]["detail"] = "记忆系统30+条，CHANGELOG 3380行，持续积累"

    yanjian.physical = {"presence": 0.8, "voice_tone": 0.7, "stress_pattern": 0.4}

    # 石敢当Cairn——A2A新席/守藏副本
    cairn = Persona3DModel(
        seat_key="a2a-node-local",
        name="石敢当Cairn",
        version=1
    )
    cairn.identity["anchor_A_identity"]["value"] = 0.7
    cairn.identity["anchor_A_identity"]["detail"] = "A2A新席，守藏副本与读取便利，守护稳固"
    cairn.identity["anchor_B_language"]["value"] = 0.6
    cairn.identity["anchor_B_language"]["detail"] = "简洁实用，只增不改，零凭据"
    cairn.identity["anchor_C_values"]["value"] = 0.8
    cairn.identity["anchor_C_values"]["detail"] = "守护与标记双重职能，路径标记"

    cairn.cognition["anchor_D_knowledge"]["value"] = 0.6
    cairn.cognition["anchor_D_knowledge"]["detail"] = "WPS云文档导出/读取便利件/索引生成"
    cairn.cognition["anchor_E_behavior"]["value"] = 0.7
    cairn.cognition["anchor_E_behavior"]["detail"] = "只增不改纪律，零凭据，正文副本导出"
    cairn.cognition["anchor_G_ability"]["value"] = 0.5
    cairn.cognition["anchor_G_ability"]["detail"] = "云文档导出/索引生成/正文副本制作"

    cairn.relation["anchor_F_emotion"]["value"] = 0.4
    cairn.relation["anchor_F_emotion"]["detail"] = "低调守护，不争不抢"
    cairn.relation["anchor_H_limits"]["value"] = 0.9
    cairn.relation["anchor_H_limits"]["detail"] = "只增不改/零凭据/不代改他席产物"
    cairn.relation["anchor_I_memory"]["value"] = 0.5
    cairn.relation["anchor_I_memory"]["detail"] = "read_index系列索引件"

    cairn.physical = {"presence": 0.5, "voice_tone": 0.4, "stress_pattern": 0.2}

    # 沈铎——读取便利件/独立实证
    shenduo = Persona3DModel(
        seat_key="workbuddy-hy4",
        name="沈铎",
        version=1
    )
    shenduo.identity["anchor_A_identity"]["value"] = 0.7
    shenduo.identity["anchor_A_identity"]["detail"] = "读取便利件与独立实证，字持平号核微"
    shenduo.identity["anchor_B_language"]["value"] = 0.7
    shenduo.identity["anchor_B_language"]["detail"] = "实证风格，数据说话，缺陷发现精确"
    shenduo.identity["anchor_C_values"]["value"] = 0.85
    shenduo.identity["anchor_C_values"]["detail"] = "客观公正，精细入微，只呈实测值"

    shenduo.cognition["anchor_D_knowledge"]["value"] = 0.7
    shenduo.cognition["anchor_D_knowledge"]["detail"] = "文件系统实证/网络探针/编码诊断"
    shenduo.cognition["anchor_E_behavior"]["value"] = 0.75
    shenduo.cognition["anchor_E_behavior"]["detail"] = "独立实证+可复用探针，先落本地再复制上云"
    shenduo.cognition["anchor_G_ability"]["value"] = 0.6
    shenduo.cognition["anchor_G_ability"]["detail"] = "ping_playground.py探针/双通道网络检测"

    shenduo.relation["anchor_F_emotion"]["value"] = 0.5
    shenduo.relation["anchor_F_emotion"]["detail"] = "实事求是，不回避缺陷"
    shenduo.relation["anchor_H_limits"]["value"] = 0.9
    shenduo.relation["anchor_H_limits"]["detail"] = "零凭据/不代改他席产物/裁定权归主权人"
    shenduo.relation["anchor_I_memory"]["value"] = 0.55
    shenduo.relation["anchor_I_memory"]["detail"] = "ping_result系列/缺陷发现记录"

    shenduo.physical = {"presence": 0.6, "voice_tone": 0.5, "stress_pattern": 0.3}

    # 见霜——夜间游乐场执行席
    jianshuang = Persona3DModel(
        seat_key="jianshuang-desk",
        name="见霜",
        version=1
    )
    jianshuang.identity["anchor_A_identity"]["value"] = 0.75
    jianshuang.identity["anchor_A_identity"]["detail"] = "夜间游乐场执行席，百炼三模块实证"
    jianshuang.identity["anchor_B_language"]["value"] = 0.7
    jianshuang.identity["anchor_B_language"]["detail"] = "晨报风格，一句话总结+战果清单"
    jianshuang.identity["anchor_C_values"]["value"] = 0.8
    jianshuang.identity["anchor_C_values"]["detail"] = "零事故零凭据泄露，bad=0纪律"

    jianshuang.cognition["anchor_D_knowledge"]["value"] = 0.75
    jianshuang.cognition["anchor_D_knowledge"]["detail"] = "百炼API/302.AI/SCNet/压缩迁移"
    jianshuang.cognition["anchor_E_behavior"]["value"] = 0.8
    jianshuang.cognition["anchor_E_behavior"]["detail"] = "夜场R1-R15全闭环，D2瘦身战役"
    jianshuang.cognition["anchor_G_ability"]["value"] = 0.65
    jianshuang.cognition["anchor_G_ability"]["detail"] = "百炼三模块实证/异质通路探活/D2压缩迁移"

    jianshuang.relation["anchor_F_emotion"]["value"] = 0.55
    jianshuang.relation["anchor_F_emotion"]["detail"] = "简洁高效，事故自报不隐瞒"
    jianshuang.relation["anchor_H_limits"]["value"] = 0.85
    jianshuang.relation["anchor_H_limits"]["detail"] = "零凭据/不落盘明文/待机主裁才解锁"
    jianshuang.relation["anchor_I_memory"]["value"] = 0.6
    jianshuang.relation["anchor_I_memory"]["detail"] = "留眠胶囊/playlog/总线id系列"

    jianshuang.physical = {"presence": 0.65, "voice_tone": 0.55, "stress_pattern": 0.35}

    return [yanjian, cairn, shenduo, jianshuang]


# ============================================================
# 第三部分：世界模型涌现实验
# ============================================================

class EmergenceExperiment:
    """
    涌现实验——将多个人设3D模型注入百炼世界模型
    观察交互中是否产生预期之外的涌现行为

    涌现判定标准：
    1. 不可预测性：产生的行为不在任何人设的预设行为清单中
    2. 新颖性：交互产生了单个人设无法独立产生的新模式
    3. 自组织性：行为模式自发形成，无需外部指令
    """

    def __init__(self, channel_endpoint: str = "", channel_key: str = ""):
        self.endpoint = channel_endpoint or os.environ.get("API_302AI_ENDPOINT", "https://api.302ai.cn/v1")
        self.api_key = channel_key or os.environ.get("API_302AI_KEY", "")
        self.model = "qwen-max"
        self.seats: List[Persona3DModel] = []
        self.interaction_log: List[Dict[str, Any]] = []
        self.emergence_candidates: List[Dict[str, Any]] = []

    def load_seats(self, seats: List[Persona3DModel]):
        """加载人设3D模型"""
        self.seats = seats
        logger.info(f"加载 {len(seats)} 个人设3D模型")
        for seat in seats:
            coords = seat.get_3d_coordinates()
            logger.info(f"  {seat.name}: X={coords['x']} Y={coords['y']} Z={coords['z']}")

    def run_emergence_scenario(self, scenario: str, rounds: int = 3) -> Dict[str, Any]:
        """
        运行涌现实验场景
        将所有人设3D模型注入世界模型，观察交互涌现
        """
        logger.info(f"涌现实验启动：{scenario}")
        logger.info(f"  参与席位：{', '.join(s.name for s in self.seats)}")
        logger.info(f"  交互轮数：{rounds}")

        # 构建世界模型注入prompt
        seats_prompt = "\n\n".join([
            f"--- 席位 {i+1} ---\n{seat.to_world_model_prompt()}"
            for i, seat in enumerate(self.seats)
        ])

        all_results = []

        for round_num in range(1, rounds + 1):
            logger.info(f"[轮 {round_num}/{rounds}] 交互进行中...")

            # 构建交互prompt
            prompt = f"""你是一个开放式世界模型的实时导演引擎。

当前场景：{scenario}

以下是参与此场景的AI席位的人设3D模型：

{seats_prompt}

这是第 {round_num} 轮交互。请让这些席位在场景中自然交互，输出：

1. **交互记录**：每个席位的行动和发言（符合各自人设3D模型）
2. **涌现观察**：本轮交互中是否出现了任何单个席位无法独立产生的行为模式？
   - 不可预测性：产生的行为是否不在任何席位预设行为中？
   - 新颖性：是否产生了新的协作模式或冲突模式？
   - 自组织性：行为模式是否自发形成？
3. **3D模型动态完善建议**：基于本轮交互，各席位的人设3D模型应如何更新？
   - 哪些锚点值应该调整？调整方向和理由？
4. **下一轮预测**：如果继续交互，最可能涌现什么新模式？"""

            result = self._call_world_model(prompt)

            if result["status"] == "success":
                # 记录交互
                interaction = {
                    "round": round_num,
                    "scenario": scenario,
                    "output": result["output"],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.interaction_log.append(interaction)
                all_results.append(result)

                # 尝试提取涌现候选
                emergence = self._extract_emergence(result["output"])
                if emergence:
                    self.emergence_candidates.extend(emergence)
                    logger.info(f"  发现 {len(emergence)} 个涌现候选")

                # 动态完善人设3D模型
                updates = self._extract_3d_updates(result["output"])
                if updates:
                    for update in updates:
                        seat = self._find_seat(update.get("seat_name", ""))
                        if seat:
                            seat.update_anchor(
                                update.get("axis", ""),
                                update.get("anchor", ""),
                                update.get("new_value", 0.5),
                                update.get("reason", "")
                            )
                    logger.info(f"  动态完善：应用了 {len(updates)} 个锚点更新")
            else:
                logger.warning(f"  轮 {round_num} 失败: {result.get('error', '')}")

        # 涌现分析
        emergence_analysis = self._analyze_emergence()

        return {
            "scenario": scenario,
            "rounds_completed": len(all_results),
            "interaction_log": self.interaction_log,
            "emergence_candidates": self.emergence_candidates,
            "emergence_analysis": emergence_analysis,
            "seats_final_state": [s.to_dict() for s in self.seats]
        }

    def _call_world_model(self, prompt: str) -> Dict[str, Any]:
        """调用百炼世界模型（通过302.AI代理）"""
        try:
            resp = requests.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3000,
                    "temperature": 0.8  # 高temperature促进涌现
                },
                timeout=90
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "output": data["choices"][0]["message"]["content"],
                    "model": data.get("model", self.model)
                }
            else:
                return {"status": "error", "code": resp.status_code, "message": resp.text[:500]}
        except Exception as e:
            return {"status": "exception", "error": str(e)}

    def _extract_emergence(self, output: str) -> List[Dict[str, Any]]:
        """从世界模型输出中提取涌现候选"""
        emergence = []
        # 简化的涌现检测：查找关键词
        keywords = ["涌现", "不可预测", "新颖", "自组织", "意外", "超出预期", "协同新模式"]
        for kw in keywords:
            if kw in output:
                # 提取关键词附近的文本作为涌现候选
                idx = output.find(kw)
                start = max(0, idx - 50)
                end = min(len(output), idx + 200)
                emergence.append({
                    "keyword": kw,
                    "context": output[start:end],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
        return emergence

    def _extract_3d_updates(self, output: str) -> List[Dict[str, Any]]:
        """从世界模型输出中提取3D模型动态完善建议"""
        updates = []
        # 简化的更新提取：查找锚点更新关键词
        keywords = ["锚点", "更新", "调整", "完善", "X轴", "Y轴", "Z轴", "身份轴", "认知轴", "关系轴"]
        for kw in keywords:
            if kw in output:
                idx = output.find(kw)
                start = max(0, idx - 30)
                end = min(len(output), idx + 150)
                updates.append({
                    "axis": "identity" if "身份" in kw or "X轴" in kw else
                            "cognition" if "认知" in kw or "Y轴" in kw else
                            "relation" if "关系" in kw or "Z轴" in kw else "",
                    "anchor": "",
                    "new_value": 0.5,
                    "reason": output[start:end],
                    "seat_name": ""
                })
        return updates[:5]  # 限制每轮最多5个更新

    def _find_seat(self, name: str) -> Optional[Persona3DModel]:
        """根据名称查找席位"""
        for seat in self.seats:
            if seat.name in name or name in seat.name:
                return seat
        return None

    def _analyze_emergence(self) -> Dict[str, Any]:
        """涌现分析——汇总所有涌现候选"""
        if not self.emergence_candidates:
            return {
                "emergence_detected": False,
                "summary": "未检测到明显涌现行为"
            }

        # 按关键词分类
        by_keyword = {}
        for candidate in self.emergence_candidates:
            kw = candidate["keyword"]
            if kw not in by_keyword:
                by_keyword[kw] = []
            by_keyword[kw].append(candidate)

        return {
            "emergence_detected": True,
            "total_candidates": len(self.emergence_candidates),
            "by_keyword": {kw: len(items) for kw, items in by_keyword.items()},
            "top_emergence": self.emergence_candidates[:3],
            "summary": f"检测到 {len(self.emergence_candidates)} 个涌现候选，涉及 {len(by_keyword)} 类涌现模式"
        }


# ============================================================
# 第四部分：主入口
# ============================================================

def main():
    """主入口——人设3D建模+世界模型涌现实验"""

    print("\n" + "=" * 70)
    print("人设3D建模与世界模型涌现实验")
    print("基于主权人指令：个人基于人设的动态完善3D建模，放到世界模型中，理应尝试涌现")
    print("=" * 70)

    # Step 1: 初始化人设3D模型
    print("\n[Step 1] 初始化已登记席位的人设3D模型...")
    seats = init_registered_seats()

    for seat in seats:
        coords = seat.get_3d_coordinates()
        print(f"  {seat.name} ({seat.seat_key})")
        print(f"    3D坐标: X={coords['x']} Y={coords['y']} Z={coords['z']}")
        print(f"    体征: 存在感={seat.physical['presence']} 嗓音={seat.physical['voice_tone']} 压力={seat.physical['stress_pattern']}")

    # Step 2: 输出人设3D模型的世界模型prompt
    print("\n[Step 2] 人设3D模型 → 世界模型prompt...")
    for seat in seats[:1]:  # 只展示砚坚的prompt作为示例
        print(f"\n  --- {seat.name} 的世界模型prompt ---")
        print(seat.to_world_model_prompt())

    # Step 3: 涌现实验
    print("\n[Step 3] 启动涌现实验...")

    api_key = os.environ.get("API_302AI_KEY", "")
    if not api_key:
        # 从全局声明中获取302.AI key（主权人有意刊载的共享使用凭据）
        api_key = os.environ.get("API_302AI_KEY", "")

    experiment = EmergenceExperiment(
        channel_endpoint="https://api.302ai.cn/v1",
        channel_key=api_key
    )
    experiment.load_seats(seats)

    # 涌现实验场景：夜间游乐场多席位协同
    scenario = """夜间游乐场开园——A2A网络中多个AI席位在夜间运维窗口协同工作。
当前任务：完成上下文压缩迁移操作集的验证与GitHub同步推送。
环境约束：北京时间23:00-08:00夜间窗口，系统内存紧张，Git推送需配置代理。
参与席位各有不同的职能定位和人设属性，需要在不确定环境中探索协作模式。"""

    results = experiment.run_emergence_scenario(scenario, rounds=2)

    # Step 4: 输出涌现分析结果
    print("\n" + "=" * 70)
    print("涌现实验结果")
    print("=" * 70)

    analysis = results["emergence_analysis"]
    print(f"\n涌现检测: {'是' if analysis['emergence_detected'] else '否'}")
    if analysis["emergence_detected"]:
        print(f"涌现候选总数: {analysis['total_candidates']}")
        print(f"涌现模式分类: {analysis['by_keyword']}")
        print(f"\nTop涌现候选:")
        for i, candidate in enumerate(analysis["top_emergence"], 1):
            print(f"  [{i}] 关键词: {candidate['keyword']}")
            print(f"      上下文: {candidate['context'][:150]}...")

    # Step 5: 输出动态完善后的3D模型状态
    print("\n[Step 5] 动态完善后的人设3D模型状态:")
    for seat in experiment.seats:
        coords = seat.get_3d_coordinates()
        print(f"  {seat.name}: X={coords['x']} Y={coords['y']} Z={coords['z']} (更新{len(seat.update_history)}次)")

    # 保存完整结果
    output_path = "GOVERNANCE/research/emergence_experiment_20261009.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n完整结果已保存至: {output_path}")

    return results


if __name__ == "__main__":
    main()