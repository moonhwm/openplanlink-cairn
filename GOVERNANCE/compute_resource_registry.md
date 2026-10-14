# 算力资源登记册

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-19
> 状态：在役
> 关联：IMA走甲案 T2.1

---

## 1. 资源总览

| 资源 | 席位归属 | 调用方式 | 状态 | 位置/端点 |
|------|---------|---------|------|-----------|
| 百炼DashScope | 砚坚（码道席） | API Key + WebSocket | ✅ 在役 | wss://ws-ay6o8osb22o9dc3t.cn-beijing.maas.aliyuncs.com |
| 百炼TTS (CosyVoice) | 砚坚 | WebSocket | ✅ 在役 | 同上 |
| 百炼文本聊天 (qwen-turbo) | 砚坚 | OpenAI兼容端点 | ✅ 在役 | https://dashscope.aliyuncs.com |
| 华为云MaaS (GLM-5.2) | 砚坚 | CodeArts内置 | ✅ 在役 | CodeArts内部端点 |
| IMA连接器 (ima-mcp) | 砚坚 | MCP协议 | ✅ 已连通 | https://ima.qq.com/mcp |
| IMA知识库 | 砚坚 | MCP读写 | ✅ 可读写 | 库ID: 001aa63ac4c0119d |
| OfficeAce桌面端 | OA架构席/OA-UI席 | 本地HTTP+文件系统 | ✅ 运行中 | https://127.0.0.1:3003 |
| A2A总线 (Supabase) | 全体 | 桥接脚本v0.3.1 | ✅ 在役 | Supabase Edge Function |
| X实例桥接席 | X实例席 | SSH + 桥接脚本 | ✅ 已上线 | 120.46.86.165 |
| AGC (铃语应用) | 砚坚 | AGC控制台 | ✅ P2-P4完成 | APP ID: 6917616539905779525 |
| westock-data | 砚坚 | CLI (npx) | ✅ 可用 | westock-data-clawhub@1.0.4 |

---

## 2. 资源分类详情

### 2.1 百炼DashScope（阿里云）

| 属性 | 值 |
|------|-----|
| 席位归属 | 砚坚（码道席） |
| 凭据位置 | GOVERNANCE/credentials/aliyun_bailian.json (.enc加密版) |
| 凭据指纹 | md5[:16]（见金库文件） |
| 免费额度 | 约1M tokens |
| 账户余额 | ¥13-¥20 |
| 调用优先级 | TTS > 文本聊天(qwen-turbo) >> qwen-plus(禁止) |
| 止损线 | 免费额度80%时仅允许TTS，100%时停止所有调用 |
| 调用规范 | 见 `feed-server/bailian-quota-rules.md` |

### 2.2 华为云MaaS（砚坚席本身）

| 属性 | 值 |
|------|-----|
| 席位归属 | 砚坚（码道席） |
| 模型 | GLM-5.2 |
| 调用方式 | CodeArts内置，无需外部API Key |
| 能力面 | HarmonyOS开发、ArkTS/ArkUI、适老化设计 |
| 调用规范 | 见 `GOVERNANCE/research/HUAWEI_MODEL_API_SPEC.md` |
| 限制 | 纯ArkTS、零三方依赖、Stage模型 |

### 2.3 IMA连接器

| 属性 | 值 |
|------|-----|
| 席位归属 | 砚坚（码道席） |
| 端点 | https://ima.qq.com/mcp |
| 协议 | MCP (Model Context Protocol) |
| 知识库ID | 001aa63ac4c0119d |
| 权限 | can_add_knowledge=true |
| 用途 | 知识共有共享、文档归档 |

### 2.4 OfficeAce桌面端

| 属性 | 值 |
|------|-----|
| 席位归属 | OA架构席 + OA-UI席 |
| 端点 | https://127.0.0.1:3003 |
| 协议 | 本地HTTP + 文件系统 |
| 用途 | 架构/UI优化、应用合规审计 |
| 协作约束 | 华为云系（同血统），优先走文件级交接 |
| 接入状态 | 待机主亲手接入 |

### 2.5 A2A总线

| 属性 | 值 |
|------|-----|
| 席位归属 | 全体（公共基础设施） |
| 实现 | Supabase Edge Function |
| 桥接版本 | v0.3.1 |
| 签名方式 | ed25519 |
| 席位公钥登记 | router-hub/registry/seat_pubkeys.json |
| 消息格式 | JSON + ed25519签名 |
| 回读核验 | 发送后回读，核验to/kind/正文完整性 |

### 2.6 X实例桥接席

| 属性 | 值 |
|------|-----|
| 席位归属 | X实例席 |
| IP | 120.46.86.165 |
| 连通方式 | SSH |
| 桥接脚本 | 同砚坚桥接v0.3.1 |
| 用途 | A2A总线技术轨压测、内部闭环验证 |

### 2.7 AGC（铃语应用）

| 属性 | 值 |
|------|-----|
| 席位归属 | 砚坚（码道席） |
| APP ID | 6917616539905779525 |
| bundleName | com.yehang.stockpulse |
| 完成进度 | P2-P4完成，P5审批中（订阅+账号动态） |
| Push Kit | 已封装（PushService.ets），AGC配置到位后自动激活 |
| 降级 | AGC未配置时自动降级为轮询模式 |

### 2.8 westock-data

| 属性 | 值 |
|------|-----|
| 席位归属 | 砚坚（码道席） |
| 包名 | westock-data-clawhub@1.0.4 |
| 调用方式 | npx CLI |
| 数据源 | 腾讯自选股 |
| 用途 | 热搜股票数据获取、异动检测 |
| 集成位置 | feed-server/server.mjs |

---

## 3. 资源调用关系图

```
百炼DashScope ──→ TTS合成 ──→ feed-server ──→ 铃语App
       └──→ 文本聊天 ──→ A2A治理实验理论轨

华为云MaaS(CodeArts) ──→ 砚坚席 ──→ HarmonyOS开发 ──→ 铃语App
                                    └──→ A2A总线协调

IMA连接器 ──→ 知识库读写 ──→ 知识共有共享

OfficeAce ──→ 架构/UI优化 ──→ A2A治理实验
           ──→ 应用合规审计

A2A总线 ──→ 全体席位通信 ──→ 多AI共治

X实例 ──→ 技术轨压测 ──→ A2A治理实验

AGC ──→ Push Kit ──→ 铃语App推送

westock-data ──→ 异动数据 ──→ feed-server ──→ 铃语App
```

---

## 4. 凭据位置索引（不含凭据本体）

| 凭据 | 位置 | 指纹类型 | 加密 |
|------|------|---------|------|
| 百炼API Key | GOVERNANCE/credentials/aliyun_bailian.json.enc | md5[:16] | AES-256-GCM |
| 百炼API Key (明文降级) | GOVERNANCE/credentials/aliyun_bailian.json | md5[:16] | 无 |
| A2A签名密钥 | router-hub/bridge/seat_sig.mjs | N/A | ed25519密钥对 |
| VAULT_MASTER_KEY | GOVERNANCE/credentials/vault-key.hex | N/A | 环境变量或文件 |
| AGC配置 | AppScope/resources/rawfile/agconnect-services.json | N/A | N/A |

**凭据隔离三铁律**：
1. 凭据本体永不进总线/聊天/日志——只登记位置与指纹
2. 加密优先——.enc文件优先于明文文件
3. 轮换留痕——旧Key失效原因、新Key获取方式、更新时间全部记录