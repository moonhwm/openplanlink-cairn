/**
 * 异动条目：服务端（X 服务器云端秒级监测）产出。
 * kind=fact：客观异动事实（涨跌幅/量能/价格穿越）；
 * kind=signal：自家策略信号与白话解读（机主 09-14 松绑，禁收益承诺/催促指令/对外公开）。
 */
export interface AlertItem {
  alertId: string;      // 唯一 ID，通知点击回传定位用
  ts: number;           // 秒级时间戳
  symbol: string;       // 如 600176
  name: string;         // 如 中国巨石
  direction: 'up' | 'down' | 'flat';
  kind?: 'fact' | 'signal'; // 缺省按 fact 处理
  headline: string;     // 一句话白话结论，如「中国巨石 2 分钟涨了 2.3%」
  detail: string;       // 补充事实（量能、价位）
  signalNote?: string;  // 自家策略信号白话解读（仅 kind=signal 时有值；合规降级后剥离）
  audioUrl?: string;    // 云端 TTS 音频流地址；无则不显示播报钮
  complianceStatus?: string; // DKnowC安全合规分类：Safe/Unsafe/ConditionallySafe/Focus/Unknown
}

export interface AlertFeed {
  items: AlertItem[];
  serverTs: number;
}
