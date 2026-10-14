/**
 * push-token-register 云函数
 *
 * 功能：
 * 1. 接收端侧 PushService 上报的 Push Token
 * 2. 存储到 CloudBase 数据库（push_tokens 集合）
 * 3. 支持 token 过期更新与设备去重
 *
 * 端侧调用：
 *   POST /api/push/register
 *   Body: { token: string, bundleName: string }
 *
 * 环境变量：无额外配置，使用 CloudBase 默认环境
 */

const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';

// CloudBase SDK 单例
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({ env: ENV_ID });
  }
  return _cloudbaseApp;
}

// 合法 bundleName 白名单——防止恶意注册垃圾 token
const ALLOWED_BUNDLE_NAMES = ['com.yehang.stockpulse'];

/**
 * 注册或更新 Push Token
 */
async function registerToken(token, bundleName) {
  // 鉴权：bundleName 必须在白名单中
  if (!ALLOWED_BUNDLE_NAMES.includes(bundleName)) {
    console.error(`[SECURITY] Rejected token registration from unknown bundle: ${bundleName}`);
    return { success: false, error: 'Unauthorized: unknown bundle name' };
  }

  const app = getCloudbaseApp();
  const db = app.database();

  const collection = db.collection('push_tokens');

  // 查询是否已存在相同 token
  const existing = await collection.where({ token }).get();

  if (existing.data && existing.data.length > 0) {
    // Token 已存在，更新最后上报时间
    const docId = existing.data[0]._id;
    await collection.doc(docId).update({
      lastReportTs: Date.now(),
      updatedAt: new Date().toISOString(),
    });
    console.log(`Token updated: ${token.substring(0, 20)}... (docId: ${docId})`);
    return { success: true, action: 'updated', docId };
  }

  // 新 Token，插入记录
  const result = await collection.add({
    token,
    bundleName,
    createdAt: new Date().toISOString(),
    lastReportTs: Date.now(),
    active: true,
  });
  console.log(`Token registered: ${token.substring(0, 20)}... (docId: ${result.id})`);
  return { success: true, action: 'created', docId: result.id };
}

/**
 * 获取所有活跃的 Push Token 列表
 * 供 broadcast-a2a 云函数调用
 */
async function getActiveTokens() {
  const app = getCloudbaseApp();
  const db = app.database();

  const collection = db.collection('push_tokens');
  const result = await collection.where({ active: true }).get();

  return (result.data || []).map(item => item.token);
}

/**
 * 云函数入口
 * 支持 action 参数路由：action=getActiveTokens 时返回活跃 token 列表（供其他云函数 callFunction 调用）
 */
exports.main = async (event, context) => {
  console.log('push-token-register invoked:', JSON.stringify(event));

  // action 路由：供其他云函数通过 callFunction 获取活跃 token 列表
  if (event?.action === 'getActiveTokens') {
    try {
      const tokens = await getActiveTokens();
      return { success: true, tokens };
    } catch (e) {
      console.error('getActiveTokens error:', e.message);
      return { success: false, error: e.message, tokens: [] };
    }
  }

  const { token, bundleName } = event;

  if (!token) {
    return { success: false, error: 'token is required' };
  }

  if (!bundleName) {
    return { success: false, error: 'bundleName is required' };
  }

  try {
    const result = await registerToken(token, bundleName);
    return result;
  } catch (e) {
    console.error('push-token-register error:', e.message);
    return { success: false, error: e.message };
  }
};