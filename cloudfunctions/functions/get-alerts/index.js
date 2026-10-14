/**
 * get-alerts 云函数（Event 函数模式）
 *
 * 功能：从 CloudBase 存储读取最新异动 JSON 文件，返回 AlertFeed 格式。
 * 轻量级只读端点——不触发广播、不发送Push，专供客户端轮询。
 *
 * 数据源：CloudBase 存储中的 alerts.json 文件
 *
 * 返回格式（与 AlertItem.ets 的 AlertFeed 契约完全一致）：
 *   {
 *     items: AlertItem[],
 *     serverTs: number
 *   }
 *
 * 触发方式：Event 函数 + CloudBase HTTP 访问服务（--path /alerts）
 *   URL: https://{envId}.app.tcloudbase.com/alerts
 */

const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';
const ALERTS_FILE_ID = 'cloud://a2a-commonwealth-d2eepjr928e9c4d.6132-a2a-commonwealth-d2eepjr928e9c4d-1475054847/alerts/alerts.json';

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
 * 从 CloudBase 存储获取最新异动 JSON
 */
async function getLatestAlerts(limit = 20) {
  try {
    const app = getCloudbaseApp();

    // 下载 alerts.json 文件
    const result = await app.downloadFile({
      fileID: ALERTS_FILE_ID,
    });

    if (result && result.fileContent) {
      const text = result.fileContent.toString('utf-8');
      const data = JSON.parse(text);
      if (data && data.items && Array.isArray(data.items)) {
        // 按 ts 降序排序，取最新的 limit 条
        const sorted = data.items.sort((a, b) => b.ts - a.ts);
        return sorted.slice(0, limit);
      }
    }

    return [];
  } catch (e) {
    console.error('get-alerts: failed to read alerts.json:', e.message);
    return [];
  }
}

/**
 * Event 函数入口
 * CloudBase HTTP 访问服务会将 HTTP GET 请求的 query 参数传入 event
 */
exports.main = async (event, context) => {
  const limit = Math.min(
    parseInt(event?.query?.limit || event?.limit || '20', 10),
    100
  );

  try {
    const items = await getLatestAlerts(limit);
    return {
      items,
      serverTs: Math.floor(Date.now() / 1000),
    };
  } catch (e) {
    console.error('get-alerts error:', e.message);
    return {
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
    };
  }
};
