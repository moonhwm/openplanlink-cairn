# 行情播报工程 · 任务白皮书 R3（Push Kit 实装）

> 版本：R3.0 草案（2026-09-15，砚坚起草，待白秉烛核准）
> 执行席：码道 IDE · 鸿蒙开发智能体 · GLM-5.2-ArkTS-SPARK
> 前置条件：R1（卡片流加固）+ R2（设置页实装）+ R2a（补件）均已闭环
> 本文档定义 Push Kit 实装的完整技术方案。执行前必须先读本工程根目录的 `AGENTS.md` 与 `CHANGELOG.md`。

---

## 第一章 · 任务范围与前置条件

R3 的目标是：**把 PushService.ets 从占位封装升级为真实 Push Kit 集成**，实现云端异动 → Push Kit 推送 → 锁屏通知 → 点按拉起 → 自动播报的完整链路。

### 1.1 前置条件（机主操作，砚坚无法替代）

| # | 操作 | 责任方 | 预计耗时 | 状态 |
|---|------|--------|----------|------|
| P1 | 华为个人开发者注册（免费） | 机主 | 已完成 | ✅ |
| P2 | AppGallery Connect 建项目+应用，bundleName=`com.yehang.stockpulse` | 机主 | 10 分钟 | ✅ 已完成（2026-09-16） |
| P3 | AGC 开通 Push Kit 服务 | 机主 | 5 分钟 | ✅ 已完成（2026-09-16） |
| P4 | 下载 `agconnect-services.json` 放 `AppScope/resources/rawfile/` | 机主 | 5 分钟 | ✅ 已完成（2026-09-16） |
| P5 | AGC 申请订阅通知自分类权益（SUBSCRIPTION 类型） | 机主 | 约 15 工作日 | ⏳ 申请中（2026-09-16） |
| P6 | X 服务器落地（FEED_URL 替换 + Push Token 上报接口） | 顾权席 | 待定 | 待办 |

**P5 是关键路径瓶颈**——订阅通知自分类权益审批约 15 工作日，在审批通过前无法推送 SUBSCRIPTION 类通知。审批期间可先用 DEFAULT 类通知（不需自分类权益）进行开发调试。

### 1.2 砚坚可自主完成的工作（不依赖 P2-P6）

| # | 工作 | 依赖 |
|---|------|------|
| W1 | PushService.ets 实装 getToken + 重试逻辑 | 无（代码层面可写，运行需 P2-P4） |
| W2 | PushMessageAbility 新建（接收场景化消息） | 无 |
| W3 | module.json5 配置更新（action.ohos.push.listener） | 无 |
| W4 | EntryAbility 集成 PushService.getToken 调用 | 无 |
| W5 | serviceNotification.requestSubscribeNotification 调用 | 无（代码层面可写，运行需 P5） |
| W6 | Push Token 上报接口封装（reportToken） | 无（接口地址待 P6） |

**策略**：砚坚先完成 W1-W6 全部代码编写，机主完成 P2-P4 后即可联调，P5 审批期间用 DEFAULT 类通知调试。

---

## 第二章 · 技术方案

### 2.1 PushService.ets 实装

当前 PushService.ets 是占位封装，`init` 中只做 AGC 配置探针。R3 需要解封 TODO，实装以下功能：

```typescript
import { pushService } from '@kit.PushKit';
import { BusinessError } from '@kit.BasicServicesKit';
```

**getToken 流程**：
1. `init(context)` 中调用 `pushService.getToken()` 获取 Push Token
2. 成功 → 调用 `reportToken(token)` 上报到 X 服务器
3. 失败 → 按错误码判断是否重试（1000900001/0008/0009/0011 可重试，最多 3 次，间隔 1s）
4. AGC 配置缺失 → 降级为仅日志（保持现有行为）

**关键约束**：
- `getToken()` 必须在 Stage 模型 UIAbility 的 `onCreate` 中调用
- Token 长度约 112 字符但可能变化，不要固定判断长度
- 不要频繁申请 Token，建议每次启动时获取一次
- `pushService` 模块从 API 4.0.0(10) 起可用，本项目 compatibleSdkVersion=20 满足

**reportToken 上报**：
- POST 到 X 服务器 `/api/push/register`
- 请求体：`{ token: string, bundleName: "com.yehang.stockpulse" }`
- 失败时 hilog warn，不影响 App 主流程
- 接口地址待 P6（X 服务器落地）后替换，当前用占位 URL

### 2.2 PushMessageAbility 新建

