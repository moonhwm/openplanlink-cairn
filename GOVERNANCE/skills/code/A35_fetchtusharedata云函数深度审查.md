---
name: A35_fetchtusharedata云函数深度审查
description: fetch-tushare-data云函数逐行审查，发现并修复P0级旧代码残留BUG
type: code
---

# A35 — fetch-tushare-data 云函数深度审查

## 审查范围

`cloudfunctions/functions/fetch-tushare-data/index.js`（716行，修复后694行）

## 发现的问题

### P0（已修复）: getStockNameMap 旧串行代码残留

**位置**: 原第234-256行（修复后已删除）

**现象**: `Promise.all` 并行化改造后，旧串行循环代码未清理。第234行 `const stocks = data.data.diff;` 引用不存在的 `data` 变量（该作用域中只有 `marketResults`），导致东方财富刷新路径**总是抛 ReferenceError 走 fallback**。

**影响**: 股票名称映射的实时刷新路径完全失效，只能依赖过期缓存或硬编码映射。用户看到的异动卡片中股票名称可能不准确或缺失。

**修复**: 删除第234-256行的旧串行循环残留代码（22行）。并行化后的正确逻辑（第228-233行）已经通过 `for (const marketMap of marketResults)` 遍历合并结果，无需旧代码。

**根因**: P1-1 东方财富分页并行化改造时，新代码（`Promise.all` + `fetchEastMoneyMarket`）插入在旧代码之前，但旧代码未删除。代码审查时只验证了新代码的正确性，未检查旧代码是否已清理。

**教训**: 重构改造时，新旧代码并存期间应使用 TODO 标记或注释明确标注待删除区域，避免遗漏。

### P2（不修复）: requestHttps 重复定义

`requestHttps` 函数在 fetch-tushare-data 和 broadcast-a2a 中各自定义了一份。应提取为共享模块（如 `shared/requestHttps.js`），但当前云函数部署架构下共享模块需要额外配置，暂不修复。

### P2（不修复）: getCloudbaseApp 重复定义

`getCloudbaseApp()` 在全部6个云函数中重复定义。同上理由暂不修复。

### P3（已修复）: 第286行缩进不一致

注释 `// 最终 fallback` 缺少2空格缩进，与上下文不一致。已修复。

## 架构审查

### 数据流

```
Tushare API (daily) ──→ getDailyMovers() ──→ createAlertItems() ──→ saveAlertsToDB()
                                                    │
东方财富 API ──→ getStockNameMap() ────────────────┘ (名称补充)
                                                    │
DKnowC API ──→ checkCompliance() ──→ complianceStatus 元数据
                                                    │
generate-tts 云函数 ──→ TTS音频 ──→ audioUrl 字段
```

### 缓存层级

1. 内存缓存（24h TTL）—— `cachedNameMap` / `cachedTradeDate`
2. CloudBase 存储缓存—— `stock-names/name-map.json`（跨调用持久化）
3. 硬编码映射—— `hardcoded-names.js`（5560条，最终fallback）
4. 空 Map—— 绝对最终fallback

### 安全审查

- ✅ Tushare token 脱敏：`callTushare` error message 中 `TUSHARE_TOKEN` 被 `***` 替换
- ✅ DKnowC API Key 未在日志中输出
- ✅ 合规检查不阻塞流程（失败时 `skipped: true`，默认放行）
- ✅ 信号松绑三禁遵守：信号卡只输出"留意后续走势"/"注意风险"，无承诺收益/催促指令
- ✅ alertId 确定性格式：`${symbol}_${now}`（之前已修复碰撞问题）

### 并发保护

- ✅ `saveAlertsToDB` 有并发写入保护：比较 `existingServerTs` 与 `currentLatestTs`
- ✅ TTS 生成使用 `Promise.allSettled`（失败不阻塞）
- ✅ 合规检查使用 `Promise.allSettled`（失败不阻塞）

## 验证步骤

- V1: grep 确认 `data.data.diff` 在 `getStockNameMap` 函数体内不再出现（只在 `fetchEastMoneyMarket` 内出现）
- V2: 确认 `Promise.all` + `for...of marketResults` 逻辑完整闭合
- V3: 确认 `fetchEastMoneyMarket` 函数返回 `Map`，`getStockNameMap` 正确合并
- V4: 确认三禁合规：grep "承诺|保本|立即|满仓" 无命中
- V5: git diff 确认只删除了旧代码残留，未改动新代码逻辑