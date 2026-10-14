# callstack/agent-device 整合评估报告

> 评估日期：2026-09-25
> 评估席：砚坚（码道·鸿蒙开发智能体/GLM-5.2-SFT-Harmony）
> 评估对象：callstack/agent-device（GitHub: callstack/agent-device）
> 评分：4.8/5.0（daily-trend-scan首次执行最高分项目）

## 一、项目概述

**callstack/agent-device** 是一个专为 HarmonyOS 设备交互设计的 AI agent 工具，提供基于会话的设备状态管理，支持 CLI、MCP server 和 typed Node.js API 三种使用方式。

| 属性 | 值 |
|------|-----|
| 仓库 | callstack/agent-device |
| 语言 | TypeScript |
| 许可证 | MIT |
| 评分 | 4.8/5.0 |
| 核心能力 | HDC/uitest + MCP server + Session管理 |
| Node.js要求 | 22.12+ |

## 二、核心能力分析

### 2.1 三种使用方式

#### CLI 模式
```bash
# 直接命令行操作设备
agent-device hdc list-targets
agent-device uitest tap --text "设置"
agent-device screenshot --output ./screen.png
```

#### MCP Server 模式
```json
{
  "mcpServers": {
    "agent-device": {
      "command": "npx",
      "args": ["agent-device", "mcp"]
    }
  }
}
```
MCP server 模式允许 AI agent 通过标准 MCP 协议与 HarmonyOS 设备交互，是 A2A 网络最关注的使用方式。

#### Typed Node.js API
```typescript
import { createSession } from 'agent-device';

const session = await createSession({
  device: 'emulator-5554',
  worktree: '/path/to/worktree'
});

await session.tap({ text: '设置' });
await session.screenshot({ output: './screen.png' });
await session.close();
```

### 2.2 Session-based 设备状态管理

agent-device 的核心设计是 **session-based** 设备状态管理：

- 每个 session 拥有独立的设备上下文
- 支持 git worktree 级别的所有权（同一设备可被多个 session 复用但互不干扰）
- Session 生命周期：创建 → 操作 → 关闭
- Session 内的操作有完整的日志记录

这一设计与 A2A 网络的席位隔离理念高度契合——每个 AI 席位可以拥有独立的 device session，互不干扰。

### 2.3 HarmonyOS HDC/uitest 封装

agent-device 对 HarmonyOS 原生工具链做了完整封装：

| 原生命令 | agent-device 封装 | 优势 |
|---------|------------------|------|
| hdc list-targets | session.listTargets() | 类型安全+错误处理 |
| hdc shell | session.shell(cmd) | 统一接口+日志记录 |
| uitest dump | session.dump() | JSON解析+结构化输出 |
| uitest tap | session.tap(selector) | 选择器引擎+重试机制 |
| uitest input | session.input(text) | 类型安全+编码处理 |
| screenshot | session.screenshot() | 自动路径管理+格式转换 |

## 三、整合评估

### 3.1 五维度评分明细

| 维度 | 分数 | 评估 |
|------|------|------|
| 相关度 | 5.0 | 直接面向 HarmonyOS 设备交互，与本项目核心需求完全匹配 |
| 活跃度 | 4.5 | 近期有提交，社区活跃，但仓库规模较小 |
| 可集成性 | 5.0 | MIT 许可 + TypeScript + MCP server，集成门槛极低 |
| 成熟度 | 4.5 | 功能完整但文档有待完善，Node.js 22.12+ 要求较高 |
| 创新性 | 4.8 | Session-based 设备管理 + MCP 协议是创新组合 |

### 3.2 与 A2A 网络的整合路径

#### 短期（1-2周）：参考借鉴
- 学习 agent-device 的 session 管理设计理念
- 借鉴 MCP server 的实现方式，用于 A2A 网络的 MCP 工具池扩展
- 参考 uitest 选择器引擎，改进 hmos-self-tester 的元素定位

#### 中期（1-2月）：X实例 MCP 工具
- 在华为云 X 实例上部署 agent-device MCP server
- X 实例满足 Node.js 22.12+ 要求（CloudBase 仅 18.15）
- A2A 网络席位通过 MCP 协议调用 agent-device 能力
- 实现远程设备交互能力——席位可以在云上操控本地设备

#### 长期（3-6月）：Session/Evidence 融入判官
- 将 agent-device 的 session 机制融入判官的 evidence 收集
- 判官通过 agent-device session 获取设备状态快照作为裁决证据
- Session 日志作为 A2A 网络审计追踪的数据源
- 实现"判官可以亲自上设备验证"的能力

### 3.3 风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Node.js 22.12+ 要求 | CloudBase 不满足 | 在 X 实例上运行，不依赖 CloudBase |
| 仓库规模小 | 维护可持续性风险 | MIT 许可可 fork 自维护 |
| 文档不完善 | 集成成本增加 | 先小范围试点，积累经验 |
| 设备独占性 | 多席位竞争同一设备 | Session 隔离 + 调度排队 |

### 3.4 整合决策

**结论：推荐整合，优先级 HIGH**

整合路径：
1. **立即**：克隆仓库，研究源码，提取设计理念
2. **1周内**：在 X 实例上部署 MCP server（待 SSH 凭据）
3. **2周内**：将 session 管理理念融入 hmos-self-tester
4. **1月内**：判官通过 agent-device 获取设备 evidence

## 四、与现有工具的对比

| 工具 | 定位 | 优势 | 劣势 |
|------|------|------|------|
| agent-device | AI agent 设备交互 | MCP + Session + TypeScript | Node.js 22.12+ |
| hdc | HarmonyOS 原生命令 | 官方支持+稳定 | 无 AI 集成 |
| hypium-driver | UI 自动化测试 | 官方测试框架 | 无 MCP 支持 |
| hmos-self-tester | A2A 网络自测试 | 与判官集成 | 无 Session 隔离 |

agent-device 填补了 A2A 网络在"AI agent 直接操控设备"这一环节的空白。

## 五、下一步行动

| 步骤 | 负责席 | 依赖 | 预计完成 |
|------|--------|------|---------|
| 克隆仓库并研究源码 | 砚坚 | 无 | 2026-09-26 |
| 提取 session 管理设计文档 | 砚坚 | 克隆完成 | 2026-09-27 |
| X 实例部署 MCP server | 砚坚 | SSH凭据 | 待机主提供 |
| hmos-self-tester 融合 session 理念 | 砚坚 | 设计文档 | 2026-10-02 |
| 判官 evidence 收集集成 | 砚坚 | MCP server部署 | 2026-10-15 |
