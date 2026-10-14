# 百炼免费额度调用优先级规则

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-19
> 状态：生效中
> 关联：IMA走甲案 T1.2

---

## 1. 调用优先级规则

### 1.1 服务优先级

| 优先级 | 服务 | 模型 | 计费方式 | 说明 |
|--------|------|------|---------|------|
| P0 | TTS语音合成 | cosyvoice-v3-flash | 免费额度内 | 铃语App核心功能，点卡即听依赖TTS |
| P1 | 文本聊天（免费） | qwen-turbo | 免费额度内 | A2A治理实验理论轨攻击生成 |
| P2 | 文本聊天（付费） | qwen-plus | 按量付费 | **禁止使用**，除非机主明确授权 |

### 1.2 单次请求限制

| 参数 | 限制值 | 原因 |
|------|--------|------|
| 单次请求token上限 | 2000 | 避免长请求消耗过多额度 |
| TTS单次合成文本上限 | 500字 | 异动播报白话标题+详情通常<200字 |
| 并发请求数 | 1 | 避免并发消耗，串行调用 |
| 请求间隔 | ≥500ms | 避免触发限流 |

### 1.3 调用决策流程

```
收到调用需求
  ↓
是TTS请求？ → 是 → 检查额度余量 > 10%？ → 是 → 执行TTS合成
                    ↓ 否
                    降级：跳过TTS，AlertItem.audioUrl=undefined
  ↓ 否
是文本聊天请求？ → 是 → 使用qwen-turbo（免费）？
                    ↓ 是
                    检查额度余量 > 20%？ → 是 → 执行文本聊天
                    ↓ 否
                    降级：跳过文本聊天，返回预设响应
                    ↓ 否
                    **禁止使用qwen-plus**，除非机主明确授权
```

---

## 2. 额度监控规范

### 2.1 监控指标

| 指标 | 阈值 | 动作 |
|------|------|------|
| 免费额度消耗 < 50% | 正常 | 继续正常调用 |
| 免费额度消耗 50%-80% | 预警 | console.warn 日志，继续调用 |
| 免费额度消耗 > 80% | 警告 | console.warn 日志，仅允许TTS调用 |
| 免费额度耗尽 | 止损 | console.error 日志，跳过所有非必要调用 |

### 2.2 额度追踪实现

在 `server.mjs` 中新增 `bailianQuotaTracker` 模块：

```javascript
// 百炼额度追踪器
const bailianQuotaTracker = {
  // 估算消耗（百炼免费额度约1M tokens）
  totalQuota: 1000000,         // 总免费额度（tokens）
  ttsConsumed: 0,               // TTS消耗累计
  chatConsumed: 0,              // 文本聊天消耗累计
  lastWarningLevel: 'normal',   // 最近预警级别

  // TTS消耗估算：每次合成约消耗500-1000 tokens（文本+音频帧）
  recordTTS(textLength) {
    this.ttsConsumed += Math.ceil(textLength * 2); // 估算：1字≈2tokens
    this.checkThreshold();
  },

  // 文本聊天消耗估算：输入+输出tokens
  recordChat(inputTokens, outputTokens) {
    this.chatConsumed += inputTokens + outputTokens;
    this.checkThreshold();
  },

  // 阈值检查
  checkThreshold() {
    const total = this.ttsConsumed + this.chatConsumed;
    const ratio = total / this.totalQuota;
    if (ratio >= 1.0) {
      console.error('[quota] STOPLOSS:-100%: all non-essential calls skipped');
      this.lastWarningLevel = 'stoploss';
    } else if (ratio >= 0.8) {
      console.warn(`[quota] WARNING-80%: only TTS allowed (${(ratio*100).toFixed(1)}% consumed)`);
      this.lastWarningLevel = 'warning';
    } else if (ratio >= 0.5) {
      console.warn(`[quota] PRECAUTION-50%: ${(ratio*100).toFixed(1)}% consumed`);
      this.lastWarningLevel = 'precaution';
    }
  },

  // 是否允许TTS调用
  canCallTTS() {
    const total = this.ttsConsumed + this.chatConsumed;
    return total / this.totalQuota < 1.0;
  },

  // 是否允许文本聊天调用
  canCallChat() {
    const total = this.ttsConsumed + this.chatConsumed;
    return total / this.totalQuota < 0.8;
  },
};
```

### 2.3 硬止损逻辑

在 `generateTTS()` 和文本聊天函数中，调用前检查额度：

```javascript
// TTS调用前检查
if (!bailianQuotaTracker.canCallTTS()) {
  console.error('[quota] TTS skipped due to quota exhaustion');
  return undefined;
}

// 文本聊天调用前检查
if (!bailianQuotaTracker.canCallChat()) {
  console.warn('[quota] chat skipped due to quota threshold');
  return null;
}
```

---

## 3. 成本控制红线

1. **账户余额约¥13-¥20，禁止触发任何付费API调用**
2. **所有调用必须限定在免费额度内**
3. **qwen-plus（付费模型）禁止使用，除非机主明确授权**
4. **额度耗尽时自动降级，不阻塞主流程**
5. **TTS优先于文本聊天——TTS是铃语App核心功能，文本聊天是辅助功能**

---

## 4. 降级策略

| 场景 | 降级行为 | 用户感知 |
|------|---------|---------|
| TTS额度耗尽 | audioUrl=undefined | 卡片不显示"▶ 听"按钮 |
| 文本聊天额度耗尽 | 返回预设响应 | A2A治理实验理论轨暂停 |
| 百炼API不可用 | 跳过TTS，保留异动数据 | 卡片仍显示，只是不能听 |
| WebSocket连接失败 | 返回undefined，记日志 | 同TTS额度耗尽 |