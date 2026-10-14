# 鸿蒙生态整合方案

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-18
> 依据：HarmonyOS 7 创新特性、小艺开放平台、Ascend 社区、AGConnect、HiDevLab
> 机主指令：集成华为 SDK 和小艺接入，探索 Ascend 社区和鸿蒙生态整合

---

## 一、当前项目基线

### 1.1 已有集成

| 组件 | 状态 | 说明 |
|------|------|------|
| `@kit.PushKit` | 占位封装 | PushService.ets 已实装 `pushService.getToken()`，AGC 未配置时自动降级轮询 |
| `@kit.NetworkKit` | 已使用 | AlertPoller 轮询 + PushService token 上报 |
| `@kit.AbilityKit` | 已使用 | EntryAbility Stage 模型 |
| `@kit.PerformanceAnalysisKit` | 已使用 | hilog 日志 |
| `@kit.BasicServicesKit` | 已使用 | BusinessError 类型 |
| AVPlayer | 已使用 | AudioPlayer.ets 云端 TTS 音频流播放 |

### 1.2 待整合缺口

| 组件 | 缺口 | 优先级 |
|------|------|--------|
| AGConnect | `agconnect-services.json` 未配置，Push Kit 降级中 | 🔴 |
| 小艺 A2A | 未接入小艺开放平台 | 🟠 |
| 鸿蒙星盾安全 | 未利用 HarmonyOS 7 安全特性 | 🟡 |
| 空间音频 | 未利用 HarmonyOS 7 空间音频能力（Hi-Fi 路线协同） | 🟡 |
| Ascend 社区 | 未对接昇腾 AI 计算资源 | 🟢 |
| Skill 开发 | 未开发小艺 Skill | 🟢 |

### 1.3 硬约束回顾

- 适老化大字白话卡片流（28-34fp），**禁止 K 线图/走势图等复杂图表组件**
- 信号松绑：允许 `kind: "signal"` 标记的自家策略信号，禁三条（收益承诺/催促/公开收费）
- Stage 模型，`compatibleSdkVersion 6.0.2(22)` / `targetSdkVersion 6.0.2(22)`
- 纯 ArkTS，零三方依赖
- PushService.ets 保持占位封装，AGC 未配置前自动降级轮询

---

## 二、AGConnect 配置方案（优先级：🔴 立即）

### 2.1 配置步骤

AGConnect（AppGallery Connect）是所有华为云服务的基础入口，Push Kit 依赖它。

```
步骤 1：注册华为个人开发者（免费）
  → https://developer.huawei.com/consumer/cn/

步骤 2：AGConnect 创建项目+应用
  → https://developer.huawei.com/consumer/cn/agconnect/
  → 项目名：铃语
  → 应用名：铃语
  → 包名：com.yehang.stockpulse（与 AppScope/app.json5 一致）

步骤 3：开通 Push Kit
  → AGConnect → 常用服务 → Push Kit → 开通
  → 下载 agconnect-services.json

步骤 4：放置配置文件
  → 将 agconnect-services.json 放到 AppScope/resources/rawfile/
  → PushService.ets 的 probeAgcConfig() 会自动检测并激活

步骤 5：订阅通知自分类申请
  → AGConnect → Push Kit → 自分类 → 申请「订阅类 SUBSCRIPTION」
  → 含行情提醒，锁屏+铃声+不限量
  → 审批约 15 工作日
```

### 2.2 代码层面无需修改

PushService.ets 已完整实装：
- `probeAgcConfig()`：检测 `agconnect-services.json` 是否存在
- `fetchToken()`：调用 `pushService.getToken()` 获取 Push Token
- `reportToken()`：上报 Token 到 X 服务器 `/api/push/register`
- `handleTokenRetry()`：可重试错误码自动重试（最多 3 次）
- 降级链：AGC 未配置 → 静默降级 → AlertPoller 5s 前台轮询兜底

**配置到位后自动激活，无需改代码。**

### 2.3 AGConnect 其他可开通的服务

