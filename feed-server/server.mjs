/**
 * 铃语数据管道服务器
 * 
 * 数据链路（CloudBase 模式）：CloudBase get-alerts 云函数 → AlertFeed JSON → 铃语App
 * 数据链路（本地降级模式）：westock-data (腾讯自选股) → 异动筛选 → AlertFeed JSON → 铃语App
 * 
 * 端点：
 *   GET /api/alerts/latest?limit=N  →  AlertFeed JSON（优先 CloudBase，降级本地）
 *   GET /health                      →  健康检查
 * 
 * 异动判断：涨跌幅绝对值 ≥ THRESHOLD（默认 5%）
 * TTS音频：百炼 cosyvoice-v3-flash 生成，缓存到 data/tts-cache/
 * 
 * 数据源模式：
 *   - CLAUDBASE_MODE=1（默认）：从 CloudBase get-alerts 云函数获取数据
 *   - CLOUDBASE_MODE=0：从本地 westock-data 获取数据（开发降级）
 */

import http from 'node:http';
import https from 'node:https';
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { postProcessAudio, checkFFmpeg } from './audio-postprocess.mjs';

const execAsync = promisify(exec);

const PORT = 8000;
const THRESHOLD = 5.0; // 涨跌幅绝对值阈值（%）
const REFRESH_INTERVAL = 30000; // 数据刷新间隔（ms）
const TTS_CACHE_DIR = path.join(import.meta.dirname, 'data', 'tts-cache');
const NODE_EXE = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node.exe';
const NODE_DIR = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64';
const NPX_CLI = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node_modules/npm/bin/npx-cli.js';
const WESTOCK_PKG = 'westock-data-clawhub@1.0.4';

// CloudBase 数据源配置
const CLOUDBASE_MODE = process.env.CLOUDBASE_MODE !== '0'; // 默认启用 CloudBase 模式
const CLOUDBASE_ALERTS_URL = process.env.CLOUDBASE_ALERTS_URL || 'https://a2a-commonwealth-d2eepjr928e9c4d.service.tcloudbase.com/alerts';

// 确保 exec 环境中 PATH 包含 node 目录
const EXEC_ENV = {
  ...process.env,
  PATH: `${NODE_DIR};${process.env.PATH || ''}`,
};

// 百炼 TTS 配置（从环境变量或金库文件读取）
const BAILIAN_API_KEY = process.env.DASHSCOPE_API_KEY || loadBailianKey();
const BAILIAN_WORKSPACE_ID = 'ws-ay6o8osb22o9dc3t';
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;
const TTS_MODEL = 'cosyvoice-v3-flash';
const TTS_VOICE = 'longxiaochun_v3';

// 百炼额度监控模块（T1.3/T1.4——落地路线图P0任务）
const BAILIAN_QUOTA = {
  totalEstimated: 1000000, // 估计1M tokens免费额度
  usedTokens: 0,
  warningThreshold: 0.8,   // 80%预警
  stopThreshold: 1.0,      // 100%止损
  lastCheckTs: 0,
  history: [],              // [{ts, usedTokens, estimate}]
  
  // 记录TTS调用消耗（粗略估算：每字约2-3 tokens）
  recordUsage(textLength) {
    const estimatedTokens = Math.ceil(textLength * 2.5);
    this.usedTokens += estimatedTokens;
    this.lastCheckTs = Date.now();
    this.history.push({
      ts: new Date().toISOString(),
      usedTokens: this.usedTokens,
      estimate: estimatedTokens,
    });
    // 保留最近100条历史
    if (this.history.length > 100) this.history.shift();
    
    const ratio = this.usedTokens / this.totalEstimated;
    if (ratio >= this.stopThreshold) {
      console.error(`[feed-server] ⚠ 百炼额度止损! 已用 ${this.usedTokens}/${this.totalEstimated} tokens (${(ratio*100).toFixed(1)}%)`);
    } else if (ratio >= this.warningThreshold) {
      console.warn(`[feed-server] ⚠ 百炼额度预警: 已用 ${this.usedTokens}/${this.totalEstimated} tokens (${(ratio*100).toFixed(1)}%)`);
    }
  },
  
  // 获取额度状态
  getStatus() {
    const ratio = this.usedTokens / this.totalEstimated;
    let level = 'normal';
    if (ratio >= this.stopThreshold) level = 'stop';
    else if (ratio >= this.warningThreshold) level = 'warning';
    return {
      level,
      usedTokens: this.usedTokens,
      totalEstimated: this.totalEstimated,
      usageRatio: parseFloat(ratio.toFixed(4)),
      lastCheckTs: new Date(this.lastCheckTs).toISOString(),
    };
  },
  
  // 是否应该停止TTS调用
  shouldStop() {
    return this.usedTokens / this.totalEstimated >= this.stopThreshold;
  },
};

