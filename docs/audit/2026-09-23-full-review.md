# 铃语应用 · 全量代码审查 + 合规走查报告

> 审查人：砚坚（码道·鸿蒙开发智能体 / deepseek-v4-pro-0813）
> 审查时间：2026-09-23 18:40（燃烧窗口内）
> 审查范围：**14 文件**（端侧 8 个 .ets + 云函数 6 个 .js）
> 审查维度：适老化（28-34fp 大字白话）｜三禁（收益承诺/催促指令/对外收费）｜契约（AlertFeed）｜安全合规

---

## 一、审查结论

合规总体**良好**——适老化、三禁、无图表组件均达标，示例卡正确标注。但发现 **2 个高危 fail-open 问题**、**2 个中危问题**、**5 个低危问题**，建议在接入 LLM（双模型切换方案）前完成 P0 加固。

| 级别 | 数量 | 说明 |
|------|------|------|
| 🔴 P0 高危 | 2 | 合规/鉴权 fail-open，接入 LLM 后风险放大 |
| 🟠 P1 中危 | 2 | 契约不同步、凭据硬编码 |
| 🟡 P2 低危 | 5 | 域名过时、类型隐患、无鉴权、边界待确认 |

---

## 二、高危发现（P0，需立即修复）

### H1 — 合规检查 fail-open（fetch-tushare-data）

**位置**：`cloudfunctions/functions/fetch-tushare-data/index.js` L732-778

**问题**：DKnowC 合规检查「只贴标签、不拦截」。当合规检查判断某 signal 卡为 `Unsafe`/`Focus`（non-compliant）时，代码仅 `nonCompliantCount++` 并记日志，**该卡片仍会被保留、生成 TTS、播报、入库**（L799 `saveAlertsToDB(alerts)` 保存的是全量 `alerts`，未过滤 non-compliant）。

```js
// L767-777：只记录，不拦截
if (cr.value.compliant) {
  compliantCount++;
} else {
  nonCompliantCount++;
  console.log(`[compliance] ⚠ NON-COMPLIANT: ...`); // 仅日志
}
```

**风险**：当前 signalNote 是硬编码中性文本，影响有限；但**一旦接入 LLMRouter 生成白话解读**（可能产出"建议买入/满仓"等违规文案），fail-open 意味着合规系统故障时三禁被静默突破。

**修复建议**：non-compliant 的 signal 卡应**降级为 fact**（剥离 signalNote 与自家信号角标）或直接过滤，仅 Safe/ConditionallySafe 放行 signal 形态。

---

### H2 — 广播端点鉴权 fail-open（broadcast-a2a）

**位置**：`cloudfunctions/functions/broadcast-a2a/index.js` L307-315

**问题**：`BROADCAST_API_KEY` 未配置时，鉴权逻辑走 `if (!expectedKey) { console.log('[WARN] ... allowing unauthenticated access') }`——**允许无鉴权访问广播端点**。

```js
const expectedKey = process.env.BROADCAST_API_KEY || '';
if (!expectedKey) {
  console.log('[WARN] ... allowing unauthenticated access'); // fail-open
} else if (apiKey !== expectedKey) {
  res.writeHead(401, ...); return;
}
```

**风险**：生产环境若遗漏 `BROADCAST_API_KEY` 配置，广播端点完全无鉴权暴露，可被任意触发 Push 广播。

**修复建议**：未配置 API Key 时，对非 `/healthz` 路径**默认拒绝**（fail-closed），仅显式声明开放才放行。

---

## 三、中危发现（P1）

### M1 — 契约不同步（signalNote 字段缺失）

**位置**：`entry/src/main/ets/model/AlertItem.ets`（契约）vs `fetch-tushare-data/index.js` L621（服务端产出）

**问题**：服务端 `createAlertItems` 返回 `signalNote`、`pctChg`、`close`、`vol` 字段，但端侧 `AlertItem` 接口仅声明 `alertId/ts/symbol/name/direction/kind/headline/detail/audioUrl/complianceStatus`，**未声明 `signalNote` 字段**。端侧通过 `detail`（L620 已拼接 signalNote）间接展示，但契约未对齐。

**修复建议**：`AlertItem` 契约补 `signalNote?: string`，供未来 LLM 生成的白话解读独立展示（如 signal 卡副标题）。

---

### M2 — 凭据硬编码 fallback（generate-tts）

**位置**：`cloudfunctions/functions/generate-tts/index.js` L19

**问题**：`BAILIAN_WORKSPACE_ID` 硬编码 fallback `'ws-ay6o8osb22o9dc3t'`（真实 workspace ID 落入源码）。虽非密钥本身，但配合 API Key 可定位百炼资源。

**修复建议**：fallback 改为空串，workspace ID 仅从环境变量注入（与 API Key 同策略）。

---

## 四、低危发现（P2）

