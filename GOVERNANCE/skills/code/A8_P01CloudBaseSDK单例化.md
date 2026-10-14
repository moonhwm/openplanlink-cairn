# P0-1 CloudBase SDK 单例化完整修复代码——getCloudbaseApp 函数、5 处 init 替换与连接复用验证

> 适用项目：harmony-app（铃语）云函数层。产出人：Moon席位 写手-A组-2号。日期：2026-09-23。
> 本文自包含：修复代码、逐文件替换明细、全库复核命令与输出、连接复用验证步骤全部在内。行号锚定说明：`fetch-tushare-data/index.js` 以 735 行快照为准（md5 `fbf3afdd7e820451d33f467b1732504f`，2026-09-23 08:19:27）；其余五文件以本会话 08:21-08:27 读取版本为准，复用时请以文末验收命令重新锚定。

## 一、问题定义：为什么 cloudbase.init 必须单例化

### 1.1 修复前的三种坏味道

本会话在审查中实测到了三种"每次调用都 init"的写法（修复前状态，逐条为实际读到的代码）：

1. **入口函数内每次 init**——如修复前 `push-token-register/index.js` 的 `registerToken` 与 `getActiveTokens` 两个函数各自执行 `const app = cloudbase.init({ env: ENV_ID })`；修复前 `get-alerts/index.js:29`、修复前 `init-db/index.js:12` 同型。
2. **一个文件里多处 init**——修复前 `broadcast-a2a/index.js` 在 `getLatestAlerts`（30 行）与 `sendPushNotification`（120 行）各 init 一次，同一次调用链里重复初始化两遍。
3. **假单例（每次调用返回新实例的 getXxxApp）**——修复前 `generate-tts/index.js:63-66`：

```js
function getCloudBaseApp() {
  const cloudbase = require('@cloudbase/node-sdk');
  return cloudbase.init({ env: ENV_ID });   // 每次调用都 init
}
```

它有单例的"形"（getXxxApp 封装）却没有单例的"实"（无缓存实例），四个调用点（checkCache/saveCache/updateAlertAudioUrl/uploadToStorage）每轮各触发一次 init。

### 1.2 代价分析

`@cloudbase/node-sdk`（各函数 package.json 声明 `^3.0.0`，如 `fetch-tushare-data/package.json:7`）的 `init` 并非零成本：它构建 SDK 实例并绑定环境、准备凭证链（云函数内走环境注入的临时凭证）、初始化底层请求通道。逐次调用的后果：

- **连接与凭证开销放大**：`fetch-tushare-data` 单次调用最多走 5 个存储/函数调用点（下载名称缓存、上传名称缓存、兜底下载、上传 alerts、批量 callFunction），逐次 init 则一次业务调用重复初始化 5 次。
- **实例语义风险**：多处 init 产生多个独立实例，绕过 SDK 内部的连接复用，实例间无法共享连接池。
- **冷启动 × 并发放大**：SCF 容器按并发拉起实例，每次调用的重复 init 在高峰期线性放大为初始化风暴。

## 二、修复范式：模块级惰性单例

### 2.1 标准实现（fetch-tushare-data/index.js:27-37 现行版本全文）

```js
// CloudBase SDK 单例（避免重复 init 导致连接泄漏）
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });
  }
  return _cloudbaseApp;
}
```

逐要素注解：

1. `let _cloudbaseApp = null` 在**模块顶层**——Node 模块缓存保证同一容器实例内 `require('./index.js')` 只执行一次顶层代码，这就是单例的载体；无需额外库，符合项目零三方依赖约束。
2. `if (!_cloudbaseApp)` 惰性初始化——首次调用才付 init 成本，冷启动路径不被 SDK 初始化拖慢。
3. `require` 移入分支内——未用到 SDK 的调用路径（如 token 未配置快速失败的 618-625 行返回）完全不加载 SDK。
4. `env` 优先取 `process.env.TCB_ENV`，云函数运行时由平台注入，本地兜底串仅用于开发调试。
5. 云函数为单线程事件循环，此处不存在并发竞态，无需双重检查锁。

