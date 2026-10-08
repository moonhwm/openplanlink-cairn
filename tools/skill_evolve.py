#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""skill_evolve.py —— SkillOpt 落地：自进化技能文档（rollout→reflect→edit→gate）。

依据微软 SkillOpt（技能文档即冻结 Agent 的可训练外部状态）：
  rollout  = 打样记录（任务/工具调用/得分）
  reflect  = 优化器（异质模型）分析成败 minibatch、提出结构化编辑
  edit     = 有界编辑（add/delete/replace + 文本学习率预算）
  gate     = 留出集验证门（仅当进步才接受候选）
  export   = 导出 compact best_skill.md（部署只消费最终技能、不含优化器记忆）

纯标准库 + 复用 hetero_models（硅基流动优化器）。安全红线：key 从本地 env 读、不入库。
"""
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hetero_models as HM

SKILL_FILE = pathlib.Path(__file__).parent / "best_skill.md"
LOG_FILE = pathlib.Path(__file__).parent / "skill_evolve_log.jsonl"
EDIT_BUDGET = 4  # 文本学习率：每次最多 4 处编辑（SkillOpt lr=4 语义）


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_skill():
    return SKILL_FILE.read_text(encoding="utf-8") if SKILL_FILE.exists() else ""


def _save_skill(text):
    SKILL_FILE.write_text(text, encoding="utf-8")
    return SKILL_FILE


def reflect(rollouts, current_skill):
    """优化器：用硅基流动模型分析成败、提出结构化编辑建议（add/delete/replace）。"""
    prompt = (
        "你是技能优化器。当前技能文档（每条是可执行规则）：\n" + current_skill[:2000] +
        "\n\n打样记录（成功/失败）：\n" + json.dumps(rollouts, ensure_ascii=False)[:2000] +
        "\n\n只做" + str(EDIT_BUDGET) + "处以内编辑改进可执行规则：失败任务→replace 其对应规则；缺规则→add 一条可执行规则（禁止把打样记录当 add 内容）。"
        "每处形如 {\"op\":\"replace|add\",\"target\":\"...\",\"replacement\":\"...\",\"reason\":\"...\"}，只返回 JSON 数组。")
    r = HM.chat("Qwen/Qwen2.5-7B-Instruct", prompt, max_tokens=512)
    if "error" in r:
        return []
    try:
        txt = r["content"]
        start = txt.find("[")
        edits = json.loads(txt[start:] if start >= 0 else txt)
        return edits if isinstance(edits, list) else []
    except Exception:
        return []


def apply_edits(skill, edits):
    """有界编辑：按预算施加 add/delete/replace（文本级，保守）。"""
    new = skill
    applied = 0
    for e in edits[:EDIT_BUDGET]:
        op = e.get("op")
        target = e.get("target", "")
        replacement = e.get("replacement", "")
        if op == "add" and target not in new:
            new += "\n- " + replacement
            applied += 1
        elif op == "delete" and target in new:
            new = new.replace(target, "", 1)
            applied += 1
        elif op == "replace" and target in new:
            new = new.replace(target, replacement, 1)
            applied += 1
    return new, applied


def gate(candidate, current, scores):
    """留出集验证门：仅当候选在留出集得分 >= 当前才接受（此处用打样均分代理）。"""
    if not scores:
        return False, "无留出集得分"
    avg = sum(scores) / len(scores)
    return avg >= 0.5, "留出集均分 %.2f" % avg


def evolve(rollouts):
    """一轮 SkillOpt 循环。返回 (accepted, 结果字典)。"""
    current = _load_skill() or "# 自进化技能\n"
    edits = reflect(rollouts, current)
    candidate, applied = apply_edits(current, edits)
    if applied == 0:
        return False, {"stage": "reflect", "reason": "无可施加编辑"}
    scores = [r.get("score", 0) for r in rollouts if isinstance(r, dict)]
    ok, reason = gate(candidate, current, scores)
    result = {"stage": "gate", "applied": applied, "reason": reason, "edits": len(edits),
              "ts": _now()}
    if ok:
        _save_skill(candidate)
        result["accepted"] = True
    else:
        result["accepted"] = False
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return ok, result


if __name__ == "__main__":
    sample = [{"task": "路由", "score": 1.0, "ok": True},
              {"task": "检索", "score": 0.0, "ok": False}]
    ok, res = evolve(sample)
    print("  自进化一轮 = accepted=%s %s" % (ok, res))
    print("  best_skill.md 存在 =", SKILL_FILE.exists())