| 编号 | 位置 | 问题 |
|------|------|------|
| L1 | get-alerts L16 注释 | URL 写 `service.tcloudbase.com/alertsD`（多余 `D` + 已废弃旧域名，应为 `app.tcloudbase.com`） |
| L1b | broadcast-a2a L289 | CORS `allowedOrigins` 用旧域名 `service.tcloudbase.com` |
| L2 | fetch-tushare-data L579/584 | `absPct` 为 `toFixed(2)` 字符串，`absPct >= 8.0` 隐式转数值比较；功能正确但类型不严谨 |
| L3 | push-token-register L80 | 无鉴权，任意 token 可注册进 `push_tokens` 集合 |
| L4 | PushService.ets 全文 | 已从「占位封装」演变为「带降级实装」（getToken/reportToken/receiveMessage 均已实装），**需机主确认是否超越 AGENTS.md §二.4 边界** |
| L5 | init-db L21 | 初始化集合 `alerts/user_stocks/user_preferences/tts_cache` 缺 `push_tokens`（broadcast-a2a/push-token-register 依赖） |

---

## 五、合规通过项（✅ 达标）

| 维度 | 结论 |
|------|------|
| **适老化** | ✅ 字号标准档 34/30/28/22/20/28/18，特大档 40/34/34/26/24/32/20，符合 28-34fp 大字；深色底 `#0d1117` 高对比 |
| **三禁·收益承诺** | ✅ 全文无「保证收益/保本/稳赚」等绝对化措辞 |
| **三禁·催促指令** | ✅ 无「立即买入/满仓/快上车」等强指令 |
| **三禁·对外收费** | ✅ 无对外公开/收费形态 |
| **无图表组件** | ✅ 无 K线/走势图/graph，纯卡片流 |
| **示例卡标注** | ✅ DEMO_ITEMS 明确标「示例」，「首屏永不空白」达标 |
| **signalNote 中性** | ✅ 当前硬编码「留意后续走势/注意风险」属中性提示，不违反三禁 |

---

## 六、修复优先级路线图

```
P0（接入 LLM 前必做，30min）：
  1. H1 合规 fail-closed：non-compliant 降级 fact/过滤
  2. H2 鉴权 fail-closed：未配 Key 默认拒绝

P1（本周）：
  3. M1 契约补 signalNote 字段
  4. M2 凭据 fallback 去硬编码

P2（排期）：
  5. L1/L1b 域名统一 app.tcloudbase.com
  6. L2 absPct 类型改为 number
  7. L3 push-token-register 加轻量鉴权
  8. L4 PushService 边界待机主裁决
  9. L5 init-db 补 push_tokens 集合
```

---

## 七、与 LLMRouter 方案的关系

本报告 H1（合规 fail-open）是**接入双模型切换的强前置**：LLMRouter 生成的 signalNote 是 LLM 产物（非硬编码），合规检查必须 fail-closed 才能守住 AGENTS.md 三禁红线。建议在 `llm-router` 的 `compliance` 任务中直接复用本报告的 fail-closed 结论，将 DKnowC `Unsafe/Focus` 判定为硬拦截。
---

## 八、修复状态追踪（2026-09-23 更新）

| 编号 | 级别 | 问题 | 修复状态 | 修复方式 | Git Commit |
|------|------|------|----------|----------|------------|
| H1 | 🔴 P0 | 合规 fail-open | ✅ 已修复 | non-compliant signal 卡降级为 fact + TTS 跳过降级卡 | `531c772` |
| H2 | 🔴 P0 | 鉴权 fail-open | ✅ 已修复 | 未配 BROADCAST_API_KEY 时返回 503 拒绝 | `531c772` |
| M1 | 🟠 P1 | 契约缺 signalNote | ✅ 已修复 | AlertItem.ets 补 `signalNote?: string` + Index.ets 显示 | `531c772` + `2fc7a80` |
| M2 | 🟠 P1 | 凭据硬编码 fallback | ✅ 已修复 | BAILIAN_WORKSPACE_ID fallback 改空串 | `531c772` |
| L1 | 🟡 P2 | 注释域名错误 | ✅ 已修复 | service→app.tcloudbase.com | `531c772` |
| L1b | 🟡 P2 | CORS 旧域名 | ✅ 已修复 | allowedOrigins 域名修正 | `531c772` |
| L2 | 🟡 P2 | absPct 字符串隐式比较 | ⏳ 待修复 | 功能正确，类型不严谨，低优先级 | — |
| L3 | 🟡 P2 | push-token-register 无鉴权 | ✅ 已修复 | 加 ALLOWED_BUNDLE_NAMES 白名单 | `5e292e9` |
| L4 | 🟡 P2 | PushService 超占位边界 | ✅ 已判定 | AGC 已配置，实装合理，不需回退 | `5e292e9` |
| L5 | 🟡 P2 | init-db 缺 push_tokens | ✅ 已修复 | collections 补 push_tokens | `5e292e9` |

**总计：9 项发现，8 项已修复/判定，1 项待修复（L2 低优先级）**

### 端侧增强（审查外发现）
- Index.ets 卡片流新增 signalNote 白话解读显示（金色字体，与 fact 卡区分）—— commit `2fc7a80`

### 遗留
- 端侧 HAP 未重新构建（中文路径 + build-profile.json5 配置 + 项目结构需升级，需 DevEco Studio 操作）
- L2 absPct 类型改为 number（低优先级，功能正确）