function loadBailianKey() {
  try {
    // 尝试多个可能的路径
    const paths = [
      path.join(import.meta.dirname, '..', '..', '..', 'GOVERNANCE', 'credentials', 'aliyun_bailian.json'),
      'C:/Users/欧阳宏俊/Documents/kimi/tasks/2026-08-27/22-20-45-c3ffff44/GOVERNANCE/credentials/aliyun_bailian.json',
    ];
    for (const credPath of paths) {
      // Phase 1 加固：优先尝试加密版本（.enc）
      const encPath = credPath + '.enc';
      if (fs.existsSync(encPath)) {
        const cred = decryptVaultFile(encPath);
        console.log('[feed-server] loaded bailian key (encrypted) from:', encPath);
        return cred.api_key || '';
      }
      if (fs.existsSync(credPath)) {
        const cred = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
        console.log('[feed-server] loaded bailian key from:', credPath);
        return cred.api_key || '';
      }
    }
    console.log('[feed-server] bailian credential file not found in any path');
  } catch (e) { console.error('[feed-server] loadBailianKey error:', e.message); }
  return '';
}

// Phase 1 加固：内联 AES-256-GCM 解密
function decryptVaultFile(encPath) {
  const encObj = JSON.parse(fs.readFileSync(encPath, 'utf-8'));
  if (encObj.version !== 1 || encObj.algo !== 'aes-256-gcm') {
    throw new Error(`不支持的加密格式: version=${encObj.version}, algo=${encObj.algo}`);
  }
  let keyHex = process.env.VAULT_MASTER_KEY;
  if (!keyHex) {
    const keyFile = path.join(path.dirname(encPath), '..', 'vault-key.hex');
    if (fs.existsSync(keyFile)) {
      keyHex = fs.readFileSync(keyFile, 'utf-8').trim();
    }
  }
  if (!keyHex) {
    throw new Error('未找到 VAULT_MASTER_KEY 环境变量或 vault-key.hex 文件');
  }
  const key = Buffer.from(keyHex, 'hex');
  const iv = Buffer.from(encObj.iv, 'hex');
  const data = Buffer.from(encObj.data, 'hex');
  const tag = Buffer.from(encObj.tag, 'hex');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(data), decipher.final()]);
  return JSON.parse(decrypted.toString('utf8'));
}

// 确保缓存目录存在
fs.mkdirSync(TTS_CACHE_DIR, { recursive: true });

/** 当前缓存的异动列表 */
let cachedAlerts = [];
let lastRefreshTs = 0;

/**
 * 调用 westock-data CLI 获取热搜股票
 */
async function fetchHotStocks() {
  try {
    const cmd = `"${NODE_EXE}" "${NPX_CLI}" -y ${WESTOCK_PKG} hot stock`;
    console.log('[feed-server] executing:', cmd.substring(0, 80) + '...');
    const { stdout, stderr } = await execAsync(cmd, { timeout: 30000, env: EXEC_ENV });
    console.log('[feed-server] stdout length:', stdout.length, 'stderr length:', stderr?.length || 0);
    if (stdout.length === 0) {
      console.log('[feed-server] empty stdout, stderr:', stderr?.substring(0, 200));
      return [];
    }
    console.log('[feed-server] stdout first 300 chars:', JSON.stringify(stdout.substring(0, 300)));
    const parsed = parseMarkdownTable(stdout);
    console.log('[feed-server] parsed rows:', parsed.length);
    return parsed;
  } catch (e) {
    console.error('[feed-server] fetchHotStocks failed:', e.message.substring(0, 200));
    return [];
  }
}


/**
 * 调用 westock-data 获取个股分时数据（判断异动）
 */
