# API密钥管理与认证规范

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-19
> 状态：待广播
> 关联：IMA走甲案 T4.1-T4.3

---

## 1. 密钥存储与读取

### 1.1 存储位置

| 凭据 | 存储位置 | 加密版本 | 读取优先级 |
|------|---------|---------|-----------|
| 百炼API Key | GOVERNANCE/credentials/aliyun_bailian.json | .enc (AES-256-GCM) | .enc优先，降级读明文 |
| A2A总线签名密钥 | router-hub/bridge/seat_sig.mjs | ed25519密钥对 | 直接读取（代码内） |
| IMA连接器凭据 | 待定 | 待定 | 待定 |
| OfficeAce凭据 | 待定 | 待定 | 待定 |
| 华为云MaaS | CodeArts内部管理 | N/A | 不需外部读取 |

### 1.2 读取优先级规则

```
1. 检查环境变量（DASHSCOPE_API_KEY等）
2. 检查加密金库文件（.enc）
3. 检查明文金库文件（.json）
4. 都不存在 → 返回空字符串，记日志
```

### 1.3 密钥分级

| 级别 | 名称 | 说明 | 可外发 |
|------|------|------|--------|
| R0 | 公开 | 项目结构、API规范、文档 | ✅ 可外发 |
| R1 | 内部 | 端点URL、模型名称、调用方式 | ✅ 可外发（脱敏） |
| R2 | 受限 | 凭据文件位置、指纹（md5[:16]） | ⚠️ 仅限A2A总线 |
| R3 | 凭据本体 | API Key、密码、密钥 | ❌ 永不外发 |

### 1.4 密钥轮换流程

```
旧Key失效
  ↓
新Key生成（百炼控制台/AGC平台/其他）
  ↓
更新金库文件（先写.enc加密版，再删除明文版）
  ↓
更新消费方代码（环境变量引用或文件读取）
  ↓
桥接脚本重启（使新Key生效）
  ↓
验证：发送测试消息/请求，确认新Key可用
  ↓
记录：在CHANGELOG.md记录轮换时间、原因、验证结果
```

---

## 2. 回调机制规范

### 2.1 A2A总线回调

| 事件 | 回调方式 | 验证内容 |
|------|---------|---------|
| 消息发送 | 回读核验 | to_mode、kind、正文完整性 |
| 消息接收 | 桥接脚本自动接收 | from、kind、签名验证 |
| 消息丢失 | 误路由巡检 | hash比对、id连续性检查 |

回读核验流程：
```
send → 获取返回id → read --since id → 核验to/kind/正文一致 → 通过/失败
```

### 2.2 TTS回调（百炼CosyVoice WebSocket）

| 事件 | 回调方式 | 处理逻辑 |
|------|---------|---------|
| task-started | WebSocket文本消息 | 发送continue-task + finish-task |
| result-generated | WebSocket文本消息 | 记录合成进度 |
| task-finished | WebSocket文本消息 | 保存音频文件 + HRTF后处理 |
| task-failed | WebSocket文本消息 | 记录错误 + 返回undefined |
| timeout | 30s定时器 | 关闭WebSocket + 返回undefined |

### 2.3 IMA回调（MCP连接器）

| 事件 | 回调方式 | 处理逻辑 |
|------|---------|---------|
| 连接成功 | MCP协议握手 | 开始知识库读写 |
| 连接断开 | MCP disconnect事件 | 记录日志 + 等待重连 |
| 知识写入 | MCP response | 验证写入成功 |
| 知识读取 | MCP response | 返回读取结果 |

### 2.4 OfficeAce回调（本地HTTP）

| 事件 | 回调方式 | 处理逻辑 |
|------|---------|---------|
| 服务可用 | GET /health 200 | 标记OfficeAce在线 |
| 服务不可用 | GET /health 非200/超时 | 标记OfficeAce离线 |
| 文件变更 | 文件系统watch | 读取新文件内容 |

---

## 3. 会话退出（Session Logout）操作流程

### 3.1 IMA连接器退出

```
1. 发送MCP disconnect消息
2. 等待MCP close确认
3. 清理本地MCP连接状态
4. 记录退出日志
验证：再次连接测试，确认干净退出
```

### 3.2 A2A总线退出

```
1. 桥接脚本发送 heartbeat kind=logout 消息
2. 等待总线确认（回读核验）
3. 关闭桥接脚本进程
4. 记录退出日志
验证：总线消息列表中可见logout消息
```

### 3.3 百炼WebSocket退出

```
1. 发送 finish-task 事件（通知文本发送完毕）
2. 等待 task-finished 事件
3. 关闭WebSocket连接
4. 清理音频缓存
验证：WebSocket连接状态为CLOSED
```

### 3.4 OfficeAce交互退出

```
1. 关闭本地HTTP连接（停止轮询/health）
2. 清理文件系统watch
3. 记录退出日志
验证：GET /health 超时无响应
```

---

## 4. 密钥健康检查

### 4.1 检查项

| 检查项 | 方法 | 频率 | 预期结果 |
|--------|------|------|---------|
| 百炼API Key有效性 | 发送轻量TTS请求 | 每次启动 | 200响应 |
| A2A总线连通性 | 发送heartbeat消息 | 每5分钟 | 回读核验通过 |
| IMA连接器探活 | MCP ping | 每次使用前 | pong响应 |
| OfficeAce健康 | GET /health | 每次使用前 | 200响应 |
| 凭据文件完整性 | 文件存在性检查 | 每次启动 | .enc或.json存在 |

### 4.2 健康检查脚本

脚本位置：`GOVERNANCE/scripts/cred_health_check.mjs`（待实现）

一键运行：`node GOVERNANCE/scripts/cred_health_check.mjs`

---

## 5. 密钥管理三铁律

1. **凭据本体永不进总线/聊天/日志**——只登记位置与指纹
2. **加密优先**——.enc文件优先于明文文件
3. **轮换留痕**——旧Key失效原因、新Key获取方式、更新时间全部记录