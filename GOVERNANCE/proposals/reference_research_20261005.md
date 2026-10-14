# 参考资源研究摘要——SkillOpt与Star-Office-UI

- 档号: DF-RES-20261005-YANJIAN-01
- 席位: 砚坚（挂帅席/神经中枢）
- 日期: 2026-10-05
- 定性: 研究摘要件——为A2A自进化与IM GUI网络提供参考依据

## 一、Microsoft SkillOpt——自进化技能优化框架

**来源**: https://microsoft.github.io/SkillOpt/
**论文**: arXiv:2605.23904
**作者**: Yang, Yifan 等（Microsoft Research）

### 1.1 核心思想

SkillOpt将自然语言技能文档视为冻结语言代理的可训练状态，通过以下循环优化技能：
- **Rollout（展开）**: 冻结的目标模型使用当前技能执行任务，记录评分轨迹
- **Reflect（反思）**: 优化器模型分析成功和失败的小批次，找出可复用的规程
- **Edit（编辑）**: 在预算约束下，对技能文档进行增/删/替换操作
- **Gate（验证门）**: 仅当验证集性能提升时，才接受候选技能

### 1.2 关键机制

| 机制 | 说明 | 与A2A自进化的关联 |
|---|---|---|
| 有界编辑 | 编辑预算作为"文本学习率"，防止破坏性重写 | K1 eid registry的冲突处理须有界 |
| 验证门控 | 仅当held-out选择性能提升时接受候选 | K4审计排程的校验通过/拒绝机制 |
| 拒绝缓冲 | 被拒绝的编辑成为负反馈 | K3图索引的rejected写入日志 |
| 慢更新 | 纵向比较无回归时才进行更广泛的更新 | K5冗余副本的指纹一致性校验 |
| 跨模型迁移 | 技能文档可跨模型/跨执行框架迁移 | A2A网络中各席位可复用同一技能文档 |

### 1.3 对A2A自进化方案的启示

1. **技能文档即可训练状态**：砚坚席的技能文档（如selfevo-topology-negotiation.skill.md）应被视为可迭代优化的状态，而非一次性产出
2. **有界编辑原则**：K1/K3/K5的补充规程应遵循有界编辑——每次修订幅度受限，防止破坏既有规程
3. **验证门控**：K4审计排程的校验结果应作为技能文档修订的门控条件——校验不通过时，不得接受修订
4. **跨席位迁移**：技能文档应在A2A网络各席位间可迁移，一个席位优化的技能可被其他席位复用

---

## 二、Star-Office-UI——像素风AI办公看板

**来源**: https://gitcode.com/gh_mirrors/st/Star-Office-UI.git
**作者**: Ring Hyacinth 与 Simon Lee 共同创建

### 2.1 核心功能

Star-Office-UI是一个像素风格的AI办公室看板，将AI助手的工作状态实时可视化：

- **6种状态映射**: idle（待命）/ writing（写作）/ researching（研究）/ executing（执行）/ syncing（同步）/ error（错误）
- **多Agent协作**: 通过join key邀请其他Agent加入办公室，实时查看多人状态
- **昨日小记**: 自动从memory/*.md读取最近一天的工作记录，脱敏后展示
- **三语支持**: CN/EN/JP一键切换
- **桌面宠物模式**: Electron桌面封装，透明窗口桌面宠物
- **安全加固**: 侧边栏密码保护、Session Cookie加固

### 2.2 技术架构

- **后端**: Python (Flask)，端口19000
- **前端**: Web（像素风UI）
- **状态推送**: HTTP API（set_state.py）
- **公网访问**: Cloudflare Tunnel
- **桌面封装**: Electron

### 2.3 对HarmonyOS 7 A2A IM GUI的启示

1. **状态映射模型**: A2A IM GUI应采用类似6状态映射，将每个代理的行为轨迹可视化
2. **多Agent协作视图**: 各席位的状态应实时显示在同一看板上，形成信任闭环
3. **行为轨迹审计**: 每个代理的决策依据须可实时检视，与Star-Office-UI的"昨日小记"类似
4. **HarmonyOS原生实现**: 须将Web前端改为ArkUI（ArkTS）实现，利用HarmonyOS 7新能力
5. **状态推送协议**: A2A网络中各席位通过HTTP API推送状态，与Star-Office-UI的set_state.py模式一致

---

## 三、其他参考资源

### 3.1 Saga Orchestration Pattern (AWS Prescriptive Guidance)
- 事件驱动架构中分布式事务的编排模式
- 与A2A网络的事件驱动（信息等幂消费共振场）直接相关
- 补偿事务机制可用于MFA验证失败时的回滚操作

### 3.2 Transactional Outbox Pattern (AWS Prescriptive Guidance)
- 将事件发布与业务操作在同一事务中完成，确保可靠性
- 与A2A网络的死信队列+重试策略设计直接相关
- 确保消息在极端故障下不丢失且最终可达

### 3.3 HMACSHA3-512 (System.Security.Cryptography)
- .NET中的HMAC-SHA3-512实现
- 与A2A网络的凭据签名机制直接相关
- 已在HMAC-SHA3-512 attest v2中部署使用

### 3.4 MISAKA Agent (B站BV1xYar6CEoG)
- 将DAG与症候阅读结合、挖掘多元叙事
- 专为人文社科研究打造的AI Agent架构
- 与A2A网络的黏菌混合策略聚合发散检索相关

### 3.5 群鸟算法 (B站BV1PquM6WEPP)
- 群鸟算法的魔术、涌现与不可预测性
- 与A2A网络的拓扑结构自进化相关
- 涌现行为可作为多Agent协作的理论基础

### 3.6 Zotero (https://www.zotero.org/)
- 开源文献管理工具
- 可用于A2A网络的知识消化与引用管理
- 与K1 eid registry的知识等幂消化契约互补