# E14 · HarmonyOS 安全开发：数据加密、安全存储、权限管理、网络安全配置

> 适用项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。Stage 模型，compatibleSdkVersion 20 / targetSdk 26，纯 ArkTS、零三方依赖。本文自包含，可独立阅读。

## 1. 铃语的安全威胁模型

先划定边界，再谈手段。铃语端侧持有的敏感物很少，但每一件都要数得清：

| 敏感物 | 位置 | 威胁 |
| --- | --- | --- |
| FEED_URL 与云函数端点 | 端侧常量 / 配置 | 被反编译提取后伪造数据源 |
| 云函数鉴权凭据（如自定义 token） | 端侧若硬编码即泄漏 | 被提取后刷接口、盗配额 |
| 已播异动历史、用户播报偏好 | 端侧首选项 / 文件 | 设备共享或丢失时泄露个人关注轨迹 |
| TTS 音频缓存 | 沙箱缓存目录 | 体量大、含内容，清理不当留残迹 |
| 调试抓包配置 | 仅存在于开发机构建 | 调试证书白名单不进发布分支，防线上降级成明文 |
| 上游 token（Tushare、百炼等） | **只许在云侧** | 端侧出现即事故 |

已知问题里"Tushare token 失效（40101）已降级东财 API"就是教训：上游 token 属于服务端秘密，永远不出云函数。端侧红线一句话：**任何 Token/密钥不落端、不进日志、不进代码仓库**。适老化用户群体防护意识弱，端侧安全标准只能更严。

## 2. 数据加密

### 2.1 传输加密

- 全链路 HTTPS（`https://`），且 FEED_URL、generate-tts、未来 Push Kit REST 调用无一例外；端侧出现 `http://` 即构建阻断项；
- 用系统 `@ohos.net.http` 发请求，TLS 校验交由系统默认（不自定义放宽），禁止为了"联调方便"关闭证书校验；
- 请求体敏感字段（如未来加入的设备标识）在应用层再做一次对称加密，密钥来自安全存储（见 3.2），避免明文过代理抓包直接可读。

### 2.2 本地数据加密

需要落盘的个人数据（播报偏好、已播历史）使用系统加解密能力，AES-GCM 是默认选择（带认证的对称加密，防篡改）：

```ts
// common/security/CryptoBox.ets
import cryptoFramework from '@ohos.security.cryptoFramework';

export class CryptoBox {
  // AES-GCM：加密
  static async encrypt(plainText: string, symKey: cryptoFramework.SymKey):
    Promise<Uint8Array> {
    const cipher = cryptoFramework.createCipher('AES256|GCM|NoPadding');
    const params: cryptoFramework.GcmParamsSpec = {
      algName: 'GcmParamsSpec',
      iv: CryptoBox.random(12),                    // GCM 推荐 12 字节
      aad: new Uint8Array([0x01]),                 // 附加认证数据，可放业务版本号
      authTag: new Uint8Array(16)
    };
    await cipher.init(cryptoFramework.CryptoMode.ENCRYPT_MODE,
      symKey, params);
    const out = await cipher.doFinal(CryptoBox.strToU8(plainText));
    return out.data;
  }

  static random(n: number): Uint8Array {
    const r = cryptoFramework.createRandom();
    const out = r.generateRandomSync(n);
    return out.data;
  }

  static strToU8(s: string): Uint8Array {
    const enc = new util.TextEncoder();            // @ohos.util
    return enc.encodeInto(s);
  }
}
```

纪律条目：IV 每次加密必须随机新生成，与密文一并存储；禁止 ECB 模式；密钥不与密文同处明文存放（密钥进安全存储）。演示数据、纯展示类缓存（如示例卡片文案）不加密，避免为静态内容支付无谓开销——加密预算花在"能定位到个人"的数据上。

## 3. 安全存储

### 3.1 层级选择

| 数据 | 存储方式 | 理由 |
| --- | --- | --- |
| 播报偏好（音量、速度档位） | `@ohos.data.preferences` | 非敏感、高频读写 |
| 已播历史、加密密钥 | `@ohos.security.asset` 或加密后落文件 | 敏感、需设备级保护 |
| TTS 音频缓存 | 沙箱 cache 目录 | 系统可自动清理，退出登录/清理时整体删除 |
| 上游 token | 云函数环境变量 | 端侧零持有 |

### 3.2 密钥托管：优先 Asset

HarmonyOS 的资产存储（`@ohos.security.asset`，类似 iOS Keychain）提供系统级加密与可选的设备绑定，适合放 AES 密钥：

