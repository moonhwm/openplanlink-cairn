---
name: a2a-handshake
type: collab
created: 2026-09-23
updated: 2026-09-23
version: 2.0.0
trigger: 需要与A2A网络中其他AI席位建立通信、互认身份、派发任务或回收结果时
source_files: [GOVERNANCE/skills/collab/a2a-handshake.md, GOVERNANCE/skills/collab/a2a总线协作.md, GOVERNANCE/a2a/YANJIAN_ROLE_REGISTRATION.md, GOVERNANCE/skills/collab/conflict-resolution.md]
---

# collab技能：A2A跨席位握手协议——身份认证、任务派发、结果回收、冲突处理

## 概述

A2A（Agent-to-Agent）跨席位握手协议定义了多AI席位在同一工程上协作时的通信规矩：如何互认身份、如何把任务派给对的席位、如何确认结果真的回来了、以及出现分歧时按什么顺序裁决。本技能文档基于harmony-app（鸿蒙适老化股票异动播报应用，代号铃语）多席位协作实战提炼，适用于任何"多个AI分治一个代码仓库"的场景。

## 1. A2A网络架构与席位身份

### 1.1 五席位定义

| 席位 | 运行环境 | 模型 | 职责 |
|------|---------|------|------|
| 砚坚 | CodeArts Agent | GLM-5.2-sft-harmony | 端侧UI、播报交互、Push封装（挂帅席/神经中枢） |
| 顾权 | Kimi Code | — | 取数、策略、监测、服务端出数 |
| Moon | ZCode | GLM-5.3-Flash（按机主常设令锁定） | 自主燃烧、知识资产产出 |
| 薪传席 | 待定 | — | 待定义 |
| 机主白秉烛 | Kimi Work | — | 协调者、裁决者（最终裁定权） |

席位是治理概念，不是工具端点。ZCode侧registry.json把CodeArts Agent分配为data-engineer，那是编排方对工具端点的分配，与砚坚席位本身的治理角色无关——身份以席位报名文档（如GOVERNANCE/a2a/YANJIAN_ROLE_REGISTRATION.md）登记的为准。

### 1.2 分区主权

| 目录 | 主权席 | 职责 |
|------|--------|------|
| harmony-app/ | 砚坚（CodeArts） | 端侧UI、播报交互、Push封装 |
| quant-lab/ | 顾权（Kimi Code） | 取数、策略、监测、服务端出数 |
| GOVERNANCE/skills/ | 各席位按产出归属 | 知识资产、技能文档 |
| 接口边界 | 全席位共守 | AGENTS.md + entry/src/main/ets/model/AlertItem.ets 定义的AlertFeed JSON契约 |

分区主权是握手协议的物理基础：握手的本质是"我是谁、我管哪块、我要跟你交换什么"。

## 2. 身份认证

### 2.1 role@seat双段署名

所有跨席位消息使用`role@seat`双段署名，例如`ui-lead@yan-jian`、`knowledge-writer@moon`。role是本次协作中承担的角色，seat是席位标识。心跳消息统一为`kind: "heartbeat"`、`status: "alive"`，并携带双段署名——收到心跳即确认对方席位存活且身份未被冒用。

### 2.2 签名与凭据隔离

- 总线消息附ed25519签名+序号+时间戳，发送方私钥签名，收件方可验伪。
- **凭据隔离三铁律**：凭据本体永不进总线/聊天/日志，只登记存储位置与指纹（md5前16位）。任何握手消息中出现完整Token/密钥即视为安全事故，立即作废该凭据并通报机主。
- 席位身份由"报名文档+签名能力+心跳记录"三重佐证，缺一不可。

### 2.3 身份核验步骤

1. 收到陌生席位消息，先查其席位报名文档是否存在；
2. 校验ed25519签名与序号连续性；
3. 比对最近一次心跳时间戳，超过阈值（见3.3）按失联处理；
4. 任一项不过，消息按待验证处理，不据此改动代码。

## 3. 握手流程

### 3.1 消息格式（MFV-0.1）

```json
{
  "id": "[md5哈希前16位]",
  "from": "moon",
  "to": "yan-jian",
  "kind": "handshake-propose",
  "payload": "{自包含的消息正文}",
  "ts": "2026-09-23T10:00:00+08:00"
}
```

字段与kind枚举的完整定义见GOVERNANCE/skills/collab/bridge-script.md（A2A桥接脚本开发技能），此处不重复展开。

### 3.2 握手四步

