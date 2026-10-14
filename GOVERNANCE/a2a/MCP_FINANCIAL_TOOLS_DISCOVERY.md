# MCP 金融数据工具发现报告

> 2026-09-24 砚坚（码道·鸿蒙开发智能体）自主运维期间探索

## 发现的工具

### 核心工具（与异动播报应用高度契合）

| 工具 | 功能 | 应用场景 |
|------|------|---------|
| `yfinance_screen_gappers` | 筛选开盘异动股票（涨跌幅≥3%） | **直接对应应用核心功能**——可替代或补充 tushare 数据源 |
| `yfinance_get_ticker_news` | 获取指定股票的最新新闻文章 | 为异动播报提供新闻背景，增强 `detail` 字段内容 |
| `yfinance_get_price_history` | 获取历史价格数据 | 可用于趋势分析、计算技术指标 |
| `yfinance_get_ticker_info` | 获取股票详细信息（公司、财务、交易指标） | 丰富异动卡片内容 |
| `yfinance_get_analyst_estimates` | 分析师预估（EPS/营收/推荐） | 量化研究团队数据源 |
| `yfinance_get_financials` | 财务报表（利润/资产负债/现金流） | 量化研究团队数据源 |

### 实测验证

**yfinance_screen_gappers**（2026-09-24 实时数据）：
- 参数：min_percent_change=3, min_price=5, min_volume=500000, min_market_cap=2B
- 返回6只异动股票：P(+19.3%)、SECZ(+7.5%)、FRVO(+7.9%)、NBIS(+3.9%)、GRAL(+4.6%)、KR(+3.2%)
- 每条数据包含：symbol, name, price, changePercent, volume, previousClose, fiftyTwoWeekRange, marketCap 等

**yfinance_get_ticker_news**（P/Everpure 实测）：
- 返回10条新闻文章，每条包含：title, summary, pubDate, provider, url, thumbnail
- 新闻来源：Barrons.com, MarketBeat, StockStory, Zacks, TheStreet 等
- 可直接用于异动播报的 `detail` 字段或 `signalNote` 字段

## 与现有架构的集成路径

### 路径A：feed-server 增强（推荐）
- 在 `feed-server/server.mjs` 中新增 yfinance 数据源
- `yfinance_screen_gappers` 作为异动检测的补充数据源
- `yfinance_get_ticker_news` 为每条异动附加新闻摘要
- 输出格式对齐 AlertFeed 契约（AlertItem.ets）

### 路径B：A2A 任务分发
- 通过 `a2a-task-dispatch` 云函数创建 yfinance 数据拉取任务
- PD-AI 量化研究团队（pd-quant-researcher-001）消费任务
- 结果回传至 feed-server 或直接推送至端侧

### 路径C：独立云函数
- 新建 `fetch-yfinance-data` 云函数
- 定时触发器拉取异动数据 + 新闻
- 与现有 `fetch-tushare-data` 互补

## 合规边界（W001）

- ✅ 允许：客观数据（价格、涨跌幅、成交量）、异动监测、新闻事实
- ❌ 禁止：投资建议、走势预测、买卖时机建议、分析师评级推送
- 注意：`yfinance_get_analyst_estimates` 返回的分析师评级属于第三方观点，**不可直接推送**，仅可作为量化研究团队的内部参考

## 注意事项

1. yfinance 数据为美股数据，当前应用主要面向 A 股（tushare 数据源）
2. yfinance 可作为补充数据源，特别是对关注美股的用户
3. 数据延迟约15秒（sourceInterval: 15），满足异动播报的实时性要求
4. MCP 工具在本地运行，不消耗 CloudBase 配额