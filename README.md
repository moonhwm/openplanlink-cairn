# 铃语（StockPulse）· 鸿蒙 NEXT 私有分发工程

适老化语音提醒 App。**云端（X 服务器）秒级监测 → Push Kit 推送 → 锁屏大字通知 → 点按拉起 → 自动语音播报**。只报客观异动事实，不含任何买卖建议。

> 应用显示名「铃语」（典出苏轼塔铃：铃先响，风将至），bundleName `com.yehang.stockpulse` 保持不变（AGC 注册锚）。

- 目标机型：Mate X5（HarmonyOS NEXT 纯血）；`compatibleSdkVersion 6.0.2(22)` / `targetSdkVersion 6.0.2(22)`
- 形态：原生 ArkTS Stage 模型，单 entry 模块，零三方依赖
- 分发：私有调试证书直装（免审核免软著免备案零公开，100 台/年）

## 目录结构

```
AppScope/                     应用级配置（bundleName=com.yehang.stockpulse）
entry/src/main/ets/
  entryability/EntryAbility   Push 初始化 + Settings 初始化 + 通知点击带 alertId 拉起
  pages/Index.ets             大字异动卡片流，点卡即听（服务未连通时显示「示例」卡）
  pages/Settings.ets          设置页（自选股增删 / 播报开关 / 字体档切换 / 主题 / 免打扰）
  services/PushService        Push Kit 集成封装（AGC 未配置时自动降级为轮询）
  services/AlertPoller        前台 5s 轮询兜底（退避策略：失败翻倍封顶 30s）
  services/AudioPlayer        云端 TTS 音频流点按播报（AVPlayer）
  services/SettingsService    设置数据持久化（Preferences：自选股/播报开关/字体档/主题/免打扰/已读/播报历史）
  model/AlertItem             异动事实卡数据契约（含 kind=fact/signal, complianceStatus）
cloudfunctions/functions/
  fetch-tushare-data          A股日线行情获取 + 异动筛选 + 名称映射 + 合规检查 + TTS预生成
  broadcast-a2a               A2A总线消息广播（API Key鉴权 + CORS限制）
  generate-tts                百炼CosyVoice TTS音频生成（WebSocket）
  get-alerts                  异动列表查询（CloudBase存储读取）
  push-token-register         Push Kit token注册（AGC配置后激活）
  init-db                     数据库初始化
GOVERNANCE/                   治理文档体系（AGENTS.md/CHANGELOG/技能文档/A2A协议/密码学报告）
```

## 构建

**本机构建**（DevEco Studio 6.0.2+，**纯英文路径必需**）：

> ⚠️ hvigor 工具链不支持中文路径。项目当前位于 `C:\Users\欧阳宏俊\...`（含中文用户名），必须先迁移到纯英文路径再构建。详见 [hvigor 中文路径诊断技能](GOVERNANCE/skills/diag/hvigor-chinese-path.md)。

```bash
# 1. 复制项目到纯英文路径（排除缓存目录）
robocopy <项目原路径> C:\dev\lingyu\harmony-app /E /XD node_modules oh_modules .hvigor .codeartsdoer

# 2. 在英文路径下构建（debug 模式）
cd C:\dev\lingyu\harmony-app
devecocli build --build-mode debug
# 产物：entry/build/default/outputs/default/entry-default-unsigned.hap
```

**云构建**（CodeArts Build）：

1. 把本目录上传码道仓库（CodeArts Repo）。
2. CodeArts Build 新建构建任务 → 选官方「HarmonyOS 应用构建」模板（自带 SDK/Hvigor）。
3. 产物 `entry-default-signed.hap` 下载后经 `hdc install` 装 X5。

## 签名与装机（机主一次动作，约 10 分钟）

1. 免费注册华为个人开发者（无费用）。
2. 任一可联网电脑装 DevEco Studio → 打开本工程 → 自动化签名（自动生成调试证书+profile）。
3. X5 开开发者模式 → UDID 录入调试设备列表 → `hdc install` 直装。
4. 调试证书一年有效，到期重签（已建日历提醒）。

详见 [签名配置指南](GOVERNANCE/skills/governance/hmos-signing.md)。

## 云函数部署

### 环境变量配置

在 CloudBase 控制台为每个云函数配置环境变量：

| 云函数 | 必需环境变量 | 可选环境变量 |
|--------|-------------|-------------|
| fetch-tushare-data | `TUSHARE_TOKEN`, `TCB_ENV` | `ALERT_THRESHOLD`(默认5.0), `DKNOWC_API_KEY` |
| broadcast-a2a | `BROADCAST_API_KEY`, `TCB_ENV` | — |
| generate-tts | `DASHSCOPE_API_KEY`, `TTS_VOICE`, `TCB_ENV` | — |
| get-alerts | `TCB_ENV` | — |
| push-token-register | `TCB_ENV` | — |
| init-db | `TCB_ENV` | — |

### 部署步骤

1. 安装 CloudBase CLI：`npm install -g @cloudbase/cli`
2. 登录：`cloudbase login`
3. 部署全部云函数：`cloudbase functions deploy --all`
4. 或单个部署：`cloudbase functions deploy fetch-tushare-data`

## 推送实装（候 AGC）

