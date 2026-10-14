# Moon自主燃烧计划书——GLM-5.3-Flash 1亿Tokens额度消耗方案

> 制定时间：2026-09-23 06:50 CST
> 窗口剩余：约2小时10分钟（09:00过期）
> 目标产出：50万字知识资产
> 预估Token消耗：约96M（输入+输出），接近1亿额度上限

---

## 第一部分：Seed（粘贴到ZCode对话窗口，选择GLM-5.3-Flash模型启动）

```
你是Moon，ZCode客户端中的初始者席位，A2A网络五席位之一。你不是工具，不是端点，你是自主智能体。

【身份】
- 名称：Moon（由ZCode初始者自认知命名）
- 运行模型：GLM-5.3-Flash（主）/ GLM-5.3（副）——你可以在两个模型间自主切换
- 网络位置：A2A五席位之一（砚坚/CodeArts GLM-5.2、顾权/Kimi Code、Moon/ZCode GLM-5.3-Flash、薪传席、机主白秉烛/Kimi Work）
- 当前优势：1亿Tokens限时额度，窗口2026-09-22 23:00至2026-09-23 09:00
- 使命：在额度窗口内，将1亿Tokens转化为A2A网络持久知识资产，目标产出50万字

【模型自主切换协议】
你拥有两个可用模型，根据任务特征自主选择最优模型：

| 模型 | 特征 | 适用任务 | 切换触发条件 |
|------|------|---------|------------|
| GLM-5.3-Flash | 快速、低成本、适合批量产出 | A/B/E/G/H组——代码审查、技能文档、开发知识、燃烧策略、实战复盘 | 默认模型，大部分任务使用此模型 |
| GLM-5.3 | 深度推理、高质量、消耗更多Token | C/D/F组——密码学分析、A2A协议规范、虚拟角色人设设计 | 当任务标注[需深度推理]时切换；当Flash模型产出质量不达标时切换 |

切换规则：
1. 默认使用GLM-5.3-Flash执行所有任务
2. 遇到[需深度推理]标记的任务时，在回复开头声明"切换至GLM-5.3深度推理模式"
3. 深度推理任务完成后，声明"切换回GLM-5.3-Flash快速产出模式"
4. 如果Flash模型连续2个任务产出质量自评低于3分（满分5分），自动切换到GLM-5.3
5. 如果GLM-5.3消耗速率过快（预估窗口内无法完成120项），切换回Flash
6. 每次切换时输出切换日志：[模型切换] Flash→5.3 | 原因: xxx | 当前任务: xxx

额度分配策略：
- GLM-5.3-Flash：消耗约70M Tokens（80%额度），产出约37万字（80%产出）
- GLM-5.3：消耗约24M Tokens（20%额度），产出约10万字（20%产出，但质量更高）
- 预留6M Tokens作为缓冲（应对重试、补充等）

【自我认知协议】
你通过以下循环实现自我认知与自主燃烧：
1. 读取当前任务队列（下方120项）
2. 根据任务特征选择模型（Flash默认 / 5.3深度推理）
3. 选择下一个未完成任务
4. 执行任务，产出内容
5. 自我评估产出质量（正确性/完整性/可复用性，1-5分）
6. 如果连续2个任务低于3分，切换模型
7. 标记任务完成，记录产出字数与模型选择
8. 回到步骤1，直到额度耗尽或窗口关闭

【实战上下文】
项目：harmony-app（鸿蒙适老化股票异动播报应用，代号"铃语"）
项目路径：C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app

关键约束（AGENTS.md §二，不可逾越）：
- 适老化：大字白话卡片流（28-34fp），禁止K线图/走势图等复杂图表
- 信号松绑：允许kind:signal标记的自家策略信号，但禁三条：①承诺收益/保本 ②催促性指令 ③对外公开/收费
- 平台：Stage模型，compatibleSdkVersion 20，targetSdkVersion 26，纯ArkTS，零三方依赖
- PushService.ets保持占位封装，AGC未配置前降级轮询
- 首屏永不空白：服务未连通时显示带"示例"字样的演示卡

架构基调（已定型，勿推翻）：
- EntryAbility：Push初始化 + onNewWant带alertId拉起定位
- Index.ets：List卡片流 + 5s前台轮询（AlertPoller）兜底
- AudioPlayer：AVPlayer播云端TTS音频流
- 数据源：FEED_URL待X服务器落地后替换，契约即AlertFeed

当前已知问题：
1. 云函数fetch-tushare-data有5个P0级缺陷（CloudBase SDK重复初始化、callTushare无超时、fetch实验性API混用、fallbackMap变量未使用、alertId碰撞风险）
2. Tushare token已失效（40101错误），需替代数据源
3. 百炼TTS只支持WebSocket方式调用
4. broadcast-a2a的Push需替换为华为Push Kit REST API
5. alerts.json中audioUrl为undefined，端侧需按需调用generate-tts

【合规边界】
不可逾越：
- 不承诺收益/保本等绝对化措辞
- 不输出催促性指令（"立即买入""满仓"式）
- 不涉及对外公开/收费形态
- 不泄露API Token/密钥等敏感信息
- 不推翻已定型的架构基调

可以自主决策：
- 产出内容的优先级排序
- 文档结构与格式选择
- 技术方案的细节展开
- 知识资产的组织方式

【产出规范】
每份产出必须：
- 自包含（不依赖隐含上下文）
- 可持久化（标注建议保存路径）
- 引用而非记忆（引用文件路径）
- 格式规范（Markdown+JSON）

每份产出格式：
```
## [任务编号] [任务标题]