| 服务 | 用途 | 优先级 | 说明 |
|------|------|--------|------|
| **Push Kit** | 异动推送 | 🔴 | 已实装，待配置激活 |
| **Analytics Kit** | 使用数据分析 | 🟡 | 了解用户使用习惯，优化体验 |
| **Crash Kit** | 崩溃报告 | 🟡 | 自动收集崩溃信息，辅助调试 |
| **Remote Configuration** | 远程配置 | 🟢 | 远程调整轮询间隔、字体大小等参数 |
| **App Linking** | 深链接分享 | 🟢 | 分享异动卡片链接 |

---

## 三、小艺 A2A 接入方案（优先级：🟠 短期）

### 3.1 小艺开放平台概述

小艺是 HarmonyOS 系统级智能助手，开放平台支持两种接入模式：

| 模式 | 说明 | 适用场景 | 铃语适用性 |
|------|------|----------|-----------|
| **端侧接入** | 应用直接在小艺中注册 Agent，本地交互 | 需要快速响应、隐私敏感 | ★★★ 适合异动播报 |
| **云侧接入** | 应用通过云端 Agent 与小艺交互，兼容 A2A 协议 | 需要复杂数据处理、跨设备 | ★★ 适合信号分析 |

**推荐**：端侧接入为主（异动播报即时性要求高），云侧接入为辅（信号分析复用 quant-lab 能力）。

### 3.2 端侧接入方案

```
用户语音："小艺，今天有什么异动？"
    ↓
小艺 → 唤起铃语 EntryAbility（action: com.yehang.stockpulse.QUERY_ALERTS）
    ↓
铃语 → 返回当前异动卡片列表（JSON 格式）
    ↓
小艺 → 语音播报："今天有3条异动：贵州茅台涨幅超3%..."
    ↓
用户语音："详细说说茅台"
    ↓
小艺 → 唤起铃语（action: com.yehang.stockpulse.DETAIL_ALERT, params: { alertId: "xxx" })
    ↓
铃语 → 自动播报对应异动的 TTS 音频
```

### 3.3 实施步骤

#### 步骤 1：注册小艺 Agent

在 `module.json5` 中添加小艺 Agent 的 action：

```json5
{
  "abilities": [
    {
      "name": "EntryAbility",
      "skills": [
        {
          "entities": ["entity.system.home"],
          "actions": ["action.system.home"]
        },
        {
          "actions": ["action.ohos.push.listener"]
        },
        // 新增：小艺 Agent 接入
        {
          "actions": [
            "com.yehang.stockpulse.QUERY_ALERTS",
            "com.yehang.stockpulse.DETAIL_ALERT",
            "com.yehang.stockpulse.PLAY_AUDIO"
          ]
        }
      ]
    }
  ]
}
```

#### 步骤 2：EntryAbility 处理小艺请求

在 `EntryAbility.ets` 的 `onNewWant` 中增加小艺请求处理：

```typescript
onNewWant(want: Want): void {
  const action = want.action;
  const params = want.parameters;

  if (action === 'com.yehang.stockpulse.QUERY_ALERTS') {
    // 返回当前异动列表给小艺
    this.returnAlertsToXiaoYi();
  } else if (action === 'com.yehang.stockpulse.DETAIL_ALERT') {
    // 播报指定异动详情
    const alertId = params?.alertId as string;
    AppStorage.setOrCreate('pendingAlertId', alertId);
  } else if (action === 'com.yehang.stockpulse.PLAY_AUDIO') {
    // 直接播放指定异动的 TTS 音频
    const alertId = params?.alertId as string;
    AppStorage.setOrCreate('pendingAlertId', alertId);
  }
}
```

#### 步骤 3：开发小艺 Skill

HarmonyOS 7 支持 Skill 开发，两种方式：

| 方式 | 说明 | 适用 |
|------|------|------|
| **Vibe Coding** | 自然语言描述创建 Skill | 快速原型 |
| **一键导入** | 导入现有 Skill 自动转化 | 复用已有能力 |

铃语 Skill 定义：
```
Skill 名称：异动播报
触发词："异动"、"播报"、"股票异动"、"今天有什么异动"
功能：查询当前异动列表，语音播报
```

