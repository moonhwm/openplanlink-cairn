# 铃语（StockPulse）知识库 Overview

> 适老化语音提醒App——云端秒级监测→Push推送→锁屏大字通知→点按拉起→自动语音播报

## 项目概况

- **应用名**：铃语（StockPulse）
- **bundleName**：com.yehang.stockpulse
- **版本**：0.1.0
- **平台**：HarmonyOS NEXT（Stage模型，compatibleSdkVersion 6.0.2(22)）
- **语言**：纯ArkTS（端侧）+ Node.js ESM（服务端feed-server）
- **依赖策略**：零三方依赖（端侧仅用@kit.*官方Kits）
- **分发**：私有调试证书直装（免审核免软著免备案零公开，100台/年）

## 知识库结构

### 维度一：代码仓内容知识（[codebase-knowledge/](codebase-knowledge/index.md)）

按模块树组织，描述每个模块提供什么能力及如何组织。

| 模块 | 核心职责 |
|------|---------|
| [入口能力（EntryAbility）](codebase-knowledge/入口能力（EntryAbility）.md) | 应用入口、Push/Settings初始化、通知拉起、小艺A2A |
| [主页面（Index）](codebase-knowledge/主页面（Index）.md) | 大字异动卡片流、点卡即听、轮询兜底 |
| [设置页面（Settings）](codebase-knowledge/设置页面（Settings）.md) | 自选股/播报/字体/主题/免打扰设置 |
| [轮询服务（AlertPoller）](codebase-knowledge/轮询服务（AlertPoller）.md) | 前台5s轮询、退避策略、429限流 |
| [音频播放服务（AudioPlayer）](codebase-knowledge/音频播放服务（AudioPlayer）.md) | AVPlayer云端TTS音频播放 |
| [推送服务（PushService）](codebase-knowledge/推送服务（PushService）.md) | Push Kit封装、AGC降级、Token上报 |
| [设置服务（SettingsService）](codebase-knowledge/设置服务（SettingsService）.md) | Preferences持久化、全量设置项 |
| [数据契约（AlertItem）](codebase-knowledge/数据契约（AlertItem）.md) | AlertItem/AlertFeed接口定义 |
| [数据管道服务器（feed-server）](codebase-knowledge/数据管道服务器（feed-server）.md) | 异动检测、TTS生成、HTTP服务 |
| [音频后处理模块（audio-postprocess）](codebase-knowledge/音频后处理模块（audio-postprocess）.md) | HRTF渲染、EQ滤波、动态压缩 |

### 维度二：项目规范知识（[project-knowledge/](project-knowledge/index.md)）

按横切主题组织，描述全仓层面的规范和约定。

| 主题 | 说明 |
|------|------|
| [构建系统](project-knowledge/build_system/build_system.md) | hvigorw、devecocli、Stage模型 |
| [配置体系](project-knowledge/configuration_system/configuration_system.md) | build-profile、module.json5、oh-package |
| [日志系统](project-knowledge/logging_system/logging_system.md) | hilog统一框架、TAG/DOMAIN约定 |
| [异常处理](project-knowledge/error_handling/error_handling.md) | 静默降级策略、错误回调机制 |
| [依赖管理](project-knowledge/dependency_management/dependency_management.md) | 零三方依赖、HarmonyOS Kits |
| [业务术语](project-knowledge/business_term/business_term.md) | 铃语、异动、适老化、信号卡/事实卡 |
| [HarmonyOS Kits](project-knowledge/external_dependency/harmonyos_kits.md) | @kit.*官方Kit使用详情 |
| [百炼TTS](project-knowledge/external_dependency/bailian_tts.md) | CosyVoice语音合成服务 |

## 架构基调

- **EntryAbility**：Push初始化 + onNewWant带alertId拉起定位
- **Index.ets**：List卡片流 + 5s前台轮询（AlertPoller）兜底
- **AudioPlayer**：AVPlayer播云端TTS音频流
- **数据源**：FEED_URL待X服务器落地后替换，契约即AlertFeed
- **降级链**：Push未实装→轮询兜底→首屏示例卡

## 硬约束

1. **适老化**：主界面=大字白话卡片流（28-34fp高对比深色底），禁止K线图/走势图等复杂图表
2. **信号松绑**：允许自家策略信号（kind="signal"），禁收益承诺/催促指令/对外公开收费
3. **平台**：Stage模型，compatibleSdkVersion 6.0.2(22)，纯ArkTS，零三方依赖
4. **PushService保持占位封装**：AGC未配置前自动降级轮询
5. **首屏永不空白**：服务未连通时显示带"示例"字样的演示卡