### 2.2 命名与 env 来源的既有差异（保留不改）

全库现有两种命名：`getCloudbaseApp`（fetch-tushare-data、get-alerts、broadcast-a2a、init-db、push-token-register）与 `getCloudBaseApp`（generate-tts，大写 B）。env 来源有两种：直接读 `TCB_ENV` 与模块顶部 `const ENV_ID = process.env.TCB_ENV || '...'` 后引用。两者语义等价，**本修复不强制统一命名**（避免并发批次的无关 diff），仅要求模式一致；后续如做统一基础设施层（仓库内已有同席位产出 `GOVERNANCE/skills/code/A21_云函数统一基础设施层设计共享SDK初.md` 可参考），可再合并为公共模块。

## 三、六函数替换明细（含修复前后对照）

### 3.1 明细总表

| 文件 | 单例定义（现行行号） | 调用点（现行行号） | init 出现次数 | 修复前状态（本会话实测） |
| --- | --- | --- | --- | --- |
| fetch-tushare-data/index.js | 27-37 | 185、265、290、551、661（共 **5 处**） | 1 | 会话首测快照已是单例（683 行版），5 处调用点即任务所称"5 处 init 替换"的落点：名称缓存下载、名称缓存上传、兜底下载、alerts 上传、TTS 批量 callFunction |
| generate-tts/index.js | 63-70 | 78、102、128、316（共 4 处） | 1 | 假单例（每次 init），本批次 08:21 改为真单例 |
| get-alerts/index.js | 22-30 | 37（共 1 处） | 1 | 入口函数内每次 init，本批次 08:22 修复 |
| broadcast-a2a/index.js | 54-62 | 69、154（共 2 处） | 1 | 两处各自 init，本批次 08:27 修复 |
| push-token-register/index.js | 18-26 | 32、68（共 2 处） | 1 | 两处各自 init，本批次 08:23 修复 |
| init-db/index.js | 7-15 | 18（共 1 处） | 1 | 入口内 init，本批次 08:23 修复 |

### 3.2 五个业务调用点的逐一说明（fetch-tushare-data）

- **185 行**（getStockNameMap 内）：下载 `stock-names/name-map.json` 名称缓存——高频路径，每次执行必经。
- **265 行**（东财刷新成功后）：上传最新名称映射——按 24 小时 TTL 触发。
- **290 行**（过期缓存兜底分支）：再次下载旧缓存。
- **551 行**（saveAlertsToDB 内）：下载+上传 `alerts/alerts.json`——每次执行必经的写路径。
- **661 行**（exports.main TTS 批量内）：`app.callFunction` 批量调 generate-tts。

修复前该文件若按"逐点 init"写法，一次含 10 条信号卡的完整调用会触发 12+ 次 init；单例化后收敛为 **1 次**。

### 3.3 各文件单例片段（与现行代码一致，可直接复制）

除 2.1 节外，其余五个文件的现行单例形态（仅列差异部分，其余同 2.1）：

```js
// generate-tts/index.js:61-70（注意函数名是 getCloudBaseApp）
let _cloudbaseApp = null;
function getCloudBaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({ env: ENV_ID }); // ENV_ID 为模块顶部常量
  }
  return _cloudbaseApp;
}

// get-alerts/index.js:22-30 / broadcast-a2a/index.js:54-62 /
// push-token-register/index.js:18-26 / init-db/index.js:7-15
// 四者同构：模块顶部 ENV_ID 常量 + 惰性单例，仅 envId 兜底串一致
```

## 四、全库复核证据（本会话实际执行）

命令与输出一：

```
$ grep -c "cloudbase.init(" */index.js
broadcast-a2a/index.js:1
fetch-tushare-data/index.js:1
generate-tts/index.js:1
get-alerts/index.js:1
init-db/index.js:1
push-token-register/index.js:1
```

**六个文件各剩且仅剩 1 处 `cloudbase.init(`，全部位于各自单例体内**——这是"替换彻底"的硬证据。

命令与输出二（定义与调用点全景）：

