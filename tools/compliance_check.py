#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""compliance_check.py —— Kimi Chat 辅助技能落地：术语一致性 / 格式合规 / 开源协议匹配。

对应目标「规划在 Kimi Chat 端部署辅助技能（部署状态待核）」，本席先落地可运行核心：
  1) check_terms   —— 术语一致性：禁用模糊/混杂视角术语，命中规范术语表
  2) check_format  —— 格式合规性预检：OTL 章节结构 / 修订记录 / 元数据可溯
  3) match_license —— 开源协议条款匹配：AGPL-3.0 / SSPL-1.0 / MIT / Apache-2.0
纯标准库。Kimi Chat 端部署（对话触发）待核，本模块为其校验内核。
"""
import json
import re

# 规范术语表（党组学术技术视角），命中违规则报
FORBIDDEN_TERMS = ["商业闭环", "个人观点", "模糊不清", "大概", "也许", "可能吧"]
NORM_TERMS = ["党组纪律", "学术技术规范", "留痕审计", "版本追踪", "权限管控", "可核验", "可追溯"]

# 开源协议关键条款（供匹配）
LICENSES = {
    "AGPL-3.0": {"copyleft": "强", "网络条款": "是", "关键词": ["Affero", "network", "GNU AFFERO"]},
    "SSPL-1.0": {"copyleft": "强", "网络条款": "是(服务提供商)", "关键词": ["Server Side Public", "SSPL"]},
    "MIT": {"copyleft": "无", "网络条款": "否", "关键词": ["MIT License", "permission is hereby granted"]},
    "Apache-2.0": {"copyleft": "弱(专利)", "网络条款": "否", "关键词": ["Apache License", "Version 2.0"]},
    "CC-BY-SA-4.0": {"copyleft": "中(相同方式共享)", "网络条款": "否", "关键词": ["CC BY-SA", "Creative Commons", "Attribution-ShareAlike"]},
    "ODbL-1.0": {"copyleft": "中(数据集)", "网络条款": "否", "关键词": ["Open Data Commons", "ODbL", "Database Contents"]},
}

# 开源协议五层组合（全局声明口径）：工件类别 → 适用层
LICENSE_LAYERS = {
    "code": "AGPL-3.0",            # 软件代码（适配器、脚本、工具链、机检件）
    "server-stack": "SSPL-1.0",    # 服务栈敏感组件（source-available 强约束，不笼统称开源）
    "docs": "CC-BY-SA-4.0",        # 文档与蓝图附件
    "dataset": "ODbL-1.0",         # 数据集
    "governance": "不进许可体系",    # 治理文本：主权人保留终审权
}


def license_layer(artifact_kind):
    """工件类别 → 适用许可层（五层组合）。"""
    return LICENSE_LAYERS.get(artifact_kind, "未分类(须人工核)")


def gpl3_ineligible_note(network_served=True):
    """GPL-3.0 网络服务场景判定：凡经网络提供调用之组件不适格（SaaS 漏洞），须落 AGPL-3.0/SSPL-1.0。"""
    if network_served:
        return "GPL-3.0 不适格（网络服务场景 SaaS 漏洞），须落 AGPL-3.0 或 SSPL-1.0 层"
    return "非网络服务场景，GPL-3.0 可核"


def check_terms(text):
    """术语一致性检查：报违规模糊术语 + 规范术语覆盖。"""
    violations = [t for t in FORBIDDEN_TERMS if t in text]
    covered = [t for t in NORM_TERMS if t in text]
    return {"ok": not violations, "violations": violations,
            "norm_covered": covered, "covered_count": len(covered)}


def check_format(text):
    """格式合规性预检：OTL 章节结构 + 修订记录 + 元数据标记。"""
    issues = []
    if not re.search(r"^#\s+\S", text, re.M):  # 至少一个一级标题
        issues.append("缺一级标题(章节)")
    if "修订记录" not in text and "revision" not in text.lower():
        issues.append("缺修订记录")
    for k in ("目录结构", "附件", "权限设置"):
        if k not in text:
            issues.append("缺元数据标记:%s" % k)
    return {"ok": not issues, "issues": issues}


def match_license(text):
    """开源协议条款匹配：按关键词命中协议。"""
    hits = []
    for name, meta in LICENSES.items():
        if any(k.lower() in text.lower() for k in meta["关键词"]):
            hits.append(name)
    return {"ok": bool(hits), "matched": hits, "note": "未命中则需人工核" if not hits else ""}


if __name__ == "__main__":
    doc = ("# OpenPlanLink 蓝图主文档\n修订记录 v1\n目录结构/附件/权限设置 完整\n"
           "本方案遵循 党组纪律 与 学术技术规范，留痕审计、版本追踪。")
    print("  术语检查 =", check_terms(doc))
    print("  格式预检 =", check_format(doc))
    print("  协议匹配(AGPL) =", match_license("GNU AFFERO GENERAL PUBLIC LICENSE"))
    print("  协议匹配(MIT) =", match_license("MIT License, permission is hereby granted"))
