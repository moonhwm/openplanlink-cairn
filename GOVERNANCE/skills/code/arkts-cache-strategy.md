# code技能：ArkTS多层缓存策略

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：harmony-app项目中所有涉及缓存的代码（云函数+端侧）

## 1. 缓存架构设计原则

### 三层缓存模型

```
L1 内存缓存（同一次函数调用内复用）
  ↓ miss
L2 持久化缓存（CloudBase存储，跨函数调用复用）
  ↓ miss/expired
L3 数据源（外部API）
  ↓ fail
L2-stale（过期持久化缓存作为降级）
  ↓ miss
L4 硬编码fallback（静态数据）
  ↓ miss
空值兜底
```

## 2. fetch-tushare-data缓存实例

### 股票名称映射缓存（6层降级链）

```javascript
// L1: 内存缓存（24小时TTL）
if (cachedNameMap && (Date.now() - cachedNameMapTs) < NAME_MAP_CACHE_TTL) {
  return cachedNameMap;
}

// L2: CloudBase存储缓存（24小时TTL）
const result = await app.downloadFile({ cloudPath: 'stock-names/name-map.json' });
if (stored && stored.names && age < NAME_MAP_CACHE_TTL) {
  return new Map(Object.entries(stored.names));
}

// L2-stale: 过期存储缓存作为降级预备（不return，继续尝试刷新）
if (age >= NAME_MAP_CACHE_TTL) {
  cachedNameMap = new Map(Object.entries(stored.names)); // 加载到内存
  cachedNameMapTs = Date.now();
  // 不return，继续尝试L3
}

// L3: 东方财富API（4市场并行刷新）
const fresh = await fetchNameMapFromEastMoney();
if (fresh.size > 0) {
  // 异步回写到L2（不阻塞返回）
  await persistNameMap(fresh);
  return fresh;
}

// L2-stale fallback: 刷新失败时内存缓存已是过期数据
if (cachedNameMap) return cachedNameMap;

// L4: 硬编码5560条fallback
const hardcoded = require('./hardcoded-names');
return new Map(Object.entries(hardcoded));

// 空值兜底
return new Map();
```

### 交易日缓存（3层降级链）

```javascript
// L1: 内存缓存（1小时TTL）
if (cachedTradeDate && (Date.now() - cachedTradeDateTs) < TRADE_DATE_CACHE_TTL) {
  return cachedTradeDate;
}

// L2: Tushare trade_cal API
const tradeCal = await callTushare('trade_cal', params, 'cal_date');
return tradeCal.items[0][0];

// L3: 当前日期推算（工作日=今天，周末=最近周五）
```

### alerts.json缓存（并发写入保护）

```javascript
// 读取 → 检查并发冲突 → 合并去重 → 写入
const existing = await app.downloadFile({ cloudPath: 'alerts/alerts.json' });

// 并发写入保护：如果现有数据更新，跳过
if (existingServerTs > currentLatestTs) return;

// 按 alertId 去重合并
const alertMap = new Map();
for (const item of existingItems) alertMap.set(item.alertId, item);
for (const alert of alerts) alertMap.set(alert.alertId, alert);

// 保留最新500条
const allItems = Array.from(alertMap.values())
  .sort((a, b) => b.ts - a.ts)
  .slice(0, 500);
```

## 3. TTL设置规范

| 缓存项 | L1 TTL | L2 TTL | 理由 |
|--------|--------|--------|------|
| 股票名称映射 | 24h | 24h | 股票名称极少变化 |
| 交易日 | 1h | N/A | 盘中不变，但跨日需刷新 |
| alerts.json | 不缓存 | 实时读写 | 数据时效性要求高 |
| TTS音频 | 不缓存 | 永久（SHA256键） | 相同文本音频不变 |

## 4. 缓存一致性保障

### 写入后更新内存缓存

```javascript
// 刷新成功后同步更新内存缓存
cachedNameMap = freshMap;
cachedNameMapTs = Date.now();
```

### 过期缓存先加载再刷新

```javascript
// 关键修复：过期数据先加载到内存作为降级预备
// 刷新失败时内存缓存已是fallback，不会返回空值
if (age >= NAME_MAP_CACHE_TTL) {
  cachedNameMap = new Map(Object.entries(stored.names));
  cachedNameMapTs = Date.now();
  // 不return，继续尝试刷新
}
```

### 异步回写不阻塞返回

```javascript
// 刷新成功后异步回写到CloudBase存储
// 即使回写失败也不影响当前返回
try {
  await app.uploadFile({
    cloudPath: 'stock-names/name-map.json',
    fileContent: Buffer.from(JSON.stringify(nameObj), 'utf-8'),
  });
} catch (e) {
  console.log('Failed to persist name map:', e.message);
}
```

## 5. generate-tts缓存设计

### SHA256缓存键

```javascript
function getCacheKey(text) {
  return crypto.createHash('sha256').update(text).digest('hex').substring(0, 16);
}
```

### 缓存命中流程

```
1. 计算文本SHA256前16位 → cacheKey
2. 查询CloudBase存储 tts-cache/{cacheKey}.json
3. 命中 → 返回缓存的audioUrl，更新alerts.json
4. 未命中 → 调用百炼WebSocket生成音频
5. 生成成功 → 上传音频到tts/{cacheKey}.mp3
6. 保存缓存元数据到tts-cache/{cacheKey}.json
7. 更新alerts.json中对应alertId的audioUrl
```

---

*本技能文档由砚坚席位于2026-09-23编写，基于fetch-tushare-data多层缓存架构实战经验提炼。*