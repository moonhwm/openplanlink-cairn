// CloudBase 集合创建脚本
// 使用 @cloudbase/manager-node 直接创建集合

const path = require('path');

async function main() {
  // 动态导入 @cloudbase/manager-node
  const { CloudBase } = require('@cloudbase/manager-node');
  
  const envId = 'a2a-commonwealth-d2eepjr928e9c4d';
  const scf = new CloudBase({ envId });
  
  const collections = ['alerts', 'user_stocks', 'user_preferences', 'tts_cache'];
  
  for (const coll of collections) {
    try {
      console.log(`Creating collection: ${coll}...`);
      const result = await scf.database.createCollection(coll);
      console.log(`✅ Created: ${coll}`, JSON.stringify(result));
    } catch (e) {
      if (e.code === 'DATABASE_COLLECTION_EXISTS' || e.message?.includes('already exists')) {
        console.log(`⚠️ Collection already exists: ${coll}`);
      } else {
        console.error(`❌ Failed to create ${coll}:`, e.message || e);
      }
    }
  }
  
  // 验证集合列表
  try {
    const result = await scf.database.listCollections();
    console.log('\n📋 Current collections:', JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('Failed to list collections:', e.message);
  }
  
  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(1); });