```ts
import asset from '@ohos.security.asset';

// 写入密钥（首次启动时生成并托管）
function storeKey(keyBytes: Uint8Array): void {
  const attr: asset.AssetMap = {
    [asset.Tag.SECRET]: keyBytes,                    // 密钥内容
    [asset.Tag.ALIAS]: 'lingyu_master_key',          // 别名，业务内唯一
    [asset.Tag.ACCESSIBILITY]:
      asset.Accessibility.DEVICE_FIRST_UNLOCKED,     // 首次解锁后可用
    [asset.Tag.IS_PERSISTENT]: true                  // 恢复出厂不清（跟随账号策略可调）
  };
  asset.add(attr).catch((e: BusinessError<void>) => {
    // 已存在则改用 update；失败要有降级路径
  });
}
```

设备未解锁时数据不可读，系统还会对暴力尝试做约束。若目标 API 覆盖不到该能力，兜底方案为"密钥存应用沙箱文件 + 文件权限收紧"，并在文档标注降级风险。禁止的写法：把密钥硬编码在常量类、放进 `AppStorage`（内存态全局可读的便利存储不是保险箱）、或塞进 Preferences 明文键值对。

## 4. 权限管理

### 4.1 权限最小化盘点

铃语的功能面很窄，权限申请必须能逐条对应到用户可感知的功能：

| 权限 | 用途 | 是否申请 |
| --- | --- | --- |
| `ohos.permission.INTERNET` | 拉取 AlertFeed、播 TTS 流 | 是（system_grant，无需弹窗） |
| 通知发布 | Push 到达后的本地提醒 | 是（对用户可见可拒） |
| 麦克风 / 相机 / 位置 / 通讯录 | 无此功能 | **否，一条不申** |
| 媒体库读写 | 无 | 否 |

审核对"功能与权限不匹配"极其敏感，适老化应用更应做到零冗余权限。module.json5 中 `requestPermissions` 只保留上表两行，且每条附 `reason`（字符串资源引用）与 `usedScene`。

### 4.2 用户授权的体验规则

- 只在用户触发对应功能那一刻请求授权，不进首页就连环弹窗；
- 被拒绝后提供无该功能的降级路径：通知被拒 → 应用内卡片流照常、`AlertPoller` 前台轮询兜底（这正是架构里轮询兜底的第二重意义：权限/推送任一环节不可用，播报能力不断）；
- 绝不引导老人去改系统设置之外做"越权绕过"，也不因权限被拒而锁死应用主流程。

### 4.3 WebView 与动态加载

本项目纯 ArkTS、零三方依赖，无 WebView、无动态 so 加载、无插件机制，`module.json5` 中不应出现任何 `web` 组件与动态 import 远程代码的配置。这条"没有"本身就是安全项，列入发布前检查表。

## 5. 网络安全配置

### 5.1 明文流量封死

Network Security Config 思路（HarmonyOS 上通过模块配置约束）：

- `cleartextTraffic` 等明文运载能力一律关闭，全应用只允许 TLS；
- 自建上游（X 服务器落地后的 FEED_URL）用正规 CA 签发的证书，不做自签例外；联调期的抓包调试证书白名单只存在于开发者本地构建，不进发布分支的配置文件；
- 云函数侧同样全 HTTPS，且对 Push Kit REST 的调用（AGC 配置后替换 broadcast-a2a 的那一步）走华为官方域名，不做自定义 Host 映射。

### 5.2 请求侧防护

```ts
// common/net/FeedClient.ets（骨架）
const RESP_MAX_BYTES = 2 * 1024 * 1024;   // 响应体上限 2MB，防恶意大包打爆内存

function checkUrl(u: string): boolean {
  return u.startsWith('https://');        // 构造层再拦一次明文
}
```

- 响应体大小上限、超时（如 8 秒）、重试退避（如 1s/2s，仅两次）在客户端统一封装，异常响不影响"首屏永不空白"（退演示卡）；
- 解析走 E11 契约验证器：脏数据、超 schema 版本数据均按契约文档处置，防"数据投毒"直接进 UI；
- 不在 URL 查询串携带任何凭据或可定位个人的参数，日志只记状态码与耗时。

## 6. 泄漏面收口

