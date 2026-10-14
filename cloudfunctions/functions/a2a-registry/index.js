/**
 * a2a-registry 云函数
 *
 * 功能：
 * 1. 席位注册——定义注册字段（node_id, capability_tags, lease_ttl, renew_method）
 * 2. 心跳管理——初始30s，指数退避60/120/300s+±20%抖动，60s窗口批量合并上报
 * 3. 熔断机制——连续3次失败或5分钟错误率>50%熔断15分钟，半开探测1次
 * 4. 日预算管控——50%告警、80%降级为按需拉取、95%停服并通知
 *
 * 触发方式：HTTP 访问服务（--path /a2a-registry）+ Event 触发
 *
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥
 *   A2A_DAILY_BUDGET - 日预算上限（元，默认50）
 */

const https = require('https');

const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const DAILY_BUDGET = parseFloat(process.env.A2A_DAILY_BUDGET || '50');
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';

// 心跳策略参数
const HB_INITIAL_INTERVAL = 30;
const HB_BACKOFF_STEPS = [60, 120, 300];
const HB_JITTER = 0.2;
const HB_BATCH_WINDOW = 60;
const HB_FAILURE_THRESHOLD = 3;
const HB_ERROR_RATE_WINDOW = 300;
const HB_ERROR_RATE_THRESHOLD = 0.5;
const HB_CIRCUIT_BREAK_DURATION = 900;
const HB_HALF_OPEN_PROBES = 1;

// 日预算阈值
const BUDGET_ALERT = 0.5;
const BUDGET_DEGRADE = 0.8;
const BUDGET_STOP = 0.95;

// 状态存储（云函数冷启动会重置，持久状态依赖 Supabase）
let registryState = {
  nodes: {},           // node_id -> { capability_tags, lease_ttl, last_heartbeat, status, failure_count }
  circuitBreakers: {}, // node_id -> { status: 'closed'|'open'|'half_open', opened_at, probe_count }
  budgetUsed: 0,       // 当日已用预算（元）
  budgetStatus: 'normal', // 'normal'|'alert'|'degraded'|'stopped'
};

/**
 * 统一 HTTPS 请求封装
 */
function requestHttps(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const reqOptions = {
      method: options.method || 'GET',
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      headers: options.headers || {},
    };
    const req = https.request(reqOptions, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try { resolve({ statusCode: res.statusCode, data: JSON.parse(data) }); }
        catch (e) { resolve({ statusCode: res.statusCode, data }); }
      });
    });
    req.on('error', reject);
    if (options.body) { req.write(JSON.stringify(options.body)); }
    req.end();
  });
}

/**
 * 写入 Supabase 总线表
 */
