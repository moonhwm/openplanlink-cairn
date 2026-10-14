# signalNote 接入 LLMRouter 落地方案

> 编写：砚坚（码道·鸿蒙开发智能体 / deepseek-v4-pro-0813）
> 日期：2026-09-24
> 前置文档：`docs/llm-auto-switch/LLM_AUTO_SWITCH_PLAN.md`（双模型切换方案）、`docs/audit/2026-09-23-full-review.md`（H1 合规 fail-closed 修复）
> 状态：设计稿（待机主注入真实 API 凭据后立项）

---

## 一、背景与目标

### 1.1 现状

`fetch-tushare-data` 云函数当前对 signal 卡的白话解读是**硬编码模板**（`index.js` L585-592）：

```js
if (kind === 'signal') {
  if (direction === 'up') {
    signalNote = '留意后续走势';
  } else if (direction === 'down') {
    signalNote = '注意风险';
  }
}
```

这段代码无论股票是「放量突破」「缩量回调」「涨停打开」「跌停封死」等何种情形，输出的解读只有两句固定的中性话术。**它守住了合规底线（三禁），但丧失了信息量**——signal 卡的核心价值本应是「用大白话告诉机主：为什么这条异动值得关注、背后可能是什么」。

### 1.2 目标

引入 LLMRouter（双模型专家团切换层）为 signal 卡生成**动态白话解读**，同时保持三条硬约束不被突破：

1. **合规三禁**（不承诺收益 / 不催促指令 / 不对外收费）——LLM 产物必须过 fail-closed 硬闸
2. **适老化**（28-34fp 大字、大白话、一句话说清）
3. **首屏永不空白 / 降级兜底**——LLM 不可用时降级回硬编码，绝不让卡片因 LLM 故障而缺失

### 1.3 与既有修复的关系

本方案直接复用 `docs/audit/2026-09-23-full-review.md` 的 **H1 结论**：

> 合规检查必须 fail-closed 才能守住三禁红线。LLMRouter 生成的 signalNote 是 LLM 产物（非硬编码），DKnowC 判定 `Unsafe/Focus` 必须硬拦截（降级为 fact），而非只贴标签。

如果 H1 未修复（fail-open），本方案接入 LLM 后，一旦 LLM 产出「建议买入/满仓」类文案，三禁将被静默突破。**H1 是本方案的强前置，已闭环。**

---

## 二、架构设计

### 2.1 总体拓扑

```
东方财富 API / Tushare（数据源）
        │
        │ 涨幅 ≥ 8% 判定为 signal
        ▼
fetch-tushare-data 云函数
   │
   ├─ 1. 组装异动事实（headline/detail，确定性生成）
   │
   ├─ 2. LLM Router 生成 signalNote（仅 kind=signal 触发，3s 超时）
   │       │
   │       ├─ 模型路由：deepseek-v4-pro-0813（signal_note 类型默认路由）
   │       ├─ 失败降级：切备选模型重试一次
   │       └─ 彻底失败：降级回硬编码模板（「留意后续走势/注意风险」）
   │
   ├─ 3. DKnowC 合规检查（fail-closed）
   │       ├─ Safe/ConditionallySafe → 保留 kind=signal + signalNote
   │       └─ Unsafe/Focus → 降级为 fact（剥离 signalNote，删除角标）
   │
   └─ 4. 入库（saveAlertsToDB）
```

### 2.2 部署形态抉择

| 方案 | 描述 | 优点 | 缺点 | 推荐 |
|------|------|------|------|------|
| **A 内嵌模块** | 把 `llm-router/index.js` 作为 fetch-tushare-data 的本地依赖 `require` | 零额外网络跳数、延迟最低、无需新云函数 | 耦合度高、LLMRouter 升级需重部署数据函数 | ⭐ 推荐（V1） |
| **B 独立云函数** | LLMRouter 单独部署为 `llm-router` 云函数，fetch-tushare-data 通过 CloudBase callFunction 调用 | 解耦、可独立扩展、共享给其他云函数 | 多一跳 callFunction 延迟、调用鉴权 | 阶段二 |
| **C 直连双 API** | fetch-tushare-data 直接 HTTP 调 deepseek/pangu API，不走 LLMRouter | 最简单 | 放弃路由/台账/降级逻辑，退化 | 仅原型验证 |

**V1 选方案 A**：LLMRouter 是纯逻辑层（无外部依赖，仅 `fs/path/crypto/https`），可直接作为 npm 模块打包进 fetch-tushare-data。后续需要共享时再拆方案 B。

### 2.3 signalNote 生成时机