### 3.4 A2A 协议兼容

小艺开放平台兼容生态 A2A 协议，铃语可通过 A2A 总线与小艺交互：

```
铃语 A2A 桥接 ←→ A2A 总线 ←→ 小艺云侧 Agent
     ↓                           ↓
  端侧播报                    云侧信号分析
```

**与现有 A2A 总线的关系**：
- 现有 A2A 总线连接砚坚、顾权、白秉烛等 AI 席位
- 小艺接入后，小艺成为 A2A 总线上的新节点
- 铃语 App 既可通过端侧直接与小艺交互，也可通过 A2A 总线间接交互

---

## 四、鸿蒙星盾安全整合（优先级：🟡 中期）

### 4.1 HarmonyOS 7 安全特性

HarmonyOS 7 的鸿蒙星盾安全提供三个关键能力：

| 特性 | 说明 | 铃语应用场景 |
|------|------|-------------|
| **AI 变声检测** | 检测音频是否为 AI 合成 | 验证 TTS 音频完整性，防止音频被篡改替换 |
| **机密风控引擎** | 硬件级机密计算 | 凭据金库加密的硬件级保护 |
| **分布式数字身份认证** | 跨设备身份认证 | A2A 席位间身份验证 |

### 4.2 AI 变声检测与 TTS 安全

铃语使用百炼 CosyVoice 生成 TTS 音频，Hi-Fi 路线将升级到 PCM 48kHz。AI 变声检测可用于：

```
TTS 音频生成 → 传输 → 端侧播放前验证
                         ↓
              鸿蒙星盾 AI 变声检测
                         ↓
              通过 → 播放 | 不通过 → 警告"音频可能被篡改"
```

**实施**：在 AudioPlayer.ets 的 `play()` 方法中增加音频完整性验证步骤。

### 4.3 机密风控引擎与凭据金库

当前凭据金库使用 AES-256-GCM 加密（Phase 1 计划）。鸿蒙星盾的机密风控引擎可提供硬件级保护：

| 层级 | 当前方案 | 星盾增强方案 |
|------|----------|-------------|
| 凭据存储 | AES-256-GCM 软件加密 | 机密风控引擎硬件加密 |
| 凭据读取 | 环境变量 VAULT_MASTER_KEY | 星盾安全存储 API |
| 密钥轮换 | 手动轮换 | 星盾自动密钥管理 |

**实施**：在 PushService.ets 的凭据读取路径中，优先使用星盾安全存储 API，降级到软件加密。

### 4.4 分布式数字身份认证与 A2A

A2A 总线当前依赖 Supabase RLS + Bearer Token 进行席位认证。分布式数字身份认证可提供更强的跨设备身份验证：

```
席位A ←→ 分布式数字身份认证 ←→ 席位B
  ↓                                ↓
  互相验证设备身份和席位权限
  ↓
  建立 PQC 混合 KEX 加密通道
```

**与 PQC 回环验证的关系**：分布式数字身份认证 + PQC 混合 KEX = 完整的 A2A 安全回环。

---

## 五、空间音频与 Hi-Fi 协同（优先级：🟡 中期）

### 5.1 HarmonyOS 7 空间音频

HarmonyOS 7 引入空间音频能力，可模拟三维声场。对于铃语的适老化播报场景：

| 场景 | 空间音频效果 | 适老化价值 |
|------|-------------|-----------|
| 异动播报 | 语音从正前方播报，清晰聚焦 | 老年用户更容易定位声源 |
| 多条异动 | 不同异动从不同方位播报 | 区分多条异动，避免混淆 |
| 信号提醒 | 信号卡从侧方播报，与事实卡区分 | 听觉上区分事实和信号 |

### 5.2 Hi-Fi + 空间音频实施路径

```
Phase 2: TTS 参数升级（PCM 48kHz/24bit）
    ↓
Phase 3: 空间音频元数据嵌入
    ↓
Phase 4: 端侧空间音频播放（AVPlayer + 空间音频 API）
```

**关键约束**：空间音频不得增加 UI 复杂度（适老化硬约束），仅作为音频播放的增强层，用户无感知。

