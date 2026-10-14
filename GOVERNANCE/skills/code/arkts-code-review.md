---
name: arkts-code-review
type: code
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要对端侧ArkTS代码进行系统性审查时
source_files: [entry/src/main/ets/]
---

# 端侧ArkTS代码审查技能

## 概述
对HarmonyOS端侧ArkTS代码进行系统性审查的技能，覆盖8个维度：适老化合规、架构一致性、状态管理、网络请求、错误处理、资源管理、安全性和性能。审查产出分级问题清单（P0/P1/P2）和修复方案。

## 适用场景
- 端侧代码定期审查（每轮迭代后）
- 新功能上线前的质量把关
- AGENTS.md硬约束合规性检查
- 跨席位交接前的代码走查

## 执行步骤
1. **文件清单确认**：列出entry/src/main/ets/下所有.ets文件，确认审查范围
2. **逐文件审查**：按8个维度审查每个文件：
   - 适老化合规：字号28-34fp、无复杂图表、大字白话卡片流
   - 架构一致性：与AGENTS.md架构基调对齐
   - 状态管理：@State/@Prop/@Link使用正确、状态流转无错乱
   - 网络请求：http.createHttp()使用正确、超时设置、req.destroy()在finally中
   - 错误处理：catch带参数、降级路径、用户提示
   - 资源管理：AVPlayer/Preferences/Http等资源正确释放
   - 安全性：无硬编码凭据、TLS验证、输入校验
   - 性能：List虚拟化、防连击、退避策略
3. **合规性检查**：对照AGENTS.md硬约束逐条验证
4. **问题分级**：P0=影响功能/安全；P1=影响维护性/效率；P2=锦上添花
5. **修复实施**：按P0→P1→P2顺序修复
6. **验证修复**：grep确认修复点、确认无回归

## 质量门槛
- 审查覆盖全部.ets文件，无遗漏
- 每个问题标注文件路径和行号
- 修复方案可执行且有验证方法
- AGENTS.md硬约束逐条通过/不通过判定
- 修复后grep验证无残留

## 经验记录
- FEED_URL等常量在多文件重复硬编码是最常见的维护性问题——应提取为共享常量
- Settings.ets的navStack通过NavDestination.onReady回调获取（context.pathStack），不是BUG——这是ArkTS Navigation的正确模式
- AudioPlayer的AVPlayer事件监听器在release后自动清理，无需显式off——但显式off更安全
- ArkTS中catch必须带参数（catch (e)），不允许catch {}无参写法——已在R2修复
- PushService.ets的probeAgcConfig使用getRawFileContentSync（同步方法），但rawFile很小（几KB），影响可忽略

## 关联文档
- AGENTS.md（项目宪法——硬约束/架构基调）
- GOVERNANCE/skills/code/arkts-cloud-function-pattern.md（云函数模式技能）
- GOVERNANCE/skills/code/arkts-network-wrapper.md（网络封装技能）
- GOVERNANCE/skills/code/arkts-cache-strategy.md（缓存策略技能）