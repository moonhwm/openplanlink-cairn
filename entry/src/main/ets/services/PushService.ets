import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { pushService } from '@kit.PushKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { http } from '@kit.NetworkKit';
import { CLOUDBASE_BASE_URL } from './SettingsService';

const TAG = 'StockPulse.PushService';
const DOMAIN = 0x0001;

/** Push Token 上报地址——CloudBase push-token-register 云函数 HTTP 端点 */
const TOKEN_REPORT_URL = `${CLOUDBASE_BASE_URL}/push-token-register`;

/** getToken 可重试错误码（官方文档） */
const RETRYABLE_ERROR_CODES = [1000900001, 1000900008, 1000900009, 1000900011];
const MAX_RETRY_COUNT = 3;
const RETRY_INTERVAL = 1000;

/**
 * Push Kit 集成封装。
 *
 * 降级：AGC 未配置时（agconnect-services.json 缺失），本服务静默降级，
 * 前台轮询（AlertPoller）兜底。AGC 配置到位后自动获取 Push Token 并上报 X 服务器。
 */
export class PushService {
  private static tokenReported = false;
  private static retryCount = 0;

  static async init(context: common.UIAbilityContext): Promise<void> {
    try {
      const hasAgc = await PushService.probeAgcConfig(context);
      if (!hasAgc) {
        hilog.info(DOMAIN, TAG, 'agconnect-services.json absent, push degraded to polling');
        return;
      }
      hilog.info(DOMAIN, TAG, 'agconnect-services.json found, initializing Push Kit');
      await PushService.fetchToken();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `init failed: ${(e as Error).message}`);
    }
  }

  /**
   * 获取 Push Token 并上报 X 服务器。
   * 失败时按错误码判断是否重试（最多 3 次，间隔 1s）。
   */
  private static async fetchToken(): Promise<void> {
    try {
      const token = await pushService.getToken();
      hilog.info(DOMAIN, TAG, `getToken succeeded, token length=${token.length}`);
      PushService.retryCount = 0;
      await PushService.reportToken(token);
      PushService.tokenReported = true;
    } catch (e) {
      const err = e as BusinessError;
      hilog.warn(DOMAIN, TAG, `getToken failed: code=${err.code}, message=${err.message}`);
      PushService.handleTokenRetry(err.code);
    }
  }

  /**
   * 重试逻辑：可重试错误码且未超过最大重试次数时，延迟 1s 后重试。
   */
  private static handleTokenRetry(errorCode: number): void {
    if (PushService.retryCount < MAX_RETRY_COUNT && RETRYABLE_ERROR_CODES.includes(errorCode)) {
      PushService.retryCount++;
      hilog.warn(DOMAIN, TAG, `getToken retry ${PushService.retryCount}/${MAX_RETRY_COUNT}`);
      setTimeout(() => PushService.fetchToken(), RETRY_INTERVAL);
    } else {
      hilog.warn(DOMAIN, TAG, 'getToken exhausted retries or non-retryable error');
    }
  }

  /**
   * 上报 Push Token 到 X 服务器。
   * 失败时仅记日志，不影响 App 主流程。
   */
  private static async reportToken(token: string): Promise<void> {
    const req = http.createHttp();
    try {
      const resp = await req.request(TOKEN_REPORT_URL, {
        method: http.RequestMethod.POST,
        connectTimeout: 5000,
        readTimeout: 5000,
        header: { 'Content-Type': 'application/json' },
        extraData: JSON.stringify({ token, bundleName: 'com.yehang.stockpulse' })
      });
      if (resp.responseCode === 200) {
        hilog.info(DOMAIN, TAG, 'token reported to server');
      } else {
        hilog.warn(DOMAIN, TAG, `token report failed: http ${resp.responseCode}`);
      }
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `token report error: ${(e as Error).message}`);
    } finally {
      req.destroy();
    }
  }

  private static async probeAgcConfig(context: common.UIAbilityContext): Promise<boolean> {
    try {
      const raw = context.resourceManager.getRawFileContentSync('agconnect-services.json');
      return raw != null && raw.length > 0;
    } catch (e) {
      return false;
    }
  }
}