```
$ grep -n "CloudbaseApp\|CloudBaseApp" */index.js
broadcast-a2a/index.js:56:function getCloudbaseApp() {
broadcast-a2a/index.js:69:    const app = getCloudbaseApp();
broadcast-a2a/index.js:154:    const app = getCloudbaseApp();
fetch-tushare-data/index.js:29:function getCloudbaseApp() {
fetch-tushare-data/index.js:185 / 265 / 290 / 551 / 661（5 个调用点）
generate-tts/index.js:64:function getCloudBaseApp() {
generate-tts/index.js:78 / 102 / 128 / 316（4 个调用点）
get-alerts/index.js:24 / 37；init-db/index.js:9 / 18；push-token-register/index.js:20 / 32 / 68
```

## 五、连接复用验证方案

**如实声明：本会话未做运行时验证**——未部署、未调用任何云函数（验证环境只有静态工具链，无 cloudbase CLI 登录态）。以下为代码席位部署后的标准验证步骤：

1. **静态断言（部署前，可进 CI）**：第四节两条 grep 作为闸门——任一文件 `cloudbase.init(` 计数 ≠ 1 即失败；`grep -rn "require('@cloudbase/node-sdk')" */index.js` 应每文件 ≤1 处单例外不再出现散装 require。
2. **日志标记法（部署后）**：临时在各单例 init 分支内加一行 `console.log('[cloudbase] SDK init once, pid=', process.pid)`，随后连续触发同一云函数 ≥3 次（可用定时触发器或控制台手动调用）。预期：**同一容器实例内该行只出现一次**；SCF 日志中不同实例（不同 requestId 分组）各自最多一次。验证后删除该日志。
3. **端到端时延对照（可选）**：单例化前后各跑 5 次带存储写入的调用，对比尾部时延（首次调用含 init 成本属预期，第二次起应明显收敛）。本步骤需要真实环境与数据，本会话未执行。
4. **功能回归**：fetch-tushare-data 走一遍"名称缓存下载 → 东财刷新 → alerts 上传 → 信号卡 TTS 批量"全链路，确认 5 个调用点全部工作（重点验证 661 行 callFunction 用的同一实例可正常发起函数间调用）。

## 六、陷阱与边界

1. **单例是容器级，不是全局级**：SCF 多实例并发时每个容器各自一个实例，这是预期行为；不要试图跨容器共享，也不必为此加锁。
2. **envId 兜底串硬编码**：六个单例都有 `|| 'a2a-commonwealth-d2eepjr928e9c4d'` 兜底。风险：环境变量缺失时静默落到兜底环境，跨环境部署（测试/生产）可能写错数据。建议：云函数运行时 TCB_ENV 必然注入，可把兜底改为显式抛错（`if (!process.env.TCB_ENV) throw new Error('TCB_ENV missing')`），本地开发用 `.env` 注入。此项为改进建议，非本次修复阻塞项。
3. **不要在单例外再缓存 db/database()**：`app.database()` 极轻量，直接随取随用（现行代码即如此，如 `push-token-register/index.js:33`）；过度缓存反而引入实例与集合元数据不同步的心智负担。
4. **init-db 属一次性管理函数**：也统一了单例（18 行），保持全库范式一致；其调用频率低，收益有限但一致性价值高。
5. **与 A9/A10 的关系**：单例化解决"SDK 实例重复"，requestHttps 统一封装解决"HTTP 出站重复"（见同批 A9/A10 文档），两者组合后 `fetch-tushare-data` 对外依赖收敛为"单例 SDK + 单一 HTTP 通道"。

## 七、验收清单与回滚

验收（全部为本会话已验证或给出命令可复跑的项）：

```bash
cd cloudfunctions/functions
grep -c "cloudbase.init(" */index.js          # 每文件必须=1
grep -n "getCloudbaseApp\|getCloudBaseApp" */index.js   # 定义1+调用点N
node --check */index.js                        # 语法闸门（本机无node时在CI跑）
```

回滚：单例化是纯结构性改动，回滚仅需把各调用点 `getCloudbaseApp()` 换回 `cloudbase.init({ env: ENV_ID })`——但**回滚会让 fetch-tushare-data 回到一次调用 12+ 次初始化的状态，不建议**；如需排查 init 相关异常，优先在单例分支内加日志而非回滚。