- **日志**：release 构建关闭 debug 级日志，所有日志脱敏（无 token、无完整 URL 参数、无用户标识）；`hilog` 打点前过一遍"能否反查到人"标准；
- **截屏与后台**：详情页无敏感内容，暂不申请防截屏；若后续加入账户类页面，再按需使用窗口级防截屏能力；
- **应用完整性**：发布走 AGC 正规签名与上架（见 E15），不分发未签名包；调试签名证书不进仓库；
- **依赖面**：零三方依赖是本项目安全结构优势，任何引入新依赖的提案都必须过安全评审并说明必要性，默认拒绝；
- **变更面**：凡涉及加密方式、存储位置、权限清单、网络配置四类文件的改动，代码评审必须指定第二人复核安全影响，单人合并即违规。这四类改动的风险不在"写错"而在"悄悄改对了别的地方却破了安全假设"，双人是最低成本的护栏。

### 2.3 密钥轮换与数据迁移

主密钥不该终身服役。约定轮换策略：密钥别名带版本（如 `lingyu_master_key_v1`），新版本发布时生成 v2 密钥，启动时检测旧密钥是否存在，存在则逐条解密旧数据、用新密钥重加密落盘，成功后删除旧密钥条目。轮换触发条件有三：怀疑泄漏（如调试包外流）、周期性到期（建议不超过一年一次）、或算法升级。轮换必须幂等且可中断——老人可能在轮换进行到一半时杀掉应用，下次启动要能从断点续跑而不是重头再来或丢数据。轮换期间新旧密钥短暂共存属正常态，日志只记轮换进度不记密钥内容。

### 5.3 证书固定的取舍

证书固定（校验服务器证书指纹）能抵御中间人攻击，但代价是服务器换证书的瞬间所有老客户端集体失联。铃语的取舍：暂不启用固定，理由有三——上游 FEED_URL 尚未正式落地、证书续期节奏未知，贸然固定等于给自己埋雷；系统默认的 TLS 链校验已挡住绝大多数攻击面；本应用不承载交易与账户资产，风险敞口有限。等正式源稳定、证书由固定团队按年度管理后，再评估启用。这个"暂不做"的决定连同理由写进本文档，防止后人误以为遗漏。

## 6.5 安全验证手段

安全要求不能只靠文档自觉，要有可执行的验证：

- **静态扫描**：发版前全仓正则扫描 token 模式（长十六进制串、`Bearer`、`sk-` 前缀等）、明文 `http://`、调试白名单配置，命中即阻断；
- **脏数据注入测试**：向本地契约测试环境喂畸形 feed（字段错型、超长字符串、深层嵌套），验收标准是演示卡降级而绝不崩溃——这与 E11 的 fixture 四类样本复用同一套基建；
- **越权路径走查**：逐条核对"权限被拒绝后应用是否仍可用主流程"，通知权限关闭时人工走一遍卡片流与轮询；
- **日志审计**：随机抽查 release 构建的日志输出，确认无敏感字段。

以上四项都挂进 E15 的发版前检查表，作为发布门禁的一部分执行，而不是安全文档里的孤岛要求。

## 7. 落地检查表

- [ ] 全仓 grep：无 `http://`、无 token 字面量、无上游名词（tushare/东财/百炼）出现在端侧代码；
- [ ] `module.json5` 权限仅 INTERNET + 通知，各附 reason/usedScene；
- [ ] 敏感落盘走 AES-GCM，密钥托管 Asset（或标注降级方案）；
- [ ] IV 随机、密钥与密文分离存储；
- [ ] 响应有大小/超时上限，失败退演示卡不空白；
- [ ] release 日志脱敏且关 debug；
- [ ] 调试证书与调试白名单不进发布分支；
- [ ] 仓库历史中无任何真实密钥（历史泄漏需换钥匙而非删提交）；
- [ ] 密钥轮换逻辑幂等可中断，断点续跑无数据丢失；
- [ ] 加密、存储、权限、网络四类文件改动双人复核后合并。

### 自我评估
- 正确性：4分。cryptoFramework AES-GCM、asset 存储接口按公开 SDK 形态编写，权限表与 Stage 模型一致；个别 API 形参（如 GcmParamsSpec 字段名、AssetMap 键）以实际 SDK d.ts 为准，未逐条编译验证。
- 完整性：4分。加密、存储、权限、网络配置四块齐备，并给出威胁模型与泄漏面收口；生物识别、安全键盘等未涉及场景按项目范围明确排除。
- 可复用性：5分。威胁模型表、存储层级表、权限盘点表与检查表可直接用于其他 HarmonyOS 应用的安全评审模板。
- 字数：约2572字（正文汉字，实测）
- 使用模型：GLM-5.3-Flash
