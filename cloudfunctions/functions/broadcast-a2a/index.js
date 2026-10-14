/**
 * broadcast-a2a 云函数
 *
 * 功能：
 * 1. 从 CloudBase 存储读取最新异动条目（alerts.json）
 * 2. 通过 A2A 总线广播异动消息（Supabase 实时推送）
 * 3. 通过 CloudBase 推送服务向鸿蒙设备发送 Push 通知
 * 4. 支持 HTTP 触发（Web 函数模式，scf_bootstrap）和 Event 触发
 *
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL（可选）
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥（可选）
 *   PUSH_BUNDLE_NAME - 鸿蒙应用包名
 *   PORT / SCF_RUNTIME_PORT - Web 函数模式端口（自动注入）
 */

const http = require('http');
const https = require('https');
const config = require('./config');
const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const PUSH_BUNDLE_NAME = process.env.PUSH_BUNDLE_NAME || 'com.yehang.stockpulse';
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';
const ALERTS_FILE_ID = 'cloud://a2a-commonwealth-d2eepjr928e9c4d.6132-a2a-commonwealth-d2eepjr928e9c4d-1475054847/alerts/alerts.json';
// kimi 通道总开关（默认 false，2026-09-24 机主令彻底停用 kimi 调用）
const KIMI_ENABLED = config.KIMI_ENABLED;

/**
 * 统一 HTTPS 请求封装（替代实验性 fetch）
 */
function requestHttps(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const reqOptions = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {},
    };
    const req = https.request(reqOptions, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`JSON parse failed: ${e.message}`)); }
      });
    });
    req.on('error', reject);
    req.setTimeout(options.timeout || 15000, () => {
      req.destroy(new Error('Request timeout'));
    });
    if (options.body) req.write(options.body);
    req.end();
  });
}

// CloudBase SDK 单例
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({ env: ENV_ID });
  }
  return _cloudbaseApp;
}

/**
 * 从 CloudBase 存储获取最新异动
 */
async function getLatestAlerts(limit = 20) {
  try {
    const app = getCloudbaseApp();

    const result = await app.downloadFile({ fileID: ALERTS_FILE_ID });

    if (result && result.fileContent) {
      const text = result.fileContent.toString('utf-8');
      const data = JSON.parse(text);
      if (data && data.items && Array.isArray(data.items)) {
        const sorted = data.items.sort((a, b) => b.ts - a.ts);
        return sorted.slice(0, limit);
      }
    }

    return [];
  } catch (e) {
    console.error('broadcast-a2a: failed to read alerts.json:', e.message);
    return [];
  }
}

/**
 * 通过 Supabase Realtime 广播异动消息
 */
async function broadcastToSupabase(alerts) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.log('Supabase not configured, skipping broadcast');
    return;
  }

  try {
    const data = await requestHttps(`${SUPABASE_URL}/rest/v1/cross_mode_channel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        from_mode: 'yan-jian-codearts-glm52',
        to_mode: 'all',
        kind: 'alert-feed',
        payload_md: JSON.stringify({
          items: alerts,
          serverTs: Math.floor(Date.now() / 1000),
          source: 'broadcast-a2a',
        }),
        status: 'new',
        ts: new Date().toISOString(),
      }),
    });

    console.log(`Broadcast ${alerts.length} alerts to Supabase`);
  } catch (e) {
    console.error('Supabase broadcast error:', e.message);
  }
}

/**
 * 通过华为 Push Kit REST API 发送 Push 通知
 *
 * 华为 Push Kit 服务端推送流程：
 * 1. 获取 OAuth 2.0 Bearer Token（使用 AGC projectId + JWT）
 * 2. 调用 POST https://push-api.cloud.huawei.com/v3/{projectId}/messages:send
 *
 * 环境变量：
 *   HUAWEI_PUSH_PROJECT_ID - AGC projectId（必需）
 *   HUAWEI_PUSH_CLIENT_ID - AGC clientId（必需，用于获取OAuth Token）
 *   HUAWEI_PUSH_CLIENT_SECRET - AGC clientSecret（必需，用于获取OAuth Token）
 *   HUAWEI_PUSH_TOKEN - 设备Push Token（调试用，生产环境应从数据库获取）
 *
 * 当环境变量未配置时，Push功能自动跳过（不报错），等AGC配置完成后即可使用。
 */
async function sendPushNotification(alert) {
  const PROJECT_ID = process.env.HUAWEI_PUSH_PROJECT_ID || '';
  const CLIENT_ID = process.env.HUAWEI_PUSH_CLIENT_ID || '';
  const CLIENT_SECRET = process.env.HUAWEI_PUSH_CLIENT_SECRET || '';

  if (!PROJECT_ID || !CLIENT_ID || !CLIENT_SECRET) {
    console.log('Push Kit not configured (need HUAWEI_PUSH_PROJECT_ID/CLIENT_ID/CLIENT_SECRET), skipping push');
    return;
  }

  // 从 CloudBase 数据库获取所有活跃的 Push Token
  let deviceTokens = [];
  try {
    const app = getCloudbaseApp();
    const db = app.database();
    const result = await db.collection('push_tokens').where({ active: true }).get();
    deviceTokens = (result.data || []).map(item => item.token);
  } catch (e) {
    console.log('Failed to fetch device tokens from DB, falling back to env var');
    // Fallback：调试用环境变量中的单个 Token
    const envToken = process.env.HUAWEI_PUSH_TOKEN || '';
    if (envToken) deviceTokens = [envToken];
  }

  if (deviceTokens.length === 0) {
    console.log('No device push tokens available, skipping push');
    return;
  }

  try {
    // 步骤1：获取 OAuth 2.0 Bearer Token
    const tokenData = await requestHttps('https://oauth-login.cloud.huawei.com/oauth2/v3/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
      }).toString(),
      timeout: 10000,
    });

    const accessToken = tokenData.access_token;
    if (!accessToken) {
      console.error('Push: No access_token in OAuth response');
      return;
    }

    // 步骤2：向所有设备批量发送 Push 消息
    const pushUrl = `https://push-api.cloud.huawei.com/v3/${PROJECT_ID}/messages:send`;
    const message = {
      notification: {
        title: alert.headline,
        body: alert.detail || '',
      },
      android: {
        notification: {
          channel_id: 'alert_channel',
          sound: 'default',
          click_action: {
            type: 1,
            intent: `${PUSH_BUNDLE_NAME}.EntryAbility`,
          },
        },
      },
      data: JSON.stringify({
        alertId: alert.alertId,
        symbol: alert.symbol,
        kind: alert.kind || 'fact',
        audioUrl: alert.audioUrl || '',
      }),
      token: deviceTokens,
    };

    const pushResult = await requestHttps(pushUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ message }),
      timeout: 10000,
    });

    console.log(`Push sent to ${deviceTokens.length} devices:`, JSON.stringify(pushResult).substring(0, 200));
  } catch (e) {
    console.error('Push error:', e.message);
  }
}

