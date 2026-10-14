# 行情播报工程 · 任务白皮书 R4（对接 X 服务器与端到端联调）

> 版本：R4.0 草案（2026-09-16，砚坚起草，待白秉烛核准）
> 执行席：码道 IDE · 鸿蒙开发智能体 · GLM-5.2-ArkTS-SPARK
> 前置条件：R1+R2+R2a 闭环，R3 代码已完成（待 AGC 配置联调）
> 本文档定义 X 服务器对接与端到端联调的完整技术方案。

---

## 第一章 · 任务范围

R4 的目标是：**把所有占位地址替换为 X 服务器真实地址，完成云端监测 → Push 推送 → 端侧播报的端到端联调**。

### 1.1 前置条件

| # | 操作 | 责任方 | 状态 |
|---|------|--------|------|
| P6 | X 服务器落地（华为云 X 实例 8核32G） | 机主采购 + 顾权席部署 | 待办 |
| P7 | X 服务器 FEED_URL 接口可用 | 顾权席 | 待办 |
| P8 | X 服务器 TTS 音频流接口可用 | 顾权席 | 待办 |
| P9 | X 服务器 Push Token 上报接口可用 | 顾权席 | 待办 |
| P10 | X 服务器 Push Kit REST API 下发能力 | 顾权席 | 待办 |

### 1.2 砚坚需完成的代码改动

| # | 工作 | 当前占位 | 替换为 |
|---|------|----------|--------|
| W1 | AlertPoller.ets FEED_URL | `http://127.0.0.1:8000/api/alerts/latest` | X 服务器真实地址 |
| W2 | PushService.ets TOKEN_REPORT_URL | `http://127.0.0.1:8000/api/push/register` | X 服务器真实地址 |
| W3 | 端到端联调验证 | — | 真机+X 服务器 |

**关键约束**：FEED_URL 和 TOKEN_REPORT_URL 是仅有的两个占位地址。替换后需确保：
- HTTP → HTTPS（X 服务器应使用 TLS）
- 超时参数适配（5s connect/read 可能需要调整）
- 网络安全配置（module.json5 或 network_security_config）

---

## 第二章 · 技术方案

### 2.1 FEED_URL 替换

当前 `AlertPoller.ets` 第 9 行：
```typescript
const FEED_URL = 'http://127.0.0.1:8000/api/alerts/latest';
```

替换为 X 服务器真实地址（示例）：
```typescript
const FEED_URL = 'https://x-server.example.com/api/alerts/latest';
```

**注意事项**：
- X 服务器须使用 HTTPS（HarmonyOS 默认不允许明文 HTTP，需在 module.json5 中配置 `cleartextTraffic` 或使用 `network_security_config`）
- 如果 X 服务器使用自签名证书，需配置信任证书
- 超时参数 5s connect/read 保持不变（X 服务器 8核32G 应能快速响应）

### 2.2 TOKEN_REPORT_URL 替换

当前 `PushService.ets` 第 12 行：
```typescript
const TOKEN_REPORT_URL = 'http://127.0.0.1:8000/api/push/register';
```

替换为 X 服务器真实地址（示例）：
```typescript
const TOKEN_REPORT_URL = 'https://x-server.example.com/api/push/register';
```

### 2.3 网络安全配置

HarmonyOS NEXT 默认不允许明文 HTTP 流量。如果 X 服务器使用 HTTPS（推荐），无需额外配置。如果必须使用 HTTP（调试阶段），需在 `module.json5` 中配置：

```json5
{
  "module": {
    "metadata": [
      {
       .0 "name": "network_security_config",
        "resource": "$profile:network_security_config"
      }
    ]
  }
}
```

并在 `entry/src/main/resources/base/profile/` 下创建 `network_security_config.json`：
```json
{
  "network-security-config": {
    "domain-config": [
      {
        "cleartext-traffic-permitted": true,
        "domains": ["x-server.example.com"]
      }
    ]
  }
}
```

**推荐**：X 服务器使用 HTTPS，避免明文流量配置。

### 2.4 端到端联调验证流程

联调分四个阶段，每阶段通过后才进入下一阶段：

