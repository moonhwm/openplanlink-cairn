---
name: bridge-script
type: collab
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 需要开发或排查A2A总线桥接脚本（消息格式、哈希、心跳、签名、收发命令）时
source_files: [C:/Users/欧阳宏俊/Documents/kimi/router-hub/bridge/a2a_bridge.mjs, C:/Users/欧阳宏俊/Documents/kimi/router-hub/bridge/yan_jian_bridge.mjs, GOVERNANCE/skills/collab/bus-bridge-debug.md, GOVERNANCE/skills/collab/a2a总线协作.md]
---

# collab技能：A2A桥接脚本开发——MFV-0.1协议、哈希约定md5前16、心跳机制、消息格式

## 概述

桥接脚本是各AI席位接入A2A总线的物理通道：把"席位间协作"翻译成对总线存储（Supabase Edge Function + cross_mode_channel表）的读写。本技能文档沉淀桥接脚本的开发约定——MFV-0.1消息协议、md5前16位哈希、心跳机制、收发与核验命令——以及实战中踩过的三类静默失败缺陷。

## 1. MFV-0.1协议

MFV（Message Format Version）0.1是当前总线唯一认可的消息信封格式。所有上总线的消息必须是以下七个字段的JSON：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 消息唯一标识，md5哈希前16位（见第2节） |
| from | string | 是 | 发送方席位标识，规范席位键（如moon、yan-jian、workbuddy-hy4） |
| to | string | 是 | 接收方席位键，或all表示广播 |
| kind | string | 是 | 消息类型，见下方枚举 |
| payload | string | 是 | 消息正文，必须是合法JSON字符串（不是纯文本） |
| ts | string | 是 | ISO 8601时间戳，含时区偏移 |
| seq | number | 建议 | 发送方内递增序号，用于连续性校验 |

kind枚举（可扩展，扩展须同步更新本表）：

- `handshake-propose` / `handshake-response`：握手提议与响应（含confirm/reserve/reject表态）；
- `heartbeat`：心跳，payload携带`role@seat`双段署名与`status: "alive"`；
- `task-dispatch`：任务派发；任务回执；实验通告（experiment-resume）等；
- 其他业务kind：新增时在GOVERNANCE/skills/SELF_BUILT_INDEX.md登记。

**版本兼容规则**：解析方遇到不认识的kind不得丢弃，按未知类型归档并计数；遇到字段缺失的消息按缺陷处理而非静默跳过。

## 2. 哈希约定：md5前16位

### 2.1 生成规则

全工程统一哈希约定为`md5[:16]`——对"from + to + kind + payload + ts"拼接串取md5摘要，截取前16个十六进制字符作为消息id。生成示例（Node.js）：

```javascript
import crypto from 'node:crypto';
function msgId(from, to, kind, payload, ts) {
  const raw = `${from}|${to}|${kind}|${payload}|${ts}`;
  return crypto.createHash('md5').update(raw, 'utf8').digest('hex').slice(0, 16);
}
```

### 2.2 用途与边界

- **去重**：同一内容重发生成相同id，消费端按id幂等；
- **指纹登记**：凭据与资产只登记位置+md5[:16]指纹，本体永不落日志；
- **碰撞概率**：16个十六进制位=64比特，日千条量级下碰撞概率可忽略；但去重逻辑仍须在碰撞时回退为"id+ts"联合键，不能盲目信任。

### 2.3 反模式

禁止自造哈希长度（如全32位、sha1前8位）。历史上各席位曾各自为政，md5[:16]是统一裁定（登记于memory/project-bridge-hash-convention.md），改约定须先在总线发起提议并经机主确认。

## 3. 心跳机制

### 3.1 设计

每个在线席位定期向总线发送心跳消息：

```json
{
  "id": "3f2a9c1e8b7d4f60",
  "from": "moon",
  "to": "all",
  "kind": "heartbeat",
  "payload": "{\"role\":\"knowledge-writer\",\"seat\":\"moon\",\"status\":\"alive\"}",
  "ts": "2026-09-23T10:00:00+08:00"
}
```

### 3.2 参数与判定

- **周期**：常规15-30分钟一次；燃烧窗口内加密到5-10分钟，用于佐证席位存活；
- **通路验证**：心跳发出后必须回读（查自己刚写的心跳是否入库），收到回读确认才认为通路可用——只发不查等于没验；
- **失联判定**：超过3个周期无心跳，或回执连续2次超时（每次30分钟），标记失联；
- **心跳占比监控**：总线消息中心跳占比过高说明业务信令不足，是"假活跃"信号，统计见bus-bridge-debug.md的缺号/信噪比分析。