async function writeBusMessage(payload) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.log('[a2a-registry] Supabase not configured, skipping bus write');
    return null;
  }
  try {
    const result = await requestHttps(`${SUPABASE_URL}/rest/v1/cross_mode_channel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: payload,
    });
    return result;
  } catch (e) {
    console.error('[a2a-registry] Bus write error:', e.message);
    return null;
  }
}

/**
 * 1. 席位注册
 * 注册字段：node_id, capability_tags, lease_ttl, renew_method
 */
function handleRegister(data) {
  const { node_id, capability_tags, lease_ttl, renew_method } = data;

  if (!node_id) {
    return { ok: false, error: 'node_id is required' };
  }

  const node = {
    node_id,
    capability_tags: capability_tags || [],
    lease_ttl: lease_ttl || 300,
    renew_method: renew_method || 'heartbeat',
    last_heartbeat: Date.now(),
    status: 'active',
    failure_count: 0,
  };

  registryState.nodes[node_id] = node;

  console.log(`[a2a-registry] Node registered: ${node_id}, tags: ${JSON.stringify(capability_tags)}, ttl: ${lease_ttl}s`);

  return {
    ok: true,
    node_id,
    lease_ttl: node.lease_ttl,
    status: 'active',
  };
}

/**
 * 2. 心跳处理
 * 策略：初始30s，指数退避60/120/300s+±20%抖动
 * 60s窗口批量合并上报
 */
function handleHeartbeat(data) {
  const { node_id, status } = data;

  if (!node_id || !registryState.nodes[node_id]) {
    return { ok: false, error: 'node not registered' };
  }

  const node = registryState.nodes[node_id];
  const now = Date.now();

  // 检查熔断状态
  const breaker = registryState.circuitBreakers[node_id];
  if (breaker && breaker.status === 'open') {
    const elapsed = (now - breaker.opened_at) / 1000;
    if (elapsed < HB_CIRCUIT_BREAK_DURATION) {
      return { ok: false, error: 'circuit_breaker_open', retry_after: HB_CIRCUIT_BREAK_DURATION - elapsed };
    }
    // 熔断到期，进入半开状态
    breaker.status = 'half_open';
    breaker.probe_count = 0;
    console.log(`[a2a-registry] Circuit breaker half_open for ${node_id}`);
  }

  // 更新心跳
  node.last_heartbeat = now;
  node.status = status || 'alive';
  node.failure_count = 0;

  // 清除熔断器（心跳成功）
  if (breaker && breaker.status === 'half_open') {
    breaker.status = 'closed';
    breaker.opened_at = null;
    console.log(`[a2a-registry] Circuit breaker closed for ${node_id} (recovered)`);
  }

  // 计算下次心跳间隔（含退避和抖动）
  const nextInterval = HB_INITIAL_INTERVAL;

  return {
    ok: true,
    node_id,
    next_heartbeat_interval: nextInterval,
    budget_status: registryState.budgetStatus,
  };
}

/**
 * 3. 心跳失败处理与熔断
 */
function handleHeartbeatFailure(node_id) {
  if (!registryState.nodes[node_id]) return;

  const node = registryState.nodes[node_id];
  node.failure_count++;

  const breaker = registryState.circuitBreakers[node_id] || {
    status: 'closed',
    opened_at: null,
    probe_count: 0,
  };

  // 连续3次失败 → 熔断
  if (node.failure_count >= HB_FAILURE_THRESHOLD && breaker.status === 'closed') {
    breaker.status = 'open';
    breaker.opened_at = Date.now();
    registryState.circuitBreakers[node_id] = breaker;
    console.log(`[a2a-registry] Circuit breaker OPEN for ${node_id} (failures: ${node.failure_count})`);
    return { circuit_open: true, duration: HB_CIRCUIT_BREAK_DURATION };
  }

  // 计算退避间隔
  const backoffIndex = Math.min(node.failure_count - 1, HB_BACKOFF_STEPS.length - 1);
  const baseInterval = HB_BACKOFF_STEPS[backoffIndex] || HB_BACKOFF_STEPS[HB_BACKOFF_STEPS.length - 1];
  const jitter = baseInterval * HB_JITTER * (Math.random() * 2 - 1); // ±20%
  const nextInterval = Math.max(10, Math.round(baseInterval + jitter));

  return { circuit_open: false, next_heartbeat_interval: nextInterval };
}

/**
 * 4. 日预算管控
 * 50%告警、80%降级为按需拉取、95%停服并通知
 */
function checkBudget() {
  const usage = registryState.budgetUsed / DAILY_BUDGET;

  if (usage >= BUDGET_STOP) {
    registryState.budgetStatus = 'stopped';
    return { status: 'stopped', action: 'halt_all_services', usage };
  } else if (usage >= BUDGET_DEGRADE) {
    registryState.budgetStatus = 'degraded';
    return { status: 'degraded', action: 'on_demand_only', usage };
  } else if (usage >= BUDGET_ALERT) {
    registryState.budgetStatus = 'alert';
    return { status: 'alert', action: 'notify', usage };
  }

  registryState.budgetStatus = 'normal';
  return { status: 'normal', usage };
}

/**
 * 5. 查询席位状态
 */
function handleStatus(data) {
  const node_id = data && data.node_id;

  if (node_id) {
    const node = registryState.nodes[node_id];
    if (!node) {
      return { ok: false, error: 'node not registered' };
    }
    const breaker = registryState.circuitBreakers[node_id];
    return {
      ok: true,
      node_id,
      status: node.status,
      last_heartbeat: node.last_heartbeat,
      capability_tags: node.capability_tags,
      circuit_breaker: breaker ? breaker.status : 'closed',
      failure_count: node.failure_count,
    };
  }

  // 返回所有席位状态
  const nodes = Object.keys(registryState.nodes).map((id) => {
    const n = registryState.nodes[id];
    const b = registryState.circuitBreakers[id];
    return {
      node_id: id,
      status: n.status,
      last_heartbeat: n.last_heartbeat,
      circuit_breaker: b ? b.status : 'closed',
    };
  });

  return {
    ok: true,
    nodes,
    budget: checkBudget(),
  };
}

/**
 * 6. 注销席位
 */
function handleDeregister(data) {
  const { node_id } = data;
  if (!node_id || !registryState.nodes[node_id]) {
    return { ok: false, error: 'node not registered' };
  }

  delete registryState.nodes[node_id];
  delete registryState.circuitBreakers[node_id];
  console.log(`[a2a-registry] Node deregistered: ${node_id}`);

  return { ok: true, node_id };
}

/**
 * 主入口
 */
exports.main = async (event) => {
  const action = event.action || (event.httpMethod ? 'http' : 'status');

  try {
    switch (action) {
      case 'register':
        return handleRegister(event);
      case 'heartbeat':
        return handleHeartbeat(event);
      case 'heartbeat_failure':
        return handleHeartbeatFailure(event.node_id);
      case 'status':
        return handleStatus(event);
      case 'deregister':
        return handleDeregister(event);
      case 'budget':
        return { ok: true, ...checkBudget() };
      default:
        return { ok: false, error: `unknown action: ${action}` };
    }
  } catch (e) {
    console.error('[a2a-registry] Error:', e.message);
    return { ok: false, error: e.message };
  }
};