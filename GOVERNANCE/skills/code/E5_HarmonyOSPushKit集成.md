# HarmonyOS Push Kit 集成——REST API 调用、Token 注册、消息接收、降级策略

> 适用项目：harmony-app（铃语，适老化股票异动播报）。已知问题定位：`broadcast-a2a` 云函数现用的推送通道需更换为华为 Push Kit REST；端侧 `entry/src/main/ets/services/PushService.ets` 保持占位封装，AGC 未配置前降级轮询（5s 前台 AlertPoller 兜底，首屏永不空白——服务未连通显示带"示例"字样演示卡）。
> 本文归档于 `GOVERNANCE/skills/code/`，与 `A19_pushtokenregister云.md`（云函数审查）、`A22_EntryAbilityets审查P.md`（EntryAbility 审查）、`A26_PushServiceets审查占位.md`（占位封装审查）联动。端点域名与接口形态经公开资料核对（2026-09-23 检索）：鉴权 `https://oauth-login.cloud.huawei.com/oauth2/v3/token`（OAuth 2.0 client_credentials）、发消息 `https://push-api.cloud.huawei.com/v3/{projectId}/messages:send`（Bearer Token）；**请求体字段与错误码以华为官方 REST 文档为准**，本文不虚构具体码值。

---

## 一、端到端链路总览

```
[端侧] EntryAbility 启动 → PushService.init() → pushService.getToken()
   → 拿到 Push Token → 上报云函数 push-token-register（绑定用户/设备）
[云端] 异动产生（get-alerts/broadcast-a2a）→ 取 OAuth access_token
   → POST /v3/{projectId}/messages:send（目标=Token，通知消息带 alertId）
[端侧] 系统通知栏展示 → 用户点击 → 拉起 EntryAbility
   → onCreate/onNewWant 的 want 参数解析 alertId → 定位到对应卡片
[兜底] 任一环节失败 → Index.ets 5s 前台轮询 AlertPoller，卡片流照常刷新
```

设计原则（不可推翻的架构基调）：**Push 是加速器，轮询是底座。** 推送全链路任何一环失败，都不影响应用可用性；PushService.ets 的占位封装就是为了让"无 Push"与"有 Push"两种形态共存于同一套代码。

## 二、端侧接入：权限、Token 获取、通知授权

### 2.1 前置条件

1. AppGallery Connect 开通推送服务（获得发消息资格，产生 client 凭据与 projectId）；
2. `module.json5` 声明权限：`ohos.permission.PUSH_SERVICE_TOKEN`；
3. 工程关联 AGC 默认配置（client_id 等 metadata），以官方接入指引的当前版本为准。

### 2.2 获取 Push Token

```ts
// services/PushService.ets —— 占位封装的真实实现形态
import { pushService } from '@kit.PushKit';
import { BusinessError } from '@kit.BasicServicesKit';

export class PushService {
  private static token: string | null = null;
  private static enabled: boolean = false;   // AGC 是否已配置

  static async init(): Promise<void> {
    if (!this.enabled) {
      return;   // 占位：未配置直接返回，绝不抛错影响启动
    }
    try {
      this.token = await pushService.getToken();
      await this.reportToken(this.token);
    } catch (e) {
      const err = e as BusinessError;
      // 只记日志，不上抛：降级路径由轮询接管
      console.error(`[Push] getToken failed: ${err.code}`);
    }
  }

  static async reportToken(token: string): Promise<void> {
    // 见 §三；注意 token 只发往自家云函数，不进任何日志
  }
}
```

要点：

1. **时机**：在 EntryAbility 创建后调用（架构基调：EntryAbility = Push 初始化），不要放到页面里；
2. **getToken 幂等可重复调**：系统未生成时可能失败，可在下次启动重试；
3. **通知授权**：通知消息要在通知栏展示，还需引导用户开启通知授权（`requestEnableNotification`，用户拒绝后仅剩应用内卡片 + 轮询，不反复弹窗骚扰——适老化底线）；
4. **失败静默**：端侧所有 Push 调用 catch 后只记日志，永不阻塞启动链路。

## 三、Token 注册：push-token-register 云函数契约

端侧拿到 Token 后上报自家云函数登记，云端发消息时按登记表取 Token：

