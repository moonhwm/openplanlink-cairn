# 网络请求层审查——https 封装、超时处理、重试机制、降级策略

## 一、审查范围与总评

本篇为 harmony-app（代号铃语）端侧网络层的审查知识资产。端侧网络调用共两处（均在本审查当日完整通读）：

- entry/src/main/ets/services/AlertPoller.ets（100 行）：数据主通道，GET 拉取异动 feed；
- entry/src/main/ets/services/PushService.ets 的 reportToken（:77-97）：token 上报通道，POST。

URL 配置层为 SettingsService.getFeedUrl（SettingsService.ets:351-361），默认值与 AlertPoller 内的 DEFAULT_FEED_URL（AlertPoller.ets:10）同为 CloudBase 云函数 https 端点，Settings 页可改（Settings.ets:514-530），改写入口与默认值同源，无第二真相源。

总评：两处调用各自手写、没有统一封装，但单点质量都不差——超时显式、finally 必 destroy、错误按 HTTP 语义分级、退避与静默降级齐全、坏响应不污染界面。当前"两处复制粘贴"尚可容忍，第三处网络调用出现之前应抽出统一封装（第二节给出骨架）。全链路 https、无明文 http、无内嵌密钥，合规红线达标。

## 二、https 与封装现状审查

两个端点均为 https（AlertPoller.ets:10、PushService.ets:11）。feed 地址支持用户改写，Settings 页提示语明确"X 服务器落地后替换为正式地址；本机联调可填局域网 IP"（Settings.ets:532）——即该入口是给联调期用的逃生门，正式期由 getFeedUrl 默认值接管。

两处调用的公共样板完全一致：http.createHttp() → request(选项) → finally req.destroy()（AlertPoller.ets:39、:85-87；PushService.ets:78、:94-96）。destroy 纪律是 NetworkKit 的坑位知识——不 destroy 会泄漏底层连接，长期轮询场景必炸，本仓两处都做对了。差异点：POST 带了 Content-Type: application/json（PushService.ets:84），GET 未带任何 header（无需鉴权头，feed 是公开读）；AlertPoller 未显式设 expectDataType，NetworkKit 默认按响应头返回 string，与后续 JSON.parse 用法匹配（但见第七节建议 3 的加固项）。

**封装建议（第三处出现前落地）：** 统一一个 NetKit 静态类收敛样板与常量，示意（零三方依赖，仅 @kit.NetworkKit）：

```typescript
export class NetKit {
  static readonly CONNECT_TIMEOUT = 5000;
  static readonly READ_TIMEOUT = 5000;

  static async getJson(url: string): Promise<string> {
    const req = http.createHttp();
    try {
      const resp = await req.request(url, {
        method: http.RequestMethod.GET,
        connectTimeout: NetKit.CONNECT_TIMEOUT,
        readTimeout: NetKit.READ_TIMEOUT,
        expectDataType: http.HttpDataType.STRING
      });
      if (resp.responseCode !== 200) {
        throw new Error(`http ${resp.responseCode}`);
      }
      return resp.result as string;
    } finally {
      req.destroy();   // 泄漏防线唯一收敛点
    }
  }
}
```

收益：超时常量单点、destroy 单点、状态码语义单点；AlertPoller 与 PushService 各删约 15 行样板；未来加鉴权头或证书校验只改一处。

## 三、超时处理审查

两处均为 connectTimeout 5000 加 readTimeout 5000（AlertPoller.ets:43-44；PushService.ets:82-83）。逐项评估：

- **数值合理。** feed 是轻量 JSON（limit=20 条异动），5 秒读超时是服务端异常时的合理止损；token 上报同理。连接 5 秒照顾弱网老人（电梯、地库、乡镇弱信号）。
- **叠加上限明确。** 理论最坏一次请求约 10 秒（连接加读取各 5 秒）；配合轮询退避（第四节），弱网下最长感知间隔可控，不会出现"永远转圈"的界面态——因为 UI 根本不转圈：界面始终显示旧数据或演示卡，超时只影响数据新鲜度，不传导为界面焦虑。这正是适老化网络层的正确姿态：网络慢不该变成老人的心理负担。
- **超时后的行为路径完整。** 超时在 NetworkKit 里以异常形式抛出，被 fetchLatest 的外层 catch 接住（AlertPoller.ets:81-84），走 applyBackoff 加大下一轮间隔——即超时不是"丢弃重试"而是"本轮放弃、下轮拉长"，节奏调整而非风暴重试。
- **待改进：** 超时字面量在两文件各写一份，应随第二节 NetKit 常量化；feed 未来若变大（limit 提高或带音频地址长列表）需重估 readTimeout，建议与 limit 参数联动写注释。

## 四、重试机制审查