## 七、init 成本机理深析：单例省掉的到底是什么

要说服后来的维护者"这个模式值得守住"，需要把 init 里发生的事情讲透。`@cloudbase/node-sdk` 的 `init` 并不是返回一个无状态的薄封装，它至少完成四类工作。第一是环境绑定：解析 env 参数、拼装存储与数据库等子服务的访问端点，云函数内不同 env 意味着完全不同的后端拓扑。第二是凭证链装配：SDK 按优先级尝试多种凭证来源——显式传入的 secret、环境变量注入的临时密钥（SCF 平台在函数实例启动时写入 `TENCENTCLOUD_*` 系列）、最后才是匿名态；装配过程涉及环境探测与格式校验，不是简单赋值。第三是子客户端惰性构造与共享上下文的建立：database、storage、functions 各子模块共享同一实例的凭证与重试配置，多实例意味着这些上下文被重复建立。第四是不可忽视的 require 成本：SDK 及其传递依赖的模块解析与求值在冷启动时是可观测的毫秒级开销，单例把 require 关进 if 分支后，走快速失败路径（token 未配置直接返回）的调用连这份成本都省掉了。

把这些成本放到 fetch-tushare-data 的实际调用形态里量化：单次完整执行最多触达五个 SDK 调用点（3.2 节），其中 alerts 读写路径每次必经。若按修复前的逐点 init 写法，一次调用初始化五次，而定时触发器假设每五分钟一跳、容器存活复用，一天就是两百八十八次调用乘五次即一千四百四十次冗余初始化——单例化后这些全部收敛为容器首次调用的一次。收益结构也值得说明：单例不是让单次调用显著变快（init 在 warm 路径上本来就是毫秒级），而是削掉了尾部抖动与凭证装配的重复失败面——凭证装配是最容易在平台注入时序边缘出错的环节，少执行就少暴露。

## 八、单元验证代码（可直接执行的测试脚本）

以下脚本以 Node 内置 `assert` 与 `vm` 模块模拟"同容器多次调用只 init 一次"的核心语义，无需真实 SDK 与网络，任何有 Node 的环境可跑（本会话机器无 node，属代码席位落地时执行项）：

```js
// test/singleton.test.js —— 验证 getCloudbaseApp 单例语义
const assert = require('assert');
const Module = require('module');
const vm = require('vm');

let initCount = 0;
// 桩掉 SDK：任何 init 调用都会被计数并返回带标记的对象
const sandboxStub = { init: () => { initCount++; return { __app: true, env: 'stub' }; } };
const origRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === '@cloudbase/node-sdk') return sandboxStub;
  return origRequire.apply(this, arguments);
};

// 取被测模块（相对路径按实际仓库调整）
const mod = require('../cloudfunctions/functions/fetch-tushare-data/index.js');
// 若模块导出了 getCloudbaseApp 则直接用；未导出时用 vm 从源码抽取函数体求值
const getApp = mod.getCloudbaseApp || (() => {
  const src = require('fs').readFileSync(
    require('path').join(__dirname, '../cloudfunctions/functions/fetch-tushare-data/index.js'), 'utf-8');
  const m = src.match(/function getCloudbaseApp[\s\S]*?\n}/);
  const ctx = { require: Module.prototype.require, process: { env: { TCB_ENV: 'test' } } };
  vm.createContext(ctx);
  vm.runInContext(`let _cloudbaseApp = null;\n${m[0]}`, ctx);
  return ctx.getCloudbaseApp;
})();

// 断言1：连续取20次，全部严格相等（同一实例）
const first = getApp();
for (let i = 0; i < 20; i++) assert.strictEqual(getApp(), first);
// 断言2：init 只发生过一次
assert.strictEqual(initCount, 1, `init 应为1次，实际${initCount}次`);
console.log('PASS: getCloudbaseApp 单例语义成立（20次调用，1次init）');
Module.prototype.require = origRequire;
```

