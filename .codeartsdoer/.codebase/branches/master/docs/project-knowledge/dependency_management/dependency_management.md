---
name: 依赖管理
description: 零三方依赖策略、oh_modules、HarmonyOS Kits
type: project-knowledge
category: dependency_management
---

# 依赖管理

## 零三方依赖策略

端侧App（ArkTS）严格遵循零三方依赖原则——仅使用HarmonyOS官方Kits（@kit.*），不引入任何第三方npm/ohpm包。这是AGENTS.md硬约束。

**oh-package.json5依赖声明**：
- `dependencies: {}` — 无运行时依赖
- `devDependencies`：仅测试框架 @ohos/hypium 和 @ohos/hamock

## HarmonyOS Kits使用清单

| Kit | 用途 | 使用模块 |
|-----|------|---------|
| @kit.AbilityKit | UIAbility、AbilityConstant、Want、common | EntryAbility |
| @kit.ArkUI | window、声明式UI组件 | EntryAbility、Index、Settings |
| @kit.ArkData | preferences（持久化） | SettingsService |
| @kit.NetworkKit | http（HTTP请求） | AlertPoller、PushService |
| @kit.MediaKit | media.AVPlayer（音频播放） | AudioPlayer |
| @kit.PushKit | pushService、pushCommon（推送） | EntryAbility、PushService |
| @kit.BasicServicesKit | BusinessError | EntryAbility、PushService |
| @kit.PerformanceAnalysisKit | hilog（日志） | 全部模块 |

## feed-server依赖（服务端，非端侧）

feed-server为Node.js服务端模块，不受零三方依赖约束：
- `westock-data-clawhub@1.0.4` — 腾讯自选股数据获取
- Node.js内置模块：http, https, crypto, fs, path, child_process, util
- 百炼CosyVoice TTS — 通过WebSocket调用，无SDK依赖