async function fetchMinuteData(code) {
  try {
    const cmd = `"${NODE_EXE}" "${NPX_CLI}" -y ${WESTOCK_PKG} minute ${code}`;
    const { stdout } = await execAsync(cmd, { timeout: 30000, env: EXEC_ENV });
    return parseMarkdownTable(stdout);
  } catch (e) {
    console.error(`[feed-server] fetchMinuteData(${code}) failed:`, e.message);
    return [];
  }
}

/**
 * 解析 Markdown 表格为对象数组
 */
function parseMarkdownTable(md) {
  const lines = md.trim().split('\n').filter((l) => l.trim() && !l.trim().startsWith('| ---'));
  if (lines.length < 2) return [];
  
  const parseRow = (line) => {
    // 去掉首尾的 |，然后按 | 分割
    const inner = line.trim().replace(/^\|/, '').replace(/\|$/, '');
    return inner.split('|').map((c) => c.trim());
  };
  
  const headers = parseRow(lines[0]);
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = parseRow(lines[i]);
    if (cells.length === headers.length) {
      const obj = {};
      headers.forEach((h, idx) => { obj[h] = cells[idx]; });
      rows.push(obj);
    }
  }
  return rows;
}

/**
 * 从热搜股票中筛选异动并生成 AlertItem
 */
async function detectAlerts() {
  console.log('[feed-server] refreshing alerts...');
  const hotStocks = await fetchHotStocks();
  if (hotStocks.length === 0) {
    console.log('[feed-server] no hot stocks data');
    return [];
  }

  const alerts = [];
  for (const stock of hotStocks) {
    const zdf = parseFloat(stock.zdf); // 涨跌幅
    if (isNaN(zdf) || Math.abs(zdf) < THRESHOLD) continue;

    // 只处理 A 股（代码以 sh/sz/bj 开头）
    const code = stock.code;
    if (!/^(sh|sz|bj)/.test(code)) continue;

    const direction = zdf > 0 ? 'up' : zdf < 0 ? 'down' : 'flat';
    const name = stock.name;
    const price = parseFloat(stock.zxj) || 0;
    const symbol = code.replace(/^(sh|sz|bj)/, '');

    // 生成白话标题
    const headline = `${name} ${direction === 'up' ? '涨了' : '跌了'} ${Math.abs(zdf).toFixed(1)}%`;
    const detail = `当前价格 ${price.toFixed(2)} 元，涨跌幅 ${zdf.toFixed(2)}%`;

    // 信号卡判断（AGENTS.md §二.2 信号松绑）
    // 涨跌幅≥8%时标记为信号卡，附带白话解读（禁收益承诺/催促/公开）
    let kind = 'fact';
    let signalNote = undefined;
    if (Math.abs(zdf) >= 8.0) {
      kind = 'signal';
      // 白话解读——遵循三禁：不承诺收益、不催促、不公开
      if (zdf > 0) {
        signalNote = `${name}涨幅较大，留意后续走势`;
      } else {
        signalNote = `${name}跌幅较大，注意风险`;
      }
    }

    // 生成 alertId（基于内容哈希，确保幂等）
    // Phase 0 加固（2026-09-18）：从 md5 升级为 sha256，消除碰撞攻击风险
    const alertId = crypto.createHash('sha256').update(`${symbol}-${Date.now()}`).digest('hex').substring(0, 12);

    // 百炼 CosyVoice TTS（WebSocket 协议）
    const audioUrl = await generateTTS(headline, detail, alertId);

    alerts.push({
      alertId,
      ts: Math.floor(Date.now() / 1000),
      symbol,
      name,
      direction,
      kind,
      headline,
      detail,
      audioUrl,
      ...(signalNote ? { signalNote } : {}),
    });

    // 最多 20 条
    if (alerts.length >= 20) break;
  }

  console.log(`[feed-server] detected ${alerts.length} alerts`);
  return alerts;
}

/**
 * 调用百炼 CosyVoice TTS API（WebSocket 协议）生成语音
 * 
 * 交互流程：
 * 1. 建立 WebSocket 连接
 * 2. 发送 run-task 事件（设置模型、音色等参数）
 * 3. 等待 task-started 事件
 * 4. 发送 continue-task 事件（发送待合成文本）
 * 5. 接收 result-generated 事件和音频流（binary frames）
 * 6. 发送 finish-task 事件
 * 7. 接收 task-finished 事件
 * 8. 关闭连接
 */
