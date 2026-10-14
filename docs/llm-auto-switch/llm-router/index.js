/**
 * LLM Auto-Switch Router —— 铃语应用双模型专家团自动切换层
 *
 * 目标：在 OpenPangu-2.0-pro ↔ deepseek-v4-pro-0813 之间自动切换，
 *       以最大吞吐在 2026-09-23 22:00 前烧完 10,000,000 token。
 *
 * 组件：
 *   LLMRouter       统一入口：调度 + 记账
 *   RuleEngine      决策矩阵：任务类型/负载/额度/时间窗口/失败重试
 *   PanguAdapter    OpenPangu-2.0-pro 适配器
 *   DeepSeekAdapter deepseek-v4-pro-0813 适配器
 *   BurnLedger      燃烧台账（append-only，md5[:16] 锚定）
 *
 * 用法（Node.js >= 18，可选部署为 CloudBase 云函数）：
 *   node llm-router/index.js --burn   # 启动高性能燃烧引擎
 *   node llm-router/index.js --route '{"type":"signal_note","payload":"..."}'
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');

// ─────────────────────────────────────────────────────────────
// 0. 配置（环境变量注入，凭据不落盘）
// ─────────────────────────────────────────────────────────────
const CFG = {
  targetTokens: Number(process.env.BURN_TARGET_TOKENS || 10_000_000), // 1000 万
  deadline: process.env.BURN_DEADLINE_ISO || '2026-09-23T22:00:00+08:00', // 22:00 截止
  quota: {
    pangu: Number(process.env.PANGU_QUOTA || 5_000_000),   // OpenPangu 预算
    deepseek: Number(process.env.DEEPSEEK_QUOTA || 5_000_000), // DeepSeek 预算
  },
  endpoints: {
    pangu: process.env.PANGU_ENDPOINT || 'https://pangu.example.com/v1/chat/completions',
    deepseek: process.env.DEEPSEEK_ENDPOINT || 'https://inferhub.example.com/v1/chat/completions',
  },
  keys: {
    pangu: process.env.PANGU_API_KEY || '',
    deepseek: process.env.DEEPSEEK_API_KEY || '',
  },
  models: {
    pangu: process.env.PANGU_MODEL || 'OpenPangu-2.0-pro',
    deepseek: process.env.DEEPSEEK_MODEL || 'deepseek-v4-pro-0813',
  },
  // 时间窗口硬闸（秒）
  tCriticalSec: Number(process.env.BURN_T_CRITICAL_SEC || 1800), // 剩 30min 倒逼
  // 降级超时（秒）
  timeout: {
    signal_note: 3,
    compliance: 5,
    polish: 5,
    code_review: 8,
    legal: 8,
    architecture: 10,
  },
};

// ─────────────────────────────────────────────────────────────
// 1. BurnLedger —— 燃烧台账
// ─────────────────────────────────────────────────────────────
class BurnLedger {
  constructor(file) {
    this.file = file;
    this.dir = path.dirname(file);
    if (!fs.existsSync(this.dir)) fs.mkdirSync(this.dir, { recursive: true });
    this.used = { pangu: 0, deepseek: 0 };
    this.count = 0;
  }

  record(model, taskType, tokensIn, tokensOut) {
    this.used[model] += (tokensIn + tokensOut);
    this.count += 1;
    const entry = {
      ts: new Date().toISOString(),
      model,
      taskType,
      tokensIn,
      tokensOut,
      total: tokensIn + tokensOut,
      cumUsed: this.used,
      anchor: crypto.createHash('md5').update(`${Date.now()}:${model}:${this.count}`).digest('hex').slice(0, 16),
    };
    fs.appendFileSync(this.file, JSON.stringify(entry) + '\n');
    return entry;
  }

  progress(t0) {
    const used = this.used.pangu + this.used.deepseek;
    const elapsedSec = (Date.now() - t0) / 1000;
    const rate = elapsedSec > 0 ? Math.round(used / elapsedSec) : 0;
    const deadlineMs = new Date(CFG.deadline).getTime();
    const remainSec = Math.max(0, (deadlineMs - Date.now()) / 1000);
    const remain = Math.max(0, CFG.targetTokens - used);
    return { used, remain, rate, remainSec, remainRate: remain / Math.max(1, remainSec) };
  }
}

// ─────────────────────────────────────────────────────────────
// 2. Adapters —— 双模型适配器
// ─────────────────────────────────────────────────────────────
function httpPostJson(endpoint, apiKey, body, timeoutSec) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const u = new URL(endpoint);
    const req = https.request({
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      timeout: timeoutSec * 1000,
    }, (res) => {
      let raw = '';
      res.on('data', (c) => (raw += c));
      res.on('end', () => {
        try {
          resolve(JSON.parse(raw));
        } catch (e) {
          reject(new Error(`bad json: ${raw.slice(0, 120)}`));
        }
      });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function buildMessages(task) {
  return [
    { role: 'system', content: '你是铃语应用（股票异动播报）后端，输出白话、适老化、合规（不承诺收益/不催促指令/不对外收费）的中文内容。' },
    { role: 'user', content: JSON.stringify(task.payload) },
  ];
}

const Adapter = {
  async pangu(task, timeoutSec) {
    const r = await httpPostJson(CFG.endpoints.pangu, CFG.keys.pangu, {
      model: CFG.models.pangu,
      messages: buildMessages(task),
    }, timeoutSec);
    return {
      model: 'pangu',
      text: r?.choices?.[0]?.message?.content || '',
      usage: r?.usage || { prompt_tokens: 0, completion_tokens: 0 },
    };
  },
  async deepseek(task, timeoutSec) {
    const r = await httpPostJson(CFG.endpoints.deepseek, CFG.keys.deepseek, {
      model: CFG.models.deepseek,
      messages: buildMessages(task),
    }, timeoutSec);
    return {
      model: 'deepseek',
      text: r?.choices?.[0]?.message?.content || '',
      usage: r?.usage || { prompt_tokens: 0, completion_tokens: 0 },
    };
  },
};

// ─────────────────────────────────────────────────────────────
// 3. RuleEngine —— 决策矩阵
// ─────────────────────────────────────────────────────────────
const TYPE_REROUTE = {
  signal_note: 'deepseek',
  compliance: 'deepseek',
  polish: 'pangu',
  code_review: 'pangu',
  legal: 'pangu',
  architecture: 'deepseek',
};

class RuleEngine {
  /**
   * 返回 'pangu' | 'deepseek'
   * 优先级：时间倒逼 > 额度耗尽 > 任务类型路由
   */
  decide(task, ledger, t0) {
    const model = task.preferred || TYPE_REROUTE[task.type] || 'deepseek';
    const other = model === 'pangu' ? 'deepseek' : 'pangu';

    // 1. 时间窗口倒逼：剩时 < tCriticalSec → 切吞吐更高者
    const deadlineMs = new Date(CFG.deadline).getTime();
    const remainSec = (deadlineMs - Date.now()) / 1000;
    if (remainSec < CFG.tCriticalSec) {
      return this._fastest(ledger);
    }
    // 2. 额度耗尽：切备选
    if (ledger.used[model] >= CFG.quota[model]) {
      return other;
    }
    // 3. 任务类型路由：默认按能力矩阵
    return model;
  }

  _fastest(ledger) {
    // 吞吐 = 已用量；剩余额度多者为"可再烧"者
    const pR = CFG.quota.pangu - ledger.used.pangu;
    const dR = CFG.quota.deepseek - ledger.used.deepseek;
    return dR >= pR ? 'deepseek' : 'pangu';
  }
}