**同步生成（V1）**：在 `createAlertItems` 内部、合规检查之前生成。理由：
- signal 卡占比低（涨幅 ≥ 8% 的股票极少），同步生成不会成为瓶颈
- 合规检查紧接其后，形成「生成 → 合规 → 决定形态」的原子链路，逻辑清晰

**异步生成（V2，暂缓）**：先入库硬编码 signalNote，后台队列更新。仅在 signal 卡占比上升、或 LLM 延迟超过 3s P99 时引入。

---

## 三、降级链（核心设计）

降级链是本方案的灵魂，确保「首屏永不空白」硬约束在任何 LLM 故障下不破。

```
第 0 层：LLM 生成 signalNote（deepseek 优先，3s 超时）
   │
   ├─ 成功 → 进入合规检查
   │
   ├─ 主模型失败（网络/超时/5xx）→ 备选模型重试一次（+3s，共 ≤6s）
   │       │
   │       ├─ 成功 → 进入合规检查
   │       └─ 失败 → 降级第 1 层
   │
   ├─ 未配置 API Key → 降级第 1 层
   │
第 1 层：硬编码模板降级（「留意后续走势/注意风险」）
   └─ 进入合规检查（中性话术必过 Safe）
```

**关键点**：
1. **降级是静默的**——LLM 失败不抛错中断链路，只记日志 `[llm] degraded to template`
2. **降级不改变 kind**——硬编码模板仍是 signal 卡的合法解读，卡片形态不变
3. **降级可观测**——台账记录 `degraded: true`，便于统计 LLM 可用率

---

## 四、合规联动（fail-closed 编排）

### 4.1 编排顺序（不可颠倒）

```
LLM/模板生成 signalNote
   → DKnowC 合规检查（判断 signalNote + headline 组合是否安全）
   → 决定：
        compliant     → kind 保持 signal，保留 signalNote
        non-compliant → kind 降级 fact，删除 signalNote，detail 剥离白话解读
```

**为何合规检查必须在 signalNote 生成之后**：合规检查的对象是「最终要展示给用户的文案」，而不是「生成前的模板」。LLM 产出的 signalNote 才是有违规风险的输入，必须送检。

### 4.2 LLM 输出的结构约定

要求 LLM 以结构化 JSON 输出，便于合规检查精准定位：

```json
{
  "signalNote": "放量突破年线，量能较前日放大明显，留意能否站稳",
  "tone": "neutral",
  "riskFlag": null
}
```

- `signalNote`：一句话白话解读（≤ 40 字，适老化）
- `tone`：语气标签（neutral 中性 / cautious 提示风险 / 自填）
- `riskFlag`：LLM 自检标记（若 LLM 自觉含催促/收益承诺，标 `violation`，前置拦截）

### 4.3 双重护栏

| 层 | 机制 | 作用 |
|----|------|------|
| **LLM 自检** | prompt 强约束 + `riskFlag` 字段 | 从源头降低违规概率 |
| **DKnowC 硬闸** | 合规检查 fail-closed | 兜底拦截 LLM 漏网的违规文案 |

两层叠加，即使 LLM 无视 prompt 约束产出「建议满仓买入」，DKnowC 仍会判 `Unsafe` 并降级为 fact。

---

## 五、Prompt 设计

### 5.1 system prompt（复用 LLMRouter 现有基调）

```
你是铃语应用（股票异动播报）后端。为老年用户生成一句话白话解读（≤40字）。
硬约束：
1. 禁止承诺收益/保本（如「必涨」「稳赚」）
2. 禁止催促性指令（如「立即买入」「满仓」）
3. 禁止对外公开/收费暗示
4. 用大白话，不用专业术语堆砌
仅输出 JSON：{"signalNote":"...","tone":"neutral|cautious","riskFlag":null|"violation"}
```

### 5.2 user payload（传入事实）

```json
{
  "name": "中国巨石",
  "symbol": "600176",
  "direction": "up",
  "pctChg": 9.87,
  "close": 12.34,
  "turnoverRate": 3.2,
  "vol": 185000
}
```

### 5.3 输出示例

| 情形 | LLM 输出 signalNote |
|------|---------------------|
| 放量上涨 9.87% | 放量上攻，换手明显放大，留意能否站稳价位 |
| 缩量上涨 8.5% | 涨幅可观但量能不足，追高需谨慎 |
| 放量下跌 8.2% | 放量回落，短期抛压较重，建议观望 |
| 跌停封死 | 封死跌停，卖压集中，注意后续走势 |

---

## 六、成本与性能控制

