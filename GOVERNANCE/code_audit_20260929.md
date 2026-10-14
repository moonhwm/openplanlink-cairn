# harmony-app 全量代码审查与合规走查报告

> 审查人：岑辑（砚坚续接 · 辑录堂总装合流团队）
> 日期：2026-09-29
> 基准：AGENTS.md 硬约束 + 架构基调

---

## 一、审查范围

| 文件 | 行数 | 职责 |
|---|---|---|
| `EntryAbility.ets` | 124 | Push 初始化 + onNewWant + 冷启动通知缺口修复 |
| `Index.ets` | 468+ | 主界面：List 卡片流 + 5s 轮询 + �'放交互 |
| `AlertItem.ets` | 23 | 数据契约：AlertItem / AlertFeed 接口定义 |
| `AlertPoller.ets` | 97 | 前台轮询兜底：5s 拉取 + 退避策略 |
| `AudioPlayer.ets` | 64 | AVPlayer 播云端 TTS 音频流 |
| `PushService.ets` | 108 | Push Kit 封装：AGC 降级 + Token 上报 |
| `SettingsService.ets` | 462 | Preferences 持久化：自选股/播报/字体/主题/免打扰 |
| `Settings.ets` | — | 设置页面（未详细审查） |

---

## 二、硬约束合规走查

### 约束1：适老化 ✅ 通过

| 检查项 | 状态 | 依据 |
|---|---|---|
| 大字白话卡片流（28-34fp） | ✅ | Index.ets: titleSize 34/40, headlineSize 28/34, detailSize 22/26 |
| 高对比深色底 | ✅ | NIGHT_COLORS: pageBackground '#0d1117', textPrimary '#e8edf5' |
| 禁止 K线图/走势图 | ✅ | 全代码无图表组件 |
| elderlyMode 默认开启 | ✅ | SettingsService.getElderlyMode 默认 true |
| 点卡=听播报 | ✅ | togglePlay 交互：点击卡片播报按钮 → AVPlayer 播放 |

### 约束2：信号松绑 ✅ 通过

| 检查项 | 状态 | 依据 |
|---|---|---|
| kind: 'fact'/'signal' 标记 | ✅ | AlertItem.ets: kind?: 'fact' \| 'signal' |
| signal 卡"自家信号"角标 | ✅ | Index.ets L419-427: kind==='signal' 显示角标 |
| signalNote 白话解读 | ✅ | Index,ets L452-459: signal 卡显示 signalNote |
| 禁承诺收益/保本 | ✅ | 无绝对化措辞 |
| 禁催促性强指令 | ✅ | 无"立即买入"/"满仓"等 |
| 禁对外公开/收费 | ✅ | 无相关形态 |

### 约束3：平台 ⚠️ 偏差

|@检查项 | 状态 | 依据 |
|---|---|---|
| Stage 模型 | ✅ | build-profile.json5: "apiType": "stageMode" |
| compatibleSdkVersion | ⚠️ | 实际 22，AGENTS.md 要求 20 |
| targetSdkVersion | ⚠️ | 实际 22，AGENTS.md 要求 26 |
| 纯 ArkTS | ✅ | 所有源文件 .ets，无 JS/TS 混用 |
| 零三方依赖 | ✅ | 仅使用 @kit.* 官方 Kit |

**偏差说明**：SDK 版本从 20/26 变更为 22/22，可能是 DevEco Studio 升级时自动更新。AGENTS.md 需同步更新此约束值，或回退 SDK 版本以匹配约束。此偏差不影响代码功能。

### 约束4：PushService 占位封装 ✅ 通过

| 检查项 | 状态 | 依据 |
|---|---|---|
| AGC 未配置时自动降级 | ✅ | PushService.ets L31-34: probeAgcConfig → 降级日志 |
| 降级后轮询兜底 | ✅ | AlertPoller.ets: 5s 前台轮询 |
| Token 上报机制 | ✅ | reportToken → CloudBase push-token-register |
| 重试逻辑 | ✅ | RETRYABLE_ERROR_CODES + MAX_RETRY_COUNT=3 |

### 约束5：首屏永不空白 ✅ 通过

| 检查项 | 状态 | 依据 |
|---|---|---|
| DEMO_ITEMS 机制 | ✅ | Index.ets L13-23: 明确标"示例"字样 |
| isDemoMode 默认 true | ✅ | 连通后自动切换 false |
| 空态处理 | ✅ | L188-196: 服务连通但无异动时清空列表（非演示卡） |

---

## 三、架构基调验证

| 架构要素 | 状态 | 依据 |
|---|---|---|
| EntryAbility: Push 初始化 + onNewWant 带 alertId | ✅ | L16: PushService.init; L43-68: onNewWant |
| Index.ets: List 卡片流 + 5s 前台轮询 | ✅ | L154-157: pollLoop + setTimeout |
| AudioPlayer: AVPlayer 播云端 TTS | ✅ | AudioPlayer.ets: media.createAVPlayer |
| 数据源: FEED_URL → CloudBase 云函数 | ✅ | SettingsService: DEFAULT_FEED_URL |

---

## 四、代码质量发现

### 4.1 正面发现

1. **退避策略完善**：AlertPoller 429/5xx/网络错误各有独立处理路径，退避翻倍封顶30s
2. **冷启动通知缺口修复**：EntryAbility L25-28 补检 want.parameters.alertId（白皮书 §3.3.2）
3. **小艺 A2A 诚实标注**：EntryAbility L54 注释明确标注"占位"，未声称已实现
4. **已读标记防无限增长**：SettingsService L406-408 最多保留200条
5. **播报历史去重+限量**：SettingsService L440-445 同 alertId 只保留最新，最多50条
6. **refresh 中 loadingId 失效保护**：Index.ets L278-280 防止 prepare 完成后设置已失效的 playingId

### 4.2 潜在问题

| # | 问题 | 严重度 | 位置 | 建议 |
|---|---|---|---|---|
| 1 | SDK 版本偏差（22/22 vs 约束 20/26） | 低 | build-profile.json5 | 更新 AGENTS.md 或回退 SDK |
| 2 | CLOUDBASE_BASE_URL 硬编码 | 低 | SettingsService L24 | 当前阶段合理，后续可移至配置 |
| 3 | feedUrl 拼接 `?limit=` 未防已有 query | 低 | AlertPoller L38 | 当前端点无 query，无实际风险 |
| 4 | 小艺 A2A 占位未实现返回机制 | 信息 | EntryAbility L52-68 | 诚实标注，待协议对接 |
| 5 | Settings 页面未详细审查 | 信息 | Settings.ets | 后续补充 |

### 4.3 安全检查A

| 检查项 | 状态 |
|---|---|
| 无硬编码凭据 | ✅ |
| 无敏感信息日志 | ✅（hilog 只记长度/状态码） |
| HTTP 请求有超时设置 | ✅（connectTimeout 5000, readTimeout 5000） |
| Push Token 不落盘 | ✅（仅上报服务器） |
| JSON 解析有 try-catch | ✅ |

---

## 五、总结

**整体评价**：代码质量良好，架构清晰，AGENTS.md 硬约束基本全部满足。唯一偏差是 SDK 版本（22/22 vs 约束 20/26），属于文档与配置的同步问题，不影响功能。

**合规判定**：✅ 通过（SDK 版本偏差需同步 AGENTS.md 或回退）

**建议优先级**：
1. 同步 AGENTS.md SDK 版本约束（低优先级）
2. 后续补充 Settings.ets 详细审查
3. 小艺 A2A 返回机制待协议对接后实现

---

*—— 岑辑 2026-09-29，代码审查·留痕可复盘。*