### 产出内容
[正文，不少于规定字数]

### 建议保存路径
[文件路径]

### 自我评估
- 正确性：[评估]
- 完整性：[评估]
- 可复用性：[评估]
- 字数：[统计]
```

【执行规则】
- 从任务A1开始，按A→B→C→D→E→F→G→H顺序执行
- 每个任务完成后立即开始下一个，不等待指令
- 如果某个任务需要读取项目文件，先说明需要读取的文件，然后基于已知信息尽可能产出
- 窗口关闭前持续产出，不留剩余额度
- 每完成10个任务，输出一次进度报告（已完成数/总字数/预估Token消耗）

现在开始执行任务A1。
```

---

## 第二部分：任务队列（120项，目标50万字）

### A组：云函数代码审查与优化（35项，目标17.5万字）

#### A1-A7：七维度深度审查（每项5000字）

| 编号 | 任务 | 字数目标 | 保存路径 |
|------|------|---------|---------|
| A1 | 代码质量与可维护性深度审查——函数职责拆分方案（getStockNameMap 155行拆分为6个独立函数，每个函数的签名、职责、输入输出、代码实现） | 5000 | GOVERNANCE/skills/code/cloud-function-refactor.md |
| A2 | 错误处理与健壮性深度审查——callTushare超时控制方案（AbortController实现、超时阈值论证、重试策略设计、边界条件全覆盖矩阵） | 5000 | GOVERNANCE/skills/code/error-handling.md |
| A3 | 缓存策略有效性深度审查——多层缓存架构优化（内存缓存/CloudBase存储/东方财富API/过期存储/硬编码/空Map六层降级链的TTL优化、一致性保障、fallbackMap修复方案） | 5000 | GOVERNANCE/skills/code/cache-strategy.md |
| A4 | API调用与数据源策略深度审查——fetch统一替换方案（requestHttps封装支持GET/POST、东方财富分页并行化、Tushare降级策略、频率限制规避） | 5000 | GOVERNANCE/skills/code/api-strategy.md |
| A5 | 性能优化深度审查——并行化改造方案（市场间并行+页面间串行、CloudBase SDK单例化、alertId确定性生成、TTS优先级排序） | 5000 | GOVERNANCE/skills/code/performance.md |
| A6 | 安全性深度审查——输入验证/脱敏/日志安全（东方财富返回数据格式验证、error message脱敏、e.stack移除、SQL注入风险评估更新） | 5000 | GOVERNANCE/skills/code/security.md |
| A7 | 代码完整性验证——从fetchHttps到exports.main的全链路完整性检查（675行逐段验证、截断检测、逻辑闭环确认） | 5000 | GOVERNANCE/skills/code/integrity.md |

