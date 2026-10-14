import { preferences } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'StockPulse.SettingsService';
const DOMAIN = 0x0001;

/** Preferences 持久化键名 */
const PREF_NAME = 'stockpulse_settings';
const KEY_WATCHLIST = 'watchlist';           // 自选股列表，JSON string[]
const KEY_BROADCAST_ENABLED = 'broadcast';   // 播报开关，boolean
const KEY_FONT_SIZE_LEVEL = 'font_level';    // 字体档，'standard' | 'large'
const KEY_ELDERLY_MODE = 'elderly_mode';    // 适老化模式，boolean（默认 true）
const KEY_THEME_MODE = 'theme_mode';        // 显示模式，'night' | 'day'（默认 'night'）
const KEY_DND_ENABLED = 'dnd_enabled';      // 免打扰开关，boolean（默认 false）
const KEY_DND_START = 'dnd_start';          // 免打扰开始时段，number（默认 22）
const KEY_DND_END = 'dnd_end';          // 免打扰结束时段，number（默认 8）
const KEY_AUTO_THEME = 'auto_theme';      // 自动主题切换，boolean（默认 true）
const KEY_FEED_URL = 'feed_url';          // 数据源地址，string（默认 CloudBase 云函数）
const KEY_READ_ALERTS = 'read_alerts';    // 已读异动ID列表，JSON string[]
const KEY_PLAY_HISTORY = 'play_history';  // 播报历史，JSON Array<{alertId, ts}>

/** CloudBase 云函数基础地址——所有端点共享同一域名 */
export const CLOUDBASE_BASE_URL = 'https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.ap-shanghai.app.tcloudbase.com';

/** 默认数据源地址（get-alerts 云函数 HTTP 端点） */
export const DEFAULT_FEED_URL = `${CLOUDBASE_BASE_URL}/alerts`;

/** 字体档枚举 */
export type FontSizeLevel = 'standard' | 'large';

/** 显示模式枚举 */
export type ThemeMode = 'night' | 'day';

/** 主题颜色方案 */
export interface ThemeColors {
  pageBackground: string;
  cardBackground: string;
  textPrimary: string;
  textSecondary: string;
  accentGold: string;
  riseRed: string;
  fallGreen: string;
}

/** 夜间模式配色 */
export const NIGHT_COLORS: ThemeColors = {
  pageBackground: '#0d1117',
  cardBackground: '#1c2433',
  textPrimary: '#e8edf5',
  textSecondary: '#c6ceda',
  accentGold: '#f0b232',
  riseRed: '#e74c3c',
  fallGreen: '#2ecc71',
};

/** 白天模式配色 */
export const DAY_COLORS: ThemeColors = {
  pageBackground: '#f5f7fa',
  cardBackground: '#ffffff',
  textPrimary: '#1d2129',
  textSecondary: '#86909c',
  accentGold: '#d4951a',
  riseRed: '#cf0a2c',
  fallGreen: '#00b42a',
};

/**
 * 设置数据管理：自选股列表、播报开关、字体档。
 * 三项均通过 Preferences 持久化，杀进程重启后恢复。
 * 初始化时机：EntryAbility.onCreate 调用 init(context)。
 * 读取时机：Index.aboutToAppear 与 Settings.aboutToAppear 各自读取。
 */
export class SettingsService {
  private static pref: preferences.Preferences | null = null;


