---
name: fail-open-fix
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 代码审查发现 fail-open 安全漏洞（合规检查/鉴权/降级逻辑只贴标签不拦截），需要修复为 fail-closed
source_files: [cloudfunctions/functions/fetch-tushare-data/index.js, cloudfunctions/functions/broadcast-a2a/index.js]
---

# Fail-Open 修复技能

## 概述
识别和修复云函数中的 fail-open 安全漏洞——即合规检查、鉴权、降级逻辑在异常或未配置时"放行而非拦截"的设计缺陷。修复目标是将所有 fail-open 路径转为 fail-closed（默认拒绝），确保系统在异常状态下仍守住安全边界。

## 适用场景
- 合规检查只贴标签不拦截（non-compliant 内容仍被保存/播报）
- 鉴权逻辑在未配置 Key 时允许无鉴权访问
- 降级逻辑在检查失败时保留原始危险内容而非降级为安全形态
- 任何"异常时放行"的设计模式审查

## 执行步骤
1. **识别 fail-open 路径**：搜索 `|| ''`、`|| '默认值'`、`if (!expectedKey)`、`console.log('[WARN]` 等模式，定位所有"异常时放行"的代码路径
2. **评估影响范围**：fail-open 路径的下游影响——保存到 DB？生成 TTS？对外暴露 HTTP 端点？触发 Push 广播？
3. **设计 fail-closed 修复**：
   - 合规检查：non-compliant 内容降级为安全形态（如 signal → fact），剥离敏感字段
   - 鉴权：未配置 Key 时返回 503/403 拒绝，而非允许
   - 降级联动：降级后的内容必须跳过下游危险操作（如 TTS 生成、播报）
4. **验证修复**：`node -c` 语法验证 + 重新部署云函数 + 逻辑走查
5. **更新审查报告**：在审查报告中标记修复状态和 git commit

## 质量门槛
- 所有 fail-open 路径必须转为 fail-closed（无例外）
- 降级后的内容必须联动跳过下游操作（仅降级不跳过 = 半修复）
- 未配置凭据时必须返回错误码（503/403），而非允许访问
- 修复后必须重新部署受影响的云函数
- 语法验证必须通过（`node -c`）

## 经验记录
- **fail-open 是云函数最高危模式**：合规检查"只贴标签不拦截"等于没有合规检查；鉴权"未配Key时允许访问"等于没有鉴权。接入 LLM 后风险放大
- **合规降级必须联动 TTS 跳过**：signal 卡被降级为 fact 后，TTS 循环必须跳过该卡（不设置 audioUrl），否则降级卡仍会播报白话解读，合规闸门形同虚设
- **端侧场景鉴权用 bundleName 白名单优于 API Key**：API Key 需在端侧硬编码（不安全），bundleName 白名单由系统签名保证不可伪造
- **fail-closed 修复必须同时处理"降级"和"跳过"两个环节**：只降级不跳过 = 下游仍处理危险内容；只跳过不降级 = 上游仍保留危险标记

## 关联文档
- docs/audit/2026-09-23-full-review.md（全量审查报告，含 H1/H2 fail-open 发现）
- AGENTS.md §二.2（信号松绑三禁——fail-closed 是三禁的技术保障）
- GOVERNANCE/skills/diag/full-code-review.md（全量代码审查技能）