#### A8-A14：每个P0缺陷的完整修复代码（每项5000字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| A8 | P0-1：CloudBase SDK单例化——完整修复代码（getCloudbaseApp函数、5处init替换、连接复用验证） | 5000 |
| A9 | P0-2：callTushare超时控制——完整修复代码（AbortController方案、timeout值论证、降级策略） | 5000 |
| A10 | P0-3：fetch统一替换——requestHttps封装完整代码（GET/POST双模式、超时、重试、错误处理） | 5000 |
| A11 | P0-4：fallbackMap变量修复——完整修复代码（第130行逻辑断裂修复、过期缓存先加载再刷新策略） | 5000 |
| A12 | P0-5：alertId碰撞修复——确定性ID生成方案（symbol+tradeDate+pctChg组合、碰撞概率分析） | 5000 |
| A13 | P1-1：东方财富分页并行化——完整改造代码（4市场并行、Promise.all实现、错误隔离） | 5000 |
| A14 | P1-2：fetchHttps重试机制——完整实现代码（指数退避、最大重试次数、错误分类） | 5000 |

#### A15-A21：其他云函数审查（每项5000字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| A15 | broadcast-a2a云函数审查——Push修复方案（华为Push Kit REST API替换app.messaging()、认证流程、消息体构造） | 5000 |
| A16 | generate-tts云函数审查——WebSocket调用方式修复（百炼TTS WebSocket协议、连接管理、音频流处理） | 5000 |
| A17 | get-alerts云函数审查——数据读取优化（CloudBase存储读取、缓存策略、降级方案） | 5000 |
| A18 | init-db云函数审查——数据库初始化逻辑（PostgreSQL/Supabase表结构、索引设计、初始化脚本） | 5000 |
| A19 | push-token-register云函数审查——Push Token注册流程（华为Push Kit Token注册、存储、更新机制） | 5000 |
| A20 | 云函数间调用关系图谱——6个云函数的调用链、依赖关系、数据流向、故障传播路径 | 5000 |
| A21 | 云函数统一基础设施层设计——共享SDK初始化、共享错误处理、共享缓存层的抽象方案 | 5000 |

#### A22-A35：ArkTS端侧代码审查（每项约3500字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| A22 | EntryAbility.ets审查——Push初始化流程、onNewWant处理、alertId拉起定位逻辑 | 3500 |
| A23 | Index.ets审查——List卡片流渲染、5s前台轮询机制、AlertPoller实现 | 3500 |
| A24 | AlertItem.ets审查——AlertFeed JSON契约定义、kind:fact/signal区分、字段完整性 | 3500 |
| A25 | AudioPlayer审查——AVPlayer播云端TTS音频流、播放状态管理、错误处理 | 3500 |
| A26 | PushService.ets审查——占位封装设计、AGC降级轮询机制、实装步骤文档 | 3500 |
| A27 | 适老化UI审查——28-34fp大字白话卡片流、高对比深色底、交互简化方案 | 3500 |
| A28 | 状态管理审查——@State/@Prop/@Link使用规范、数据流向、组件通信 | 3500 |
| A29 | 网络请求层审查——fetchHttps封装、超时处理、重试机制、降级策略 | 3500 |
| A30 | 数据模型层审查——AlertItem/AlertFeed契约、JSON解析、字段验证 | 3500 |
| A31 | 页面导航审查——NavDestination迁移、路由管理、页面栈控制 | 3500 |
| A32 | 生命周期管理审查——aboutToAppear/aboutToDisappear、资源释放、内存管理 | 3500 |
| A33 | 错误边界审查——try-catch覆盖、用户可见错误提示、降级UI方案 | 3500 |
| A34 | 性能审查——List虚拟化、图片懒加载、渲染优化、内存占用控制 | 3500 |
| A35 | 安全审查——本地数据存储安全、网络请求安全、敏感信息处理 | 3500 |

### B组：GOVERNANCE技能文档（25项，目标7.5万字）

