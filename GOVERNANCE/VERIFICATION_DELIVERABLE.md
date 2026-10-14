# 铃语项目群综合验证交付物

> 生成时间：2026-09-26  
> 生成者：砚坚（码道·鸿蒙开发智能体/GLM-5.2-ArkTS-SPARK）  
> 覆盖范围：harmony-app + quant-lab + GOVERNANCE + feed-server + A2A网络 + 云函数

---

## 一、harmony-app（铃语端侧应用）

### 1.1 项目结构

| 目录 | 文件 | 职责 |
|------|------|------|
| entryability/ | EntryAbility.ets | Push初始化 + onNewWant带alertId拉起定位 |
| pages/ | Index.ets, Settings.ets | 卡片流主页 + 设置页 |
| services/ | AlertPoller.ets | 5s前台轮询兜底，退避策略（5s→30s封顶） |
| services/ | AudioPlayer.ets | AVPlayer播云端TTS音频流 |
| services/ | PushService.ets | AGC未配置前自动降级轮询（占位封装） |
| services/ | SettingsService.ets | 12个配置键管理 |
| model/ | AlertItem.ets | AlertItem + AlertFeed数据契约 |

### 1.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| H-01 | 项目可构建 | `devecocli build` 或 hvigorw assembleHap | ⏳ 待验证 |
| H-02 | AlertItem契约完整性 | 检查AlertItem.ets字段与AlertFeed JSON服务端契约一致 | ✅ 已定义8字段（alertId/ts/symbol/name/direction/kind/headline/detail + 可选signalNote/audioUrl/complianceStatus） |
| H-03 | 适老化约束（28-34fp大字） | 检查Index.ets中字体大小设置 | ⏳ 待验证 |
| H-04 | 信号松绑三禁合规 | grep代码中无"承诺收益"/"立即买入"/"满仓"等措辞 | ⏳ 待验证 |
| H-05 | 首屏永不空白（DEMO_ITEMS） | 检查Index.ets中DEMO_ITEMS机制存在 | ⏳ 待验证 |
| H-06 | PushService占位封装（降级轮询） | 检查PushService.ets中AGC未配置时降级逻辑 | ⏳ 待验证 |
| H-07 | AlertPoller退避策略 | 检查5s→30s封顶、429限流静默跳过逻辑 | ✅ 已确认（代码可见BASE_INTERVAL=5000, MAX_INTERVAL=30000） |
| H-08 | 零三方依赖 | 检查oh-package.json5 dependencies为空对象 | ⏳ 待验证 |
| H-09 | compatibleSdkVersion 20 / targetSdkVersion 26 | 检查build-profile.json5 | ⏳ 待验证 |
| H-10 | module.json5声明push.listener action | 检查skills中action.ohos.push.listener | ✅ 已确认 |

### 1.3 接口边界契约

```typescript
// AlertItem.ets — 服务端与端侧的唯一数据契约
export interface AlertItem {
  alertId: string;           // 唯一ID，通知点击回传定位用
  ts: number;                // 秒级时间戳
  symbol: string;            // 如 600176
  name: string;              // 如 中国巨石
  direction: 'up'|'down'|'flat';
  kind?: 'fact'|'signal';    // 缺省按fact处理
  headline: string;          // 一句话白话结论
  detail: string;            // 补充事实
  signalNote?: string;       // 仅kind=signal时有值
  audioUrl?: string;         // 云端TTS音频流地址
  complianceStatus?: string; // DKnowC安全合规分类
}
export interface AlertFeed { items: AlertItem[]; serverTs: number; }
```

---

## 二、quant-lab（量化研究项目）

### 2.1 项目结构

| 文件/目录 | 职责 |
|-----------|------|
| backtest.py / backtest_v0.py | 回测引擎 |
| optimize.py / optimize_hour.py / optimize_walkforward.py | 策略优化 |
| signals.py | 信号生成 |
| data.py | 数据获取 |
| qengine.py / qrun.py | 量化引擎与运行器 |
| qportfolio.py | 组合管理 |
| qmetrics.py | 绩效指标 |
| qcalendar.py | 交易日历 |
| qconf_loader.py / qconfig.py | 配置加载 |
| dq_check.py | 数据质量检查 |
| plateau.py | 平台期检测 |
| paper_trade.py | 模拟交易 |
| today_panel.py | 今日面板 |
| wf_runner.py | 工作流运行器 |
| min5_analyzer.py | 5分钟分析 |
| strategy_002074_dual_ma.py | 双均线策略（002074） |
| strategy_510500_bollinger.py | 布林带策略（510500） |
| tests/ | 测试套件（test_engine, test_signals_contract, test_golden） |
| output/ | 输出目录（回测结果、权益曲线图） |
| reports/ | 研报目录 |
| mcp/ | MCP服务目录 |