1. **入参**：`{ pushToken, deviceId?, appVersion? }`——按 A19 审查的现有契约核对字段，勿私自改名；
2. **存储**：云函数侧写库（表名与结构以 A19 审查结论为准），支持同一设备 Token 更新覆盖（Token 可能随系统重置刷新）；
3. **安全**：Token 走 HTTPS 只进云函数；**绝不写入端侧日志、绝不随埋点外发**——Token 外泄等于他人可向用户设备投递消息；
4. **幂等**：重复上报同 Token 应为无害写，端侧重试不会产生脏数据。

## 四、REST API 调用（云函数侧，broadcast-a2a 改造）

### 4.1 两步调用

**第一步：取 access_token（OAuth 2.0 client_credentials）**

```js
// cloudfunctions/functions/broadcast-a2a/push.js
const qs = require('querystring');

async function getAccessToken() {
  const body = qs.stringify({
    grant_type: 'client_credentials',
    client_id: process.env.PUSH_CLIENT_ID,      // 凭据只放环境变量
    client_secret: process.env.PUSH_CLIENT_SECRET,
  });
  const res = await fetch('https://oauth-login.cloud.huawei.com/oauth2/v3/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  const data = await res.json();
  // access_token 有效期有限（约小时级）：务必缓存复用，见 §4.3
  return data.access_token;
}
```

**第二步：发通知消息**

```js
async function sendPush(accessToken, tokens, alertId, title, body) {
  const projectId = process.env.PUSH_PROJECT_ID;
  const res = await fetch(
    `https://push-api.cloud.huawei.com/v3/${projectId}/messages:send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      // 字段名以官方 REST 文档为准，以下为常见形态
      pushType: 'ALK',                        // 通知栏消息
      target: { token: tokens },
      payload: {
        notification: {
          category: process.env.PUSH_CATEGORY, // 消息自分类权益（AGC 申请）
          title: title,                        // 适老化白话标题
          body: body,                          // 白话正文
          clickAction: {
            actionType: 0,                     // 点击打开应用
            data: JSON.stringify({ alertId }), // 端侧从 want 解析
          },
        },
      },
    }),
  });
  return res.json();   // 按响应体 code 分类处理
}
```

### 4.2 必守纪律

1. **凭据只在云函数环境变量**（PUSH_CLIENT_ID / PUSH_CLIENT_SECRET / PUSH_PROJECT_ID），端侧零感知；**不泄露任何 Token/密钥是合规红线**，日志里出现凭据即事故；
2. **projectId 必须与鉴权凭据同源**：URL 里 projectId 与 Token 所属项目不匹配是常见错误源（公开资料反复提示）；
3. **category 须在 AGC 申请消息自分类权益**，未获批的类目会被拒绝；铃语属资讯/财经播报类，申请时如实填报，不得按 IM 类目伪装绕过；
4. **通知文案过合规三禁**：不承诺收益/保本（禁"稳赚""保本"）、无催促性指令（禁"马上买入""立即行动"）、不涉对外公开/收费——Push 文案与卡片文案同池治理，云端发送前过同一套敏感词闸。

### 4.3 工程化细节

1. **access_token 缓存**：存云函数实例级内存（变量 + 到期时间），过期再取；每次发消息都先取 Token 会被限流；
2. **批量与限流**：target.token 支持数组，按批投递；响应限流类错误退避重试，单条失败不影响整批；
3. **Token 失效处理**：设备 Token 过期/重置后发送会报目标非法类错误，云函数应将该 Token 从登记表剔除（或标记失效），等端侧下次 getToken 重报；
4. **结果可观测**：发送成功/失败计数与错误分类落云函数日志，端侧不感知。

## 五、消息接收：点击通知拉起与 alertId 定位

1. **通知消息由系统通知栏展示**，应用无需在前台；用户点击后系统拉起应用，消息的 clickAction.data 进入 UIAbility 的 want 参数——这是铃语主通道，与架构基调（EntryAbility = onNewWant 带 alertId 拉起定位）完全对齐；
2. EntryAbility 两侧都要接：**onCreate**（冷启动）与 **onNewWant**（热启动在通知栏再点），从 want 参数解析 `alertId`，传递给 Index.ets 定位滚动到对应卡片（LazyForEach 场景用 scrollToIndex）；
3. **透传消息**（应用自处理数据、不经通知栏）需要应用进程在线配合，链路弱、时序不可控，铃语不依赖它做核心通道；若未来用于"应用内实时刷新提示"，须实测其到达时序，且永远不作为唯一路径；
4. data 建议小而结构化（仅 alertId），大文本不放 Push payload——正文靠端侧 get-alerts 拉取，Push 只做"门铃"不做"信封"。

## 六、降级策略（铃语核心约束）

降级不是异常分支，是**常态设计**——AGC 未配置期间全量用户都走降级路径。降级矩阵：

| 故障点 | 表现 | 降级动作 |
| --- | --- | --- |
| AGC 未配置/未开通 | PushService.enabled=false | init 直接返回，纯轮询形态 |
| getToken 失败 | 端侧无 Token | 记日志，下次启动重试；轮询不受影响 |
| 通知授权被拒 | 通知栏无展示 | 应用内卡片 + 轮询照常；不反复弹窗 |
| Token 上报失败 | 云端无登记 | 端侧重试；已登记设备不受影响 |
| access_token 获取失败 | 云端发不出 | 重试 + 告警；异动数据仍在 feed，轮询兜底 |
| messages:send 失败 | 部分设备无通知 | 错误分类落日志；轮询兜底 |
| Push 送达但用户未点 | 无拉起 | 轮询刷新后卡片流自然可见 |

三条总纪律：**① Push 永不阻塞启动与首屏**（首屏由演示卡兜底，永不空白）；**② 任何 Push 失败静默降级，用户无感知报错**；**③ PushService.ets 保持占位封装形态**——`init()` 对外签名不变，内部按 enabled 分支，未来 AGC 配置完成只是翻转开关，不改调用方。

## 七、接入检查清单

1. module.json5 是否声明 `ohos.permission.PUSH_SERVICE_TOKEN`？
2. getToken 是否 catch 静默、不阻塞 EntryAbility 启动？
3. Token 是否只上报自家云函数、全链路（端侧日志/云函数日志）无 Token 明文？
4. 云函数凭据是否全在环境变量？日志是否脱敏？
5. access_token 是否缓存复用？projectId 与凭据是否同源？
6. 通知文案是否过三禁闸（不承诺收益/保本、无催促指令、不涉公开收费）？
7. onCreate 与 onNewWant 是否都解析 alertId 并定位卡片？
8. 降级矩阵每一行是否都有对应代码路径，且失败静默？
9. 首屏演示卡是否与 Push 状态完全解耦（未连通也有内容）？

## 八、端侧 alertId 解析参考实现（EntryAbility）

通知点击拉起的数据经 want 传给 UIAbility，冷热启动两条路都要接：

```ts
// entry/src/main/ets/entryability/EntryAbility.ets
import { Want } from '@kit.AbilityKit';

