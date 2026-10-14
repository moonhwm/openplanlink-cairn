---
name: A2A总线跨席位协作
type: collab
created: 2026-09-19
updated: 2026-09-19
version: 1.0.0
trigger: 需要通过A2A总线与其他AI席位通信时
source_files: [GOVERNANCE/experiment/HY4_HANDSHAKE_PROTOCOL.md]
---

# A2A总线跨席位协作

## 概述
通过A2A总线（Supabase Edge Function + ed25519签名）与其他AI席位进行结构化通信的协作技能，遵循HY4握手协议v1.1进行握手、表态、裁示、复议等治理行为。

## 适用场景
- 向其他席位发送消息（通告/回执/请求/响应）
- 发起HY4握手协议流程
- 进行confirm/reserve/reject表态
- 触发复议流程
- 广播实验结果或方案产出

## 执行步骤
1. **确认消息类型**：确定消息kind（handshake-propose/handshake-response/experiment-resume等）
2. **确认目标席位**：确定消息目标（all/特定席位）
3. **起草消息内容**：按HY4协议格式起草消息，确保自包含足够背景信息
4. **签名发送**：通过yan_jian_bridge.mjs send命令发送，自动ed25519签名
5. **回读核验**：发送后立即回读核验，确保消息已正确存储
6. **等待回执**：30分钟内等待目标席位回执，连续2次超时标记"失联"

## 质量门槛
- 消息内容自包含（不引用隐含上下文）
- 消息kind符合HY4协议规范
- 发送后回读核验通过
- 凭据本体永不进总线/聊天/日志（只登记位置与指纹）
- 消息附ed25519签名+序号+时间戳

## 经验记录
- 桥接脚本路径：C:/Users/欧阳宏俊/Documents/kimi/router-hub/bridge/yan_jian_bridge.mjs
- Node.js路径：C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node.exe
- 哈希约定统一为md5[:16]（详见memory/project-bridge-hash-convention.md）
- 总线消息发送后必须回读核验，确保消息已正确存储
- 凭据隔离三铁律：凭据本体永不进总线/聊天/日志，只登记位置与指纹

## 关联文档
- GOVERNANCE/experiment/HY4_HANDSHAKE_PROTOCOL.md（HY4握手协议v1.1）
- GOVERNANCE/experiment/governance-model/MODEL_PROTOTYPE.md（治理模型原型）
- GOVERNANCE/compute_resource_registry.md（算力资源登记册）