重试分两型，本仓各有一处，口径完整。其一，**轮内退避型（AlertPoller）**：单次 fetchLatest 不做同轮重试（快速失败），由外层 pollLoop 以 AlertPoller.getInterval() 决定下一轮（Index.ets:146-149）；失败 applyBackoff 间隔翻倍封顶 30000ms（AlertPoller.ets:90-95），成功 resetBackoff 复位 5000（:97-99）。指数退避加封顶，教科书式实现，且退避作用于"轮询节奏"而非"请求内 sleep"，不占主线程也不延迟本轮 UI。5 秒到 30 秒的封顶区间意味着最坏情况下数据最多滞后半分钟，对分钟级异动播报完全够用。其二，**即时延迟重试型（PushService.getToken）**：命中官方文档口径的 4 个可重试错误码（1000900001、1000900008、1000900009、1000900011，PushService.ets:14）且未超 3 次（:15）时 setTimeout 1 秒重试（:63-71）。错误码白名单避免对确定性失败（未开通权益类）空转，正确。

**重试盲区与边界：** reportToken 的 POST 失败无重试（PushService.ets:90-93）——对一次性上报而言，失败即永久丢 token，下次启动才有自愈机会，建议补 3 次延迟重试；setTimeout 句柄未持有、init 重入会叠加（与 A26 审查同源问题）。另有边界提醒：指数退避无抖动（jitter），多设备同时从断网恢复时会形成同步脉冲打向服务端，端侧设备规模小可忽略，记录在案备查。

## 五、降级策略审查（本篇核心）

网络层的降级设计是本仓最成熟的部分，分四层自上而下。

第一层，**通道级降级**：Push 未配置（AGC 缺探测，PushService.init :30-33 静默返回）→ 前台 5 秒轮询兜底（AlertPoller 注释 :20-21 明示推送实装后轮询保留作拉齐补偿）。推送与轮询双通道并存，任一失效另一可用；推送降低时延，轮询保证前台数据最终一致。

第二层，**响应级降级（按 HTTP 语义分支）**：fetchLatest 对 429 单列——返回 ok:false 加 rateLimited:true 并静默跳过（AlertPoller.ets:47-52），Index.refresh 对 rateLimited 分支不递增失败计数、不惊动用户（Index.ets:192-193）；5xx 与其他非 200 统一 ok:false 加退避（:54-64）。语义区分准确：429 是"服务端让慢点来"，5xx 是"服务端坏了"，前者不该吓用户；现状 429 也 applyBackoff，属于温和加大轮间隔，防止持续顶撞限流，可接受（进一步优化见第七节）。

第三层，**界面级降级**：连续失败两次以上置 connectionBroken，顶栏提示「连接中断，显示旧数据」（Index.ets:195-199），旧 items 不清空——断网时老人看到的是"旧行情加一行说明"，不是白屏或报错弹窗；首屏未连通时用 DEMO_ITEMS 演示卡（:13-23，「示例」字样防误导）；连通但空 feed 显示「今日暂无异动」（:430-443）。**ok 与 items 空的语义分离**（PollResult 接口注释，AlertPoller.ets:12-17）是整套降级的地基：ok=true 且空等于真没异动（可信空态，显示"今日暂无异动"）；ok=false 等于数据不可信（保旧数据或演示卡）。若不分离，断网会被误判成"没有异动"欺骗用户。JSON 解析失败也归入 ok:false 并记原文前 200 字符（:68-75），坏数据当网络失败处理，绝不把半截 JSON 渲染到卡片上。

第四层，**生态级降级（服务端侧，端侧只留契约）**：Tushare token 失效（40101）已降级东财 API、百炼 TTS 只支持 WebSocket、audioUrl undefined 时端侧按需调 generate-tts——这三件属 X 服务器与云函数域，端侧对策已内建：audioUrl 缺失仅隐藏播报钮（Index.ets:390 的 if (item.audioUrl)），feed 契约不变。端侧网络层对上游数据源切换是封闭的，换源不换端——这是"契约即 AlertFeed"架构基调的直接红利，也是四层里唯一不需要端侧改代码的一层。

## 六、并发与状态一致性审查

pollLoop 是 setTimeout 串行链：refresh await 完成后才排下一轮（Index.ets:146-149），**天然无并发重叠**，不需要请求去重或取消逻辑——这是用串行化换正确性的简洁选择，代价是最坏一轮 10 秒内数据陈旧，可接受。refresh 内部对新旧列表做三方核对：正在播的、正在加载的、上次失败的 alertId 若已不在新列表中，分别停播复位（:166-177），防止对已被服务端撤下的异动继续播报；togglePlay 在 await AudioPlayer.play 返回后再核对 loadingId 是否仍是自己（:260-263），注释明示此防御针对"refresh 在 await 期间清除了 loadingId"的竞态。审查结论：异步时序已按"await 后状态可能已变"的前提系统性设防，是本仓网络与状态协作质量最高的段落之一。

## 七、改进建议汇总（按优先级）