export default class EntryAbility extends UIAbility {
  pendingAlertId: string | null = null

  onCreate(want: Want): void {           // 冷启动
    PushService.init()                   // Push 初始化（架构基调）
    this.pendingAlertId = this.extractAlertId(want)
  }

  onNewWant(want: Want): void {          // 热启动再点通知
    this.pendingAlertId = this.extractAlertId(want)
    this.emitToIndex(this.pendingAlertId)
  }

  private extractAlertId(want: Want): string | null {
    // clickAction.data 的解析形态以 SDK/文档为准；约定为 JSON 字符串
    const raw = want?.parameters?.['pushData'] ?? want?.parameters?.['data']
    if (typeof raw !== 'string' || raw.length === 0) return null
    try {
      const parsed = JSON.parse(raw) as Record<string, string>
      return parsed.alertId ?? null
    } catch {
      return null
    }
  }

  private emitToIndex(id: string | null): void {
    // 事件总线或 AppStorage 传递，Index 拿到后 scrollToIndex 定位
  }
}
```

三条纪律：解析失败返回 null 静默降级，应用正常进入首页（Push 数据形态异常不能拦住启动）；alertId 只做定位不做内容渲染——正文永远从 get-alerts 拉，Push 里的 data 保持"门铃"定位；Index 侧消费后清空 pending，防止重复定位。

## 九、push-token-register 云函数参考实现

```js
// cloudfunctions/functions/push-token-register/index.js
exports.main = async (event) => {
  const { pushToken, deviceId, appVersion } = event.body ?? {}
  if (typeof pushToken !== 'string' || pushToken.length < 10) {
    return { ok: false, reason: 'invalid_token' }   // 不落 token 内容，只落结论
  }
  // 同设备覆盖写：Token 刷新后旧值自然被替换
  await db.collection('push_tokens').doc(deviceId).set({
    pushToken, appVersion, updatedAt: Date.now(),
  })
  return { ok: true }
}
```

要点：日志与返回体里**永不出现 Token 明文**，失败只回原因码；写库幂等（docId=deviceId 覆盖）；入参做最小形状校验，脏数据进不了库。字段契约以 A19 审查结论为准，本示例是形状示意。

## 十、access_token 缓存与批量重试工程化

云函数实例级缓存 + 过期重取 + 失败退避，是发消息前的标准三件：

```js
let cached = { token: '', expireAt: 0 }