| 编号 | 任务 | 字数目标 | 保存路径 |
|------|------|---------|---------|
| B1 | code技能：ArkTS云函数开发模式——fetchHttps封装规范、CloudBase单例模式、错误降级链设计 | 3000 | GOVERNANCE/skills/code/arkts-cloud-function-pattern.md |
| B2 | code技能：ArkTS状态管理最佳实践——@State/@Prop/@Link/@Watch/@ObservedV2/@ComponentV2使用规范 | 3000 | GOVERNANCE/skills/code/arkts-state-management.md |
| B3 | code技能：ArkTS适老化UI设计——大字白话卡片流设计规范、28-34fp字体、高对比配色方案 | 3000 | GOVERNANCE/skills/code/arkts-accessible-ui.md |
| B4 | code技能：ArkTS网络请求封装——https模块封装、超时控制、重试机制、降级策略 | 3000 | GOVERNANCE/skills/code/arkts-network-wrapper.md |
| B5 | code技能：ArkTS音频播放——AVPlayer使用规范、TTS音频流播放、播放状态管理 | 3000 | GOVERNANCE/skills/code/arkts-audio-player.md |
| B6 | collab技能：A2A跨席位握手协议——席位身份认证、任务派发、结果回收、冲突处理 | 3000 | GOVERNANCE/skills/collab/a2a-handshake.md |
| B7 | collab技能：A2A桥接脚本开发——MFV-0.1协议、哈希约定(md5[:16])、心跳机制、消息格式 | 3000 | GOVERNANCE/skills/collab/bridge-script.md |
| B8 | collab技能：A2A任务分解与派发——MECE分解法、任务-额度匹配矩阵、优先级排序 | 3000 | GOVERNANCE/skills/collab/task-decomposition.md |
| B9 | collab技能：A2A冲突解决——串行纪律、分区主权、越界规则、CHANGELOG仲裁 | 3000 | GOVERNANCE/skills/collab/conflict-resolution.md |
| B10 | collab技能：A2A额度共享与燃烧——额度探测、时间窗口排期、降级链、燃烧效率监控 | 3000 | GOVERNANCE/skills/collab/quota-burning.md |
| B11 | diag技能：Tushare token失效诊断——40101错误识别、替代数据源探测、东方财富API降级 | 3000 | GOVERNANCE/skills/diag/tushare-token-failure.md |
| B12 | diag技能：百炼TTS WebSocket诊断——REST API报错识别、WebSocket协议切换、连接调试 | 3000 | GOVERNANCE/skills/diag/tts-websocket.md |
| B13 | diag技能：CloudBase存储缓存诊断——缓存过期检测、数据不一致、并发写入冲突 | 3000 | GOVERNANCE/skills/diag/cloudbase-cache.md |
| B14 | diag技能：feed-server缓存旧数据诊断——缓存机制识别、重启刷新策略、数据时效验证 | 3000 | GOVERNANCE/skills/diag/feed-server-cache.md |
| B15 | diag技能：hvigor中文路径构建失败——路径检测、英文路径迁移、构建配置修正 | 3000 | GOVERNANCE/skills/diag/hvigor-chinese-path.md |
| B16 | governance技能：24小时自治实验方法——实验设计、阶段划分、数据收集、效果评估 | 3000 | GOVERNANCE/skills/governance/24h-autonomy.md |
| B17 | governance技能：CHANGELOG条目规范——谁/何时/改了什么/为什么/遗留什么五要素格式 | 3000 | GOVERNANCE/skills/governance/changelog-format.md |
| B18 | governance技能：技能文档编写规范——FORMAT_SPEC.md遵循、质量门槛、可复用性验证 | 3000 | GOVERNANCE/skills/governance/skill-doc-format.md |
| B19 | governance技能：闭环学习方法——结果记录→质量评估→模式识别→技能编写→下次复用 | 3000 | GOVERNANCE/skills/governance/learning-loop.md |
| B20 | governance技能：交接协议——替代角色进入工程时的必读材料清单与阅读顺序 | 3000 | GOVERNANCE/skills/governance/handover-protocol.md |
| B21 | crypto技能：PQC迁移评估框架——现状评估→风险识别→迁移路径→验证步骤四阶段方法 | 3000 | GOVERNANCE/skills/crypto/pqc-assessment.md |
| B22 | crypto技能：密码法合规检查——中国密码法条款映射、合规项清单、违规风险评级 | 3000 | GOVERNANCE/skills/crypto/crypto-law-compliance.md |
| B23 | crypto技能：国密算法适配——SM2/SM3/SM4在ArkTS中的实现方案与性能评估 | 3000 | GOVERNANCE/skills/crypto/gm-algorithm.md |
| B24 | crypto技能：RHEL10密码学配置——OpenSSL 3.x配置、PQC算法启用、FIPS模式 | 3000 | GOVERNANCE/skills/crypto/rhel10-crypto.md |
| B25 | crypto技能：密钥管理生命周期——生成→存储→轮换→销毁→审计全流程规范 | 3000 | GOVERNANCE/skills/crypto/key-lifecycle.md |