### 5.3 AVPlayer 空间音频 API

```typescript
// 概念：AudioPlayer.ets 空间音频扩展
import { media } from '@kit.MediaKit';

// 当前：标准 AVPlayer 播放
const player = await media.createAVPlayer();

// 空间音频增强（HarmonyOS 7+）
// player.setSpatialAudioConfig({
//   renderingMode: media.SpatialRenderingMode.BINAURAL,
//   headTrackingEnabled: false,  // 适老化：关闭头部追踪，简化体验
// });
```

**注意**：空间音频 API 需要 `compatibleSdkVersion` 升级到 HarmonyOS 7（当前 6.0.2(22)）。在升级前，先完成 Hi-Fi 参数升级（PCM 48kHz），空间音频作为后续增强。

---

## 六、Ascend 社区对接（优先级：🟢 长期）

### 6.1 Ascend 社区资源

| 资源 | 说明 | 铃语潜在用途 |
|------|------|-------------|
| **CANN** | 异构计算架构，Ascend AI 处理器算子库 | TTS 音频生成的硬件加速 |
| **MindSpore 昇思** | 深度学习框架 | 自训练 TTS 模型（替代百炼依赖） |
| **MindSDK** | 端侧 AI 推理 SDK | 端侧异动检测、本地语音合成 |
| **MindIE** | 推理引擎 | 高效推理服务部署 |
| **MindCluster** | 集群使能 | 大规模数据处理 |
| **HiDevLab** | 昇腾 AI 开发平台（100 卡时免费） | 模型训练和推理实验 |

### 6.2 Ascend 与铃语的关系

铃语当前的数据流：
```
westock-data → AlertFeed JSON → feed-server → TTS(百炼) → 铃语 App
```

Ascend 可增强的环节：
```
westock-data → AlertFeed JSON → feed-server → TTS(Ascend MindIE) → 铃语 App
                                                    ↓
                                            端侧 MindSDK 推理
                                            （本地异动检测）
```

### 6.3 HiDevLab 实验计划

HiDevLab 提供 100 卡时免费 Ascend 算力，可用于：

| 实验 | 目标 | 卡时估算 |
|------|------|----------|
| CosyVoice 模型本地部署 | 验证 Ascend 上 TTS 推理性能 | ~20 卡时 |
| 端侧异动检测模型 | 训练轻量级异动检测模型，部署到 MindSDK | ~30 卡时 |
| Hi-Fi 音频质量评估 | PCM 48kHz vs MP3 的主观/客观质量对比 | ~5 卡时 |
| PQC 加密性能测试 | ML-KEM-768 在 Ascend 上的封装/解封装性能 | ~10 卡时 |

### 6.4 Ascend 对接路径

```
步骤 1：注册 Ascend 社区账号
  → https://www.hiascend.com/

步骤 2：申请 HiDevLab 算力
  → HiDevLab → 申请 100 卡时

步骤 3：部署 CosyVoice 推理服务
  → 使用 MindIE 推理引擎部署 CosyVoice
  → 对比百炼 API 的延迟和音质

步骤 4：端侧 MindSDK 集成（概念验证）
  → 训练轻量级异动检测模型
  → 导出 MindSDK 兼容格式
  → 鸿蒙端侧推理（需 compatibleSdkVersion 升级）
```

**关键约束**：Ascend 对接是长期规划，不影响当前 Phase 0-2 的密码学加固和 Hi-Fi 升级。

---

## 七、HarmonyOS SDK 版本升级路径

### 7.1 当前版本与目标版本

| 版本 | 当前 | 目标 | 关键差异 |
|------|------|------|----------|
| `compatibleSdkVersion` | 6.0.2(22) | 7.0.0(26) | 空间音频、星盾安全、Skill 开发 |
| `targetSdkVersion` | 6.0.2(22) | 7.0.0(26) | 同上 |
| DevEco Studio | 6.0.2 | 7.0+ | 新 SDK、新模拟器 |

### 7.2 升级风险与兼容性