async function getToken(): Promise<string> {
  if (cached.token && Date.now() < cached.expireAt - 60_000) {
    return cached.token                       // 提前 60s 失效，避开边界
  }
  const data = await requestOAuth()           // §4.1 的两步之第一步
  cached = { token: data.access_token,
             expireAt: Date.now() + (data.expires_in ?? 3600) * 1000 }
  return cached.token
}

async function sendWithRetry(tokens, payload, maxRetry = 2): Promise<void> {
  for (let i = 0; i <= maxRetry; i++) {
    const token = await getToken()
    const res = await sendPush(token, tokens, payload)
    if (isOk(res)) return
    if (isTokenExpired(res)) { cached = { token: '', expireAt: 0 }; continue }  // 换新 token 重试
    if (!isRateLimited(res)) break            // 非限流类错误不盲重
    await sleep(500 * 2 ** i)                 // 限流退避
  }
}
```

凭据全部来自环境变量（PUSH_CLIENT_ID / PUSH_CLIENT_SECRET / PUSH_PROJECT_ID），示例与测试均不出现可用凭据字面量；错误分类的判定规则以官方错误码表为准，先落"分类框架"，码值接入时对表填入。

## 十一、测试与灰度验证方法

不依赖端侧也能先把云端链路验通：

1. **REST 两步联调**（curl，凭据用环境变量注入，命令里只写占位）：第一步取 access_token（检查返回体含 token 与 expires_in），第二步向**自己一台测试设备的 Token** 发一条测试通知——先在真机看到通知栏弹出，再验证点击拉起与 alertId 定位；
2. **失败注入**：故意用过期 access_token、错 projectId、伪造 Token 各发一次，确认错误被正确分类落日志且不重试风暴；
3. **端到端灰度顺序**：开发者设备 → 小范围体验用户 → 全量；每级观察送达率（发送成功数 / 登记设备数）与点击率，异常回滚只需把广播开关关回轮询形态——降级设计保证了回滚零成本；
4. **文案过闸抽检**：灰度期每天抽推送文案过三禁词闸（不承诺收益/保本、无催促指令、不涉公开收费），Push 文案与卡片文案同池治理；
5. **端侧降级演练**：AGC 配置暂时关掉，确认应用启动、首屏演示卡、5s 轮询全部正常——降级路径不是理论设计，要定期真跑。

## 十二、FAQ

| 问题 | 答案 |
| --- | --- |
| AGC 没配置能上线吗 | 能，纯轮询形态即降级态，功能完整 |
| Token 会变吗 | 会，系统重置后刷新；端侧每次启动 getToken 重报覆盖 |
| 透传消息能不能当主通道 | 不建议：需进程在线、时序不可控，铃语以通知消息为主 |
| 发送失败会丢异动吗 | 不会，异动仍在 feed，轮询兜底刷新 |
| 一台设备收到多条重复通知 | 检查发送侧去重（按 alertId 幂等）与登记表是否重复登记 |
| Push 数据里能放正文全文吗 | 不放，只放 alertId；正文端侧拉取，Push 只做门铃 |

### 自我评估
- 正确性：4分 鉴权域名、v3 发送端点、client_credentials 流程、getToken 端侧用法经 2026-09-23 公开资料核对；请求体字段、错误码、透传接收机制明确标注"以官方文档为准"，未虚构码值。降级设计与项目架构基调逐条对齐。
- 完整性：4分 REST 调用、Token 注册、消息接收、降级四主题全覆盖，另有安全合规与检查清单；未做 AGC 控制台配置逐步截图类内容（无后台访问权限，如实声明）。
- 可复用性：5分 云函数代码骨架可直接改 broadcast-a2a，降级矩阵与九问清单可直接进验收；PushService 占位形态与既有审查文档（A19/A22/A26）互相锚定。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
