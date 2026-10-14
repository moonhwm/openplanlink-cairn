// CloudBase 集合创建脚本 - 直接调用CloudBase OpenAPI
const https = require('https');
const crypto = require('crypto');

const ENV_ID = 'a2a-commonwealth-d2eepjr928e9c4d';
const REGION = 'ap-shanghai';

// 从tcb登录态获取临时密钥
const tcbConfig = require('os').homedir() + '/.cloudbase/config.json';
const fs = require('fs');

function getCredentials() {
  // 读取tcb登录配置
  const configPath = tcbConfig;
  if (fs.existsSync(configPath)) {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    return config;
  }
  throw new Error('tcb config not found at ' + configPath);
}

// 使用tcb CLI的envId直接通过SDK操作
// 方案：用 @cloudbase/node-sdk 的admin权限创建集合
async function createCollectionsViaSDK() {
  // 先安装 @cloudbase/node-sdk
  const { execSync } = require('child_process');
  const NODE_DIR = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64';
  const env = { ...process.env, PATH: `${NODE_DIR};${process.env.PATH || ''}` };
  
  console.log('Installing @cloudbase/node-sdk...');
  try {
    execSync('npm install @cloudbase/node-sdk --no-save', { 
      cwd: __dirname, env, timeout: 60000, stdio: 'pipe' 
    });
    console.log('✅ @cloudbase/node-sdk installed');
  } catch (e) {
    console.error('Failed to install:', e.message);
    return;
  }

  const cloudbase = require('@cloudbase/node-sdk');
  const app = cloudbase.init({ env: ENV_ID });
  const db = app.database();
  
  const collections = ['alerts', 'user_stocks', 'user_preferences', 'tts_cache'];
  
  for (const coll of collections) {
    try {
      console.log(`Creating collection: ${coll}...`);
      // 通过插入一条初始化文档来创建集合
      const result = await db.collection(coll).add({
        _init: true,
        createdAt: new Date().toISOString(),
        note: 'Collection initialized by cloudbase setup script'
      });
      console.log(`✅ Created ${coll}:`, result.id || result);
    } catch (e) {
      if (e.message?.includes('already exists') || e.code === -502001) {
        console.log(`⚠️ Collection ${coll} already exists`);
      } else {
        console.error(`❌ Failed ${coll}:`, e.message || e.code || JSON.stringify(e));
      }
    }
  }
  
  // 验证集合
  console.log('\n📋 Verifying collections...');
  for (const coll of collections) {
    try {
      const result = await db.collection(coll).count();
      console.log(`  ${coll}: ${result.total} documents`);
    } catch (e) {
      console.error(`  ${coll}: ERROR - ${e.message}`);
    }
  }
}

createCollectionsViaSDK().then(() => {
  console.log('\n✅ All done');
  process.exit(0);
}).catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});