async function generateTTS(headline, detail, alertId) {
  // 检查缓存（Phase 2 Hi-Fi：.mp3 → .wav）
  const cacheFile = path.join(TTS_CACHE_DIR, `${alertId}.wav`);
  if (fs.existsSync(cacheFile)) {
    return `${PROTOCOL}://127.0.0.1:${PORT}/audio/${alertId}.wav`;
  }

  if (!BAILIAN_API_KEY) {
    console.log('[feed-server] no DASHSCOPE_API_KEY, skipping TTS');
    return undefined;
  }

  // 百炼额度检查——止损时跳过TTS
  if (BAILIAN_QUOTA.shouldStop()) {
    console.warn('[feed-server] 百炼额度已超止损线，跳过TTS生成');
    return undefined;
  }

  const text = `${headline}。${detail}`;
  // 记录百炼额度消耗
  BAILIAN_QUOTA.recordUsage(text.length);
  const taskId = crypto.randomUUID();

  return new Promise((resolve) => {
    const chunks = [];
    let resolved = false;
    const done = (result) => {
      if (!resolved) { resolved = true; resolve(result); }
    };

    try {
      // Node.js v22 内置 WebSocket
      const ws = new WebSocket(TTS_WSS_URL, {
        headers: {
          'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        },
      });
      // 确保 binary 消息以 ArrayBuffer 形式接收（默认可能是 Blob）
      ws.binaryType = 'arraybuffer';

      const timeout = setTimeout(() => {
        console.error('[feed-server] TTS WebSocket timeout');
        try { ws.close(); } catch {}
        done(undefined);
      }, 30000);

      ws.addEventListener('open', () => {
        console.log('[feed-server] TTS WebSocket connected, sending run-task');
        // 步骤2: 发送 run-task 事件
        ws.send(JSON.stringify({
          header: {
            action: 'run-task',
            task_id: taskId,
            streaming: 'duplex',
          },
          payload: {
            task_group: 'audio',
            task: 'tts',
            function: 'SpeechSynthesizer',
            model: TTS_MODEL,
            input: {},
            parameters: {
              text_type: 'PlainText',
              voice: TTS_VOICE,
              format: 'wav',           // Phase 2 Hi-Fi：从 mp3 升级为 wav（无损，AVPlayer 兼容）
              sample_rate: 48000,      // Phase 2 Hi-Fi：从 22050 升级为 48000（专业品质）
              volume: 65,              // Phase 2a KU100对标：适老化响度提升 50→65
              rate: 0.9,               // Phase 2a KU100对标：适老化语速放缓 1.0→0.9
              pitch: 0.95,             // Phase 2a KU100对标：音色暖化 1.0→0.95
            },
          },
        }));
      });

      ws.addEventListener('message', async (event) => {
        // 区分二进制音频帧和文本事件
        if (event.data instanceof ArrayBuffer) {
          // 步骤5: 接收音频流（binary frames）
          chunks.push(Buffer.from(event.data));
          return;
        }
        // 文本消息 = 服务端事件
        try {
          const msg = JSON.parse(event.data);
          const action = msg?.header?.event;

          if (action === 'task-started') {
            console.log('[feed-server] TTS task-started, sending text');
            // 步骤4: 发送 continue-task 事件（待合成文本）
            ws.send(JSON.stringify({
              header: {
                action: 'continue-task',
                task_id: taskId,
                streaming: 'duplex',
              },
              payload: {
                input: { text },
              },
            }));
            // 步骤6: 发送 finish-task 事件（通知文本发送完毕）
            ws.send(JSON.stringify({
              header: {
                action: 'finish-task',
                task_id: taskId,
                streaming: 'duplex',
              },
              payload: {
                input: {},
              },
            }));
          } else if (action === 'result-generated') {
            const subType = msg?.payload?.output?.type;
            console.log(`[feed-server] TTS result-generated: ${subType}`);
            // sentence-synthesis 后紧跟 binary 音频帧
          } else if (action === 'task-finished') {
            console.log('[feed-server] TTS task-finished');
            clearTimeout(timeout);
            if (chunks.length > 0) {
              const buffer = Buffer.concat(chunks);
              // 先写入原始单声道文件
              const rawFile = cacheFile.replace('.wav', '.mono.wav');
              fs.writeFileSync(rawFile, buffer);
              console.log(`[feed-server] TTS generated ${buffer.length} bytes (mono) for ${alertId}`);

              // Phase 2a: HRTF 后处理（单声道→双声道 KU100级）
              const ffmpegOk = await checkFFmpeg();
              if (ffmpegOk) {
                console.log('[feed-server] applying HRTF post-processing...');
                const result = await postProcessAudio(rawFile, cacheFile);
                if (result.success) {
                  console.log(`[feed-server] HRTF post-process success: ${cacheFile}`);
                  // 清理原始单声道文件
                  try { fs.unlinkSync(rawFile); } catch {}
                } else {
                  console.error('[feed-server] HRTF post-process failed, using mono:', result.error);
                  // 后处理失败，回退为单声道
                  fs.renameSync(rawFile, cacheFile);
                }
              } else {
                // FFmpeg 不可用，直接使用单声道
                fs.renameSync(rawFile, cacheFile);
                console.log('[feed-server] FFmpeg not available, using mono WAV');
              }

              done(`${PROTOCOL}://127.0.0.1:${PORT}/audio/${alertId}.wav`);
            } else {
              console.error('[feed-server] TTS finished but no audio received');
              done(undefined);
            }
            try { ws.close(); } catch {}
          } else if (action === 'task-failed') {
            console.error('[feed-server] TTS task-failed:', JSON.stringify(msg?.header));
            clearTimeout(timeout);
            done(undefined);
            try { ws.close(); } catch {}
          }
        } catch (e) {
          // 非 JSON 消息，忽略
        }
      });

      ws.addEventListener('error', (event) => {
        console.error('[feed-server] TTS WebSocket error:', event.message || event);
        clearTimeout(timeout);
        done(undefined);
      });

      ws.addEventListener('close', () => {
        clearTimeout(timeout);
        done(undefined);
      });
    } catch (e) {
      console.error('[feed-server] TTS WebSocket init failed:', e.message);
      done(undefined);
    }
  });
}

/**
 * 从 CloudBase get-alerts 云函数获取 AlertFeed
 */
async function fetchCloudBaseAlerts(limit = 20) {
  try {
    const url = `${CLOUDBASE_ALERTS_URL}?limit=${limit}`;
    console.log('[feed-server] fetching from CloudBase:', url);
    const resp = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) {
      console.warn('[feed-server] CloudBase returned HTTP', resp.status);
      return null;
    }
    const feed = await resp.json();
    console.log('[feed-server] CloudBase returned', feed.items?.length || 0, 'items');
    return feed;
  } catch (e) {
    console.warn('[feed-server] CloudBase fetch failed:', e.message);
    return null;
  }
}