1. AppGallery Connect 建项目+应用，开通 Push Kit，下载 `agconnect-services.json` 放 `AppScope/resources/rawfile/`。
2. `PushService.ets` 已实装 `pushService.getToken()` → 上报 X 服务器 `/api/push/register`（AGC 配置到位后自动激活）。
3. 服务端经 Push Kit REST 下发「订阅类 SUBSCRIPTION」通知（含行情提醒，锁屏+铃声+不限量；自分类申请约 15 工作日）。
4. 通知 click 参数带 `alertId` → `onNewWant` → 页面自动播报对应音频。

降级链：Push 未实装时 App 打开期间 5s 轮询兜底，首屏永不空白。

## API 文档

### 端侧接口

| 服务 | 方法 | 说明 |
|------|------|------|
| AlertPoller | `fetchLatest(limit=20)` | 拉取最新异动列表，返回 `PollResult { ok, items, rateLimited? }` |
| AlertPoller | `getInterval()` | 获取当前轮询间隔（退避时动态增大） |
| AudioPlayer | `play(url, onDone?, onError?)` | 播放云端TTS音频流 |
| AudioPlayer | `stop()` | 停止播放并释放AVPlayer |
| SettingsService | `getWatchlist()` | 获取自选股列表 |
| SettingsService | `getBroadcastEnabled()` | 获取播报开关状态 |
| SettingsService | `getFontSizeLevel()` | 获取字体档（standard/large） |
| SettingsService | `getFeedUrl()` | 获取数据源URL |
| SettingsService | `markAlertRead(alertId)` | 标记异动已读 |
| SettingsService | `addPlayHistory(item)` | 记录播报历史 |

### 云函数接口

| 云函数 | 入参 | 出参 |
|--------|------|------|
| fetch-tushare-data | `{}` | `{ success, items: AlertItem[], serverTs, count }` |
| get-alerts | `{ limit?: number }` | `{ success, items: AlertItem[], serverTs }` |
| generate-tts | `{ alertId, text }` | `{ success, audioUrl }` |
| broadcast-a2a | `{ message, apiKey }` | `{ success, messageId }` |
| push-token-register | `{ token, deviceId }` | `{ success }` |

### 数据契约（AlertItem）

```typescript
interface AlertItem {
  alertId: string;        // 格式: ${symbol}_${timestamp}
  ts: number;             // Unix时间戳（秒）
  symbol: string;         // 股票代码（如 600176.SH）
  name: string;           // 股票中文名
  direction: 'up' | 'down' | 'flat';
  kind: 'fact' | 'signal'; // 事实卡 or 自家信号卡
  headline: string;       // 白话头条（如"中国巨石 涨了 5.2%"）
  detail: string;         // 补充细节
  signalNote?: string;    // 信号卡备注（如"留意后续走势"）
  pctChg: number;         // 涨跌幅
  close: string;          // 收盘价
  vol: string;            // 成交量
  audioUrl?: string;      // TTS音频URL
  complianceStatus?: string; // 合规检查结果
}
```

## 合规红线

1 台自用、不收费；只报涨跌幅/量能/价格穿越等客观事实；不碰荐股。

信号松绑（2026-09-14 机主裁）：允许输出自家策略信号（kind=signal），保留三禁：①承诺收益/保本等绝对化措辞；②催促性强指令；③任何对外公开/收费形态。

## 功能清单（当前版本 0.1.0）

- ✅ 大字异动卡片流（点卡即听）
- ✅ 适老化模式 / 正常模式切换
- ✅ 夜间模式 / 白天模式切换（支持自动主题）
- ✅ 免打扰模式（指定时段内自动播报静默）
- ✅ 自选股管理（添加/删除，过滤显示）
- ✅ 播报开关（关后自动播报静默）
- ✅ 字体大小切换（标准/特大）
- ✅ 首屏示例卡兜底（服务未连通时显示带「示例」字样的演示卡）
- ✅ Push Kit 占位封装（AGC 未配置时自动降级轮询）
- ✅ 前台 5s 轮询兜底（退避策略：失败翻倍封顶 30s，429 限流静默跳过）
- ✅ 冷启动通知缺口修复（want 参数 alertId 经 onCreate 补检）
- ✅ 信号卡「自家信号」角标（kind=signal，与事实卡视觉区分）
- ✅ DKnowC 合规检查集成（信号卡播报文本安全合规检测）
- ✅ 已读标记 + 播报历史（50条上限）
- ✅ readAlertIdSet 缓存优化（O(1)查找）
- ⏳ 签名配置（需机主在 DevEco Studio 中配置 signingConfigs）
- ⏳ AGC 平台审批 P5（订阅通知自分类，约 15 工作日）
- ⏳ X 服务器落地（替换 FEED_URL 占位值）
- ⏳ 模拟器验证（DevEco Studio 6.0.2 < devecocli 要求的 6.1.0）

## 已修复问题

| 级别 | 问题 | 修复版本 |
|------|------|---------|
| P0 | CloudBase SDK重复init | 2026-09-22 |
| P0 | callTushare无超时控制 | 2026-09-22 |
| P0 | requestHttps未统一封装 | 2026-09-22 |
| P0 | getStockNameMap旧代码残留（ReferenceError） | 2026-09-23 |
| P1 | 东方财富分页并行化 | 2026-09-22 |
| P1 | FEED_URL硬编码常量提取 | 2026-09-23 |
| P2 | TTS优先级排序 | 2026-09-22 |
| P2 | broadcast-a2a HTTP鉴权 | 2026-09-22 |
| P2 | readAlertIds Set缓存优化 | 2026-09-23 |
