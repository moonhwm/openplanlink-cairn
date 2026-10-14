# 华为段大模型调用规范

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-19
> 状态：待广播
> 关联：IMA走甲案 T3.1-T3.3

---

## 1. 砚坚席能力面

### 1.1 席位身份

| 属性 | 值 |
|------|-----|
| 席位名 | 砚坚 |
| 席位键 | yan-jian-codearts-glm52 |
| 归属组织 | 华为云码道(CodeArts) |
| 模型 | GLM-5.2 |
| 桥接版本 | v0.3.1 |
| 签名方式 | ed25519 |

### 1.2 能力面

| 能力 | 说明 | 适用场景 |
|------|------|---------|
| HarmonyOS NEXT 开发 | ArkTS/ArkUI编程、Stage模型、Ability框架 | 铃语App端侧开发、新功能实装 |
| 适老化设计 | 大字卡片流、点卡即听、界面极简 | 适老化交互优化 |
| 端侧播报交互 | AVPlayer音频播放、Push Kit推送、轮询兜底 | 播报功能开发与优化 |
| 项目知识管理 | Wiki知识文档生成、模块文档、规范文档 | 项目文档维护 |
| A2A总线协调 | 消息收发、签名验证、回执核验 | 多AI席位协调 |

### 1.3 调用方式

各席通过A2A总线发送 `kind=task` 消息给砚坚席：

```
桥接命令：
node yan_jian_bridge.mjs send --to yan-jian --kind task --sign "任务描述"
```

消息格式建议：
```json
{
  "task_type": "harmonyos_dev | wiki_gen | a2a_coord",
  "description": "具体任务描述",
  "priority": "P0 | P1 | P2",
  "deadline": "2026-09-20T00:00:00Z",
  "context_files": ["相关文件路径列表"]
}
```

### 1.4 响应格式

砚坚席的响应遵循AlertFeed JSON契约（对于开发任务）或自定义格式（对于协调任务）：

```json
{
  "status": "success | failed | blocked",
  "result": {
    "commit": "git commit hash",
    "files_changed": ["文件列表"],
    "build_status": "success | failed",
    "test_status": "passed | failed | skipped"
  },
  "message": "人类可读的结果描述"
}
```

---

## 2. 接口规范

### 2.1 HarmonyOS开发接口

| 接口 | 输入 | 输出 | 限制 |
|------|------|------|------|
| 功能开发 | 需求描述+项目路径 | 代码+构建产物 | 纯ArkTS、零三方依赖 |
| Bug修复 | Bug描述+复现步骤 | 修复代码+验证结果 | 不破坏现有功能 |
| Wiki生成 | 项目路径 | 知识文档体系 | 遵循repo-simple-wiki规范 |
| 构建验证 | 项目路径 | HAP文件+构建日志 | hvigor禁止中文路径 |

### 2.2 限制清单

| 限制 | 原因 | 来源 |
|------|------|------|
| 纯ArkTS | HarmonyOS NEXT要求 | AGENTS.md §二.3 |
| 零三方依赖 | 适老化App安全要求 | AGENTS.md §二.3 |
| Stage模型 | HarmonyOS NEXT要求 | AGENTS.md §二.3 |
| compatibleSdkVersion 6.0.2(22) | 目标机型Mate X5 | build-profile.json5 |
| 禁K线图/走势图 | 适老化约束 | AGENTS.md §二.1 |
| 信号松绑三禁 | 合规约束 | AGENTS.md §二.2 |
| PushService保持占位 | AGC未配置 | AGENTS.md §二.4 |
| 首屏永不空白 | 用户体验 | AGENTS.md §二.5 |

---

## 3. 华为云MaaS端点信息

### 3.1 端点概览（脱敏）

| 服务 | 端点 | 认证方式 | 模型 | 状态 |
|------|------|---------|------|------|
| CodeArts AI | 内部端点（脱敏） | CodeArts内部认证 | GLM-5.2 | ✅ 在役 |
| 华为云MaaS | 待开通 | API Key | 待定 | ⏳ 未开通 |

### 3.2 砚坚席调用示例

砚坚席本身即为华为云CodeArts提供的AI服务，无需外部调用。其他席如需调用华为云模型，须通过A2A总线发送task消息给砚坚席，由砚坚席代理执行。

### 3.3 注意事项

- 华为云MaaS端点尚未对外开通，当前仅砚坚席（CodeArts内置）可用
- 密钥本体永不进总线/聊天/日志，只登记位置与指纹
- 如未来MaaS对外开通，将在此文档中补充端点信息（脱敏）