- P2 抽 NetKit 统一封装（第二节骨架），收敛超时、destroy、状态码样板；在第三处网络调用出现前完成。
- P2 reportToken 补 3 次延迟重试；PushService 的 setTimeout 句柄化，重入先清旧定时器。
- P3 AlertPoller.request 显式 expectDataType 为 STRING，防服务端异常响应头导致 result 类型漂移。
- P3 429 可考虑仅维持基线 5 秒间隔不加退避（限流本身已是服务端给定的节奏信号），或连续多次 429 后才退避，避免单次限流拖慢真数据到达。
- P3 feed 支持 If-Modified-Since 或 ETag（需服务端配合），轮询场景省流量——老人多为流量敏感人群，304 空响应比整单 JSON 便宜得多。
- 红线自查：两处请求均不带任何凭据 header；日志只打状态码与异常消息，不含 token 明文；token 上报是设备标识注册而非凭据泄露，端点为自有云函数，边界成立。

## 八、流量与功耗预算演算

轮询型应用的隐藏成本是流量与电量，按现状参数演算一遍留档。流量侧：feed 单次响应按 20 条异动、每条约 300 字节（含 headline、detail、audioUrl 等字段）估约 6KB，加响应头约 7KB；前台每 5 秒一次、每小时 720 次，约 5MB/小时；老人挂机 4 小时（一个交易日加盘前盘后）约 20MB/天，按月 22 个交易日约 440MB——对 4G 老年套餐偏重。缓解路径有三：服务端支持 If-Modified-Since 后无变化返回 304 空体（省 90% 以上，异动不是每 5 秒都有）；limit 分时段收缩（开盘半小时 20 条、盘中 10 条、午休停推）；退避已内建（断网时不烧流量）。功耗侧：5 秒一次的 http 请求会频繁点亮无线模块，建议后续加"页面不可见暂停轮询"（现状 aboutToDisappear 停表已覆盖页面销毁，但应用退后台但页面未销毁的场景依赖系统冻结，可结合 onForeground/onBackground 补一档暂停）。这组数字的作用是给"要不要做 304"的决策提供依据——结论是要做，收益量级太大。

演算的另一个结论是轮询间隔 5 秒的合理性：异动播报的价值在"分钟级及时"，5 秒轮询给出的最坏感知延迟约 5 秒加网络往返，远超需求下限；若为省流量放宽到 10 秒，及时性仍在分钟级内，流量减半。这是一个可讨论的权衡项，不改变架构基调（5 秒是基调明文值，调整须走宪法流程），此处只留演算数据。

## 九、失败模式全目录与处置路径归档

把两处网络调用的全部失败模式按"发生在哪一层、用户看到什么、系统做什么"归档成目录，供联调与排障对号入座。域名解析失败：发生在连接前，fetchLatest 外层 catch 接住，界面保旧数据，退避加倍——典型场景是飞行模式或域名换迁。连接超时：五秒内未完成三次握手，同上路径，典型场景是弱网与防火墙拦截。读写超时：连接建立后五秒无响应体，同上，典型场景是云函数冷启动叠加慢查询。证书校验失败：https 握手被系统拒绝，同上，典型场景是端点证书过期或被中间人工具干扰——本仓不做证书固定，跟随系统信任链，属合理默认；若未来要求更强安全再评估固定策略。服务端五零几：响应到达但服务异常，退避加倍，界面保旧，提示逻辑与网络失败一致。服务端四二九限流：静默跳过、不惊动用户、温和退避。响应体坏损：二零零状态但 JSON 断裂，记前二百字符入日志，按失败处理。上报通道独有：token 上报非二零零或网络异常，仅记日志不重试不阻塞——推送能力缺位但应用完全可用，轮询照常。以上八种模式中七种汇聚到同一个用户可见结果（保旧数据），只有"服务端空态"显示空态文案——这种收敛是设计而非巧合：老人不需要分辨是哪种坏，只需要知道"现在看到的是旧信息"。

## 十、验证清单

- [ ] 断网冷启：演示卡出现，日志间隔 5s→10s→20s→30s 递增
- [ ] 断网中途：顶栏「连接中断，显示旧数据」，旧卡不清空
- [ ] 服务端注入 429：无用户可见变化，日志 rate-limited
- [ ] 恢复网络：一轮内复位 5 秒间隔，connectionBroken 提示消失
- [ ] 服务端返回坏 JSON：ok:false、日志含原文前 200 字符、界面保旧
- [ ] 抓包确认全部 https、无自定义 header 泄密
- [ ] req.destroy 覆盖所有请求路径（含异常路径，grep finally 确认）

### 自我评估
- 正确性：4分 全部行号来自本次实读的 AlertPoller.ets、Index.ets、PushService.ets、SettingsService.ets、Settings.ets；降级分层、退避数值与竞态防御结论均对应具体代码段；NetKit 骨架为建议代码，未在本环境编译运行，扣一分声明。
- 完整性：4分 覆盖 https 封装、超时、两型重试、四层降级、并发一致性、改进与验证清单；服务端侧降级（东财、WebSocket、generate-tts）仅述端侧对策，服务器内幕超出端侧审查边界。
- 可复用性：4分 四层降级框架与"ok 与空语义分离"可直接迁移到任何轮询型应用；NetKit 骨架零依赖可直接取用；验证清单可转联调脚本。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
