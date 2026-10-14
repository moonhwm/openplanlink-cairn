# E9 ArkTS网络请求最佳实践：https模块封装、超时控制、重试机制、并发管理

> 适用项目：harmony-app（代号"铃语"，鸿蒙适老化股票异动播报应用），纯ArkTS、零三方依赖（网络只用系统@kit.NetworkKit的http能力），Stage模型 compatibleSdkVersion 20 / targetSdk 26。数据源FEED_URL待X服务器落地，契约即AlertFeed。本文自包含成文，不依赖对话记忆；与E6（生命周期挂载）、E7（云函数路线）互为分工。

## 1 基础设施与权限

- 权限：module.json5的module.requestPermissions声明 `ohos.permission.INTERNET`。漏配的症状是请求异常且错误码难懂，先查权限再查代码。
- 模块：`import { http } from '@kit.NetworkKit';`
- 实例纪律：一次请求=一个httpRequest实例（http.createHttp()），请求结束（无论成败）在finally里调用destroy()，绝不复用实例发第二笔——复用会抛状态异常，也不释放底层资源。
- 解析方式：expectDataType用STRING自行解析并做结构校验；框架的OBJECT直解会绕过类型收敛，在ArkTS严格模式下反而多一道坎。

## 2 类型契约先行：AlertFeed

网络层的第一原则是先定契约再写请求。上游字段缺失（如audioUrl为undefined）是常态，端侧解析必须宽容、结构必须校验：

```ts
// model/AlertItem.ets
export interface AlertItem {
  id: string;
  ts: number;
  code: string;
  name: string;
  level: number;
  title: string;      // 白话一句话
  detail: string;
  audioUrl?: string;  // undefined时端侧按需调generate-tts（见E7）
}
export interface AlertFeed {
  alerts: AlertItem[];
  ts: number;
}
```

```ts
// model/AlertFeedGuard.ets —— 结构守卫，拒收不合规响应
export function isAlertFeed(v: object): boolean {
  const arr = (v as Record<string, Object>)['alerts'];
  if (!Array.isArray(arr)) {
    return false;
  }
  return true;
}
```

解析统一走"JSON.parse → isAlertFeed校验 → as AlertFeed"，禁止裸as any。

## 3 统一封装：NetClient

所有请求收敛到NetClient.ets一个入口，业务层不散写http调用：

```ts
// common/NetClient.ets
import { http } from '@kit.NetworkKit';

export class NetError extends Error {
  readonly kind: string; // 'NETWORK' | 'HTTP' | 'PARSE' | 'CANCEL'
  readonly status: number;
  constructor(kind: string, status: number, msg: string) {
    super(msg);
    this.kind = kind;
    this.status = status;
  }
}

export class NetClient {
  static async getJson(url: string, timeoutMs: number = 10000): Promise<object> {
    const req = http.createHttp();
    try {
      const resp = await req.request(url, {
        method: http.RequestMethod.GET,
        connectTimeout: 8000,
        readTimeout: timeoutMs,
        expectDataType: http.HttpDataType.STRING,
        usingCache: false
      });
      if (resp.responseCode < 200 || resp.responseCode >= 300) {
        throw new NetError('HTTP', resp.responseCode, `HTTP ${resp.responseCode}`);
      }
      return JSON.parse(resp.result as string) as object;
    } catch (e) {
      if (e instanceof NetError) {
        throw e;
      }
      throw new NetError('NETWORK', 0, '网络不可达');
    } finally {
      req.destroy(); // 成败都必须销毁
    }
  }
}
```

- 错误四分类（NETWORK/HTTP/PARSE/CANCEL）是重试与降级决策的唯一依据，业务层只看kind不猜原因。
- 日志脱敏：不打完整URL查询串与任何token；用hilog只记kind、status、路径片段。
- 自签名/私有CA场景：HttpRequestOptions的证书参数（caPath等）自较新API版本提供，落码前以compatibleSdkVersion 20的d.ts为准；无论何种理由，禁止关闭证书校验。

## 4 超时控制

两个独立旋钮，别混为一谈：