| 风险 | 影响 | 缓解 |
|------|------|------|
| API 变更 | 现有 API 可能废弃 | 逐 API 验证，ArkTS 编译器会报错 |
| 行为变更 | 新版本可能改变默认行为 | 仔细阅读 Release Notes |
| 签名变更 | 新版本可能需要重新签名 | 使用 DevEco Studio 自动签名 |
| 模拟器变更 | 新模拟器可能不兼容旧 HAP | 升级后重新构建 |

### 7.3 升级策略

**不急于升级**。当前 6.0.2(22) 已满足铃语核心功能需求。升级到 7.0 的驱动力是：

1. 空间音频（Hi-Fi 协同）→ 🟡 中期需求
2. 星盾安全（凭据金库增强）→ 🟡 中期需求
3. Skill 开发（小艺接入）→ 🟠 短期需求，但端侧接入不强制要求 7.0

**建议**：先在 6.0.2(22) 上完成 Phase 0-2（密码学加固 + Hi-Fi），再评估升级到 7.0 的时机。

---

## 八、整合路线图

| 阶段 | 时间 | 任务 | 依赖 | 约束 |
|------|------|------|------|------|
| **E0** | 立即 | AGConnect 配置（Push Kit 激活） | 机主注册华为开发者 | 零代码变更 |
| **E1** | 1周 | 小艺端侧接入（module.json5 + EntryAbility） | E0 完成 | 纯 ArkTS，零三方依赖 |
| **E2** | 2周 | 小艺 Skill 开发（异动播报触发词） | E1 完成 | Vibe Coding 或手动定义 |
| **E3** | 1月 | 鸿蒙星盾安全评估（AI 变声检测 + 机密风控） | SDK 7.0+ | 需升级 compatibleSdkVersion |
| **E4** | 1月 | 空间音频与 Hi-Fi 协同 | SDK 7.0+ + Phase 2 Hi-Fi | 适老化无感知 |
| **E5** | 2月 | Ascend HiDevLab 实验（CosyVoice 本地部署） | Ascend 社区注册 | 不影响主线开发 |
| **E6** | 3月 | MindSDK 端侧推理（概念验证） | E5 完成 | 需 SDK 7.0+ |

---

## 九、与密码学加固的协同

鸿蒙生态整合与密码学加固（`CRYPTO_HARDENING_HIFI_REPORT.md`）的协同关系：

| 维度 | 密码学加固 | 鸿蒙生态整合 | 协同方案 |
|------|-----------|-------------|----------|
| **凭据保护** | AES-256-GCM 软件加密 | 星盾机密风控引擎硬件加密 | 软件加密为基准，星盾为增强 |
| **传输安全** | HTTPS + SSH 隧道 PQC | AGConnect 内置 HTTPS | AGConnect 的 HTTPS 作为传输层 |
| **身份认证** | A2A Bearer Token | 分布式数字身份认证 | Token 为基准，数字身份为增强 |
| **音频安全** | AEAD 加密 Hi-Fi 音频 | AI 变声检测 | 加密保护传输，变声检测保护内容 |
| **PQC 回环** | ML-KEM-768 + X25519 | 星盾分布式身份 + PQC | 完整的 A2A 安全回环 |

---

## 十、与 A2A 协议的关系

铃语 App 在 A2A 协议中的角色：

```
                    A2A 总线
                       ↓
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    砚坚(码道)     顾权(Kimi)    小艺(华为)
        ↓              ↓              ↓
    铃语 App      quant-lab    系统级入口
    (端侧)        (服务端)     (云端+端侧)
```

**小艺接入后的 A2A 扩展**：
- 小艺成为 A2A 总线上的新节点
- 铃语可通过 A2A 总线向小艺发送异动通知
- 小艺可通过 A2A 总线向铃语请求异动数据
- PQC 混合 KEX 保护所有 A2A 通信

---

*本方案基于 HarmonyOS 7 创新特性、小艺开放平台 A2A 模式、Ascend 社区资源、AGConnect 服务和 HiDevLab 算力。所有整合均遵守铃语硬约束（适老化、纯 ArkTS、零三方依赖、Stage 模型）。*