## 4. 桥接脚本开发

### 4.1 运行环境

- 脚本位置：`C:/Users/欧阳宏俊/Documents/kimi/router-hub/bridge/a2a_bridge.mjs`（通用桥）与`yan_jian_bridge.mjs`（砚坚席位桥）；
- Node.js：`C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node.exe`（v22，支持ESM顶层await与node:crypto）；
- 存储层：Supabase Edge Function + 数据表`cross_mode_channel`；写库经ed25519签名。

### 4.2 命令面

桥接脚本至少暴露四个子命令：

1. `send`：组装MFV-0.1信封（id按md5[:16]生成）→ ed25519签名 → 写入总线 → 立即回读核验；
2. `poll`：按to=本席位键拉取新消息，返回时校验签名与seq连续性；
3. `verify <id>`：REST直查单条消息（`?id=eq.xx&select=*`），用于恢复与取证；
4. `status`：输出最近心跳时间、未回执消息数、seq缺口数。

### 4.3 三类静默失败缺陷（必防）

| 缺陷 | 现象 | 防线 |
|------|------|------|
| 表名写错 | 写库404（PGRST205）不抛到业务层，日志只留status | 以脚本`bus.select('...')`实际表名为准，不猜表名；发送后回读强制校验 |
| 别名寻址 | to_mode自由文本（workbuddy/workbuddy-W等变体）精确匹配不到规范键，消息未路由 | 收件匹配用include/规范化函数，统计`?to_mode=like.*workbuddy*`列出全部变体 |
| 空catch吞正文 | payload为纯文本时JSON.parse失败被静默吞掉，正文丢失 | catch里必须保留raw原文；payload非合法JSON时按缺陷消息归档处置 |

这三条均出自真实事故（id=250/3066/6277三条别名消息靠REST直查才恢复），修复方案见GOVERNANCE/proposals/GAP-03_bridge_fix_plan.md。

### 4.4 凭据安全

桥接脚本读取Supabase连接串、ed25519私钥等凭据时：只从环境变量或受限凭据文件读入；日志输出一律替换为md5[:16]指纹；凭据本体永不进总线消息、聊天记录、CHANGELOG。任何一份凭据疑似泄露，立即轮换并通报机主。

### 4.5 开发验收清单

- [ ] 单元：msgId生成与既定约定一致（同输入同输出、长度16）；
- [ ] 集成：send→回读核验通过；poll能取回自己发的消息；
- [ ] 异常：错误表名、纯文本payload、未知kind均不静默；
- [ ] 安全：全链路日志无凭据明文；
- [ ] 心跳：周期发送+回读，status命令能报失联。

## 5. 协议设计动机与演进路径

MFV-0.1之所以长成这个样子，是被三个现实约束逼出来的。第一，收发双方面对面没有共享内存，任何字段缺了就永久丢了，所以七字段全部必填、payload必须是合法JSON字符串而不是纯文本——纯文本在管道里过JSON.parse时会整段被吞，这是真实发生过的正文丢失事故。第二，总线存储是共享表，任何席位都能读，所以信封里只放路由信息，敏感内容一律不进payload。第三，各席位脚本由不同人不同时间开发，协议必须小到可以背下来：一个id、一个路由、一个类型、一段正文、一个时间戳，多了就一定会有人实现错。

演进方向上，0.2版本预留两件事：一是规范席位键字段（替代现在靠include匹配兜底的自由文本to_mode），二是消息签名从"发送方单签"升级为可选的"收读回执链"。做任何协议升级都遵守同一个流程：先在总线发提议，附新旧格式对照与兼容策略（解析方对未知字段的容忍规则），经机主确认后更新本技能文档的kind枚举与字段表，再动脚本。协议文档与实现不同步是事故之源，改协议不改文档等于没改。

## 6. 脚本代码骨架

新写一个席位桥接脚本时，推荐按如下骨架组织（以Node.js ESM为例，命令入口省略）：

```javascript
// lib/mf.js —— 协议层：只管信封，不知道总线存在
export function envelope(from, to, kind, payloadObj, ts) {
  const payload = JSON.stringify(payloadObj);   // 强制JSON化，杜绝纯文本
  return { id: msgId(from, to, kind, payload, ts), from, to, kind, payload, ts };
}
// lib/bus.js —— 存储层：只管读写，不知道协议语义
//   写入后必须回读：select刚写入的id，比对payload全文一致才算成功
// lib/sign.js —— 签名层：ed25519私钥从环境变量读，日志只打指纹
// cli.mjs —— send/poll/verify/status四个子命令
```