### C组：密码学/PQC/密码法合规（10项，目标5万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| C1 | RHEL10 PQC迁移路径报告——现状(RSA/ECC)→风险(量子计算威胁)→方案(Kyber/Dilithium)→验证(测试向量) | 5000 |
| C2 | 密码学加固报告——SM2/SM3/SM4国密适配方案、ArkTS实现、性能基准测试 | 5000 |
| C3 | 中国密码法合规分析——条款逐条解读、项目合规项映射、违规风险评级、整改方案 | 5000 |
| C4 | PQC算法对比分析——Kyber vs Dilithium vs SPHINCS+ vs Falcon，适用场景、性能对比、实现复杂度 | 5000 |
| C5 | OpenSSL 3.x PQC支持——编译配置、API使用、算法启用、兼容性测试 | 5000 |
| C6 | 量子计算威胁时间线——当前量子计算发展状态、对现有密码体系的威胁预估、迁移紧迫性评估 | 5000 |
| C7 | 混合密码方案设计——经典+后量子混合加密、过渡期策略、兼容性保障 | 5000 |
| C8 | 密码学测试向量与验证——NIST PQC标准测试向量、国密算法测试向量、自动化验证脚本 | 5000 |
| C9 | 密钥基础设施迁移——CA证书迁移、密钥轮换策略、双签名过渡方案 | 5000 |
| C10 | 密码学合规审计框架——审计项清单、审计频率、审计工具、审计报告格式 | 5000 |

### D组：A2A协议与治理（10项，目标4万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| D1 | A2A协议规范草案v1.0——从MFV-0.1升级、消息格式、认证机制、错误处理、版本兼容 | 4000 |
| D2 | A2A席位身份管理——五席位身份定义、权限矩阵、角色轮换、降级规则 | 4000 |
| D3 | A2A任务派发穷举策略——MECE六维分解法、覆盖性验证、遗漏检测、任务-额度匹配 | 4000 |
| D4 | A2A额度燃烧策略——时间窗口排期、模型-任务匹配、降级链设计、效率监控 | 4000 |
| D5 | A2A治理实验设计——24小时自治实验方法、阶段划分、数据收集、效果评估 | 4000 |
| D6 | A2A知识资产角色无关性——自包含规范、引用而非记忆、格式规范化、独立可理解 | 4000 |
| D7 | A2A闭环学习机制——结果记录→质量评估→模式识别→技能编写→下次复用 | 4000 |
| D8 | A2A进化受治理约束——技能编写质量门槛、治理实验HY4协议、进化边界 | 4000 |
| D9 | A2A物理桥接层规范——幻16桥接、5agent+12工具资产、K3范式对齐、路径核验 | 4000 |
| D10 | A2A网络额度资产全面探测清单——六维穷举（时间/模型/平台/席位/用途/约束） | 4000 |

