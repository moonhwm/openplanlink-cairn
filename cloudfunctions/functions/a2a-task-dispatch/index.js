/**
 * a2a-task-dispatch 云函数
 *
 * 功能：
 * 1. 任务分发——消息 schema（task_id, idempotency_key, status, retry_count, timeout）
 * 2. 状态机——queued/running/succeeded/failed/cancelled
 * 3. 去重——按 idempotency_key 去重，同 key 返回原 task_id
 * 4. 终态确认——任务进入终态后写入 task_receipt，发送方回读确认
 *
 * 状态流转规则：
 *   queued → running（领取）
 *   running → succeeded/failed（完成/失败）
 *   running → cancelled（取消）
 *   failed → queued（重试，retry_count < MAX_RETRIES）
 *
 * 触发方式：HTTP 访问服务（--path /a2a-task）+ Event 触发
 *
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥
 */

const https = require('https');
const crypto = require('crypto');

const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';

// 任务参数
const MAX_RETRIES = 3;
const TASK_TIMEOUT = 120000; // 120s
const DEDUP_TTL = 3600; // 1小时去重窗口

// 状态存储（云函数冷启动会重置，持久状态依赖 Supabase）
let taskStore = {};      // task_id -> task object
let idempotencyIndex = {}; // idempotency_key -> { task_id, expires_at }

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
 * 生成 task_id（UUID v4 简化版）
 */
function generateTaskId() {
  return crypto.randomUUID();
}

/**
 * 生成 idempotency_key（md5(payload+timestamp)[:16]）
 */
function generateIdempotencyKey(payload) {
  const ts = Date.now();
  const content = JSON.stringify(payload) + ts;
  return crypto.createHash('md5').update(content, 'utf8').digest('hex').substring(0, 16);
}

/**
 * 1. 创建任务
 * 消息 schema: task_id, idempotency_key, status, retry_count, timeout, payload
 */
function handleCreate(data) {
  const { payload, idempotency_key } = data;

  // 去重检查：同 idempotency_key 返回原 task_id
  if (idempotency_key && idempotencyIndex[idempotency_key]) {
    const existing = idempotencyIndex[idempotency_key];
    if (Date.now() < existing.expires_at) {
      console.log(`[a2a-task] Dedup hit: key=${idempotency_key}, task_id=${existing.task_id}`);
      return {
        ok: true,
        task_id: existing.task_id,
        status: taskStore[existing.task_id]?.status || 'queued',
        dedup: true,
      };
    }
    // 过期清理
    delete idempotencyIndex[idempotency_key];
  }

  const task_id = generateTaskId();
  const key = idempotency_key || generateIdempotencyKey(payload);

  const task = {
    task_id,
    idempotency_key: key,
    status: 'queued',
    payload: payload || {},
    retry_count: 0,
    timeout: TASK_TIMEOUT,
    created_at: Date.now(),
    updated_at: Date.now(),
  };

  taskStore[task_id] = task;
  idempotencyIndex[key] = {
    task_id,
    expires_at: Date.now() + DEDUP_TTL * 1000,
  };

  console.log(`[a2a-task] Task created: ${task_id}, key=${key}, status=queued`);

  return {
    ok: true,
    task_id,
    idempotency_key: key,
    status: 'queued',
  };
}

/**
 * 2. 领取任务（queued → running）
 */
function handleClaim(data) {
  const { task_id, claimed_by } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  if (task.status !== 'queued') {
    return { ok: false, error: `task status is ${task.status}, not queued` };
  }

  task.status = 'running';
  task.claimed_by = claimed_by || 'unknown';
  task.updated_at = Date.now();

  console.log(`[a2a-task] Task claimed: ${task_id}, by=${task.claimed_by}`);

  return {
    ok: true,
    task_id,
    status: 'running',
    payload: task.payload,
    timeout: task.timeout,
  };
}

/**
 * 3. 完成任务（running → succeeded）
 */
function handleComplete(data) {
  const { task_id, result } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  if (task.status !== 'running') {
    return { ok: false, error: `task status is ${task.status}, not running` };
  }

  task.status = 'succeeded';
  task.result = result;
  task.updated_at = Date.now();

  console.log(`[a2a-task] Task succeeded: ${task_id}`);

  return {
    ok: true,
    task_id,
    status: 'succeeded',
  };
}

/**
 * 4. 任务失败（running → failed，可重试则 → queued）
 */
function handleFail(data) {
  const { task_id, error } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  if (task.status !== 'running') {
    return { ok: false, error: `task status is ${task.status}, not running` };
  }

  task.retry_count++;
  task.last_error = error;
  task.updated_at = Date.now();

  if (task.retry_count < MAX_RETRIES) {
    task.status = 'queued'; // 重试
    console.log(`[a2a-task] Task retry: ${task_id}, retry_count=${task.retry_count}/${MAX_RETRIES}`);
    return {
      ok: true,
      task_id,
      status: 'queued',
      retry_count: task.retry_count,
      will_retry: true,
    };
  }

  task.status = 'failed'; // 终态
  console.log(`[a2a-task] Task failed (terminal): ${task_id}, retries exhausted`);
  return {
    ok: true,
    task_id,
    status: 'failed',
    retry_count: task.retry_count,
    will_retry: false,
  };
}

/**
 * 5. 取消任务（running → cancelled）
 */
function handleCancel(data) {
  const { task_id } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  if (task.status === 'succeeded' || task.status === 'failed' || task.status === 'cancelled') {
    return { ok: false, error: `task already in terminal state: ${task.status}` };
  }

  task.status = 'cancelled';
  task.updated_at = Date.now();

  console.log(`[a2a-task] Task cancelled: ${task_id}`);

  return {
    ok: true,
    task_id,
    status: 'cancelled',
  };
}

/**
 * 6. 查询任务状态
 */
function handleQuery(data) {
  const { task_id } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  return {
    ok: true,
    task_id,
    status: task.status,
    retry_count: task.retry_count,
    created_at: task.created_at,
    updated_at: task.updated_at,
    result: task.result,
    last_error: task.last_error,
  };
}

/**
 * 7. 终态确认（回读 task_receipt）
 */
function handleReceipt(data) {
  const { task_id } = data;

  if (!task_id || !taskStore[task_id]) {
    return { ok: false, error: 'task not found' };
  }

  const task = taskStore[task_id];
  const isTerminal = ['succeeded', 'failed', 'cancelled'].includes(task.status);

  if (!isTerminal) {
    return { ok: false, error: 'task not in terminal state' };
  }

  return {
    ok: true,
    task_id,
    status: task.status,
    confirmed: true,
    result: task.result,
    last_error: task.last_error,
  };
}

/**
 * 主入口
 */
exports.main = async (event) => {
  const action = event.action || 'query';

  try {
    switch (action) {
      case 'create':
        return handleCreate(event);
      case 'claim':
        return handleClaim(event);
      case 'complete':
        return handleComplete(event);
      case 'fail':
        return handleFail(event);
      case 'cancel':
        return handleCancel(event);
      case 'query':
        return handleQuery(event);
      case 'receipt':
        return handleReceipt(event);
      default:
        return { ok: false, error: `unknown action: ${action}` };
    }
  } catch (e) {
    console.error('[a2a-task] Error:', e.message);
    return { ok: false, error: e.message };
  }
};