| 维度 | 策略 |
|------|------|
| **触发面** | 仅 kind=signal（涨幅 ≥ 8%）触发，fact 卡零 LLM 调用 |
| **超时** | signal_note 3s（主）+ 3s（备选），硬上限 6s |
| **并发** | 单次异动扫描的 signal 卡通常 0-3 个，顺序生成即可 |
| **额度签名** | 每个 signalNote 约 in 200 / out 80 tokens，日均异动几十条，额度消耗极低 |
| **缓存** | 同一 symbol+交易日 已生成的 signalNote 缓存，避免重复调用 |

---

## 七、落地点（代码改动清单）

| # | 文件 | 改动 | 影响 |
|---|------|------|------|
| 1 | `fetch-tushare-data/package.json` | 加入 `llm-router` 本地依赖（或内联复制核心类） | 引入路由层 |
| 2 | `fetch-tushare-data/index.js` | `createAlertItems` 内、合规检查前插入 `generateSignalNote()` 调用 | 新增 LLM 生成步骤 |
| 3 | 同上 | 新增 `generateSignalNote()`：封装 LLMRouter.invoke + 降级链 + 超时 | 核心逻辑 |
| 4 | 同上 | 合规检查输入从「template signalNote」改为「LLM/模板 signalNote」 | 合规编排 |
| 5 | `llm-router/index.js` | `CFG.endpoints/keys` 从占位改为环境变量注入（已支持，仅需填值） | 真实凭据 |
| 6 | `cloudbaserc.json` | 注入 `DEEPSEEK_API_KEY` / `PANGU_API_KEY` 环境变量 | 密钥管理 |

### 7.1 核心函数骨架（generateSignalNote）

```js
/**
 * 为 signal 卡生成白话解读。
 * LLM 可用时动态生成；LLM 不可用/超时/未配凭据时降级回硬编码模板。
 * 返回 { signalNote, source: 'llm'|'template' }
 */
async function generateSignalNote(facts) {
  // 0. 无凭据直接降级
  if (!process.env.DEEPSEEK_API_KEY && !process.env.PANGU_API_KEY) {
    return { signalNote: templateNote(facts.direction), source: 'template' };
  }
  // 1. 尝试 LLMRouter.invoke（signal_note 类型，3s 超时，自带备选降级）
  try {
    const res = await router.invoke({ type: 'signal_note', payload: facts }, t0);
    if (res.ok && res.text) {
      const parsed = safeParse(res.text); // 解析 JSON，失败返回 null
      if (parsed?.signalNote) {
        return { signalNote: parsed.signalNote.slice(0, 40), source: 'llm' };
      }
    }
  } catch (e) {
    console.log('[llm] signalNote generation failed, degraded to template:', e.message);
  }
  // 2. 降级兜底
  return { signalNote: templateNote(facts.direction), source: 'template' };
}

function templateNote(direction) {
  return direction === 'up' ? '留意后续走势' : direction === 'down' ? '注意风险' : '';
}
```

---

## 八、风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| LLM 产出违规文案 | 高 | 双重护栏（prompt 自检 + DKnowC fail-closed），H1 已闭环 |
| LLM 延迟拖慢截断链路 | 中 | 3s 超时 + 降级链，signalNote 不阻塞 headline/detail 入库 |
| LLM 配额耗尽 | 中 | 台账记账 + 降级链兜底，耗尽自动回模板 |
| 信号占比上升导致成本失控 | 低 | 同 symbol+交易日缓存 + 限额开关（V2） |

---

## 九、验收标准

| # | 指标 | 标准 |
|---|------|------|
| 1 | LLM 可用率 | signal 卡 signalNote 的 `source=llm` 占比 ≥ 90%（测试环境） |
| 2 | 合规拦截率 | 100% 违规文案被 DKnowC 降级为 fact（无一条违规 signal 卡入库） |
| 3 | 降级兜底 | LLM 下线时 signal 卡仍显示模板解读，首屏不空白 |
| 4 | 延迟 | signalNote 生成不使 `createAlertItems` 端到端延迟超过 +6s |

---

## 十、待机主决策项

1. **真实 API 凭据**：`DEEPSEEK_API_KEY` / `PANGU_API_KEY` 的获取与注入（当前 endpoint 为 `*.example.com` 占位）
2. **部署形态确认**：V1 内嵌模块（方案 A）是否接受，还是直接上独立云函数（方案 B）
3. **LLM 上线开关**：是否先灰度（仅 10% signal 卡走 LLM）再全量

> 结论：本方案在 H1 合规硬闸之上，将 signalNote 从「两句固定话术」升级为「LLM 动态白话解读」，同时以三级降级链守住「首屏永不空白」。技术路径清晰，唯一阻塞是真实 API 凭据。