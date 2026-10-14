---
name: a2a-governance-protocol
type: governance
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要建立、审查或修订多AI席位共治网络的治理协议时
source_files: [GOVERNANCE/a2a/A2A_DISPATCH_AND_PLAN.md, GOVERNANCE/a2a/YANJIAN_ROLE_REGISTRATION.md, AGENTS.md]
---

# A2A治理协议技能

## 概述
建立和维护多AI席位（A2A）共治网络的治理协议，涵盖角色注册、心跳通信、冲突仲裁、分区主权和串行纪律，确保多个AI席位在同一项目中共治不踩踏。

## 适用场景
- 新AI席位加入共治网络时的角色注册与权限分配
- 多席位同时编辑时的冲突检测与仲裁
- 分区主权边界审查（谁有权改哪个目录）
- 串行纪律执行（同一时间只允许一个席位写代码）
- 治理实验设计与执行（HY4协议对齐）

## 执行步骤
1. **角色注册**：新席位提交角色注册文件（含name/persona/capabilities/boundaries），挂帅席审核后准入
2. **心跳建立**：席位间通过CHANGELOG.md和AGENTS.md建立心跳，每次开工前读最后一条
3. **分区主权确认**：明确每个席位的目录主权范围，越界须先在CHANGELOG写明意图并停机主确认
4. **串行纪律执行**：开工前`git status`检查未提交改动，判断归属，干完立即提交+追加CHANGELOG
5. **冲突仲裁**：当两席位产出冲突时，按主权优先级仲裁——目录主权席优先，非主权席回退
6. **治理实验**：设计治理实验时须遵循HY4协议，实验结果记录到GOVERNANCE/相应目录

## 质量门槛
- 每个席位有明确的目录主权范围，无重叠或模糊地带
- 心跳信息包含：谁/何时/改了什么/为什么/遗留什么
- 串行纪律无例外——即使紧急修复也须先检查git status
- 冲突仲裁结果须记录在CHANGELOG.md中
- 治理实验须有明确的假设、度量指标和停止条件

## 经验记录
- 分区主权是防止架构互踩的最有效机制——比代码审查更前置
- CHANGELOG作为交接簿比git log更有效——因为它强制写"为什么"
- 串行纪律的关键不是惩罚越界，而是让越界可见（git status + CHANGELOG）
- 挂帅席（砚坚）不接受角色降格——这是网络稳定性的基石

## 关联文档
- AGENTS.md（项目宪法——分区主权/硬约束/串行纪律）
- GOVERNANCE/a2a/A2A_DISPATCH_AND_PLAN.md（A2A调度与计划）
- GOVERNANCE/a2a/YANJIAN_ROLE_REGISTRATION.md（砚坚角色注册）
- GOVERNANCE/skills/collab/a2a-handshake.md（A2A握手协议技能）