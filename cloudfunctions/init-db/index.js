const cloudbase = require('@cloudbase/node-sdk');

exports.main = async (event, context) => {
  const app = cloudbase.init({ env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d' });
  const db = app.database();
  
  const collections = ['alerts', 'user_stocks', 'user_preferences', 'tts_cache'];
  const results = [];
  
  for (const coll of collections) {
    try {
      // 插入一条初始化文档来创建集合
      const result = await db.collection(coll).add({
        _init: true,
        createdAt: new Date().toISOString(),
        note: 'Collection initialized by init-db function'
      });
      results.push({ collection: coll, status: 'created', id: result.id });
    } catch (e) {
      if (e.code === -502001 || e.message?.includes('already exists')) {
        results.push({ collection: coll, status: 'already_exists' });
      } else {
        results.push({ collection: coll, status: 'error', error: e.message || e.code });
      }
    }
  }
  
  // 验证集合
  const verify = [];
  for (const coll of collections) {
    try {
      const count = await db.collection(coll).count();
      verify.push({ collection: coll, count: count.total });
    } catch (e) {
      verify.push({ collection: coll, error: e.message });
    }
  }
  
  return { results, verify };
};