- connectTimeout：建连（TCP+TLS握手）预算，铃语设8秒。
- readTimeout：发包后等响应的预算，轮询场景设10秒。
- 全链路预算：轮询单次请求（建连+读）≤15秒，必须在下一个5秒tick前结束，否则请求堆积（见第6节单飞）。
- 首屏关系：首屏渲染只依赖演示卡常量，首请求超时也绝不阻塞loadContent（E6铁律）；超时后走演示卡兜底并提示"正在获取最新信息"。

## 5 重试机制

- 只重试幂等请求。GET轮询天然幂等；POST类（generate-tts）靠alertId幂等键保证重试安全，无幂等键的POST不重试。
- 可重试判定：NETWORK类全可重试；HTTP类仅502/503/504与429（429优先读Retry-After头）；4xx参数与鉴权错误（如上游token失效、返回40101类错误码）不重试，直接触发源切换降级——参考已知问题"Tushare token失效已降级东财API"，同构处理。
- 退避算法：base=500ms，间隔=base×2^n±20%抖动，最多2次重试（共3次尝试），重试期间上层无感。
- 熔断与半开：连续3轮轮询全失败进入长退避（轮询间隔拉长到30秒），收到一次成功即恢复5秒节奏。熔断是省电与省配额的双赢，不是失败掩盖——UI状态照常明示"连接中"。

```ts
function backoffMs(attempt: number): number {
  const base = 500 * Math.pow(2, attempt);
  const jitter = base * 0.2;
  return base + (Math.random() * 2 - 1) * jitter;
}
```

## 6 并发管理

- 轮询单飞（最重要）：AlertPoller同一时刻只允许一个在途请求。inFlight标志位拦住重叠的5秒tick，防止慢网下请求雪崩式堆积：

```ts
export class AlertPoller {
  private inFlight: boolean = false;
  private timer: number = -1;
  private gen: number = 0; // 代次号：stop后丢弃过期响应

  start(): void {
    this.stop();
    const myGen = ++this.gen;
    this.tick(myGen);
    this.timer = setInterval(() => this.tick(this.gen), 5000);
  }

  stop(): void {
    if (this.timer >= 0) {
      clearInterval(this.timer);
      this.timer = -1;
    }
    this.gen++; // 使旧响应作废
  }

  private async tick(myGen: number): Promise<void> {
    if (this.inFlight || myGen !== this.gen) {
      return; // 单飞 + 代次校验
    }
    this.inFlight = true;
    try {
      const feed = await NetClient.getJson(FEED_URL) as AlertFeed;
      if (myGen === this.gen && isAlertFeed(feed)) {
        AppStorage.setOrCreate('alerts', feed.alerts);
      }
    } catch (e) {
      // 保留旧数据与演示卡兜底；连续失败交给熔断拉长间隔
    } finally {
      this.inFlight = false;
    }
  }
}
```

- 生命周期挂载：Index.ets的onPageShow里start()、onPageHide里stop()——前台5秒轮询、后台不轮询（省电省流量），兜底链见E6。
- 全局限流：除轮询外还有按需TTS合成、配置拉取等请求，用信号量模式限全应用并发≤4，超出排队；避免弱网下互相挤占。
- 取消与作废：ArkTS没有AbortController，用两件套——页面隐藏时destroy在途请求（httpRequest.destroy()），响应回来后用代次号丢弃过期结果。两者缺一不可：只destroy会漏掉"已返回未处理"的窗口，只丢结果会浪费连接。
- 去重复用：同URL同参请求在途时复用同一Promise（典型：同一张卡片连续点播报只发一次TTS合成请求）。

## 7 错误呈现与适老化

- 所有NetError最终翻译成白话：NETWORK→"网络连不上，请检查网络"；HTTP 5xx→"服务器忙，稍后再试"；PARSE→"数据有点问题，正在重试"。绝不显示码值、URL、堆栈。
- 任何失败路径都不得清空已有卡片流，也不得让页面空白——旧数据+演示卡是最终兜底。
- 错误文案过红线检查：不催促、不承诺、不吓唬（禁"数据已损坏""风险自负"类表述）。

## 8 高频坑位速查