  static async init(context: common.UIAbilityContext): Promise<void> {
    try {
      SettingsService.pref = await preferences.getPreferences(context, PREF_NAME);
      hilog.info(DOMAIN, TAG, 'SettingsService initialized');
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `SettingsService init failed: ${(e as Error).message}`);
    }
  }

  // ── 自选股列表 ──

  static async getWatchlist(): Promise<string[]> {
    if (!SettingsService.pref) {
      return [];
    }
    try {
      const raw = await SettingsService.pref.get(KEY_WATCHLIST, '[]') as string;
      return JSON.parse(raw) as string[];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `watchlist read failed: ${(e as Error).message}`);
      return [];
    }
  }

  static async setWatchlist(list: string[]): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_WATCHLIST, JSON.stringify(list));
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `watchlist write failed: ${(e as Error).message}`);
    }
  }

  // ── 播报开关 ──

  static async getBroadcastEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    try {
      return await SettingsService.pref.get(KEY_BROADCAST_ENABLED, true) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `broadcast read failed: ${(e as Error).message}`);
      return true;
    }
  }

  static async setBroadcastEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_BROADCAST_ENABLED, enabled);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `broadcast write failed: ${(e as Error).message}`);
    }
  }

  // ── 字体档 ──

  static async getFontSizeLevel(): Promise<FontSizeLevel> {
    if (!SettingsService.pref) {
      return 'standard';
    }
    try {
      const level = await SettingsService.pref.get(KEY_FONT_SIZE_LEVEL, 'standard') as string;
      if (level === 'large') {
        return 'large';
      }
      return 'standard';
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `font level read failed: ${(e as Error).message}`);
      return 'standard';
    }
  }

  static async setFontSizeLevel(level: FontSizeLevel): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, level);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `font level write failed: ${(e as Error).message}`);
    }
  }

  // ── 适老化模式 ──

  static async getElderlyMode(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    try {
      return await SettingsService.pref.get(KEY_ELDERLY_MODE, true) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `elderly mode read failed: ${(e as Error).message}`);
      return true;
    }
  }

  static async setElderlyMode(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_ELDERLY_MODE, enabled);
      // 适老化模式开启时自动设为特大字体，关闭时恢复标准字体
      if (enabled) {
        await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, 'large');
      } else {
        await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, 'standard');
      }
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `elderly mode write failed: ${(e as Error).message}`);
    }
  }

  // ── 显示模式（夜间/白天） ──

  static async getThemeMode(): Promise<ThemeMode> {
    if (!SettingsService.pref) {
      return 'night';
    }
    try {
      const mode = await SettingsService.pref.get(KEY_THEME_MODE, 'night') as string;
      return mode === 'day' ? 'day' : 'night';
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `theme mode read failed: ${(e as Error).message}`);
      return 'night';
    }
  }

  static async setThemeMode(mode: ThemeMode): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_THEME_MODE, mode);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `theme mode write failed: ${(e as Error).message}`);
    }
  }

  static getThemeColors(mode: ThemeMode): ThemeColors {
    return mode === 'day' ? DAY_COLORS : NIGHT_COLORS;
  }

  // ── 免打扰模式 ──

  static async getDndEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return false;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_ENABLED, false) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd read failed: ${(e as Error).message}`);
      return false;
    }
  }

  static async setDndEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_ENABLED, enabled);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd write failed: ${(e as Error).message}`);
    }
  }

  static async getDndStartHour(): Promise<number> {
    if (!SettingsService.pref) {
      return 22;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_START, 22) as number;
    } catch (e) {
      return 22;
    }
  }

  static async setDndStartHour(hour: number): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_START, hour);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd start write failed: ${(e as Error).message}`);
    }
  }

  static async getDndEndHour(): Promise<number> {
    if (!SettingsService.pref) {
      return 8;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_END, 8) as number;
    } catch (e) {
      return 8;
    }
  }

  static async setDndEndHour(hour: number): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_END, hour);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd end write failed: ${(e as Error).message}`);
    }
  }

  /** 判断当前时间是否处于免打扰时段 */
  static isDndActive(dndEnabled: boolean, startHour: number, endHour: number): boolean {
    if (!dndEnabled) {
      return false;
    }
    const now = new Date();
    const hour = now.getHours();
    // 跨天时段（如 22:00-8:00）
    if (startHour > endHour) {
      return hour >= startHour || hour < endHour;
    }
    // 同天时段（如 9:00-18:00）
    return hour >= startHour && hour < endHour;
  }

  // ── 自动主题切换 ──

  static async getAutoThemeEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    try {
      return await SettingsService.pref.get(KEY_AUTO_THEME, true) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `auto theme read failed: ${(e as Error).message}`);
      return true;
    }
  }

  static async setAutoThemeEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_AUTO_THEME, enabled);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `auto theme write failed: ${(e as Error).message}`);
    }
  }

  /** 根据当前系统时间计算应使用的主题模式：6:00-18:00 为白天，18:00-6:00 为夜间 */
  static computeAutoThemeMode(): ThemeMode {
    const hour = new Date().getHours();
    if (hour >= 6 && hour < 18) {
      return 'day';
    }
    return 'night';
  }

  // ── FEED_URL 配置 ──

  static async getFeedUrl(): Promise<string> {
    if (!SettingsService.pref) {
      return DEFAULT_FEED_URL;
    }
    try {
      return await SettingsService.pref.get(KEY_FEED_URL, DEFAULT_FEED_URL) as string;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `feed url read failed: ${(e as Error).message}`);
      return DEFAULT_FEED_URL;
    }
  }

  static async setFeedUrl(url: string): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_FEED_URL, url);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `feed url write failed: ${(e as Error).message}`);
    }
  }

  // ── 已读异动标记 ──

  static async getReadAlertIds(): Promise<string[]> {
    if (!SettingsService.pref) {
      return [];
    }
    try {
      const raw = await SettingsService.pref.get(KEY_READ_ALERTS, '[]') as string;
      return JSON.parse(raw) as string[];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `read alerts read failed: ${(e as Error).message}`);
      return [];
    }
  }

  static async markAlertRead(alertId: string): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      const raw = await SettingsService.pref.get(KEY_READ_ALERTS, '[]') as string;
      const list = JSON.parse(raw) as string[];
      if (!list.includes(alertId)) {
        list.push(alertId);
        // 最多保留 200 条已读记录，防止无限增长
        if (list.length > 200) {
          list.splice(0, list.length - 200);
        }
        await SettingsService.pref.put(KEY_READ_ALERTS, JSON.stringify(list));
        await SettingsService.pref.flush();
      }
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `mark read failed: ${(e as Error).message}`);
    }
  }

  // ── 播报历史 ──

  static async getPlayHistory(): Promise<PlayHistoryItem[]> {
    if (!SettingsService.pref) {
      return [];
    }
    try {
      const raw = await SettingsService.pref.get(KEY_PLAY_HISTORY, '[]') as string;
      return JSON.parse(raw) as PlayHistoryItem[];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `play history read failed: ${(e as Error).message}`);
      return [];
    }
  }

  static async addPlayHistory(item: PlayHistoryItem): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      const raw = await SettingsService.pref.get(KEY_PLAY_HISTORY, '[]') as string;
      const list = JSON.parse(raw) as PlayHistoryItem[];
      // 去重：同一 alertId 只保留最新一条
      const filtered = list.filter((it) => it.alertId !== item.alertId);
      filtered.unshift(item);
      // 最多保留 50 条
      if (filtered.length > 50) {
        filtered.splice(50);
      }
      await SettingsService.pref.put(KEY_PLAY_HISTORY, JSON.stringify(filtered));
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `play history write failed: ${(e as Error).message}`);
    }
  }
}

/** 播报历史条目 */
export interface PlayHistoryItem {
  alertId: string;
  symbol: string;
  name: string;
  headline: string;
  ts: number;       // 播报时间戳
  alertTs: number;  // 异动原始时间戳
}