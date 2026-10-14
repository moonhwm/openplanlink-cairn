import { http } from '@kit.NetworkKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { AlertItem, AlertFeed } from '../model/AlertItem';
import { SettingsService, DEFAULT_FEED_URL } from './SettingsService';

const TAG = 'StockPulse.AlertPoller';
const DOMAIN = 0x0001;

/** 轮询结果：ok=false 表示网络/HTTP 异常，ok=true 且 items 为空表示"连通但无异动" */
export interface PollResult {
  ok: boolean;
  items: AlertItem[];
  rateLimited?: boolean; // 429 限流：ok=false 但不计入"连接中断"提示（白皮书 §3.2.4）
}

/**
 * 前台轮询兜底：App 打开期间每 5s 拉一次最新异动。
 * 推送（PushService）实装后，本件仅作拉齐补偿。
 *
 * 退避策略（白皮书 §3.2.4）：失败后下一轮间隔翻倍、封顶 30 秒；
 * 429 限流静默跳过、按 ok=false 计但不惊动用户；
 * 5xx 按普通失败计；JSON 解析失败按 ok=false 处理并记原文前 200 字符。
 */
export class AlertPoller {
  private static currentInterval: number = 5000;
  private static readonly MAX_INTERVAL: number = 30000;
  private static readonly BASE_INTERVAL: number = 5000;

  /** 获取当前轮询间隔（退避时动态增大，成功后复位） */
  static getInterval(): number {
    return AlertPoller.currentInterval;
  }

  static async fetchLatest(limit: number = 20): Promise<PollResult> {
    const feedUrl = await SettingsService.getFeedUrl();
    const req = http.createHttp();
    try {
      const resp = await req.request(`${feedUrl}?limit=${limit}`, {
        method: http.RequestMethod.GET,
        connectTimeout: 5000,
        readTimeout: 5000
      });

      if (resp.responseCode === 429) {
        // 限流：静默跳过，ok=false 但不惊动老爷子（白皮书 §3.2.4）
        hilog.warn(DOMAIN, TAG, 'feed http 429 rate-limited, skipping silently');
        AlertPoller.applyBackoff();
        return { ok: false, items: [], rateLimited: true };
      }

      if (resp.responseCode >= 500) {
        hilog.warn(DOMAIN, TAG, `feed http ${resp.responseCode} server error`);
        AlertPoller.applyBackoff();
        return { ok: false, items: [] };
      }

      if (resp.responseCode !== 200) {
        hilog.warn(DOMAIN, TAG, `feed http ${resp.responseCode}`);
        AlertPoller.applyBackoff();
        return { ok: false, items: [] };
      }

      // 200：尝试解析 JSON
      let feed: AlertFeed;
      try {
        feed = JSON.parse(resp.result as string) as AlertFeed;
      } catch (parseErr) {
        const raw = (resp.result as string) ?? '';
        hilog.warn(DOMAIN, TAG, `json parse failed: ${raw.substring(0, 200)}`);
        AlertPoller.applyBackoff();
        return { ok: false, items: [] };
      }

      // 成功：重置退避
      AlertPoller.resetBackoff();
      return { ok: true, items: feed.items ?? [] };

    } catch (e) {
      hilog.warn(DOMAIN, TAG, `fetch failed: ${(e as Error).message}`);
      AlertPoller.applyBackoff();
      return { ok: false, items: [] };
    } finally {
      req.destroy();
    }
  }

  private static applyBackoff(): void {
    AlertPoller.currentInterval = Math.min(
      AlertPoller.currentInterval * 2,
      AlertPoller.MAX_INTERVAL
    );
  }

  private static resetBackoff(): void {
    AlertPoller.currentInterval = AlertPoller.BASE_INTERVAL;
  }
}