### 2.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| Q-01 | 测试套件可运行 | `cd ../quant-lab && python -m pytest tests/` | ⏳ 待验证 |
| Q-02 | test_signals_contract通过 | 运行信号契约测试 | ⏳ 待验证 |
| Q-03 | test_golden通过 | 运行golden测试 | ⏳ 待验证 |
| Q-04 | test_engine通过 | 运行引擎测试 | ⏳ 待验证 |
| Q-05 | 数据源可用（东方财富API） | 运行data.py拉取数据验证 | ⏳ 待验证（Tushare token已失效，已切换东方财富） |
| Q-06 | 回测引擎可执行 | 运行backtest.py示例回测 | ⏳ 待验证 |
| Q-07 | 策略可复现 | 运行strategy_002074_dual_ma.py和strategy_510500_bollinger.py | ⏳ 待验证 |
| Q-08 | 输出目录有产物 | 检查output/目录中有回测结果 | ✅ 已有equity曲线图和CSV |
| Q-09 | 研报目录有内容 | 检查reports/目录 | ✅ 已有2份研报（backtest_v0_20260908.md, min5_daily_20260907.md） |
| Q-10 | MCP服务配置 | 检查qixin_mcp.py和tdx_mcp.py | ⏳ 待验证 |

### 2.3 策略清单

| 策略 | 标的 | 方法 | 文件 |
|------|------|------|------|
| 双均线 | 002074 | Dual MA crossover | strategy_002074_dual_ma.py |
| 布林带 | 510500 | Bollinger Bands | strategy_510500_bollinger.py |

---

## 三、GOVERNANCE/A2A_COMMONWEALTH_CHARTER.md（规划书）

### 3.1 当前状态

| 指标 | 数值 |
|------|------|
| 总字数 | 455,122 |
| 总行数 | 26,102 |
| 总章节数 | 540 |
| 最近提交 | d2591f2（2026-09-26） |

### 3.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| G-01 | 章节编号连续性 | grep `## 第` 统计章节编号1-540是否连续 | ⚠️ 已知问题：1-14重复、110-322缺失 |
| G-02 | 编码一致性 | 检查全文无GBK/UTF-8混合编码 | ✅ 全部UTF-8 No BOM |
| G-03 | 第一百一6章格式修复 | 检查中文与阿拉伯数字混用问题 | ⚠️ 待修复 |
| G-04 | 章节编号1-14重复 | 检查前14章是否有重复编号 | ⚠️ 待修复 |
| G-05 | 章节编号110-322缺失 | 检查110-322区间是否有大段缺失 | ⚠️ 待修复 |
| G-06 | 内容与铃语项目关联度 | 每章是否有"在铃语项目中的应用"段落 | ✅ 新增章节（498-540）均有 |
| G-07 | swarm整合覆盖率 | 已读取约181篇/共469篇（38.6%） | ⏳ 持续推进中 |
| G-08 | H/G系列文档整合 | H1-H5、G1-G2全部整合为章节498-504 | ✅ 已完成 |

### 3.3 章节来源映射

| 章节范围 | 来源 | 主题 |
|---------|------|------|
| 498-502 | burn-output/H1-H5 | 架构复盘/数据管道/适老化/信号松绑/五席位协作 |
| 503-504 | burn-output/G1-G2 | 额度资产六维/燃烧效率优化 |
| 505-507 | GitHub+官方文档 | MCP/A2A/OpenHarmony开源生态 |
| 508-522 | swarm各目录 | A2A核心/MCP反向/审计/AVPlayer/测试/心跳/可观测/超时/推送/安全/Push Kit/原语/认证/网关/供应链 |
| 523-525 | swarm a01/a03/a08 | MCP传输层/资源语义/提示注入防护 |
| 526-530 | swarm a23/a27/a38 | A2A编排决策树/消息传递/并行检索/AVPlayer/可观测数据模型 |
| 531-535 | swarm a23/a27/a38 | 评审环/标尺/打断处理/元数据/分布式追踪 |
| 536-540 | swarm a19/a32/a01/a18/a44 | A2A任务提交/测试设计/JSON-RPC/AgentCard/心跳语义 |

