// 使用 @cloudbase/manager-node 创建集合
// manager-node 在云函数环境中需要显式凭证（secretId/secretKey）
// 但在Event Function中可以通过 cloudbase context 获取临时凭证

const cloudbase = require('@cloudbase/node-sdk');

// CloudBase SDK 单例
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const envId = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';
    _cloudbaseApp = cloudbase.init({ env: envId });
  }
  return _cloudbaseApp;
}

exports.main = async (event, context) => {
  const app = getCloudbaseApp();
  const db = app.database();
  
  const collections = ['alerts', 'user_stocks', 'user_preferences', 'tts_cache', 'push_tokens'];
  const results = [];
  
  for (const coll of collections) {
    try {
      console.log(`Creating collection: ${coll}...`);
      // 尝试 db.createCollection — 这是node-sdk v3的管理API
      const result = await db.createCollection(coll);
      results.push({ collection: coll, status: 'created', result: JSON.stringify(result) });
      console.log(`✅ Created ${coll}`);
    } catch (e) {
      const errMsg = String(e.message || e.code || e);
      console.log(`createCollection error for ${coll}: ${errMsg}`);
      
      if (errMsg.includes('already exists') || e.code === -502001) {
        results.push({ collection: coll, status: 'already_exists' });
        console.log(`⚠️ ${coll} already exists`);
      } else {
        // 尝试使用数据库管理命令
        try {
          console.log(`Trying db.command createCollection for ${coll}...`);
          // 使用 runCommand 方式（MongoDB兼容）
          const cmdResult = await db.command({ create: coll });
          results.push({ collection: coll, status: 'created_via_command', result: JSON.stringify(cmdResult) });
          console.log(`✅ Created ${coll} via command`);
        } catch (e2) {
          const e2Msg = String(e2.message || e2.code || e2);
          console.log(`command error for ${coll}: ${e2Msg}`);
          results.push({ collection: coll, status: 'error', error: e2Msg });
        }
      }
    }
  }
  
  // 验证集合
  const verify = [];
  for (const coll of collections) {
    try {
      const countResult = await db.collection(coll).count();
      verify.push({ collection: coll, count: countResult.total });
    } catch (e) {
      verify.push({ collection: coll, error: String(e.message || e.code) });
    }
  }
  
  return { results, verify };
};
