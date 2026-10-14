---
name: HarmonyOS ArkTS适老化开发
type: code
created: 2026-09-19
updated: 2026-09-19
version: 1.0.0
trigger: 需要编写HarmonyOS ArkTS代码，特别是适老化UI组件时
source_files: [entry/src/main/ets/pages/Index.ets, entry/src/main/ets/pages/Settings.ets]
---

# HarmonyOS ArkTS适老化开发

## 概述
在HarmonyOS NEXT平台上使用ArkTS开发适老化语音提醒应用的代码编写技能，核心约束是大字白话卡片流（28-34fp高对比深色底），禁止引入K线图/走势图等复杂图表组件。

## 适用场景
- 编写适老化UI页面（大字卡片流、高对比深色底）
- 编写ArkTS服务层代码（轮询、音频播放、推送封装）
- 编写HarmonyOS Stage模型入口能力
- 编写数据契约定义（AlertItem/AlertFeed）

## 执行步骤
1. **确认硬约束**：阅读AGENTS.md §二确认适老化约束（28-34fp、禁止K线、点卡即听）
2. **确认架构基调**：阅读AGENTS.md §四确认架构基调（EntryAbility→Index→AlertPoller→AudioPlayer）
3. **确认平台约束**：Stage模型、compatibleSdkVersion 20、targetSdkVersion 26、纯ArkTS、零三方依赖
4. **编写代码**：按架构基调编写代码，确保符合硬约束
5. **验证约束**：检查字体大小≥28fp、无复杂图表、首屏永不空白
6. **提交变更**：git add -A && git commit，CHANGELOG追加条目

## 质量门槛
- 字体大小≥28fp（适老化硬约束）
- 无K线图/走势图等复杂图表组件
- 首屏永不空白（服务未连通时显示示例卡）
- 零三方依赖（仅用@kit.*官方Kits）
- PushService保持占位封装（AGC未配置前自动降级轮询）

## 经验记录
- hvigor不允许项目路径含中文字符，需纯英文路径构建（详见memory/feedback-powershell-over-gitbash.md）
- Windows下Git Bash路径解析有问题，执行命令应优先使用PowerShell
- router.pushUrl/back在Stage模型中会产生WARN，应使用Navigation+NavDestination替代
- AVPlayer的prepare/play可能reject，需清理半初始化player并调用onError回调
- AlertPoller的429限流应静默返回rateLimited=true，不计入连接中断

## 关联文档
- AGENTS.md（项目宪法/硬约束/架构基调）
- .codeartsdoer/.codebase/branches/master/docs/codebase-knowledge/（Wiki模块文档）
- GOVERNANCE/SELF_EVOLUTION_PLAN_v2.md（自主进化方案）