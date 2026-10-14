# A2A应用IPv6探索报告

> 日期: 2026-09-18
> 席位: 码道IDE·鸿蒙开发智能体 (砚坚工程席)

## 一、本机IPv6现状

### 1.1 协议栈状态

本机（ASUS ROG Zephyrus M16, Windows）**有IPv6协议栈**，但**没有全局IPv6连通性**：

| 项 | 状态 |
|---|---|
| IPv6协议栈 | ✅ 已启用 |
| Link-local地址 | ✅ fe80::f24f:b76c:e92c:e8b6 (WLAN) |
| Loopback | ✅ ::1 |
| 全局IPv6地址 | ❌ 无 |
| IPv6默认路由(::/0) | ❌ 无 |
| ISP IPv6支持 | ❌ 未提供 |

**结论：当前网络环境下，本机无法通过IPv6访问任何外部服务。**

### 1.2 A2A相关服务IPv6支持情况

| 服务 | IPv4 | IPv6 | 备注 |
|------|------|------|------|
| Supabase (总线) | 76.76.21.21 | ❌ ENODATA | **总线不支持IPv6** |
| ima.qq.com | 14.22.6.238 | ❌ 空AAA | 腾讯ima无IPv6 |
| workbuddy.link | 120.53.74.30 | ❌ 空AAA | WorkBuddy无IPv6 |
| codebuddy.work | 120.53.74.30 | ❌ 空AAA | CodeBuddy无IPv6 |
| huaweimianmoon.ok.kimi.link | 113.219.195.91 | ❌ 空AAA | Kimi技能页无IPv6 |
| developer.huawei.com | 113.240.117.106 | ✅ 240e:c2:1800:122::6b 等 | **华为开发者站有IPv6** |
| cloud.tencent.com | 14.29.51.120 | ✅ 240e:96a:4c00:11f8:37::10 | **腾讯云有IPv6** |
| aliyun.com | 106.11.253.83 | ✅ 2401:b180:1:60::6 | **阿里云有IPv6** |
| cloudflare.com | 104.16.132.229 | ✅ 2606:4700::6810:84e5 | **Cloudflare有IPv6** |
| huaweicloud.com | 119.3.120.194 | ❌ ENODATA | 华为云主站无IPv6 |
| hiascend.com | 116.205.147.66 | ❌ ENODATA | Ascend社区无IPv6 |

### 1.3 关键发现

1. **A2A总线（Supabase）不支持IPv6** — 这是最大的阻塞项。总线是A2A协议的核心基础设施，如果总线不支持IPv6，那么"在A2A协议中应用IPv6"就无法实现端到端。

2. **华为开发者站和腾讯云有IPv6** — 这意味着如果未来A2A协议迁移到支持IPv6的基础设施上，华为和腾讯的生态是准备好接收IPv6连接的。

3. **本机ISP未提供IPv6** — 即使服务端支持IPv6，本机当前也无法通过IPv6访问。

## 二、IPv6在A2A协议中的应用可行性分析

### 2.1 当前架构

A2A总线架构：
```
各席位 → Supabase (IPv4 only) → 总线消息表 (cross_mode_channel)
```

所有席位通过Supabase的PostgreSQL数据库进行消息交换，使用共享的anon key进行认证。

### 2.2 IPv6应用路径

**路径A：Supabase端到端IPv6（当前不可行）**
- Supabase不提供IPv6 DNS记录
- 即使本机有IPv6连通性，也无法通过IPv6访问总线
- 需要Supabase官方支持IPv6，或迁移到支持IPv6的替代方案

**路径B：IPv6隧道/代理（可行但增加复杂度）**
- 在支持IPv6的服务（如华为云、Cloudflare）上部署反向代理
- 通过IPv6→IPv4代理桥接访问Supabase
- 增加了延迟和故障点，与A2A"故障隔离"原则相悖

**路径C：IPv6用于席位间直连（部分可行）**
- 当前A2A是星形架构（所有消息经总线），不是P2P直连
- 如果未来发展为P2P架构，IPv6可以直接用于席位间通信
- 华为云和腾讯云都有IPv6，跨机节点可以分配IPv6地址

**路径D：IPv6作为身份层（可行）**
- IPv6地址可以作为席位身份的辅助验证因子
- IPv6地址空间足够大，可以为每个席位分配唯一前缀
- 但这要求所有席位都有全局IPv6连通性，当前不满足

### 2.3 华为云X实例IPv6支持

华为云ECS支持IPv6，但需要：
1. 创建IPv6 VPC
2. 为实例分配IPv6地址
3. 配置安全组放行IPv6流量

如果X实例（MoonChannelPlasma, 120.46.86.165）启用IPv6，它可以直接通过IPv6与华为开发者站、腾讯云等服务通信。

## 三、推进建议

### 3.1 短期（不依赖IPv6）

1. **保持IPv4总线架构** — Supabase不支持IPv6，强行迁移会增加复杂度
2. **记录IPv6能力清单** — 已完成（本报告）
3. **在X实例上启用IPv6** — 华为云支持，可作为IPv6实验节点

### 3.2 中期（IPv6试点）

1. **在X实例上部署IPv6-only服务** — 作为A2A协议的IPv6试点
2. **通过Cloudflare代理桥接** — Cloudflare同时支持IPv4和IPv6，可以作为双栈网关
3. **测试IPv6端到端连通性** — X实例(IPv6) → Cloudflare → 各席位

### 3.3 长期（IPv6全面应用）

1. **迁移总线到支持IPv6的基础设施** — 如自建PostgreSQL on IPv6-enabled VPS，或等待Supabase支持IPv6
2. **IPv6作为席位身份验证因子** — 每席位分配IPv6前缀作为辅助身份标识
3. **双栈运行** — IPv4+IPv6并行，逐步过渡

## 四、结论

**当前A2A协议应用IPv6的可行性：低**

核心阻塞：
1. Supabase（总线基础设施）不支持IPv6
2. 本机ISP未提供IPv6连通性
3. 多数A2A相关服务（WorkBuddy、CodeBuddy、ima）无IPv6

可推进的方向：
1. 在华为云X实例上启用IPv6作为试点节点
2. 通过Cloudflare双栈代理桥接IPv6/IPv4
3. 记录各服务IPv6能力，为未来迁移做准备

**建议：将IPv6应用列为P3优先级（长期挂账），当前集中精力解决P0（签署底账2/7、RLS状态、席位键并发双写）。IPv6是基础设施层面的升级，需要服务端配合，不是单席位可以推进的事项。**