官方文档要求：接收 Push Kit 场景化消息的 Ability 需在 `module.json5` 的 `skills` 中配置 `action.ohos.push.listener`。

**方案选择**：
- **方案 A**（推荐）：复用 EntryAbility，在其 skills 中新增 `action.ohos.push.listener`
- **方案 B**：新建独立 PushMessageAbility

选方案 A——理由：本工程是单入口应用，新增 Ability 增加复杂度；EntryAbility 已处理 `onNewWant` 中的 alertId，复用更自然。

**module.json5 修改**：
```json5
{
  "name": "EntryAbility",
  "skills": [
    {
      "entities": ["entity.system.home"],
      "actions": ["action.system.home"]
    },
    {
      "actions": ["action.ohos.push.listener"]  // 新增：Push Kit 消息接收
    }
  ]
}
```

**EntryAbility.onCreate 中新增**：
```typescript
// 接收 DEFAULT 场景化消息（应用在前台时处理通知）
pushService.receiveMessage('DEFAULT', this, (data: pushCommon.PushPayload) => {
  hilog.info(DOMAIN, TAG, `received push message: ${JSON.stringify(data)}`);
  // 处理逻辑：从 data 中提取 alertId，写入 AppStorage，由 Index 消费
});
```

### 2.3 订阅通知自分类（SUBSCRIPTION）

**serviceNotification.requestSubscribeNotification**：
- 在 `onForeground` 中调用（用户可见时弹出授权弹窗）
- `entityIds` 为 AGC 平台申请的订阅模板 ID
- 用户同意后，服务端才能推送该模板对应的消息
- 接口调用间隔需大于 1 秒

**调用时机**：
- 首次启动：`onForeground` 中调用 `requestSubscribeNotification`
- 后续启动：检查是否已订阅（通过 `querySubscribeNotificationSetting`，API 26+）
- 用户拒绝后：不反复弹窗，在 Settings 页面提供「重新订阅」入口

**注意**：P5（自分类权益审批）未通过前，此调用会返回错误码 1000900025（No rights to access entity id）。审批期间注释掉此调用，用 DEFAULT 类通知调试。

### 2.4 通知 click → alertId → 自动播报链路

当前已实装：
- `onCreate` 补检 `want.parameters.alertId` → `AppStorage.setOrCreate('pendingAlertId', alertId)`
- `onNewWant` 处理 `want.parameters.alertId` → 同上
- `Index.aboutToAppear/onPageShow` → `checkPendingAlertId()` → `playById(pending)`

R3 需确认：
- Push Kit 通知 click 携带的参数格式——`want.parameters` 中 `alertId` 的键名是否与服务端下发时的 `click.action` 参数一致
- 服务端 Push Kit REST API 下发通知时，`click.action` 参数格式：`{ "alertId": "600176-20260914-093512" }`
- 端侧 `want.parameters.alertId` 读取——需真机验证键名匹配

### 2.5 Push Kit REST API（服务端侧，顾权席参考）

服务端调用 Push Kit REST API 下发通知的请求体示例：

```json
{
  "pushToken": "<设备 Push Token>",
  "pushType": "DEFAULT",
  "notification": {
    "title": "中国巨石 2 分钟上涨 2.3%",
    "body": "现价 25.43 元，成交放大 3.1 倍",
    "clickAction": {
      "action": "com.yehang.stockpulse.OPEN_ALERT",
      "parameters": {
        "alertId": "600176-20260914-093512"
      }
    }
  }
}
```

**关键约束**：
- `pushType: "DEFAULT"` 不需自分类权益，审批期间用此类型
- `pushType: "SUBSCRIPTION"` 需自分类权益（P5），审批通过后切换
- 通知标题和正文须遵循适老化原则：大字、白话、无术语
- 通知 click 参数中 `alertId` 是端侧定位异动卡片的唯一标识

---

## 第三章 · 代码改动清单

| 文件 | 改动 | 依赖 |
|------|------|------|
| `PushService.ets` | 解封 TODO，实装 getToken + 重试 + reportToken | P2-P4（运行时） |
| `EntryAbility.ets` | 新增 receiveMessage('DEFAULT') 调用；新增 requestSubscribeNotification（P5 后启用） | P2-P4（运行时） |
| `module.json5` | EntryAbility skills 新增 `action.ohos.push.listener` | 无 |
| `Settings.ets` | 新增「推送订阅」区域（P5 后启用，审批期间隐藏） | P5 |
| `SettingsService.ets` | 新增 pushSubscribed 状态持久化 | P5 |