// ─────────────────────────────────────────────────────────────
// 4. LLMRouter —— 统一入口
// ─────────────────────────────────────────────────────────────
class LLMRouter {
  constructor(ledger, engine) {
    this.ledger = ledger;
    this.engine = engine;
  }

  async invoke(task, t0) {
    const model = this.engine.decide(task, this.ledger, t0);
    const timeoutSec = CFG.timeout[task.type] || 8;
    try {
      const res = await Adapter[model](task, timeoutSec);
      this.ledger.record(
        model,
        task.type,
        res.usage.prompt_tokens || 0,
        res.usage.completion_tokens || 0
      );
      return { ok: true, model, text: res.text };
    } catch (e) {
      // 失败降级：切备选重试一次
      const other = model === 'pangu' ? 'deepseek' : 'pangu';
      try {
        const res2 = await Adapter[other](task, timeoutSec + 3);
        this.ledger.record(other, task.type, res2.usage.prompt_tokens || 0, res2.usage.completion_tokens || 0);
        return { ok: true, model: other, degraded: true, text: res2.text };
      } catch (e2) {
        return { ok: false, model, error: String(e2?.message || e2) };
      }
    }
  }
}

// ─────────────────────────────────────────────────────────────
// 5. 燃烧引擎 —— --burn 高性能点火
// ─────────────────────────────────────────────────────────────
function makeTask(i) {
  // 高价值任务循环：代码审查 + 信号解读 + 方案推演
  const pool = ['code_review', 'signal_note', 'architecture', 'polish', 'compliance'];
  const type = pool[i % pool.length];
  return {
    type,
    preferred: TYPE_REROUTE[type],
    payload: {
      batchId: i,
      hint: `批量燃烧任务 #${i}，类型 ${type}，产出可沉淀价值，禁止空转灌水。`,
    },
  };
}

