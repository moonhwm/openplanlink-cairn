// 使用 manager-node + 临时凭证创建 CloudBase 集合
import CloudBase from '@cloudbase/manager-node';

const ENV_ID = 'a2a-commonwealth-d2eepjr928e9c4d';

async function main() {
  // 从 tcb secrets get 获取的临时凭证
  const scf = new CloudBase({
    envId: ENV_ID,
    secretId: 'AKIDdifvyf_61Ki7AsKnsqR12zFe7xQY5-UVBOj5Y99flvjlbfdNNUFyo0Fu4994Sj1m',
    secretKey: '8iW62yNqArG7zkVeKjLjfoV8ff+zqhc0/9DanxnZFWM=',
    token: '7Wscs0g8ue7qHXjFpWF22EDeRpFh0Dta4d8ae45660af71555ba047c8c03d2109jiauTzpGZ0WI6l0g5g3P3RedotcwGPATFVR6NyKNhhIiT9HE1JNKAfBLMEiAnzdB_rTu7wD0nMpIse4FQ_YW2MEe0pMhE9zgHKOWaAu5dEQervyqf9y4s9q1w1_eJ4j9hpcWrTYiY3ji6mLaPW7toWmjXgkwdgnCYWkILTGrfVGhD5l-LfjBldfx_HCe5UOpTIZnauWj71zT13Z-2LW0FAN17AV7jpEDggdxAkgeZLq1ymsAweItJgd7mUCiE0rc2N_2BYYsie56YLNWbvwTvx1jyP7GsOO8xC_tV89u9NyP54dG4LIQwiNoUn1tiGI6BvoYY2fUs1FjIB-oTOybjwf1o_MV2a8ZkpbGGLArRHX7ThNCuqK8ZoAChF2Mf0dTDqQsLV5ubaFJ3NdIsNPbeI7vhETS1l1qQ23LF-DqTF0'
  });

  const collections = ['alerts', 'user_stocks', 'user_preferences', 'tts_cache'];

  // 先检查现有集合
  console.log('📋 Checking existing collections...');
  try {
    const result = await scf.database.listCollections();
    console.log('Existing collections:', JSON.stringify(result, null, 2));
  } catch (e) {
    console.log('listCollections error:', e.message || e);
  }

  // 创建集合
  for (const coll of collections) {
    try {
      console.log(`\nCreating collection: ${coll}...`);
      const result = await scf.database.createCollection(coll);
      console.log(`✅ Created: ${coll}`, JSON.stringify(result));
    } catch (e) {
      const msg = String(e.message || e.code || e);
      if (msg.includes('already exists') || msg.includes('DATABASE_COLLECTION_EXISTS') || e.code === -502001) {
        console.log(`⚠️ Collection already exists: ${coll}`);
      } else {
        console.error(`❌ Failed to create ${coll}:`, msg);
      }
    }
  }

  // 验证集合列表
  console.log('\n📋 Verifying collections...');
  try {
    const result = await scf.database.listCollections();
    console.log('All collections:', JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('listCollections error:', e.message);
  }

  process.exit(0);
}

main().catch(e => { console.error('Fatal:', e); process.exit(1); });