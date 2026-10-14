---
name: HarmonyOS构建问题诊断
type: diag
created: 2026-09-19
updated: 2026-09-19
version: 1.0.0
trigger: HarmonyOS项目构建失败或出现编译错误时
source_files: []
---

# HarmonyOS构建问题诊断

## 概述
诊断和修复HarmonyOS项目构建问题的技能，覆盖hvigor构建工具链、devecocli命令行工具、ArkTS编译器等常见问题。

## 适用场景
- hvigor构建失败（编译错误/依赖问题/路径问题）
- devecocli命令执行失败
- ArkTS语法/类型错误
- 模拟器启动失败
- HAP安装失败

## 执行步骤
1. **收集错误信息**：读取构建日志（.hvigor/outputs/build-logs/build.log）的最后200行
2. **分类错误类型**：
   - 编译错误（ArkTS语法/类型不匹配）→ 检查源码
   - 路径错误（中文路径/空格路径）→ 检查项目路径
   - 依赖错误（ohpm install失败）→ 检查oh-package.json5
   - 签名错误（证书/密钥不匹配）→ 检查build-profile.json5签名配置
3. **定位根因**：根据错误类型定位具体根因
4. **制定修复方案**：针对根因制定修复方案
5. **执行修复**：修改代码/配置/路径
6. **验证修复**：重新构建验证修复效果
7. **记录经验**：将诊断过程和修复方案记录到技能文档

## 质量门槛
- 错误信息完整收集（不遗漏关键日志行）
- 根因分析准确（不停留在表面症状）
- 修复方案不引入新问题
- 修复后构建通过

## 经验记录
- hvigor不允许项目路径含中文字符（详见memory/project-hvigor-no-chinese-path.md）
- 编译副本需放在纯英文路径（如A:/DevEcoStudio/harmony-app/）
- Windows下优先使用PowerShell而非Git Bash（路径解析问题）
- devecocli未找到时可通过npm install -g @deveco/deveco-cli安装
- build-profile.json5中的signingConfig可能导致签名失败，可移除后构建unsigned HAP

## 关联文档
- AGENTS.md（项目宪法/硬约束）
- .codeartsdoer/.codebase/branches/master/docs/project-knowledge/build_system/build_system.md（构建系统Wiki）
- GOVERNANCE/skills/FORMAT_SPEC.md（技能文档格式规范）