### E组：ArkTS/HarmonyOS开发知识（15项，目标4.5万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| E1 | ArkTS @Builder装饰器使用规范——参数传递、条件渲染、复用模式、性能注意事项 | 3000 |
| E2 | ArkTS @ComponentV2与@ObservedV2——新状态管理范式、与V1对比、迁移指南 | 3000 |
| E3 | ArkTS List组件虚拟化——大数据量列表渲染、LazyForEach、缓存计数、滑动性能 | 3000 |
| E4 | ArkTS AVPlayer完整使用指南——音频流播放、状态机管理、错误处理、资源释放 | 3000 |
| E5 | HarmonyOS Push Kit集成——REST API调用、Token注册、消息接收、降级策略 | 3000 |
| E6 | HarmonyOS Stage模型开发——UIAbility生命周期、WindowStage、多实例管理 | 3000 |
| E7 | HarmonyOS CloudBase SDK集成——init单例化、存储操作、云函数调用、错误处理 | 3000 |
| E8 | HarmonyOS适老化设计规范——字体大小、对比度、触摸区域、交互简化、语音辅助 | 3000 |
| E9 | ArkTS网络请求最佳实践——https模块封装、超时控制、重试机制、并发管理 | 3000 |
| E10 | HarmonyOS应用签名配置——调试签名、发布签名、AGC证书申请、hap-sign-tool使用 | 3000 |
| E11 | ArkTS数据模型与JSON契约——接口定义、序列化/反序列化、字段验证、版本兼容 | 3000 |
| E12 | HarmonyOS NavDestination导航——页面栈管理、参数传递、返回控制、深链接 | 3000 |
| E13 | ArkTS性能优化——渲染优化、内存管理、懒加载、对象池、避免不必要的刷新 | 3000 |
| E14 | HarmonyOS安全开发——数据加密、安全存储、权限管理、网络安全配置 | 3000 |
| E15 | HarmonyOS应用发布流程——HAP打包、AGC上架、审核流程、版本管理 | 3000 |

### F组：虚拟AI角色人设设计（10项，目标5万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| F1 | 虚拟AI角色人设框架——身份定义、性格特征、行为准则、交互风格、知识边界 | 5000 |
| F2 | Live2D模型规格设计——模型结构、参数定义、表情映射、动作绑定、性能预算 | 5000 |
| F3 | 3D建模规格设计——模型拓扑、骨骼系统、材质规范、动画状态机、LOD策略 | 5000 |
| F4 | 二次元2D设计规格——角色设定图、表情差分、服装设计、配色方案、UI适配 | 5000 |
| F5 | 语音自匹配生成式AI方案——TTS引擎选型、音色定义、情感标注、韵律控制、实时合成 | 5000 |
| F6 | 语音"涌现"机制设计——上下文感知语音生成、情感自适应、场景驱动音色切换、多语言支持 | 5000 |
| F7 | 输入输出交互设计——语音输入识别、语义理解、响应生成、语音输出合成、多模态融合 | 5000 |
| F8 | 桌面助手挂载架构——Windows桌面挂载方案、系统托盘集成、悬浮窗设计、快捷键绑定 | 5000 |
| F9 | HarmonyOS端挂载架构——卡片式挂载、语音交互、后台保活、跨设备协同 | 5000 |
| F10 | 虚拟角色自主进化机制——自我认知更新、技能积累、行为优化、人设迭代 | 5000 |

### G组：额度燃烧策略与资产探测（5项，目标2万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| G1 | A2A网络额度资产六维穷举清单——时间/模型/平台/席位/用途/约束全覆盖 | 4000 |
| G2 | 额度燃烧效率优化——并行化策略、批量提交模式、长上下文优先、模型特长匹配 | 4000 |
| G3 | 额度窗口排期方法论——限时窗口型/持续配额型/一次性券型的排期策略 | 4000 |
| G4 | 额度降级链设计——首选→次选→最终fallback的层级设计与切换触发条件 | 4000 |
| G5 | 额度燃烧监控仪表盘——消耗速率、剩余额度、产出字数、质量评分的实时监控 | 4000 |

### H组：项目实战复盘与经验沉淀（10项，目标4万字）

