---
name: 业务术语表
description: 铃语、异动、适老化、信号卡/事实卡等业务概念
type: project-knowledge
category: business_term
---

# 业务术语表

## 核心业务概念

### 铃语
- 定义：适老化语音提醒应用，云端秒级监测→推送→点按播报
- 别名：StockPulse（bundleName: com.yehang.stockpulse）
- 典故：典出苏轼塔铃——"铃先响，风将至"

### 异动
- 定义：股票涨跌幅绝对值超过阈值（默认5%）的客观事件
- 别名：alert
- 判断标准：涨跌幅绝对值≥THRESHOLD，仅处理A股（sh/sz/bj开头）

### 适老化
- 定义：面向老年用户的大字大卡极简交互模式
- 别名：elderly mode
- 特征：28-40fp高对比深色底、大卡大间距、点卡即听、界面极简

### 事实卡（fact）
- 定义：客观异动事实卡片，包含涨跌幅/量能/价格穿越等客观数据
- 别名：kind=fact
- 约束：只报客观事实，不含买卖建议

### 信号卡（signal）
- 定义：自家策略信号与白话解读卡片，须带kind="signal"标记
- 别名：kind=signal
- 约束：禁止收益承诺/保本等绝对化措辞、禁止催促性强指令、禁止对外公开/收费
- 视觉区分：加"自家信号"金色角标

### 点卡即听
- 定义：适老化核心交互——点击异动卡片即播放云端TTS语音播报
- 别名：togglePlay

### 首屏永不空白
- 定义：服务未连通时必须显示带"示例"字样的演示卡（DEMO_ITEMS）
- 别名：demo mode

### 免打扰
- 定义：指定时段内自动播报静默，手动点击仍可播放
- 别名：DND (Do Not Disturb)
- 默认时段：22:00-8:00

### 自选股
- 定义：用户自定义关注的股票代码列表，非空时只显示列表中的异动
- 别名：watchlist

### X服务器
- 定义：铃语App的数据源服务器，产出AlertFeed JSON供App轮询消费
- 别名：feed-server（本地开发版）

### AlertFeed
- 定义：服务端产出的异动列表JSON契约，包含items数组与serverTs时间戳
- 别名：异动数据流

### Push Token
- 定义：华为Push Kit分配的设备唯一标识，用于服务端定向推送通知
- 别名：pushToken