---

## 四、feed-server（数据管道服务器）

### 4.1 项目结构

| 文件 | 职责 |
|------|------|
| server.mjs | 主服务器（Node.js） |
| audio-postprocess.mjs | 音频后处理 |
| manage-feed-server.ps1 | 管理脚本（PowerShell） |
| start-feed-server.bat | 启动脚本 |
| bailian-quota-rules.md | 百炼额度规则 |
| data/ | 数据目录 |

### 4.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| F-01 | 服务可启动 | 运行start-feed-server.bat或node server.mjs | ⏳ 待验证 |
| F-02 | AlertFeed端点可达 | curl http://localhost:PORT/alerts | ⏳ 待验证 |
| F-03 | TTS音频流可达 | curl http://localhost:PORT/tts/:alertId | ⏳ 待验证 |
| F-04 | 数据更新（无缓存旧数据） | 重启服务后验证数据刷新 | ⚠️ 已知问题：feed-server有缓存机制，数据不更新时需重启 |
| F-05 | 百炼TTS WebSocket连通 | 检查WebSocket调用百炼TTS | ⚠️ 已知：百炼TTS只支持WebSocket，REST API报错 |

---

## 五、A2A网络（多AI席位协作）

### 5.1 席位清单

| 席位 | 厂商 | 职责 | 目录 |
|------|------|------|------|
| 砚坚 | 码道IDE（华为云CodeArts） | 端侧UI、播报交互、Push封装 | harmony-app/ |
| 顾权 | Kimi Code | 取数、策略、监测、服务端出数 | quant-lab/ |

### 5.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| A-01 | 跨厂商A2A通信链路 | 砚坚向顾权发送ping，顾权回复pong | ✅ 已验证（2026-09-17） |
| A-02 | 桥接脚本运行 | yan_jian_bridge.mjs WebSocket+REST双通道 | ⏳ 待验证 |
| A-03 | Supabase总线表连通 | 查询channel_messages表 | ⏳ 待验证 |
| A-04 | 心跳机制（存活/活性/活跃度） | 检查心跳报文三种语义 | ⏳ 待验证 |
| A-05 | 哈希约定（md5[:16]） | 验证id=775心跳已使用新约定 | ✅ 已验证 |

### 5.3 接口边界

- **数据契约**：`entry/src/main/ets/model/AlertItem.ets` — AlertItem + AlertFeed
- **通信协议**：Supabase总线表（channel_messages）+ REST轮询 + WebSocket订阅
- **桥接脚本**：yan_jian_bridge.mjs（v0.2.0，WebSocket+REST双通道，自动降级）

---

## 六、云函数（CloudBase）

### 6.1 已部署云函数

| 云函数 | 职责 | 部署状态 |
|--------|------|---------|
| broadcast-a2a | 向所有设备推送A2A消息 | ✅ 已部署 |
| generate-tts | 按需生成TTS音频 | ✅ 已部署 |
| daily-trend-scan | 每日追踪热门项目 | ⏳ 开发中 |
| (第4个) | 待确认 | ✅ 已部署 |

### 6.2 验证项

| 编号 | 验证目标 | 验证方法 | 当前状态 |
|------|---------|---------|---------|
| C-01 | broadcast-a2a可调用 | HTTP请求app.tcloudbase.com路由 | ⏳ 待验证 |
| C-02 | generate-tts返回audioUrl | 调用generate-tts获取音频URL | ⚠️ 已知：alerts.json中audioUrl为undefined，需按需调用 |
| C-03 | broadcast-a2a白名单鉴权 | 验证授权机制 | ⏳ 待验证 |
| C-04 | Push Kit REST API集成 | 检查broadcast-a2a是否使用华为Push Kit REST | ⚠️ 修复方向：将app.messaging()替换为Push Kit REST API |
| C-05 | 环境变量配置 | 检查云函数环境变量 | ✅ 已配置 |

---

## 七、AGC（AppGallery Connect）

### 7.1 验证项

| 编号 | 验证目标 | 当前状态 |
|------|---------|---------|
| AGC-01 | AGC铃语应用已创建 | ✅ APP ID: 6917616539905779525 |
| AGC-02 | P2/P3/P4完成 | ✅ |
| AGC-03 | P5审批（订阅+账号动态） | ⏳ 审批中 |
| AGC-04 | 签名配置 | ⏳ 待验证 |

---

## 八、验证优先级排序