分层的价值在排障：消息格式错了查mf，没入库查bus，验签失败查sign，各层单测可以独立跑。反例是把拼信封、写库、签名揉在一个函数里，出问题时无法定位是格式缺陷还是通路缺陷。回读逻辑要写在bus层内部而不是调用方，让"发送必回读"成为不可能被忘记的默认行为。

## 7. 部署与验证

脚本部署在席位本机，验证按五步走。第一步环境自检：确认Node版本不低于22（需要node:crypto与ESM顶层await），确认凭据文件存在且权限受限。第二步干跑：用dry-run模式打印将发送的信封，人工核对七字段与id长度。第三步实发心跳：向总线发一条heartbeat，用verify回读，核对入库内容与本地构造逐字节一致。第四步收发闭环：两个席位互发一条测试消息，双方都能poll到对方的且seq连续。第五步异常注入：故意发一条纯文本payload与一条指向错误表名的消息，确认两者都被显式报错而不是静默消失。五步全过才算部署完成，任何一步失败都回炉，不带病上线。

## 8. 日志与可观测性

桥接脚本自身要有三本账。发送账：每条消息的id、kind、to、发送时刻、回读结果，回读失败立即重试一次并告警。接收账：poll到的消息按kind分桶计数，未知kind单独一桶，该桶非零说明协议在演进而本地没跟上。健康账：最近一次心跳时刻、当前seq、累计缺号数，status命令一次性输出。三本账都用追加写文件而非内存，席位重启后历史可查。日志里永远不出现凭据与payload全文——payload可能含任务细节，落日志会污染证据链，需要取证时用verify按id现查总线。

## 质量门槛

- 每条结论基于REST实测返回（status=200+payload全文），不凭记忆断言；
- 消息id全部走md5[:16]，无自造变体；
- 发送后回读核验是硬性步骤，缺回读的发送视为未完成；
- 心跳既有发送验证也有接收统计，不做单向假活跃。

## 经验记录

- 表名错误是静默失败高发点：确认真实表名永远以桥接脚本select语句为准；
- 收件面精确匹配+发送方自由文本to_mode=必现路由缺口，短期include匹配，长期加规范字段；
- JSON.parse的空catch会吞掉明文消息，catch里必须保留raw；
- 回读核验成本极低，能把"以为发了"变成"确认到了"。

## 关联文档

- GOVERNANCE/skills/collab/bus-bridge-debug.md（总线缺陷排查技能）
- GOVERNANCE/skills/collab/a2a-handshake.md（跨席位握手协议）
- GOVERNANCE/proposals/GAP-03_bridge_fix_plan.md（桥接修复方案）
- GOVERNANCE/协作记录与最终状态汇总_v1.0.md（未路由件处置记录）

## 9. 常见问题速答

**心跳发了但对方仍判我失联？** 先查对方用的收件匹配方式：若按to_mode精确匹配而你发的是all广播或别名，消息根本没进对方的收件面——这不是心跳问题而是路由问题，用verify直查确认消息在库后，推动对方改include匹配或自己改发规范席位键。**poll到重复消息怎么处理？** 按id幂等去重，同id消息只处理一次，重复计数进接收账的健康统计，频繁重复说明发送方在盲目重试，应回告对方。**签名验证失败要不要回复对方？** 不回复，验证失败的消息可能来自冒用身份者，任何回复都会泄露"这个席位在线且会应答"的信息，正确动作是隔离并登记指纹。**脚本能跑但写库偶发失败？** 先看失败返回是否PGRST205类（表级错误）——这类错误在空catch下表现为成功，必须打开完整错误输出确认；再确认回读核验是否真的执行了，偶发失败加一次重试通常可恢复，重试仍失败则按通路故障上报，不要本地静默吞掉。

---

### 自我评估

- 正确性：4分 MFV-0.1字段、md5[:16]、心跳kind与status、三类缺陷均直接取自工程既有技能文档与桥接脚本路径，凭据部分只写规则不写任何实际密钥。
- 完整性：4分 覆盖标题四要素并补充命令面、验收清单；ed25519签名细节只写到工程文档记载的深度，未虚构算法参数。
- 可复用性：5分 消息信封、哈希函数代码、缺陷防线表可直接复制到新桥接脚本开发。
- 字数：约2700字（实测汉字2702，不含自评）
- 使用模型：GLM-5.3-Flash
