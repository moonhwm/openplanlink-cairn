# 国密算法适配：SM2/SM3/SM4 在 ArkTS 中的实现与性能评估

> 适用项目：harmony-app（铃语，鸿蒙适老化股票异动播报，纯 ArkTS + 云函数，**零三方依赖**）。
> 自包含知识资产；配套文档：密评合规见 crypto-law-compliance.md，密钥管理见 key-lifecycle.md，传输层与服务端配置见 rhel10-crypto.md 与 pqc-assessment.md。

## 一、算法概况与选型定位

| 算法 | 标准依据 | 类型 | 关键参数 | 在铃语中的定位 |
|---|---|---|---|---|
| SM2 | GB/T 32918 系列 | 椭圆曲线公钥密码 | 256 位素域曲线；签名/公钥加密/密钥交换 | AlertFeed 播报内容签名与验签（防伪造话术） |
| SM3 | GB/T 32905-2016 | 密码杂凑 | 256 位摘要 | 完整性校验、密钥指纹、审计摘要 |
| SM4 | GB/T 32907-2016 | 分组密码 | 128 位分组 / 128 位密钥；模式选 CBC/PKCS7 或 GCM（若系统支持） | alerts.json 本地缓存加密、临时会话数据 |

选型总原则：**零三方依赖约束下，国密实现一律调用鸿蒙系统能力 @kit.CryptoArchitectureKit（cryptoFramework），禁止自研密码原语**。自研实现即使功能正确，也无法通过侧信道与实现安全审查，且违反密评"正确性"要求（见 crypto-law-compliance.md 第 3.1 节）。

三条使用边界先讲清楚，避免过度设计：
1. 行情与播报文本属公开数据，SM2 加密它们没有意义；需要的是**签名（完整性 + 来源认证）**。
2. 5 秒前台轮询（Index.ets 的 AlertPoller）意味着校验逻辑是高频路径，必须缓存校验结果，不能每轮重复验签同一条目。
3. 密码操作失败不得影响首屏"永不空白"约束——验签失败时按降级策略显示带"示例"字样演示卡或跳过该条，而不是白屏或崩溃。

## 二、ArkTS 实现（cryptoFramework）

以下代码为可直接套用的骨架，全部基于系统能力。真实密钥与凭据一律来自 Asset/HUKS（见 key-lifecycle.md），**代码与文档中永不出现真实密钥值**（项目红线）。

### 2.1 SM3 摘要

```typescript
// common/GmDigest.ets
import { cryptoFramework } from '@kit.CryptoArchitectureKit';

export async function sm3Digest(data: Uint8Array): Promise<Uint8Array> {
  const md: cryptoFramework.Md = cryptoFramework.createMd('SM3');
  await md.update({ data } as cryptoFramework.DataBlob);
  const out: cryptoFramework.DataBlob = await md.digest();
  return out.data; // 32 字节摘要
}

/** 密钥指纹：审计日志中标识密钥，只留摘要前 8 字节，避免泄露密钥本体 */
export async function keyFingerprint(pubKey: Uint8Array): Promise<string> {
  const fp = await sm3Digest(pubKey);
  return Array.from(fp.slice(0, 8))
    .map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### 2.2 SM4 对称加解密（CBC + PKCS7）

```typescript
// common/GmCipher.ets
import { cryptoFramework } from '@kit.CryptoArchitectureKit';

export async function sm4Encrypt(
  keyBytes: Uint8Array, plain: Uint8Array, iv: Uint8Array
): Promise<Uint8Array> {
  const keyGen = cryptoFramework.createSymKeyGenerator('SM4_128');
  const key = await keyGen.convertKey({ data: keyBytes } as cryptoFramework.DataBlob);
  const cipher = cryptoFramework.createCipher('SM4_128|CBC|PKCS7');
  const ivSpec: cryptoFramework.IvParamsSpec = {
    algName: 'IvParamsSpec',
    iv: { data: iv } as cryptoFramework.DataBlob
  };
  await cipher.init(cryptoFramework.CryptoMode.ENCRYPT_MODE, key, ivSpec);
  const out = await cipher.doFinal({ data: plain } as cryptoFramework.DataBlob);
  return out.data;
}
// 解密对称实现：CryptoMode.DECRYPT_MODE，同一 iv，先 update 后 doFinal 的组合按数据量选择
```

要点：IV 每次加密随机生成并与密文一起存储（IV 不保密）；密钥不得硬编码，来源见 key-lifecycle.md 的 Asset 读取封装；模式字符串 `'SM4_128|CBC|PKCS7'` 严格按系统文档书写，可用 `cryptoFramework.getCipherSpecUintParam` 等接口核对支持情况。

### 2.3 SM2 签名与验签

```typescript
// common/GmSignature.ets
import { cryptoFramework } from '@kit.CryptoArchitectureKit';