async function burn(router, ledger, t0, { total = 200 } = {}) {
  const CONCURRENCY = Number(process.env.BURN_CONCURRENCY || 8);
  let cursor = 0;
  let success = 0;

  async function worker() {
    while (cursor < total) {
      const i = cursor++;
      const task = makeTask(i);
      const r = await router.invoke(task, t0);
      if (r.ok) success += 1;
      const p = ledger.progress(t0);
      if (p.used >= CFG.targetTokens) break;
    }
  }

  const workers = Array.from({ length: CONCURRENCY }, () => worker());
  await Promise.all(workers);
  const p = ledger.progress(t0);
  console.log(`[burn] done: success=${success}, used=${p.used}, rate=${p.rate} tok/s, remain=${p.remain}`);
  return p;
}

// ─────────────────────────────────────────────────────────────
// 6. CLI
// ─────────────────────────────────────────────────────────────
function main() {
  const ledgerFile = process.env.BURN_LEDGER_FILE || path.join(__dirname, 'burn-ledger.jsonl');
  const ledger = new BurnLedger(ledgerFile);
  const engine = new RuleEngine();
  const router = new LLMRouter(ledger, engine);
  const t0 = Date.now();

  const arg = process.argv[2];
  if (arg === '--burn') {
    console.log(`[burn] 点火 all-in，目标 ${CFG.targetTokens} tokens，截止 ${CFG.deadline}`);
    burn(router, ledger, t0, { total: Number(process.env.BURN_TASKS || 200) })
      .then((p) => {
        console.log(`[burn] 最终台账：${JSON.stringify(p)}`);
      })
      .catch((e) => console.error('[burn] error:', e));
  } else if (arg === '--route') {
    const task = JSON.parse(process.argv[3] || '{}');
    router.invoke(task, t0).then((r) => console.log('[route]', JSON.stringify(r)));
  } else if (arg === '--status') {
    console.log('[status]', JSON.stringify(ledger.progress(t0)));
  } else {
    console.log('用法: node index.js --burn | --route "<json>" | --status');
  }
}

if (require.main === module) main();

module.exports = { LLMRouter, RuleEngine, BurnLedger, Adapter, CFG, TYPE_REROUTE };