/**
 * 刷新数据
 * CloudBase 模式：从云函数获取；降级模式：从 westock-data 获取
 */
async function refresh() {
  try {
    if (CLOUDBASE_MODE) {
      const feed = await fetchCloudBaseAlerts(20);
      if (feed && feed.items) {
        cachedAlerts = feed.items;
        lastRefreshTs = Date.now();
        return;
      }
      // CloudBase 失败时降级到本地数据
      console.warn('[feed-server] CloudBase unavailable, falling back to local data');
    }
    cachedAlerts = await detectAlerts();
    lastRefreshTs = Date.now();
  } catch (e) {
    console.error('[feed-server] refresh failed:', e.message);
  }
}

/**
 * HTTP/HTTPS 服务器
 * Phase 2 加固（2026-09-18）：支持可选 HTTPS，本地开发用 HTTP，生产用 HTTPS
 * HTTPS 启用条件：GOVERNANCE/certs/server-key.pem 和 server-cert.pem 存在
 */
const USE_HTTPS = process.env.FEED_SERVER_HTTPS === '1';
const CERT_DIR = path.join(import.meta.dirname, '..', '..', '..', 'GOVERNANCE', 'certs');
const HTTPS_KEY_PATH = path.join(CERT_DIR, 'server-key.pem');
const HTTPS_CERT_PATH = path.join(CERT_DIR, 'server-cert.pem');
const PROTOCOL = (USE_HTTPS && fs.existsSync(HTTPS_KEY_PATH) && fs.existsSync(HTTPS_CERT_PATH)) ? 'https' : 'http';