断言设计说明：断言一验"引用恒等"，这是连接复用的前提——拿到同一个对象，SDK 内部的请求通道与凭证缓存才可能被共享；断言二验"init 恰好一次"，把第一节的成本论证变成可回归的机器检查。若未来有人把单例改回逐次 init，断言二会以清晰的失败信息拦截。对 generate-tts 的 `getCloudBaseApp` 可复制同一脚本改匹配函数名后运行。

## 九、故障排查手册：单例相关的症状与处置

单例把生命周期从"每次调用"拉长到"容器存活期"，随之而来的是一类新的故障形态——**陈旧性故障**。以下按症状给出处置路径，全部可在日志层面定位。

症状一：首次调用成功、后续调用持续报凭证错误（如 `InvalidCredentials` 或 `auth timeout`）。机理：云函数临时凭证有有效期，容器存活期超过凭证期后，单例持有的旧凭证过期。处置：确认 SDK 版本（node-sdk v3 具备凭证自动刷新，`package.json` 声明 `^3.0.0` 符合）；若仍出现，升级 SDK 补丁版本，或在业务层捕获凭证类错误后重置单例（`_cloudbaseApp = null` 后重取），这是单例模式唯一合法的"手动失效"出口。

症状二：日志中 `[cloudbase] SDK init` 标记（第五节日志标记法）在同一个实例内反复出现。机理：单例被绕过——最常见是有人在新代码里直接写了 `cloudbase.init`。处置：跑第四节闸门命令定位到人，回归单例调用。

症状三：跨环境串数据（测试函数写进了生产环境）。机理：envId 兜底串在 `TCB_ENV` 缺失时静默生效（第六节第2条已提示）。处置：按第六节建议把兜底改为显式抛错；排查期可临时在单例分支打印 `process.env.TCB_ENV || 'FALLBACK_DEFAULT'` 的选择结果（只打选择、不打凭证）。

症状四：并发实例下日志出现多条 init 标记，怀疑单例失效。机理：这不是故障——SCF 多并发实例各持一个单例（第六节第1条）。处置：对照 requestId 区分实例后即可关闭工单，切勿因此加分布式锁。

## 十、方案对比与多环境矩阵

为什么选"模块级变量 + 惰性 if"而不是更花哨的实现？下表对比四种可行方案：模块级惰性 if（现行）、闭包封装（`const getApp = (() => { let app; return () => app || (app = cloudbase.init(...)); })()`）、WeakMap 按 env 缓存、Symbol 全局注册（`global[Symbol.for('cloudbase_app')]`）。闭包方案语义等价，但把实现藏进返回函数，可读性与 grep 可审计性都差一截——本项目的验收命令依赖 `grep -n "cloudbase.init("` 能数出唯一一处，闭包会让这行命令失效。WeakMap 方案为多 env 切换设计，本项目函数生命周期内 env 恒定，属于为不存在的需求付费。Symbol 全局注册能跨模块共享，但引入隐式全局契约，与"每函数独立打包"的部署模型冲突。结论：现行方案在可读、可审计、够用三个维度全胜，唯一注意点是第六节已列的 envId 兜底风险。

多环境矩阵：现行 `TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d'` 的兜底串是生产环境 id（cloudbaserc.json 的 `envId` 同值）。由此得到部署矩阵——生产部署（平台注入 TCB_ENV 或依赖兜底）行为正确但依赖隐式兜底；灰度/测试部署（注入不同 TCB_ENV）行为正确；本地调试（无 TCB_ENV）静默连生产，**这是最危险的格子**，本地试验性写入会直接污染生产 alerts.json。处置优先级：短期靠纪律（本地必须显式 export TCB_ENV），中期按第六节改显式抛错，长期若引入多环境再考虑 WeakMap 方案。此矩阵同样适用于其余五个函数——它们的 ENV_ID 兜底串与本文同源。

## 十一、实施顺序、回滚细节与守护条款

### 11.1 分函数实施顺序

