/**
 * cred_health_check.mjs — 密钥健康检查脚本
 * ROADMAP-026
 *
 * 检查项目中所有凭据的健康状态：
 * 1. Tushare Token — 验证格式 + API 连通性
 * 2. 百炼 API Key — 验证格式 + API 连通性
 * 3. Supabase URL/KEY — 验证格式 + API 连通性
 * 4. CloudBase 环境变量 — 验证 cloudbaserc.json 配置完整性
 *
 * 用法：node cred_health_check.mjs
 * 输出：JSON 格式健康报告 + 控制台摘要
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..'); // 项目根目录（GOVERNANCE 的上级）

// ── 结果收集 ──
const results = [];

function addResult(name, status, detail) {
  results.push({ name, status, detail, ts: new Date().toISOString() });
}

// ── 1. Tushare Token ──
async function checkTushare() {
  const token = 'a7ad47b0fcdc8964610b7101dcfee0016ce47cf3db2bf6e421ab21d0';

  // 格式检查
  if (!token || token.length < 30) {
    addResult('Tushare Token', 'FAIL', 'Token 格式无效（长度不足）');
    return;
  }

  // API 连通性检查
  try {
    const resp = await fetch('https://api.tushare.pro', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_name: 'trade_cal',
        token: token,
        params: { exchange: 'SSE', is_open: '1', limit: '1', offset: '0' },
        fields: 'cal_date',
      }),
      signal: AbortSignal.timeout(10000),
    });

    if (!resp.ok) {
      addResult('Tushare Token', 'FAIL', `API 返回 HTTP ${resp.status}`);
      return;
    }

    const data = await resp.json();
    if (data.code === 0) {
      addResult('Tushare Token', 'PASS', `API 连通正常，trade_cal 返回 ${data.data?.items?.length || 0} 条`);
    } else {
      addResult('Tushare Token', 'WARN', `API 返回错误码 ${data.code}: ${data.msg}`);
    }
  } catch (e) {
    addResult('Tushare Token', 'FAIL', `API 连接失败: ${e.message}`);
  }
}

// ── 2. 百炼 API Key ──
async function checkBailian() {
  // 从 cloudbaserc.json 读取
  const cloudbasercPath = path.join(ROOT, 'cloudfunctions', 'cloudbaserc.json');
  let apiKey = '';
  let workspaceId = '';

  try {
    if (fs.existsSync(cloudbasercPath)) {
      const config = JSON.parse(fs.readFileSync(cloudbasercPath, 'utf-8'));
      const ttsFn = config.functions?.find((f) => f.name === 'generate-tts');
      if (ttsFn?.config?.envVariables) {
        apiKey = ttsFn.config.envVariables.DASHSCOPE_API_KEY || '';
        workspaceId = ttsFn.config.envVariables.BAILIAN_WORKSPACE_ID || '';
      }
    }
  } catch (e) {
    // 忽略读取错误
  }

  // 格式检查
  if (!apiKey) {
    addResult('百炼 API Key', 'FAIL', '未在 cloudbaserc.json 中找到 DASHSCOPE_API_KEY');
    return;
  }

  if (!apiKey.startsWith('sk-')) {
    addResult('百炼 API Key', 'WARN', 'API Key 格式异常（不以 sk- 开头）');
    return;
  }

  // API 连通性检查——尝试 WebSocket 连接（百炼只支持 WebSocket）
  // 这里只验证 URL 可达性，不实际合成语音
  try {
    const wssUrl = `wss://${workspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;
    // 用 fetch 检查 HTTPS 端点是否可达（WebSocket 升级端点）
    const httpsUrl = `https://${workspaceId}.cn-beijing.maas.aliyuncs.com`;
    const resp = await fetch(httpsUrl, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    // 期望返回 403 或 404（说明服务在线，只是拒绝了普通 HTTP 请求）
    if (resp.status === 403 || resp.status === 404 || resp.status === 200) {
      addResult('百炼 API Key', 'PASS', `API Key 格式正确，服务端点可达 (${httpsUrl})`);
    } else {
      addResult('百炼 API Key', 'WARN', `服务端点返回异常状态码 ${resp.status}`);
    }
  } catch (e) {
    addResult('百炼 API Key', 'WARN', `服务端点连接失败（可能网络限制）: ${e.message}`);
  }
}

// ── 3. Supabase 凭据 ──
async function checkSupabase() {
  const cloudbasercPath = path.join(ROOT, 'cloudfunctions', 'cloudbaserc.json');
  let supabaseUrl = '';
  let supabaseKey = '';

  try {
    if (fs.existsSync(cloudbasercPath)) {
      const config = JSON.parse(fs.readFileSync(cloudbasercPath, 'utf-8'));
      const bcFn = config.functions?.find((f) => f.name === 'broadcast-a2a');
      if (bcFn?.config?.envVariables) {
        supabaseUrl = bcFn.config.envVariables.SUPABASE_URL || '';
        supabaseKey = bcFn.config.envVariables.SUPABASE_ANON_KEY || '';
      }
    }
  } catch (e) {
    // 忽略读取错误
  }

  // 格式检查
  if (!supabaseUrl || !supabaseKey) {
    addResult('Supabase 凭据', 'FAIL', '未在 cloudbaserc.json 中找到 SUPABASE_URL 或 SUPABASE_ANON_KEY');
    return;
  }

  if (!supabaseUrl.startsWith('https://') || !supabaseUrl.includes('.supabase.co')) {
    addResult('Supabase 凭据', 'FAIL', 'SUPABASE_URL 格式无效');
    return;
  }

  if (!supabaseKey.startsWith('eyJ')) {
    addResult('Supabase 凭据', 'WARN', 'SUPABASE_ANON_KEY 格式异常（JWT 应以 eyJ 开头）');
    return;
  }

  // API 连通性检查
  try {
    const resp = await fetch(`${supabaseUrl}/rest/v1/`, {
      headers: {
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`,
      },
      signal: AbortSignal.timeout(5000),
    });

    if (resp.ok || resp.status === 404) {
      addResult('Supabase 凭据', 'PASS', 'URL 格式正确，API 连通正常');
    } else if (resp.status === 401 || resp.status === 403) {
      addResult('Supabase 凭据', 'WARN', `API 连通但认证失败 (${resp.status})——KEY 可能已过期`);
    } else {
      addResult('Supabase 凭据', 'WARN', `API 返回异常状态码 ${resp.status}`);
    }
  } catch (e) {
    addResult('Supabase 凭据', 'FAIL', `API 连接失败: ${e.message}`);
  }
}

// ── 4. CloudBase 配置完整性 ──
async function checkCloudBaseConfig() {
  const cloudbasercPath = path.join(ROOT, 'cloudfunctions', 'cloudbaserc.json');

  if (!fs.existsSync(cloudbasercPath)) {
    addResult('CloudBase 配置', 'FAIL', 'cloudbaserc.json 不存在');
    return;
  }

  try {
    const config = JSON.parse(fs.readFileSync(cloudbasercPath, 'utf-8'));

    const issues = [];

    // 检查 envId
    if (!config.envId) {
      issues.push('envId 未配置');
    }

    // 检查每个函数的必需字段
    const requiredFnFields = ['name', 'config'];
    for (const fn of config.functions || []) {
      for (const field of requiredFnFields) {
        if (!fn[field]) {
          issues.push(`函数 ${fn.name || '(无名)'} 缺少字段: ${field}`);
        }
      }
      if (fn.config && !fn.config.runtime) {
        issues.push(`函数 ${fn.name} 缺少 runtime 配置`);
      }
    }

    // 检查关键环境变量
    const fetchFn = config.functions?.find((f) => f.name === 'fetch-tushare-data');
    if (fetchFn && !fetchFn.config?.envVariables?.TUSHARE_TOKEN) {
      issues.push('fetch-tushare-data 缺少 TUSHARE_TOKEN');
    }

    const ttsFn = config.functions?.find((f) => f.name === 'generate-tts');
    if (ttsFn && !ttsFn.config?.envVariables?.DASHSCOPE_API_KEY) {
      issues.push('generate-tts 缺少 DASHSCOPE_API_KEY');
    }

    if (issues.length === 0) {
      addResult('CloudBase 配置', 'PASS', `配置完整，${config.functions?.length || 0} 个函数全部就绪`);
    } else {
      addResult('CloudBase 配置', 'WARN', `${issues.length} 个问题: ${issues.join('; ')}`);
    }
  } catch (e) {
    addResult('CloudBase 配置', 'FAIL', `配置解析失败: ${e.message}`);
  }
}

// ── 5. 凭据文件存在性检查 ──
function checkCredentialFiles() {
  const credPaths = [
    { path: path.join(ROOT, 'GOVERNANCE', 'credentials', 'aliyun_bailian.json'), name: '百炼凭据文件' },
    { path: path.join(ROOT, 'GOVERNANCE', 'credentials', 'supabase_channel.json'), name: 'Supabase凭据文件' },
  ];

  for (const { path: credPath, name } of credPaths) {
    if (fs.existsSync(credPath)) {
      try {
        const content = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
        const keys = Object.keys(content);
        addResult(name, 'PASS', `文件存在，包含字段: ${keys.join(', ')}`);
      } catch (e) {
        addResult(name, 'WARN', `文件存在但解析失败: ${e.message}`);
      }
    } else {
      addResult(name, 'INFO', '文件不存在（凭据已内联到 cloudbaserc.json）');
    }
  }
}

// ── 主流程 ──
async function main() {
  console.log('=== 密钥健康检查 ===');
  console.log(`时间: ${new Date().toISOString()}`);
  console.log('');

  // 同步检查
  checkCredentialFiles();
  await checkCloudBaseConfig();

  // 异步 API 连通性检查
  await Promise.all([
    checkTushare(),
    checkBailian(),
    checkSupabase(),
  ]);

  // 输出摘要
  console.log('');
  console.log('=== 检查结果 ===');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'WARN' ? '⚠️' : r.status === 'FAIL' ? '❌' : 'ℹ️';
    console.log(`${icon} ${r.name}: ${r.status} — ${r.detail}`);
  }

  // 统计
  const pass = results.filter((r) => r.status === 'PASS').length;
  const warn = results.filter((r) => r.status === 'WARN').length;
  const fail = results.filter((r) => r.status === 'FAIL').length;
  const info = results.filter((r) => r.status === 'INFO').length;
  console.log('');
  console.log(`总计: ${pass} PASS / ${warn} WARN / ${fail} FAIL / ${info} INFO`);

  // 输出 JSON 报告
  const report = {
    timestamp: new Date().toISOString(),
    summary: { pass, warn, fail, info },
    results,
  };
  const reportPath = path.join(ROOT, 'GOVERNANCE', 'cred-health-report.json');  try {
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n报告已保存: ${reportPath}`);
  } catch (e) {
    console.log(`\n报告保存失败: ${e.message}`);
  }

  // 退出码：有 FAIL 则返回 1
  process.exitCode = fail > 0 ? 1 : 0;
}

main().catch((e) => {
  console.error('健康检查执行失败:', e);
  process.exitCode = 2;
});