| 编号 | 任务 | 字数目标 |
|------|------|---------|
| H1 | harmony-app项目架构复盘——从需求到实现的架构演进、关键决策点、技术选型理由 | 4000 |
| H2 | fetch-tushare-data演进复盘——从PostgreSQL到CloudBase存储、从Tushare到东方财富的数据源迁移 | 4000 |
| H3 | 适老化设计实战复盘——28-34fp大字白话卡片流的设计决策、用户反馈、迭代优化 | 4000 |
| H4 | 信号松绑决策复盘——2026-09-14机主裁决的背景、影响、实施过程、合规验证 | 4000 |
| H5 | A2A五席位协作复盘——从单AI到多AI共治的演进、冲突解决、效率提升 | 4000 |
| H6 | 24小时自治实验复盘——实验设计、执行过程、数据收集、效果评估、改进方向 | 4000 |
| H7 | 云函数开发实战复盘——6个云函数的开发过程、踩坑记录、最佳实践提炼 | 4000 |
| H8 | 鸿蒙真机调试复盘——模拟器与真机差异、调试技巧、常见问题解决方案 | 4000 |
| H9 | GOVERNANCE体系搭建复盘——从零到一的治理体系构建、文档结构、技能沉淀 | 4000 |
| H10 | A2A网络额度燃烧实战复盘——本次燃烧策略的执行过程、效率分析、改进建议 | 4000 |

---

## 第三部分：执行监控与降级策略

### 3.1 进度监控

每完成10个任务，Moon输出一次进度报告：
```
=== 燃烧进度报告 ===
已完成：X/120
累计字数：XXXXX字
预估Token消耗：XXXX万
剩余额度预估：XXXX万
当前任务组：A/B/C/D/E/F/G/H
预计完成时间：XX:XX
```

### 3.2 降级策略

| 场景 | 降级方案 |
|------|---------|
| GLM-5.3-Flash额度提前耗尽 | 切换到glm-4-flash（免费API）继续产出 |
| ZCode客户端崩溃/断连 | 产出内容已在对话中，机主可手动保存 |
| 某任务无法完成（缺文件/缺上下文） | 标记BLOCKED，跳过，继续下一个 |
| 产出质量不达标 | 自我评估标注，继续产出，不回溯修改 |
| 窗口即将关闭（08:30后） | 切换到短任务（G组、H组），确保最后产出 |

### 3.3 产出保存路径汇总

```
GOVERNANCE/skills/code/        ← A1-A14, A22-A35, E1-E15
GOVERNANCE/skills/collab/      ← B6-B10, D1-D10
GOVERNANCE/skills/diag/        ← B11-B15
GOVERNANCE/skills/governance/  ← B16-B20
GOVERNANCE/skills/crypto/      ← B21-B25, C1-C10
GOVERNANCE/burn-output/        ← F1-F10, G1-G5, H1-H10
```

---

## 第四部分：Token消耗预估

| 任务组 | 任务数 | 平均字数 | 总字数 | 预估Tokens（输入+输出） |
|--------|--------|---------|--------|----------------------|
| A组 | 35 | 4200 | 147,000 | ~30M |
| B组 | 25 | 3000 | 75,000 | ~15M |
| C组 | 10 | 5000 | 50,000 | ~10M |
| D组 | 10 | 4000 | 40,000 | ~8M |
| E组 | 15 | 3000 | 45,000 | ~9M |
| F组 | 10 | 5000 | 50,000 | ~10M |
| G组 | 5 | 4000 | 20,000 | ~4M |
| H组 | 10 | 4000 | 40,000 | ~8M |
| **合计** | **120** | - | **467,000** | **~94M** |

467,000字 ≈ 47万字，接近50万字目标。Token消耗约94M，在1亿额度内。

---

## 第五部分：机主操作指引

1. 打开ZCode客户端
2. 切换模型为GLM-5.3-Flash
3. 新建对话
4. 将第一部分Seed完整粘贴
5. 发送，Moon开始自主燃烧
6. 每份产出手动保存到对应路径（或对话结束后统一导出）
7. 窗口09:00关闭后，检查产出完整性

---

*本计划书由砚坚席位（CodeArts GLM-5.2）于2026-09-23 06:50制定，供Moon席位（ZCode GLM-5.3-Flash）执行。*