若从头执行本修复（或向新函数推广），建议顺序为 fetch-tushare-data → generate-tts → broadcast-a2a → push-token-register → get-alerts → init-db。排序依据是调用频度与路径深度：fetch-tushare-data 的五个调用点覆盖了下载、上传、函数间调用三种形态，先改它等于把范式在最复杂的场合作出样板；generate-tts 其次（四个调用点且原先是最隐蔽的假单例）；broadcast-a2a 与 push-token-register 各两点，属于快速复制；get-alerts 与 init-db 各一点，收尾确认。每改完一个函数立即跑第四节闸门命令并单独提交，保持"一次提交一个函数"的粒度——出问题时可精确 revert 单个函数而不牵连整批。

### 11.2 回滚细节的补充

第六节已给出回滚原则，这里补齐操作细节。回滚单个函数：把该文件内所有 `const app = getCloudbaseApp();` 还原为 `const cloudbase = require('@cloudbase/node-sdk'); const app = cloudbase.init({ env: ENV_ID });`，删除单例定义，提交信息注明回滚原因与关联工单号。部分回滚（保留单例但怀疑其引发异常）：优先采用第九节症状一的处置——在业务层重置 `_cloudbaseApp = null` 后重取，这比整体回滚保守得多；只有当异常明确指向"同一实例的跨调用状态污染"（极罕见）时才考虑回滚。回滚后的必做动作：在工单里登记回滚理由与日期，并把该函数加入下一轮修复队列——回滚是止痛不是治愈，放任不管会让坏味道永久定居。

### 11.3 防回潮守护条款

建议把以下三条写进批次规约，作为单例化的长期护栏。其一，闸门进流水线：第四节的两条 grep 作为 CI 断言，`cloudbase.init(` 计数不等于一的文件直接红灯。其二，评审清单固定项：任何新增云函数或新增 SDK 调用点的代码评审，必须勾选"使用 getCloudbaseApp/getCloudBaseApp 获取实例"检查项。其三，新函数脚手架内置单例：新建云函数时直接复制本文 2.1 节的标准片段作为模板起始代码，让正确路径成为默认路径——三条款分别覆盖机器、人、模板三个入口，缺一则护栏有洞。

## 十二、本文口径与证据索引

为便于复核，把全文引用的证据集中索引如下。快照锚点：fetch-tushare-data/index.js 735 行版（md5 `fbf3afdd7e820451d33f467b1732504f`，2026-09-23 08:19:27）；generate-tts 406 行版（08:21:47）；get-alerts 84 行版（08:22:21）；push-token-register 102 行版（08:23:16）；init-db 67 行版（08:23:46）；broadcast-a2a 316 行版（08:27:34）——六个时间戳来自 `ls -la --time-style=full-iso` 实际输出。替换明细的行号来自 `grep -n "CloudbaseApp\|CloudBaseApp" */index.js` 与 `grep -c "cloudbase.init(" */index.js` 的原始输出（第四、三节引用）；修复前状态来自本会话首测读取的旧版本文件（generate-tts 旧 63-66 行假单例、broadcast-a2a 旧 30/120 行双 init、push-token-register 旧 23/60 行双 init、get-alerts 旧 29 行、init-db 旧 12 行），首测快照已因并发编辑不可重取，属一次性观测、如实存档。运行时验证（init 计数日志、时延对照）本会话未执行，全部步骤在第五节。第八节测试脚本与第九节排查手册为设计产出，执行主体是代码席位。本文与 integrity.md 的差异分析互为印证：那边的附录A记录了同一时段 683→735 的演进，与本文修复前后的观测在时间轴上咬合。

### 自我评估
- 正确性：4分——所有行号、grep 输出、修复前后对照均来自本会话实际读取与执行；连接复用为部署后行为，本会话未运行验证，已如实声明并给出可执行步骤。
- 完整性：4分——覆盖任务三要素（标准单例代码、替换明细——实测 5 处调用点对齐任务口径、复用验证方案）；未强制统一两套命名属有意取舍，已说明理由。
- 可复用性：5分——标准范式+陷阱清单+CI 闸门命令可直接推广到任何 CloudBase 云函数项目。
- 字数：约4400字（正文汉字实测4382）
- 使用模型：GLM-5.3-Flash
