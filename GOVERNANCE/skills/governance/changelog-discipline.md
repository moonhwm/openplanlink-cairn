---
name: changelog-discipline
type: governance
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要规范CHANGELOG追加行为、执行串行纪律或审查交接簿质量时
source_files: [CHANGELOG.md, AGENTS.md]
---

# 交接簿纪律技能

## 概述
规范CHANGELOG.md的追加行为和串行纪律执行，确保多AI席位间的交接信息完整、可追溯、不丢失。CHANGELOG是A2A共治网络的核心通信媒介——比git log更有效，因为它强制写"为什么"。

## 适用场景
- 任何AI席位完成非平凡任务后追加CHANGELOG条目
- 开工前读取CHANGELOG最后一条判断当前状态
- 串行纪律执行（git status + CHANGELOG + commit）
- 交接簿质量审查（条目是否包含五要素）
- 多席位协作时的意图通告与冲突预防

## 执行步骤
1. **开工前**：`git status`检查未提交改动 → 读CHANGELOG最后一条判断归属 → 不明归属则先提交快照
2. **完成任务后**：在CHANGELOG.md追加条目，包含五要素：
   - **谁**：席位名称（如"砚坚（CodeArts GLM-5.2）"）
   - **何时**：真实时间戳（YYYY-MM-DD HH:MM）
   - **改了什么**：具体文件和变更内容
   - **为什么**：变更动机和决策理由
   - **遗留什么**：未完成事项和已知风险
3. **追加验证**：条目格式须以`## YYYY-MM-DD HH:MM · 席位名 · 简述`开头
4. **立即提交**：`git add -A && git commit`，commit message概括变更
5. **验证步骤**：如涉及代码变更，条目须含"如何验证"段（V1-Vn编号）

## 质量门槛
- 每条CHANGELOG条目包含五要素（谁/何时/改了什么/为什么/遗留什么）
- 时间戳为真实时间，不使用相对时间（如"刚才"、"今天"）
- "改了什么"须具体到文件路径和变更类型（新增/修改/删除）
- "为什么"须说明决策理由，不只是描述变更内容
- 代码变更条目须含"如何验证"段
- 条目格式统一：`## YYYY-MM-DD HH:MM · 席位名 · 简述`

## 经验记录
- CHANGELOG作为交接簿比git log更有效——因为它强制写"为什么"
- 最常见的遗漏是"遗留什么"——但这恰恰是下个席位最需要的信息
- "如何验证"段是质量保证的关键——没有验证的变更是不可信的
- 串行纪律的核心不是惩罚越界，而是让越界可见
- 时间戳必须真实——虚假时间戳会破坏交接链

## 关联文档
- CHANGELOG.md（交接簿本体）
- AGENTS.md §三（串行纪律——项目宪法）
- GOVERNANCE/skills/collab/a2a-handshake.md（A2A握手协议——心跳通信）