/**
 * generate-tts 云函数
 *
 * 功能：
 * 1. 接收异动条目（alertId + headline + detail）
 * 2. 通过 WebSocket 调用阿里百炼 TTS API 生成语音
 * 3. 将音频上传到 CloudBase 云存储
 * 4. 更新 alerts.json 中对应条目的 audioUrl 字段
 * 5. 缓存到 CloudBase 存储（tts-cache/{cacheKey}.json）避免重复生成
 *
 * 触发方式：由 fetch-tushare-data 调用 或 手动调用
 * 环境变量：DASHSCOPE_API_KEY（必需）
 * 依赖：ws（WebSocket 客户端）
 */

const WebSocket = require('ws');
const crypto = require('crypto');

const BAILIAN_WORKSPACE_ID = process.env.BAILIAN_WORKSPACE_ID || '';
const BAILIAN_API_KEY = process.env.DASHSCOPE_API_KEY || '';
const TTS_MODEL = 'cosyvoice-v3-flash';
const TTS_VOICE = 'longxiaochun_v3';
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';
const ALERTS_FILE_ID = 'cloud://a2a-commonwealth-d2eepjr928e9c4d.6132-a2a-commonwealth-d2eepjr928e9c4d-1475054847/alerts/alerts.json';

// 百炼额度监控
// 设计限制：QUOTA.usedTokens 在云函数冷启动后重置为0，仅监控单次冷启动周期内的用量。
// 百炼平台本身有独立的额度限制和告警，此对象仅作辅助参考，不作为额度控制的权威来源。
const QUOTA = {
  totalEstimated: 1000000,
  usedTokens: 0,
  warningThreshold: 0.8,
  stopThreshold: 1.0,

  recordUsage(textLength) {
    this.usedTokens += Math.ceil(textLength * 2.5);
  },

  shouldStop() {
    return this.usedTokens / this.totalEstimated >= this.stopThreshold;
  },

  getStatus() {
    const ratio = this.usedTokens / this.totalEstimated;
    return {
      level: ratio >= this.stopThreshold ? 'stop' : ratio >= this.warningThreshold ? 'warning' : 'normal',
      usedTokens: this.usedTokens,
      totalEstimated: this.totalEstimated,
      usageRatio: parseFloat(ratio.toFixed(4)),
    };
  },
};

/**
 * 生成缓存键（文本的 SHA256 前16位）
 */
function getCacheKey(text) {
  return crypto.createHash('sha256').update(text).digest('hex').substring(0, 16);
}

/**
 * 获取 CloudBase app 实例（单例）
 */
let _cloudbaseApp = null;
function getCloudBaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({ env: ENV_ID });
  }
  return _cloudbaseApp;
}

/**
 * 查询 CloudBase 存储中是否已有 TTS 缓存
 * 缓存文件格式：tts-cache/{cacheKey}.json，内容为 { audioUrl, text, voice, model, createdAt }
 */
async function checkCache(cacheKey) {
  try {
    const app = getCloudBaseApp();
    const cacheFileID = `cloud://${ENV_ID}.6132-${ENV_ID}-1475054847/tts-cache/${cacheKey}.json`;

    const result = await app.downloadFile({ fileID: cacheFileID });
    if (result && result.fileContent) {
      const text = result.fileContent.toString('utf-8');
      const data = JSON.parse(text);
      if (data && data.audioUrl) {
        console.log('TTS cache hit:', cacheKey);
        return data.audioUrl;
      }
    }
  } catch (e) {
    // 缓存文件不存在是正常情况，不记为错误
    console.log('TTS cache miss:', cacheKey);
  }
  return null;
}

/**
 * 保存 TTS 缓存到 CloudBase 存储
 */