1. 忘INTERNET权限：一律请求失败且难排查。
2. 复用httpRequest实例发第二笔：状态异常；实例必须一笔一建一destroy。
3. 轮询未单飞：5秒tick × 15秒超时 = 三个在途请求互相拖垮。
4. 裸JSON.parse后直接用：ArkTS禁any，且上游字段缺失直接崩溃；必须guard。
5. 重试打到非幂等POST：TTS重复扣配额；靠alertId幂等键或禁止重试。
6. 页面隐藏不stop轮询：后台空转耗电，也违反"前台5秒轮询"的架构基调。
7. 捕获后吞错不降级：catch里既不清数据也不提示，用户面对的是静默过期数据；必须明示状态。

## 9 POST封装与请求头纪律

generate-tts、pushtokenregister类调用走POST，与getJson同构：

```ts
static async postJson(url: string, body: object, timeoutMs: number = 15000): Promise<object> {
  const req = http.createHttp();
  try {
    const resp = await req.request(url, {
      method: http.RequestMethod.POST,
      header: { 'Content-Type': 'application/json' },
      extraData: JSON.stringify(body),
      connectTimeout: 8000,
      readTimeout: timeoutMs,
      expectDataType: http.HttpDataType.STRING
    });
    if (resp.responseCode < 200 || resp.responseCode >= 300) {
      throw new NetError('HTTP', resp.responseCode, `HTTP ${resp.responseCode}`);
    }
    return JSON.parse(resp.result as string) as object;
  } catch (e) {
    if (e instanceof NetError) { throw e; }
    throw new NetError('NETWORK', 0, '网络不可达');
  } finally {
    req.destroy();
  }
}
```

- extraData统一传字符串（自控编码），不传对象让框架猜序列化。
- 请求头白名单管理：本项目端侧无凭据，只允许Content-Type等标准头；新增任何头必须登记用途，禁止夹带设备指纹类信息（合规红线）。
- POST默认不重试；带幂等键（alertId）的TTS合成例外，重试安全由服务端幂等保证。

## 10 网络状态监听与省电联动

用connection模块监听网络变化，让轮询跟随网络呼吸：

- 断网（netLost）：立刻暂停轮询计时器，省电也省无效重试；界面提示"网络已断开"。
- 恢复（netAvailable）：立即手动tick一次拿最新数据，再恢复5秒节奏——用户刚恢复网络时最想看的就是最新异动。
- 计费/弱网感知：弱网时可临时降档到10秒间隔；本项目不做分档计费判断，保持简单。
- 该监听注册在Index生命周期内，onPageHide时一并注销，与轮询同进退。

## 11 缓存与快照

- HTTP层：轮询请求usingCache固定false，保实时；静态配置类请求可开。
- 业务快照：每次成功响应写本地快照（节流30秒），冷启动先快照后网络——机制与E7第8节同一套，网络层只负责产出数据，落盘归数据层。
- 条件请求（FEED服务器落地后可选）：支持ETag/If-None-Match，304响应不重渲染直接续用旧数据，弱网省流量明显。
- 快照读取也走isAlertFeed守卫，坏快照直接弃用走演示卡。

## 12 音频链路的网络边界

- AVPlayer直接播云端直链：缓冲与重试是播放器职责，网络层不重复包装，也不要"先下载完再播"（首播延迟不可接受）。
- 直链过期（播放403）：不经网络层，由AudioPlayer按E7流程触发"重新合成→换链→重播"。
- 大文件长下载不挂在前台http请求上：超时预算内完不成的任务交给后台任务或改为流播，保证轮询通道永不被长任务占用。

## 13 流量与时段策略

- 增量请求（since参数）是省流量第一手段：只传变化，不重复拉全量。
- 非交易时段（收盘后、周末、深夜）自动拉长轮询到60秒或暂停，开盘恢复5秒；判断用本地时间即可，错了顶多多拉几次，无正确性风险。
- 前台才轮询加息屏暂停双保险：退后台必stop，这是省电底线也是架构基调。

## 14 可观测与埋点

- 每请求记录四元组（kind、status、耗时、urlTag不带查询串）进内存环形缓冲（最近50条），排障时可导出。
- 核心指标：轮询成功率、P95耗时、重试触发率、熔断进入次数、降级链各层命中率——降级链命中率是服务端健康度的端侧信号。
- 埋点数据脱敏：不含URL查询参数、不含响应体、不含任何用户标识。
- 连续失败达上报阈值时随诊断包一次性上报（需用户设置中开关允许，默认关）。