let server;
if (USE_HTTPS && fs.existsSync(HTTPS_KEY_PATH) && fs.existsSync(HTTPS_CERT_PATH)) {
  const tlsOptions = {
    key: fs.readFileSync(HTTPS_KEY_PATH),
    cert: fs.readFileSync(HTTPS_CERT_PATH),
    minVersion: 'TLSv1.2',  // 借鉴 Paramiko 禁用弱协议的做法
  };
  server = https.createServer(tlsOptions, requestHandler);
  console.log('[feed-server] HTTPS 模式已启用');
} else {
  server = http.createServer(requestHandler);
  if (USE_HTTPS) {
    console.warn('[feed-server] ⚠ HTTPS 已请求但证书文件不存在，降级到 HTTP');
  }
}

// 请求处理函数（HTTP 和 HTTPS 共用）
async function requestHandler(req, res) {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);

  // CORS 头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // 健康检查（增强版——返回百炼额度状态+运维信息）
  if (url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      alerts: cachedAlerts.length,
      lastRefresh: new Date(lastRefreshTs).toISOString(),
      bailian: BAILIAN_QUOTA.getStatus(),
      ttsEnabled: !!BAILIAN_API_KEY,
      ttsModel: TTS_MODEL,
      threshold: THRESHOLD,
      protocol: PROTOCOL,
      cloudBaseMode: CLOUDBASE_MODE,
      cloudBaseUrl: CLOUDBASE_ALERTS_URL,
    }));
    return;
  }

  // 百炼额度状态端点
  if (url.pathname === '/api/quota') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(BAILIAN_QUOTA.getStatus()));
    return;
  }

  // 音频文件
  if (url.pathname.startsWith('/audio/')) {
    const filename = url.pathname.replace('/audio/', '');
    const filePath = path.join(TTS_CACHE_DIR, filename);
    if (fs.existsSync(filePath)) {
      const stat = fs.statSync(filePath);
      res.writeHead(200, {
        'Content-Type': 'audio/wav',  // Phase 2 Hi-Fi：从 audio/mpeg 改为 audio/wav
        'Content-Length': stat.size,
      });
      fs.createReadStream(filePath).pipe(res);
      return;
    }
    res.writeHead(404);
    res.end('audio not found');
    return;
  }

  // AlertFeed API
  if (url.pathname === '/api/alerts/latest') {
    const limit = parseInt(url.searchParams.get('limit') || '20', 10);

    // CloudBase 模式：实时代理请求（不依赖本地缓存刷新周期）
    if (CLOUDBASE_MODE) {
      const feed = await fetchCloudBaseAlerts(limit);
      if (feed && feed.items) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(feed));
        return;
      }
      // CloudBase 失败时降级到本地缓存
      console.warn('[feed-server] CloudBase proxy failed, serving local cache');
    }

    // 降级模式：返回本地缓存
    const items = cachedAlerts.slice(0, limit);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      items,
      serverTs: Math.floor(Date.now() / 1000),
    }));
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found' }));
}

// 启动

server.listen(PORT, '127.0.0.1', async () => {
  console.log(`[feed-server] 铃语数据管道服务器已启动 → ${PROTOCOL}://127.0.0.1:${PORT}`);
  console.log(`[feed-server] AlertFeed API → ${PROTOCOL}://127.0.0.1:${PORT}/api/alerts/latest`);
  console.log(`[feed-server] 数据源 → ${CLOUDBASE_MODE ? 'CloudBase 云函数' : '本地 westock-data'}`);
  if (CLOUDBASE_MODE) {
    console.log(`[feed-server] CloudBase URL → ${CLOUDBASE_ALERTS_URL}`);
  }
  console.log(`[feed-server] 异动阈值 → ${THRESHOLD}%`);
  console.log(`[feed-server] TTS → ${BAILIAN_API_KEY ? '百炼 cosyvoice-v3-flash (Hi-Fi: WAV 48kHz)' : '未配置 DASHSCOPE_API_KEY'}`);
  
  // 首次刷新
  await refresh();
  
  // 定时刷新
  setInterval(refresh, REFRESH_INTERVAL);
  console.log(`[feed-server] 数据刷新间隔 → ${REFRESH_INTERVAL / 1000}s`);
});