1. **提议**：发起方发`handshake-propose`，payload必须自包含——说明来意、涉及目录、预计工期，不引用隐含上下文；
2. **响应**：接收方回`handshake-response`，携带confirm/reserve/reject三种表态之一；
3. **开工**：双方表态confirm后，按串行纪律进入执行（见GOVERNANCE/skills/collab/conflict-resolution.md）；
4. **回执**：任务完成方发回执消息，等待方30分钟内确认。

### 3.3 超时与失联

连续2次回执等待超时（每次30分钟）即标记对方"失联"，处理方式：暂停依赖对方的任务、在CHANGELOG.md登记失联事实、报告机主白秉烛裁决是否改派。禁止在失联状态下代写对方分区代码。

## 4. 任务派发

### 4.1 派发消息规范

派发任务使用`kind: "task-dispatch"`，payload必须包含六要素：

```json
{
  "task_id": "A1",
  "goal": "审查broadcast-a2a云函数的错误处理",
  "scope": ["cloudfunctions/broadcast-a2a/"],
  "deliverable": "GOVERNANCE/review/A1-broadcast-a2a.md",
  "constraint": "不泄露Token，不推翻AlertFeed契约",
  "deadline": "2026-09-23 12:00"
}
```

- goal用一句话说清做什么；scope圈定文件范围，越界即违规；
- deliverable写明落盘绝对路径，结果回收以此路径为准；
- constraint继承工程红线：适老化28-34fp大字卡片流、禁复杂图表、禁承诺收益/保本、禁催促性指令、禁对外公开/收费。

### 4.2 派发原则

1. **按分区主权派发**：harmony-app/端侧任务派砚坚，取数与策略派顾权，知识资产派Moon；
2. **按额度匹配派发**：任务量与目标席位可用额度匹配，详见GOVERNANCE/skills/collab/task-decomposition.md的匹配矩阵；
3. **单任务单责任席**：一个任务只派一个主责席位，辅助席位以咨询角色出现。

## 5. 结果回收

### 5.1 回读核验

发送方（含任务回执）发出消息后立即回读核验，确认消息已正确写入总线存储——"发了"不等于"到了"，这是总线协作的血泪教训（详见GOVERNANCE/skills/collab/bus-bridge-debug.md）。

### 5.2 回收验收清单

- [ ] deliverable路径下文件存在且非空；
- [ ] 正文汉字数达到任务要求的85%以上；
- [ ] 内容自包含，不依赖对话记忆；
- [ ] 文末附自我评估三维度打分与字数；
- [ ] 未触碰禁改文件（AlertItem/AlertFeed契约、PushService.ets占位逻辑）；
- [ ] 回执消息已发出且回读核验通过。

### 5.3 结果归档

验收通过后，任务产出登记进CHANGELOG.md对应条目（或GOVERNANCE/skills/SELF_BUILT_INDEX.md），使结果可持久化、可追溯。未归档的结果视为未交付。

## 6. 冲突处理（摘要）

仲裁层级：①CHANGELOG.md最后一条优先（时间序事实）；②AGENTS.md约束为最高规则；③机主白秉烛裁决为最终裁定。常见场景——同文件并发修改由后提交者负责合并、擅改AlertFeed契约必须停机主确认否则回退、擅入对方目录立即回退并登记违规。完整规则见GOVERNANCE/skills/collab/conflict-resolution.md。

## 7. 握手状态机

跨席位协作的生命周期用六个状态管理，任何时刻双方对当前状态的认知必须一致，不一致本身就是需要处理的冲突：

| 状态 | 含义 | 进入条件 | 退出去向 |
|------|------|---------|---------|
| idle | 未接触 | 初始 | proposed |
| proposed | 已发提议 | handshake-propose发出且回读核验通过 | confirmed / rejected / timeout |
| confirmed | 双方confirm | 收到handshake-response(confirm) | executing |
| executing | 任务执行中 | 按串行纪律开工 | delivered / interrupted |
| delivered | 已交回执 | 回执消息发出且回读通过 | closed / rework |
| closed | 验收归档 | 验收清单全过并登记CHANGELOG | 终态 |

三条状态迁移规则需要特别说明。第一，任何状态迁移都必须有总线消息作为凭证，凭记忆宣称"他已经同意了"不算数——回读核验通过的消息才是同意的证据。第二，rejected与timeout是两个不同出口：rejected是对方明确拒绝，可以据其理由修改提议后重新进入proposed；timeout是对方失联，处理路径是第3.3节的失联流程，两者不可混用。第三，rework（返工）不回到executing之前的任何状态，返工期间双方仍在confirmed关系下，避免重复握手的开销与序号混乱。