/**
 * 核心处理逻辑——获取异动、广播、推送
 */
async function handleBroadcast(limit = 20) {
  const alerts = await getLatestAlerts(limit);

  if (alerts.length === 0) {
    return {
      success: true,
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
      message: 'No alerts found',
    };
  }

  await broadcastToSupabase(alerts);

  let pushCount = 0;
  for (const alert of alerts) {
    if (alert.kind === 'signal' || alert.direction !== 'flat') {
      await sendPushNotification(alert);
      pushCount++;
    }
  }

  return {
    success: true,
    items: alerts,
    serverTs: Math.floor(Date.now() / 1000),
    count: alerts.length,
    pushCount,
  };
}

/**
 * Event 触发入口
 */
exports.main = async (event, context) => {
  console.log('broadcast-a2a Event invoked');
  try {
    return await handleBroadcast(20);
  } catch (e) {
    console.error('broadcast-a2a error:', e.message);
    return { success: false, error: e.message };
  }
};

/**
 * Web 函数模式——HTTP 服务器（scf_bootstrap 启动）
 * 当 PORT 环境变量存在时自动启动
 */
const port = process.env.PORT || process.env.SCF_RUNTIME_PORT || 9000;

if (process.env.PORT || process.env.SCF_RUNTIME_PORT) {
  const server = http.createServer(async (req, res) => {
    console.log(`HTTP ${req.method} ${req.url}`);

    // CORS headers——限制为已知来源而非通配
    const allowedOrigins = ['https://a2a-commonwealth-d2eepjr928e9c4d.app.tcloudbase.com'];
    const origin = req.headers.origin || '';
    if (allowedOrigins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
    }
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-API-Key');

    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      res.end();
      return;
    }

    // API Key鉴权——GET /healthz 除外（健康检查不需要鉴权）
    // fail-closed：未配置 BROADCAST_API_KEY 时默认拒绝，防止无鉴权广播
    const url = new URL(req.url, `http://localhost:${port}`);
    if (url.pathname !== '/healthz') {
      const apiKey = req.headers['x-api-key'] || url.searchParams.get('apiKey') || '';
      const expectedKey = process.env.BROADCAST_API_KEY || '';
      if (!expectedKey) {
        // fail-closed：未配置 Key 时拒绝访问，防止无鉴权广播端点暴露
        console.error('[SECURITY] BROADCAST_API_KEY not configured, rejecting request (fail-closed)');
        res.writeHead(503, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: 'Service unavailable: broadcast API key not configured' }));
        return;
      } else if (apiKey !== expectedKey) {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: 'Unauthorized: invalid API key' }));
        return;
      }
    }

    const limit = parseInt(url.searchParams.get('limit') || '20', 10);

    try {
      if (url.pathname === '/healthz') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok' }));
        return;
      }
      const result = await handleBroadcast(limit);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
    } catch (e) {
      console.error('HTTP handler error:', e.message);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: e.message }));
    }
  });

  server.listen(port, () => {
    console.log(`broadcast-a2a HTTP server listening on port ${port}`);
  });
}