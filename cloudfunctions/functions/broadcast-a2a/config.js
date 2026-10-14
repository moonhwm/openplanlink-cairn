/**
 * broadcast-a2a 配置文件
 *
 * 总开关与参数集中管理。KIMI_ENABLED 为 kimi 通道总开关，
 * 默认 false（2026-09-24 机主令：彻底停用 kimi 调用，
 * 统一移交码道 GLM5.2 ArkTS 作为唯一总装节点）。
 */

module.exports = {
  // kimi 通道总开关（默认关闭，未来如需恢复改为 true）
  KIMI_ENABLED: false,

  // A2A 总线来源标识（砚坚席位键）
  FROM_MODE: 'yan-jian-codearts-glm52',

  // 心跳策略参数
  HEARTBEAT: {
    INITIAL_INTERVAL: 30,       // 初始间隔（秒）
    BACKOFF_STEPS: [60, 120, 300], // 指数退避序列（秒）
    JITTER: 0.2,                // ±20% 抖动
    BATCH_WINDOW: 60,           // 批量合并上报窗口（秒）
    FAILURE_THRESHOLD: 3,       // 连续失败熔断阈值
    ERROR_RATE_WINDOW: 300,     // 错误率统计窗口（秒）
    ERROR_RATE_THRESHOLD: 0.5,  // 错误率熔断阈值（50%）
    CIRCUIT_BREAK_DURATION: 900,// 熔断持续时间（秒，15分钟）
    HALF_OPEN_PROBES: 1,        // 半开探测次数
  },

  // 日预算管控
  BUDGET: {
    DAILY_LIMIT: 50,            // 日预算上限（元）
    ALERT_THRESHOLD: 0.5,       // 50% 告警
    DEGRADE_THRESHOLD: 0.8,     // 80% 降级为按需拉取
    STOP_THRESHOLD: 0.95,       // 95% 停服并通知
  },

  // 任务分发参数
  TASK: {
    MAX_RETRIES: 3,             // 重试上限
    TIMEOUT: 120000,            // 超时（ms）
    DEDUP_TTL: 3600,            // 去重窗口（秒）
  },
};