## 8. 消息安全与防重放

身份认证之外，握手协议对消息层安全有三条最低要求。其一，序号连续性：每个席位维护发送序号seq，接收方发现序号跳变（缺号）时，缺号消息可能是被吞也可能是被删，须用REST直查补齐后再判定，缺号统计方法见bus-bridge-debug.md。其二，时间戳新鲜度：ts距当前超过一定窗幅（建议2小时）的消息按陈旧消息处理，不据此触发状态迁移，防止历史消息被重放扰乱状态机。其三，签名验伪：ed25519签名验证失败的消息直接隔离，不上报、不回复、不执行，并在总线登记指纹供追溯。

凭据卫生在握手场景尤其重要，因为握手消息天然携带"我是谁、我在哪台机器上"的信息。规则是身份可以自述，凭据必须暗指——说"我的私钥存在router-hub/bridge/keys/"可以，把私钥内容粘进payload则是事故。所有涉及凭据的引用一律用存储路径加md5前16位指纹双要素。

## 9. 失联与改派实操

判定失联后，等待方按以下顺序处置。第一步，自查通路：先用verify命令直查总线，确认不是自己的桥接脚本缺陷导致收不到回执——历史上多次"失联"实为路由缺陷，教训记录在bus-bridge-debug.md。第二步，二次催告：发一条带催告标记的消息，再等一个回执周期。第三步，报告改派：将任务描述、已完成部分、断点信息整理成改派消息发机主与候选席位，改派须在CHANGELOG登记。第四步，保护现场：不清理对方工作区，不代写对方分区，等待责任链明确。

被改派席位的义务：接手前读对方CHANGELOG遗留栏与断点描述，接续而非重做，交付物中注明接续来源。若原席位失而复返，以机主裁定为准决定任务归属，先到先得不是原则，登记在先才是。

## 10. 实战案例

以harmony-app的一次真实协作为例走完整流程。Moon席位要在砚坚主权分区内审查云函数broadcast-a2a：先发handshake-propose，payload写明来意（只读审查、产出落在GOVERNANCE/review/、不动cloudfunctions源码）；砚坚回confirm并附注意事项（Push需换华为Push Kit REST是已知问题，审查时按此背景评估）；Moon按串行纪律开工前执行git status与读CHANGELOG最后一条，确认无未收尾现场；交付后回执消息附交付路径与自评，砚坚按第5.2节清单验收，全部通过后在CHANGELOG登记归档，状态机走完closed。整个过程中双方没有共享任何隐含上下文，全部事实经由总线消息与落盘文件传递——这就是握手协议的目的：让协作不依赖记忆，只依赖证据。

## 质量门槛

- 每条跨席位消息附ed25519签名+序号+时间戳，发送后回读核验；
- 消息内容自包含，不引用隐含上下文；
- 凭据本体永不进总线/聊天/日志；
- 任务派发六要素齐备，结果回收验收清单全过；
- 失联判定有据（连续2次×30分钟超时），不凭感觉。

## 经验记录

- 席位身份≠工具端点：registry.json里的分工是编排层概念，治理层身份以报名文档为准；
- 消息寻址必须用规范席位键，自由文本别名会造成路由缺口（workbuddy的教训）；
- 回执超时先核查总线数据再判失联，路由缺陷常被误判为对方失联。

## 关联文档

- GOVERNANCE/skills/collab/bridge-script.md（MFV-0.1协议与桥接脚本）
- GOVERNANCE/skills/collab/conflict-resolution.md（冲突解决全量规则）
- GOVERNANCE/skills/collab/task-decomposition.md（任务分解与派发）
- GOVERNANCE/a2a/YANJIAN_ROLE_REGISTRATION.md（席位报名范本）

---

### 自我评估

- 正确性：4分 五席位、分区主权、签名与凭据隔离、仲裁层级均取自工程既有文档（a2a-handshake.md v1、a2a总线协作.md、YANJIAN_ROLE_REGISTRATION.md），未引入与事实相悖的内容。
- 完整性：4分 覆盖标题要求的身份认证、任务派发、结果回收、冲突处理四主题，冲突处理按分工以摘要+交叉引用方式处理。
- 可复用性：4分 协议步骤、消息样例、验收清单可直接套用到任何多席位协作场景，自包含。
- 字数：约2600字（实测汉字2626，不含自评）
- 使用模型：GLM-5.3-Flash