**不改动的文件**：
- `AGENTS.md`（硬约束）
- `AlertItem.ets`（数据契约）
- `Index.ets`（通知拉起链路已在 R1 实装，R3 不改）
- `AudioPlayer.ets`（播报逻辑已在 R1 加固，R3 不改）
- `AlertPoller.ets`（轮询兜底保持不变，Push 实装后作为补偿）

---

## 第四章 · 验收标准

| # | 验收项 | 验证手段 | 前置条件 |
|---|--------|----------|----------|
| V1 | getToken 成功获取 Push Token | 真机 hilog 查看 token 输出 | P2-P4 |
| V2 | Token 上报到 X 服务器 | 服务端日志确认收到 token | P6 |
| V3 | AGC 未配置时降级为仅日志 | 删除 agconnect-services.json 后启动 App | 无 |
| V4 | receiveMessage 接收 DEFAULT 消息 | 服务端下发测试消息，hilog 确认接收 | P2-P4 + P6 |
| V5 | 通知 click 拉起 App 并定位异动卡片 | 真机点按通知，确认卡片定位+自动播报 | P2-P4 + P6 |
| V6 | requestSubscribeNotification 弹出授权弹窗 | 真机调用后观察弹窗 | P5 |
| V7 | module.json5 skills 配置正确 | `grep 'action.ohos.push.listener' module.json5` | 无 |
| V8 | catch 子句带参数无类型标注 | `grep 'catch\s*([^)]*:' *.ets` 无结果 | 无 |
| V9 | 零三方依赖 | `oh-package.json5 dependencies` 为空 | 无 |
| V10 | 契约双文件 diff 为空 | `git diff HEAD -- AGENTS.md AlertItem.ets` | 无 |

---

## 第五章 · 禁止事项

1. 禁止修改 `AGENTS.md`、`AlertItem.ets` 契约字段
2. 禁止引入三方依赖
3. 禁止引入 K 线图/走势图/任何图表组件
4. 禁止在通知标题/正文中出现买卖建议措辞（三不赦红线）
5. 禁止把 FEED_URL 改为真实外网地址（R4 任务）
6. 禁止删除 DEMO_ITEMS 首屏兜底
7. 禁止在 P5 审批通过前启用 SUBSCRIPTION 类通知（会报错码 1000900025）

---

## 第六章 · 交付与留痕

1. `git add -A && git commit -m "R3: Push Kit 实装"`
2. `CHANGELOG.md` 追加条目，模板：

```markdown
## YYYY-MM-DD HH:mm · 砚坚（码道·鸿蒙开发智能体/ArkTS-SPARK）· R3 Push Kit 实装

- 改了什么：<逐文件列出>
- 为什么这么改：<对应本白皮书章节号>
- 如何验证：<V1-V10 逐条结果>
- 遗留：<未做完/发现但超范围的问题>
```

3. 自报块 JSON 含 `git_show_stat` 实测数据
4. V9-V10 验证项使用可复制命令序列

---

## 第七章 · 依赖与时间线

```
机主操作          砚坚编码           顾权席服务端
─────────         ─────────          ─────────
P2 AGC 建项目  →  W1 getToken    →  P6 X 服务器
P3 开通 Push   →  W2 receiveMsg  →     Token 上报接口
P4 下载配置    →  W3 module.json5 →     Push REST API
P5 自分类权益  →  W4 EntryAbility →     下发通知
   (15工作日)  →  W5 subscribe   →
                  W6 reportToken  →
```

**关键路径**：P5（15 工作日）是最大瓶颈。建议：
1. 机主立即启动 P2-P5（AGC 操作 + 权益申请）
2. 砚坚在 P5 审批期间完成 W1-W6 全部代码编写
3. P2-P4 完成后即可用 DEFAULT 类通知联调
4. P5 通过后切换 SUBSCRIPTION 类通知

---

## 第八章 · 文档出处

| 内容 | URL | 更新日期 |
|------|-----|----------|
| getToken 指南 | developer.huawei.com/consumer/cn/doc/harmonyos-guides/push-get-token | 2026-09-09 |
| pushService API | developer.huawei.com/consumer/cn/doc/harmonyos-references/push-pushservice | 2026-09-09 |
| serviceNotification API | developer.huawei.com/consumer/cn/doc/harmonyos-references/push-servicenotification | 2026-08-29 |
| PushPayload 结构 | developer.huawei.com/consumer/cn/doc/harmonyos-references/push-pushcommon#pushpayload | 2026-09-09 |

---