async function saveCache(cacheKey, text, audioUrl) {
  try {
    const app = getCloudBaseApp();
    const cacheData = JSON.stringify({
      audioUrl,
      text,
      voice: TTS_VOICE,
      model: TTS_MODEL,
      createdAt: new Date().toISOString(),
    });

    await app.uploadFile({
      cloudPath: `tts-cache/${cacheKey}.json`,
      fileContent: Buffer.from(cacheData, 'utf-8'),
    });

    console.log('TTS cache saved:', cacheKey);
  } catch (e) {
    console.error('Cache save error:', e.message);
  }
}

/**
 * 更新 alerts.json 中对应 alertId 的 audioUrl 字段
 * 读取 → 修改 → 重新上传
 * 并发风险：多个 TTS 生成可能同时读取 alerts.json 并写回，导致 lost update（后写覆盖先写）。
 * 当前 fetch-tushare-data 中 TTS 生成是顺序执行的，实际风险较低。如需并行 TTS，应改为数据库原子更新。
 */
async function updateAlertAudioUrl(alertId, audioUrl) {
  try {
    const app = getCloudBaseApp();

    // 1. 下载当前 alerts.json
    const result = await app.downloadFile({ fileID: ALERTS_FILE_ID });
    if (!result || !result.fileContent) {
      console.error('updateAlertAudioUrl: alerts.json not found');
      return;
    }

    const data = JSON.parse(result.fileContent.toString('utf-8'));
    if (!data || !data.items || !Array.isArray(data.items)) {
      console.error('updateAlertAudioUrl: invalid alerts.json format');
      return;
    }

    // 2. 找到对应 alertId 并更新 audioUrl
    let updated = false;
    for (const item of data.items) {
      if (item.alertId === alertId) {
        item.audioUrl = audioUrl;
        updated = true;
        break;
      }
    }

    if (!updated) {
      console.log(`updateAlertAudioUrl: alertId ${alertId} not found in alerts.json`);
      return;
    }

    // 3. 重新上传 alerts.json
    await app.uploadFile({
      cloudPath: 'alerts/alerts.json',
      fileContent: Buffer.from(JSON.stringify(data), 'utf-8'),
    });

    console.log(`updateAlertAudioUrl: updated ${alertId} with ${audioUrl}`);
  } catch (e) {
    console.error('Alert update error:', e.message);
  }
}

/**
 * 通过 WebSocket 调用百炼 TTS API 生成语音
 */
async function generateTTSAudio(text) {
  if (!BAILIAN_API_KEY) {
    console.error('DASHSCOPE_API_KEY not set');
    return null;
  }

  if (QUOTA.shouldStop()) {
    console.error('Bailian quota exceeded, stopping TTS generation');
    return null;
  }

  return new Promise((resolve) => {
    const taskId = crypto.randomUUID();
    const chunks = [];
    let resolved = false;
    const done = (result) => {
      if (!resolved) { resolved = true; resolve(result); }
    };

    try {
      const ws = new WebSocket(TTS_WSS_URL, {
        headers: {
          'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        },
      });

      ws.binaryType = 'arraybuffer';

      const timeout = setTimeout(() => {
        console.error('TTS WebSocket timeout');
        try { ws.close(); } catch (e) {}
        done(null);
      }, 30000);

      ws.addEventListener('open', () => {
        console.log('TTS WebSocket connected, sending run-task');
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
              format: 'mp3',
              sample_rate: 16000,
              volume: 65,
              rate: 0.9,
              pitch: 0.95,
            },
          },
        }));
      });

      ws.addEventListener('message', (event) => {
        if (event.data instanceof ArrayBuffer) {
          chunks.push(Buffer.from(event.data));
          return;
        }
        try {
          const msg = JSON.parse(event.data);
          const action = msg?.header?.event;

          if (action === 'task-started') {
            console.log('TTS task-started, sending text');
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
          }

          if (action === 'task-finished') {
            console.log(`TTS task-finished, ${chunks.length} audio chunks received`);
            clearTimeout(timeout);
            QUOTA.recordUsage(text.length);
            const audioBuffer = Buffer.concat(chunks);
            done(audioBuffer);
            try { ws.close(); } catch (e) {}
          }

          if (action === 'task-failed') {
            console.error('TTS task-failed:', JSON.stringify(msg));
            clearTimeout(timeout);
            done(null);
            try { ws.close(); } catch (e) {}
          }
        } catch (e) {
          // 非 JSON 消息，忽略
        }
      });

      ws.addEventListener('error', (event) => {
        console.error('TTS WebSocket error:', event.message || 'unknown');
        clearTimeout(timeout);
        done(null);
      });

      ws.addEventListener('close', () => {
        clearTimeout(timeout);
        if (!resolved && chunks.length > 0) {
          console.log(`WebSocket closed with ${chunks.length} chunks, using partial audio`);
          QUOTA.recordUsage(text.length);
          const audioBuffer = Buffer.concat(chunks);
          done(audioBuffer);
        } else if (!resolved) {
          done(null);
        }
      });
    } catch (e) {
      console.error('TTS WebSocket init error:', e.message);
      done(null);
    }
  });
}

