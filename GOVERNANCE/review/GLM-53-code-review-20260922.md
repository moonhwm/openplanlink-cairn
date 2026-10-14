# 铃语App 代码全量审查报告（GLM-5.3-Flash 1亿Tokens燃烧 · 第一档①）

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-22（窗口生效期）
> 范围：entry/src/main/ets 全部8个文件 + cloudfunctions/functions 全部6个云函数
> 基线：AR-001 对抗性审查（已归档）

---

## 一、审查范围

| 模块 | 文件 | 行数 | 结论 |
|------|------|------|------|
| 端侧服务 | AudioPlayer.ets | 64 | ✅ 通过 |
| 端侧服务 | AlertPoller.ets | 100 | ✅ 通过 |
| 端侧服务 | PushService.ets | 107 | ✅ 通过（占位封装合规） |
| 端侧服务 | SettingsService.ets | 456 | ✅ 通过 |
| 端侧页面 | Index.ets | 458 | ✅ 通过 |
| 端侧页面 | Settings.ets | 557 | ⚠️ 1项低危 |
| 端侧模型 | AlertItem.ets | 22 | ✅ 通过 |
| 端侧入口 | EntryAbility.ets | 123 | ✅ 通过 |
| 云函数 | get-alerts/index.js | 76 | ⚠️ 1项低危 |
| 云函数 | push-token-register/index.js | 95 | ⚠️ 2项（含已知S-2） |
| 云函数 | init-db/index.js | 61 | ⚠️ 1项低危 |
| 云函数 | generate-tts/index.js | 403 | ✅ 通过 |
| 云函数 | broadcast-a2a/index.js | 290 | 🔴 2项高（表名错误+无鉴权） |
| 云函数 | fetch-tushare-data/index.js | 675 | ⚠️ 2项低危 |

---

## 二、发现清单

### 🔴 高危（2项）

**F-001 【broadcast-a2a】Supabase 表名错误导致广播静默失败**
- 文件：broadcast-a2a/index.js:60
- 现状：`POST ${SUPABASE_URL}/rest/v1/a2a_messages`
- 实际：A2A 总线表名为 `cross_mode_channel`（已实测确认）
- 影响：广播写库一直 404（PGRST205），A2A 总线未收到 alerts 流
- 修复：改为 `cross_mode_channel`，同时补 `to_mode`/`from_mode`/`kind` 等字段以满足收件面路由
- 优先级：**P1**

**F-002 【broadcast-a2a】HTTP 模式无鉴权 + CORS 全开**
- 文件：broadcast-a2a/index.js:262-263
- 现状：`res.setHeader('Access-Control-Allow-Origin', '*')`，HTTP GET 任意人可触发广播+推送
- 影响：任何人可调用端点造成 Push 骚扰/信息泄露
- 修复：加 API Key 校验（query/header），CORS 收敛域名
- 优先级：**P1**（与 AR-001 S-2 属同一族）

### ⚠️ 中/低危（5项）

**F-003 【get-alerts】downloadFile 参数混用**
- 文件：get-alerts/index.js:32-33
- 现状：`app.downloadFile({ fileID: ALERTS_FILE_ID })`（fileID 格式）
- 对比：fetch-tushare-data/generate-tts 均用 `cloudPath` 参数
- 风险：两种调用方式在不同 SDK 版本行为可能不一致；若 fileID 过期/迁移则读取失败
- 建议：统一用 `cloudPath: 'alerts/alerts.json'`
- 优先级：P2

**F-004 【Settings.ets】FEED_URL 无格式校验**
- 文件：Settings.ets:514-530
- 现状：保存任意字符串，不校验是否为合法 http(s) URL
- 影响：老人误输入后轮询持续失败且难排查
- 建议：saveFeedUrl 前校验 `^https?://`，非法则 toast 提示
- 优先级：P2

**F-005 【fetch-tushare-data】注释错别字**
- 文件：fetch-tushare-data/index.js:508
- 现状：注释"说明另一个实例已经写入了更新的4更新的数据"
- 影响：仅可读性
- 修复：改为"说明另一个实例已写入更新的数据"
- 优先级：P3

**F-006 【push-token-register】无鉴权 + 集合未预热**
- 文件：push-token-register/index.js + init-db/index.js:15
- 现状：①HTTP 端点无鉴权（已知 AR-001 S-2）；②`push_tokens` 集合未在 init-db 的集合清单中（依赖首次 add 自动创建）
- 影响：任何人可上报假 token 污染推送列表；集合自动创建在首次并发写时可能失败
- 建议：init-db 集合清单补 `push_tokens`；鉴权待 AGC P5 后实施
- 优先级：P3（鉴权）/ P2（集合预热）

**F-007 【Index.ets】DEMO_ITEMS detail 提及"示例"但 headline 已有"示例"**
- 文件：Index.ets:13-23
- 现状：headline="示例：中国巨石…" + detail="示例数据…" 双重标注
- 影响：低，双向保障首屏不误导（符合§二.5）
- 结论：保留，无需改
- 优先级：无需处理

---

## 三、确认无问题的关键点

1. **适老化硬约束** ✅：全代码无 K线/走势图/图表组件，字号 28-40fp，卡片流，点卡即听
2. **信号松绑三禁** ✅：signalNote 仅"留意后续走势/注意风险"，无收益承诺/催促指令/公开收费
3. **首屏永不空白** ✅：DEMO_ITEMS 兜底 + isDemoMode 状态机
4. **PushService 占位** ✅：AGC 未配置自动降级轮询，未展开实装（符合 README「推送实装」）
5. **P2 并发写入保护** ✅：serverTs 版本号比对已修复 3 处拼写错误
6. **DKnowC 合规层** ✅：并行检查+complianceStatus 字段+非阻断
7. **冷启动/后台拉起** ✅：onCreate/onNewWant/onPageShow 三重补检
8. **防连击/失败重试** ✅：loadingId/failedId 状态机完整

---

## 四、修复建议分级汇总

| 发现 | 优先级 | 建议动作 |
|------|--------|---------|
| F-001 表名错误 | P1 | 立即修复并重部署 broadcast-a2a |
| F-002 无鉴权+CORS | P1 | 加API Key校验+CORS收敛 |
| F-003 fileID/cloudPath | P2 | 统一 cloudPath |
| F-004 FEED_URL校验 | P2 | 保存前校验格式 |
| F-005 注释错别字 | P3 | 顺手修 |
| F-006 push_tokens预热 | P2/P3 | init-db补集合；鉴权待P5 |

---

## 五、执行记录

| 时间 | 完成项 |
|------|--------|
| 2026-09-22 | 全部14文件审查完成，报告成文 |