## §P5-A 消息类型申请定案（2026-09-16 · 砚坚分析，机主裁定）

### 申请消息类型勾选（3项）

| 消息类型 | 勾选 | 理由 |
|----------|------|------|
| **订阅** | ✅ | 核心匹配：用户主动添加自选股→系统推送异动提醒，等同于"主动设置的商品降价提醒" |
| **账号动态** | ✅ | 辅助匹配：账号安全通知（异地登录等），预留未来用户体系扩展 |
| **音频、视频通话** | ✅ | **预留扩展**：受豆包电话功能启发——未来铃语可能扩展AI语音交互（如长辈语音问答、重大异动AI语音通知），此类型为"来电提醒"场景预留 |
| 即时聊天 | ❌ | 铃语非聊天应用，AGENTS.md禁止催促性指令和对外收费形态 |
| 健康 | ❌ | 仅限运动类/健康类App，铃语不符合准入条件 |
| 财务 | ❌ | 仅限金融银行类/支付类App，铃语不是持牌金融机构 |
| 出行/订单物流/设备提醒/邮件/工作事项提醒 | ❌ | 均与铃语场景无关 |

### "音频、视频通话"预留决策的深度分析

豆包（ByteDance AI助手）的"电话"功能提供了重要启发：用户拨打豆包号码→AI接听→实时语音对话。铃语未来可能扩展的同构场景：
- 长辈收到异动推送→想了解更多→"打电话给铃语"→AI语音解答
- 重大异动时铃语主动"回拨"——AI语音通知（比文字推送更适老）

当前铃语的语音交互是App内TTS播报（AVPlayer播放云端音频流），不涉及电信通话。但AGC"音频、视频通话"类型的"来电提醒"子场景，为未来AI语音交互扩展预留了可能性。申请成本为零，预留有备无患。

---

## §P2-A AGC 注册与开放能力定案（2026-09-16 · 顾权代机主令，外池评审收官）

### 注册值（终审）
- 应用所属项目：**塔铃**（新建；「塔上一铃独自语」——项目=塔、应用=铃语）
- 应用名称：**铃语**（苏轼「塔上一铃独自语，明日颠风当断渡」；外池三判官斩「振铎」（撞郑振铎+生僻死结）后定案）
- 应用包名：**com.yehang.stockpulse**（与 AppScope/app.json5 bundleName 逐字一致，不可改）
- 应用分类：**应用**

### 开放能力勾选（外池 5 席评审：glm-4.7/GLM-5.2/DS-v4-flash/DS-v4-pro/doubao·hy4·GLM-5.3·K2.8 缺席登记在案）
**勾选**：推送服务、推送语音播报消息（受限申请：适老化语音提醒需推送后唤醒播报）、锁屏卡片、优先通知、代理提醒、实况窗服务（限调测期）、华为账号。
**新增勾选（3/5 票通过）**：**AI问答联网增强服务**——申请理由草稿：「用于长辈语音问答/传言核查时检索公开时效信息，检索结果经 K3 集群二次核验后合成语音播报；不直接展示检索结果，不构成投资建议。」启用时点=语音问答功能立项时；隐私政策增量一句（语音提问去标识化后用于联网检索）。
**不勾（多数否决）**：钱包/IAP（5/5）、App Linking（1:4）、云存储/云托管（5/5）、认证服务（5/5）、RISC（5/5）、围栏后台唤醒（5/5）、接续服务（5/5）、安全检测服务（1:4，GLM-5.2「防二次打包诈骗」论据登记为异常流量信号时启用）、待机屏保卡片（2:3，AOD 零操作常显与锁屏大字同族，列为锁屏族第一扩展候补）、Wear Engine（暂缓：手表播报立项日再勾，预支穿戴+音频+蓝牙三笔成本现在属负债）。
**敏感权限七项**（定位/位置语义/室内定位/蓝牙/运动健康/背板透明/设备状态检测）：5/5 不勾——零业务关联+隐私弹窗恐慌成本。

### 判官席缺席登记（如实）
- GLM-5.3（chatglm 积分 web 通道）：浏览器扩展断连，待重连后补评；
- K2.8（moonshot api.kimi.com/coding）：access_token 已于 2026-09-06 过期且目录无 k2.8 名目，需先刷新再探；
- doubao 全系（ark）：seed/pro/lite 均 404 无访问权限（账户仅 deepseek 系可用）；
- hy4-preview（tokenhub）：探针 HTTP 200 实证可用，但长任务 560s 读超时（思考型需流式通道），席位暂缺。