/**
 * 上传音频到 CloudBase 云存储
 */
async function uploadToStorage(audioBuffer, cacheKey) {
  try {
    const app = getCloudBaseApp();
    const storagePath = `tts/${cacheKey}.mp3`;

    const result = await app.uploadFile({
      cloudPath: storagePath,
      fileContent: audioBuffer,
    });

    if (result.fileID) {
      const urlResult = await app.getTempFileURL({
        fileList: [result.fileID],
      });
      if (urlResult.fileList && urlResult.fileList[0] && urlResult.fileList[0].tempFileURL) {
        return urlResult.fileList[0].tempFileURL;
      }
      return result.fileID;
    }
  } catch (e) {
    console.error('Storage upload error:', e.message);
  }

  return null;
}

/**
 * 云函数入口
 */
exports.main = async (event, context) => {
  console.log('generate-tts invoked', JSON.stringify({
    alertId: event.alertId,
    text: event.text?.substring(0, 50) + '...',
    quotaStatus: QUOTA.getStatus(),
  }));

  const { alertId, text } = event;

  if (!text) {
    return { success: false, error: 'text is required' };
  }

  if (!BAILIAN_API_KEY) {
    return { success: false, error: 'DASHSCOPE_API_KEY not configured' };
  }

  try {
    // 1. 检查缓存
    const cacheKey = getCacheKey(text);
    const cachedUrl = await checkCache(cacheKey);
    if (cachedUrl) {
      console.log('Cache hit, returning cached audio URL');
      if (alertId) {
        await updateAlertAudioUrl(alertId, cachedUrl);
      }
      return { success: true, audioUrl: cachedUrl, cached: true };
    }

    // 2. 通过 WebSocket 生成 TTS 音频
    console.log('Generating TTS audio via WebSocket...');
    const audioBuffer = await generateTTSAudio(text);
    if (!audioBuffer) {
      return { success: false, error: 'TTS generation failed' };
    }

    console.log(`TTS audio generated: ${audioBuffer.length} bytes`);

    // 3. 上传到云存储
    console.log('Uploading to cloud storage...');
    const audioUrl = await uploadToStorage(audioBuffer, cacheKey);
    if (!audioUrl) {
      return { success: false, error: 'Storage upload failed' };
    }

    // 4. 保存缓存
    await saveCache(cacheKey, text, audioUrl);

    // 5. 更新 alert 的 audioUrl
    if (alertId) {
      await updateAlertAudioUrl(alertId, audioUrl);
    }

    return {
      success: true,
      audioUrl,
      cached: false,
      audioSize: audioBuffer.length,
      quotaStatus: QUOTA.getStatus(),
    };
  } catch (e) {
    console.error('generate-tts error:', e.message);
    return { success: false, error: e.message };
  }
};