export class Sm2Signer {
  async sign(priKey: cryptoFramework.PriKey, msg: Uint8Array): Promise<Uint8Array> {
    const signer = cryptoFramework.createSign('SM2_256|SM3'); // SM2 签名内部以 SM3 为摘要
    await signer.init(priKey);
    const sig = await signer.sign(null, { data: msg } as cryptoFramework.DataBlob);
    return sig.data;
  }

  async verify(pubKey: cryptoFramework.PubKey, msg: Uint8Array, sig: Uint8Array): Promise<boolean> {
    const verifier = cryptoFramework.createVerify('SM2_256|SM3');
    await verifier.init(pubKey);
    return verifier.verify(null, { data: sig } as cryptoFramework.DataBlob,
      { data: msg } as cryptoFramework.DataBlob);
  }
}
```

部署形态：**签名在服务端（X 服务器/云函数持私钥），端侧只持公钥验签**——端侧不需要也不应该持有私钥，这同时简化密钥管理并降低泄露面。公钥可随应用分发或随 feed 下发（下发时用预置公钥二次校验，防首包替换）。

### 2.4 端侧集成约束（与架构基调对齐）

- 验签调用点放在数据进入卡片流之前（Index.ets 渲染前或 AlertPoller 解析后），失败按"跳过该条 + 计数上报"处理，不得中断整页渲染。
- 每条 alertId 的验签结果缓存于内存 Map，轮询重复到达同条目时直接命中缓存，将 5s 周期内的实际验签次数压缩到新增条目数。
- AudioPlayer、PushService.ets 等现有模块的改造仅限"读取校验结果"，不改动其播放与推送逻辑（架构基调不可推翻）。

## 三、密钥来源与存储（简述，详见 key-lifecycle.md）

- 端侧 SM2 公钥：随包内置或首次安全下发，存储为只读资源。
- SM4 密钥：优先经 HUKS 导入生成非导出密钥（HUKS_ALG_SM4，用途 ENCRYPT|DECRYPT），使密钥不出安全环境；退化方案为 Asset 存储的密钥材料 + 运行时读入。
- 云函数侧私钥：环境变量注入 + 云 KMS 信封加密，禁止写入代码仓库。

## 四、性能评估

### 4.1 方法论（先定方法，再谈数字）

任何"SM4 比 AES 慢多少"的结论都必须绑定机型与实现，性能评估按以下规程执行：

1. **测试环境**：真机优先（至少覆盖一台低端机——目标用户是老年群体，设备性能分布偏下限），模拟器结果仅作参考并明确标注；记录机型、CPU、系统版本、是否充电状态（低电量限频会显著影响结果）。
2. **数据梯度**：摘要与对称加密取 1KB / 64KB / 1MB / 16MB 四档；签名验签固定小报文（播报卡片量级，约数百字节）。
3. **迭代与统计**：每档预热 10 次后测 100 次，取中位数与 P95，报告波动区间；排除首次调用的库初始化开销（单列一项"首次初始化耗时"）。
4. **对照基线**：同接口跑 SM3 vs SHA-256、SM4 vs AES-128，得到相对比值而非孤立数字。
5. **业务口径**：最终以端到端指标验收——单条播报卡片"验签 + 渲染准备"增量耗时、5s 轮询周期内密码总开销占空比。

### 4.2 预期量级与验收阈值（经验参考，以 4.1 实测为准）

- SM3 摘要：纯软件实现通常在数百 MB/s 量级，对播报卡片（<1KB）耗时为微秒级，可忽略。
- SM4-CBC：软件实现与 SM3 同量级或略低；16MB 级大文件加密在低端机可能到百毫秒级——因此**本地缓存只加密必要字段**，不做全量 JSON 加密。
- SM2：签名/验签为毫秒级/次。端侧只做验签，配合缓存策略，单周期新增条目通常少于 10 条，总开销可控制在 10ms 量级。
- 验收阈值建议：单条目验签 P95 ≤ 5ms；轮询周期密码总开销 ≤ 20ms；首屏冷启动密码初始化 ≤ 30ms。超标处置：降低验签频率（仅对新条目验签）、摘要前置比对（先 SM3 比对，摘要未变则跳过验签）。

### 4.3 基准脚本骨架

```typescript
// perf/GmBench.ets —— 仅 Debug 构建启用，release 剥离
export async function benchVerify(times: number): Promise<number> {
  const t0 = Date.now();
  for (let i = 0; i < times; i++) {
    await sm3Digest(payload);          // 摘要
    // await verifier.verify(...)      // 验签，公钥预加载
  }
  return (Date.now() - t0) / times;    // 平均每次毫秒数，输出到 hilog（仅标志位开启时）
}
```

注意：基准输出的日志中**只出现耗时与条目数，不出现任何密钥材料或凭据**（项目红线）。

## 五、常见问题与排查清单

- 模式字符串拼写错误报"unsupported algorithm"：对照系统文档核对 `'SM4_128|CBC|PKCS7'`、`'SM2_256|SM3'` 等 spec 字符串。
- 验签随机失败：检查端与服务端摘要输入是否完全一致（含编码差异），SM2 签名与消息绑定方式两端必须一致。
- IV 重用：每次加密必须新 IV，CBC 模式下 IV 重用直接破坏安全性。
- 与 PQC 的关系：SM2 同属量子脆弱的公钥算法，国密适配完成后应将验签接口套入 pqc-assessment.md 的敏捷性抽象，为后续混合签名预留位置。
- 密评联动：本文件 2.x 节的实现即为 crypto-law-compliance.md 第 3.1 节"应用和数据"层合规项的落地证据。

## 六、算法细节与安全参数（复核清单）

以下参数级细节供代码评审与密评证据复核使用，逐条对照实现：

**SM2**：基于 256 位素域推荐曲线（sm2p256v1），签名结果为 (r,s) 各 32 字节，DER 编码后约七十字节上下；公钥非压缩点 65 字节。复核点：其一，曲线必须用标准推荐曲线，禁止自选曲线参数；其二，签名随机数每次必须新鲜——k 值重用会直接泄露私钥，实现交给系统能力后此风险由系统侧承担，但服务端若自研或换库，该项列为专项审查项；其三，加密结果的密文块顺序存在 C1C3C2 与 C1C2C3 两种历史排列，国家标准采用前者而部分老系统使用后者，两端不一致是互调失败的头号原因，联调前先对齐；其四，验签输入应为"完整报文 + 用户标识"按标准拼装，端与服务端拼装方式不一致会出现随机通过/失败的诡异现象。

**SM3**：512 位分组输入、256 位摘要输出、64 步压缩。复核点：不得把摘要截断到 128 位以下再当完整性判断用；构造带密钥摘要时必须走标准 HMAC 结构而非手工拼接（朴素拼接存在长度扩展攻击面）；作为密钥指纹使用时只取前若干字节且指纹本身无敏感性。

**SM4**：32 轮非线性变换结构。复核点：ECB 模式禁止用于超过一个分组的业务数据（相同分组映射相同密文，会泄露数据画像）；CBC 模式下 IV 必须一次一密随机生成；同一密钥不得同时承担加密与校验两种用途，用途分离是最容易被忽视又最致命的工程错误。

**模式选择对照**：

| 模式 | 适用场景 | 主要风险 |
|---|---|---|
| ECB | 仅单分组等长数据 | 相同分组泄露模式，业务数据禁用 |
| CBC + PKCS7 | 本地缓存、配置类数据 | IV 重用即失守；无认证能力，需另配 SM3 校验 |
| GCM 类认证加密 | 网络会话数据（以系统实际支持为准） | 自带认证；随机数重用后果灾难性 |

## 七、测试向量与正确性回归

实现接入后必须用标准测试向量证明正确性：采用国家标准附录与行业标准文件提供的 SM3 摘要向量、SM4 加解密向量对、SM2 签名验签向量对，做成测试夹具文件（仅 Debug 构建打包，路径建议 common/testfixture/），断言输出逐字节相等。端侧与服务端跑同一套向量，是"两端实现一致"的最廉价证明。向量文件随版本冻结；每次升级 SDK、更换系统版本、服务端换库之后，先跑向量回归再跑业务回归，任何一字节不符即阻塞发布。这条纪律同时充当密评"正确性"维度的直接证据（见 crypto-law-compliance.md）。

## 八、降级与错误处理约定

密码操作异常按三级处置，且全部受"首屏永不空白"总约束：验签失败按可疑内容处理——跳过该条目并计数上报，宁可少展示一条，也不给伪造话术任何触达老年用户的机会；存储读写失败退化为内存态运行并出示带"示例"字样演示卡兜底；初始化失败则本会话标记禁用密码特性、健康上报一条事件，主流程照常走。异常日志只区分"配置缺失、数据损坏、系统不支持"三类别码，永不包含密文、密钥与凭据——这一条同时是项目合规红线与审计要求（key-lifecycle.md 第六节）。

### 自我评估
- 正确性：4分 算法标准与参数（GB/T 32918/32905/32907、SM4 128 位、SM3 256 位）为确定事实；cryptoFramework 接口形态（createMd/createCipher/createSign 及 spec 字符串）基于鸿蒙公开 API 认知，未在本环境实测（本机为 Windows，无 DevEco/真机），落地前需以 SDK 文档复核接口签名。
- 完整性：4分 三算法实现骨架、集成约束、密钥来源、性能方法论与阈值齐备；HUKS 导入细节与 SM4-GCM 支持性待按机型确认。
- 可复用性：5分 代码骨架与性能规程可直接用于其他鸿蒙项目，与域内其他四份文档形成互引闭环。
- 字数：约2600字
- 使用模型：GLM-5.3-Flash