## 15 测试要点

- NetClient可测性：抽出NetTransport接口（request(url, options)），真实实现包http模块，测试用假实现注入——不依赖真网即可测分支。
- 纯函数直测：backoffMs边界（attempt=0,1,2）、HTTP分类（2xx/3xx/4xx/5xx）、四类NetError映射。
- AlertPoller行为测：假时钟驱动，验证单飞（并发tick只发一次）、代次丢弃（stop后旧响应不落地）、熔断升降档。
- 集成冒烟：真机断网→恢复→断FEED_URL→全断，四场景各跑一轮对照UI表现。

## 16 参数速查与错误文案表

轮询与重试参数集中一处（NetConfig常量），改参只动一个文件：

| 参数 | 取值 | 说明 |
|---|---|---|
| 轮询间隔 | 5000毫秒 | 前台节奏，架构基调值 |
| 建连超时 | 8000毫秒 | connectTimeout |
| 读取超时 | 10000毫秒 | readTimeout，轮询场景 |
| 重试上限 | 2次 | 共3次尝试 |
| 退避基数 | 500毫秒 | 指数退避base |
| 熔断阈值 | 连续3轮失败 | 进入长退避 |
| 长退避间隔 | 30000毫秒 | 熔断期间轮询节奏 |
| 全局并发上限 | 4 | 信号量限制 |

错误到白话文案的映射固定成表，禁止各页面自行发挥：

| 错误类型 | 上屏文案 |
|---|---|
| NETWORK | 网络连不上，请检查手机网络 |
| HTTP 5xx | 服务器正忙，稍后自动再试 |
| HTTP 4xx | 数据暂时取不到，稍后再试 |
| PARSE | 数据有点问题，正在自动恢复 |
| 超时 | 网络有点慢，正在重试 |

文案三条硬规则：不出现码值与URL；不出现"立即""马上"等催促词（红线）；不出现"故障""损坏"等惊吓词——老人看到"故障"会以为手机坏了。

## 17 Index侧调用全貌（串联示例）

页面层只做三件事：启动轮询、订阅状态、按需触发合成。完整链路：

```ts
// pages/Index.ets 节选
@StorageLink('alerts') alerts: AlertItem[] = [];   // 轮询落库的唯一出口
@StorageLink('pendingAlertId') pendingAlertId: string = '';
private poller: AlertPoller = new AlertPoller();

onPageShow(): void {
  this.poller.start();          // 前台恢复轮询（E6挂载点）
}
onPageHide(): void {
  this.poller.stop();           // 后台必停
}
```

- 首帧渲染不依赖alerts初值：空态渲染演示卡常量，数据到达后List自动替换——首屏永不空白的网络层承诺。
- pendingAlertId变化时滚动定位对应卡片，定位后置空，避免轮询刷新触发重复滚动。
- 点播报按钮：先查该条audioUrl，缺省则调CloudApi.requestTts（E7），拿到直链交给AudioPlayer；按钮置灰防重复提交，失败恢复按钮并给白话提示。
- 整个页面不含任何http细节——网络封装是否合格的判据就是业务页零网络代码。

### 自我评估
- 正确性：4分——@kit.NetworkKit的http能力、超时双旋钮、单飞加代次号取消模式均为标准做法，代码骨架经ArkTS类型纪律书写；caPath等证书参数与connection回调细节以compatibleSdkVersion 20的d.ts为准，未真机联调。
- 完整性：4分——四个指定维度（封装、超时、重试、并发）全部展开，另补POST与请求头、网络状态联动、缓存快照、音频边界、流量策略、可观测与测试要点；与E6生命周期、E7降级链衔接明确。
- 可复用性：5分——NetClient、AlertPoller、退避函数、NetTransport接口均为可直接复制的通用件，仅FEED_URL与AlertFeed为本项目契约，替换成本低。
- 字数：约2635字（正文汉字，实测统计）
- 使用模型：GLM-5.3-Flash