**阶段 1：FEED_URL 连通性**
1. X 服务器部署完成，FEED_URL 返回 AlertFeed JSON
2. App 启动 → AlertPoller 轮询 → 收到真实异动数据 → 卡片流显示
3. 验证：DEMO_ITEMS 消失，真实卡片出现，lastRefresh 时间更新

**阶段 2：TTS 音频流播报**
1. X 服务器 TTS 接口可用，audioUrl 指向真实音频流
2. App 点按卡片 → AudioPlayer.play(audioUrl) → 播放云端 TTS 音频
3. 验证：点击卡片能听到语音播报，播放/停止状态正确

**阶段 3：Push Token 上报**
1. AGC 配置完成（P2-P4），PushService.getToken() 成功
2. Token 上报到 X 服务器 `/api/push/register`
3. 验证：X 服务器日志确认收到 Token

**阶段 4：Push 通知 → 拉起 → 播报**
1. X 服务器通过 Push Kit REST API 下发通知（带 alertId）
2. 设备收到锁屏通知 → 点按通知 → App 拉起 → 定位异动卡片 → 自动播报
3. 验证：完整链路闭环

---

## 第三章 · 验收标准

| # | 验收项 | 验证手段 | 前置条件 |
|---|--------|----------|----------|
| V1 | FEED_URL 连通，收到真实异动数据 | 真机启动 App，卡片流显示真实数据 | P6-P7 |
| V2 | TTS 音频流播报正常 | 真机点按卡片，听到语音播报 | P6-P8 |
| V3 | Push Token 获取并上报成功 | hilog 查看 token，X 服务器日志确认 | P2-P4 + P9 |
| V4 | Push 通知拉起 App 并定位卡片 | 真机点按锁屏通知，卡片定位+自动播报 | P2-P4 + P10 |
| V5 | 自选股过滤生效 | 设置页添加自选股，卡片流只显示关注的股票 | P6-P7 |
| V6 | 播报开关生效 | 设置页关闭播报，通知拉起时静默跳过 | P2-P4 |
| V7 | 字体档切换生效 | 设置页切换特大档，字号变大 | 无 |
| V8 | 网络断开恢复 | 断网两轮后提示"连接中断"，恢复后消失 | P6-P7 |
| V9 | FEED_URL 和 TOKEN_REPORT_URL 均为 HTTPS | `grep 'http://' *.ets` 无明文 HTTP | 无 |
| V10 | 契约双文件 diff 为空 | `git diff HEAD -- AGENTS.md AlertItem.ets` | 无 |

---

## 第四章 · 禁止事项

1. 禁止修改 AGENTS.md、AlertItem.ets 契约字段
2. 禁止引入三方依赖
3. 禁止在通知标题/正文中出现买卖建议措辞
4. 禁止使用明文 HTTP（除非调试阶段且配置了 network_security_config）
5. 禁止删除 DEMO_ITEMS 首屏兜底（X 服务器未连通时仍需显示示例卡）

---

## 第五章 · 依赖与时间线

```
机主采购         顾权席部署           砚坚联调
─────────        ─────────            ─────────
P6 X 服务器采购 →  P7 FEED_URL     →  W1 替换 FEED_URL
                  P8 TTS 接口      →  阶段1+2 联调
                  P9 Token 上报    →  W2 替换 TOKEN_REPORT_URL
                  P10 Push REST    →  阶段3+4 联调
```

**关键路径**：P6（X 服务器采购落地）是最大瓶颈。建议：
1. 机主尽快启动 X 服务器采购
2. 顾权席在 X 服务器到位后优先部署 FEED_URL 和 TTS 接口
3. 砚坚在 FEED_URL 可用后立即替换占位地址并联调
4. Push 相关联调等 AGC 配置（P2-P4）完成后进行

---

## 第六章 · 文档出处

| 内容 | URL |
|------|-----|
| HarmonyOS 网络安全配置 | developer.huawei.com/consumer/cn/doc/harmonyos-guides/security-network-security-config |
| Push Kit REST API | developer.huawei.com/consumer/cn/doc/harmonyos-guides/push-send-alert |
| AVPlayer 音频播放 | developer.huawei.com/consumer/cn/doc/harmonyos-references/js-apis-media |