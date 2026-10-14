---
name: A12-alertId传递链路审查
type: code
created: 2026-09-24
updated: 2026-09-24
version: 1.0.0
trigger: 审查或维护 alertId 在推送→拉起→播报全链路的传递机制
source_files: [entry/src/main/ets/entryability/EntryAbility.ets, entry/src/main/ets/pages/Index.ets]
---

# A12 · alertId 传递链路审查

## 概述

alertId 是异动条目的唯一标识，贯穿"云端监测→Push推送→通知点击→App拉起→定位卡片→自动播报"全链路。链路中任一环节丢失 alertId 都会导致用户点击通知后无法定位到对应异动卡片。

## 链路环节

| 环节 | 传递方式 | 关键代码 | 修复历史 |
|------|---------|---------|---------|
| 1. 云端生成 | fetch-tushare-data 生成 alertId 写入 alerts.json | `alertId: ${symbol}_${ts}` | — |
| 2. Push推送 | broadcast-a2a 发送Push通知，payload携带 alertId | `data: { alertId }` | — |
| 3. 通知点击 | 系统通知点击 → Want.parameters.alertId | `want?.parameters?.alertId` | — |
| 4. 冷启动 onCreate | onCreate 读取 want.parameters.alertId → AppStorage | `AppStorage.setOrCreate('pendingAlertId', alertId)` | **白皮书§3.3.2修复**：原代码只在onNewWant处理，冷启动点通知会丢失 |
| 5. 后台 onNewWant | onNewWant 读取 want.parameters.alertId → AppStorage | `AppStorage.setOrCreate('pendingAlertId', alertId)` | — |
| 6. 前台 pushService.receiveMessage | DEFAULT类型消息直接传递给应用 → AppStorage | `AppStorage.setOrCreate('pendingAlertId', alertId)` | — |
| 7. Index.checkPendingAlertId | 读取 AppStorage.pendingAlertId → playById | `const pending = AppStorage.get('pendingAlertId')` | — |
| 8. playById 定位播报 | 在 items 中查找 alertId → togglePlay | `this.items.find((it) => it.alertId === id)` | — |

## 小艺 A2A 链路（三条 action）

| action | 传递方式 | autoPlay标志 | force参数 |
|--------|---------|-------------|----------|
| PLAY_AUDIO | pendingAlertId + autoPlay=true | ✅ 设置 | force=true（无视播报开关/免打扰） |
| DETAIL_ALERT | pendingAlertId（无autoPlay） | ❌ 不设置 | force=false（受播报开关/免打扰约束） |
| QUERY_ALERTS | xiaoYiQuery=true（无消费方，待对接） | ❌ 不设置 | — |

## 审查结论

- ✅ 冷启动缺口已修复（onCreate补检 want.parameters.alertId）
- ✅ 后台拉起路径完整（onNewWant → AppStorage → onPageShow → checkPendingAlertId）
- ✅ 前台DEFAULT消息路径完整（receiveMessage → AppStorage → checkPendingAlertId）
- ✅ 小艺PLAY_AUDIO force参数正确绕过播报开关/免打扰
- ✅ xiaoYiQuery 诚实标注"待小艺A2A数据返回协议对接"
- ✅ alertId 不在列表中时静默清除（不报错、不显示空白）

## 关联文档

- A22_EntryAbilityets审查P.md（EntryAbility审查）
- A23_Indexets审查List卡片流渲.md（Index审查）

### 自我评估
- 正确性：5分 链路环节和修复历史均直接取自源码和CHANGELOG
- 完整性：5分 覆盖8个环节+3条小艺action链路
- 可复用性：4分 alertId传递链路设计模式可迁移到其他Push通知+App拉起场景
- 字数：约900字
- 使用模型：GLM-5.2-SFT-Harmony