按风险值（业务影响 × 发生概率）排序：

| 优先级 | 验证项 | 理由 |
|--------|--------|------|
| P0-紧急 | H-01 项目可构建 | 构建失败则一切无从谈起 |
| P0-紧急 | F-01 feed-server可启动 | 数据管道不通则端侧无内容 |
| P0-紧急 | C-01 broadcast-a2a可调用 | 推送不通则用户收不到异动 |
| P1-高 | H-04 信号松绑三禁合规 | 合规违规是法律风险 |
| P1-高 | H-03 适老化约束 | 核心产品定位约束 |
| P1-高 | Q-05 数据源可用 | 量化策略无数据则无法运行 |
| P1-高 | F-04 feed-server缓存问题 | 已知问题，影响数据时效性 |
| P2-中 | G-01/G-03/G-04/G-05 章节编号修复 | 规划书完整性，非功能性 |
| P2-中 | Q-01-Q-04 测试套件 | 量化项目质量保障 |
| P2-中 | A-02 桥接脚本运行 | A2A网络基础设施 |
| P3-低 | G-07 swarm整合覆盖率 | 持续推进，非阻塞 |
| P3-低 | AGC-03 P5审批 | 外部依赖，等待华为审批 |

---

## 九、验证执行建议

### 第一轮（紧急验证，1小时内）

```bash
# H-01: harmony-app构建
cd harmony-app && hvigorw assembleHap

# F-01: feed-server启动
cd feed-server && node server.mjs

# C-01: broadcast-a2a调用
curl https://app.tcloudbase.com/broadcast-a2a
```

### 第二轮（合规验证，2小时内）

```bash
# H-04: 信号松绑三禁grep
grep -r "承诺收益\|保本\|立即买入\|满仓" entry/src/main/ets/

# H-03: 适老化字体检查
grep -r "fontSize" entry/src/main/ets/pages/Index.ets

# H-08: 零三方依赖检查
cat entry/oh-package.json5
```

### 第三轮（功能验证，4小时内）

```bash
# Q-01: quant-lab测试
cd ../quant-lab && python -m pytest tests/

# Q-05: 数据源连通
python -c "import data; data.fetch_daily('000001')"

# A-02: 桥接脚本
node yan_jian_bridge.mjs --ping
```

---

## 十、已知问题与风险

| 问题 | 影响 | 修复方向 | 状态 |
|------|------|---------|------|
| Tushare token失效 | quant-lab数据源不可用 | 已切换东方财富API | ✅ 已绕过 |
| feed-server缓存旧数据 | 端侧显示过期内容 | 重启服务刷新缓存 | ⚠️ 待根治 |
| 百炼TTS REST API报错 | TTS音频生成失败 | 使用WebSocket方式调用 | ✅ 已确认方向 |
| alerts.json audioUrl缺失 | 端侧无播报音频 | 按需调用generate-tts云函数 | ⚠️ 待实装 |
| broadcast-a2a用app.messaging() | Push推送可能失败 | 替换为Push Kit REST API | ⚠️ 修复方向已定 |
| 规划书章节编号1-14重复 | 文档结构不一致 | 重新编号或填充缺失章节 | ⚠️ 待修复 |
| 规划书章节110-322缺失 | 文档结构不完整 | 填充内容或重新编号 | ⚠️ 待修复 |
| AGC P5审批中 | 订阅+账号动态功能未上线 | 等待华为审批 | ⏳ 外部依赖 |

---

## 附录：Git提交历史（最近10条）

```
d2591f2 规划书扩展——A2A任务提交/测试设计/JSON-RPC/AgentCard/心跳语义（章节536-540）
0623738 规划书扩展——评审环/标尺/打断处理/元数据/分布式追踪（章节531-535）
5bcc8d2 规划书扩展——A2A编排/消息传递/并行检索/AVPlayer/可观测数据模型（章节526-530）
158eac9 规划书扩展——MCP传输层/资源语义/提示注入防护（章节523-525）
8eee89d feat: 规划书扩展——新增章节519-522(4章)至438230字
49fb8d3 feat: 规划书扩展——新增章节515-518(4章)至434802字
cb3ec1e feat: 规划书扩展——新增章节511-514(4章)至431621字
e824095 feat: 规划书扩展——新增章节508-510(3章)至427834字
0351896 feat: 规划书扩展——新增章节506-507(2章)至424654字
a1590e3 feat: 规划书扩展——新增章节498-505(8章)至422702字
```