import { http } from '@kit.NetworkKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'A2A.EventBusService';
const DOMAIN = 0x0002;

/** A2A节点注册中心端点 */
const NODE_REGISTRY_URL = 'http://120.46.86.165:4174';

/** 席位状态（映射Cordis Fiber状态模型） */
export enum SeatState {
  IDLE = 'idle',
  THINKING = 'thinking',
  ACTING = 'acting',
  SYNCING = 'syncing',
  ERROR = 'error',
}

/** 席位信息 */
export interface SeatInfo {
  name: string;
  role: string;
  state: SeatState;
  lastActive: string;
  tasksCompleted: number;
  tasksInProgress: number;
  avatarColor: string;
}

/** 事件日志条目 */
export interface EventLogEntry {
  eventId: string;
  timestamp: string;
  seatName: string;
  eventType: string;
  description: string;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW';
}

/** 审计信息条目 */
export interface AuditEntry {
  timestamp: string;
  seatName: string;
  action: string;
  result: 'success' | 'failure' | 'warning';
  detail: string;
}

/** 节点注册中心返回的节点数据 */
interface RegistryNode {
  nodeId: string;
  seatName: string;
  endpoint: string;
  capabilities: string[];
  status: 'online' | 'busy' | 'offline';
  lastHeartbeat: string;
  macAddress?: string;
  offlineReason?: string;
}

/** 节点注册中心返回的节点列表 */
interface RegistryResponse {
  ok: boolean;
  count: number;
  online: number;
  nodes: RegistryNode[];
}

/** 健康检查响应 */
interface HealthResponse {
  ok: boolean;
  service: string;
  version: string;
  nodesTotal: number;
  nodesOnline: number;
  timestamp: string;
}

/** 拉取结果 */
export interface FetchResult {
  ok: boolean;
  seats: SeatInfo[];
  events: EventLogEntry[];
  audits: AuditEntry[];
  connectionStatus: 'connected' | 'disconnected';
}

/** 席位名→角色映射 */
const SEAT_ROLE_MAP: Record<string, string> = {
  '砚坚': '挂帅席 / 神经中枢',
  'Moon': '编排席 / 外部灵感',
  'Qoder': '开发席',
  'Kimi': '分析席',
  '守藏': '审计席',
  'Codex': '代码审查席',
  '星枢': '安全席',
};

/** 席位名→头像颜色映射 */
const SEAT_COLOR_MAP: Record<string, string> = {
  '砚坚': '#FF6B35',
  'Moon': '#9B59B6',
  'Qoder': '#4ECDC4',
  'Kimi': '#45B7D1',
  '守藏': '#96CEB4',
  'Codex': '#E67E22',
  '星枢': '#3498DB',
};

/** 将注册中心节点状态映射为SeatState */
function mapNodeStatus(status: string): SeatState {
  switch (status) {
    case 'online':
      return SeatState.ACTING;
    case 'busy':
      return SeatState.THINKING;
    case 'offline':
      return SeatState.ERROR;
    default:
      return SeatState.IDLE;
  }
}

/** 将注册中心节点转换为SeatInfo */
function nodeToSeatInfo(node: RegistryNode): SeatInfo {
  const capabilities = node.capabilities || [];
  const role = SEAT_ROLE_MAP[node.seatName] || capabilities.join('/') || '未知席位';
  const avatarColor = SEAT_COLOR_MAP[node.seatName] || '#888888';

  // 计算最后活跃时间描述
  let lastActive = '未知';
  if (node.lastHeartbeat) {
    const hbTime = new Date(node.lastHeartbeat).getTime();
    const now = Date.now();
    const diffSec = Math.floor((now - hbTime) / 1000);
    if (diffSec < 10) {
      lastActive = '刚刚';
    } else if (diffSec < 60) {
      lastActive = `${diffSec}秒前`;
    } else if (diffSec < 3600) {
      lastActive = `${Math.floor(diffSec / 60)}分钟前`;
    } else {
      lastActive = `${Math.floor(diffSec / 3600)}小时前`;
    }
  }

  return {
    name: node.seatName,
    role: role,
    state: mapNodeStatus(node.status),
    lastActive: lastActive,
    tasksCompleted: 0, // 注册中心暂不提供任务统计
    tasksInProgress: node.status === 'busy' ? 1 : 0,
    avatarColor: avatarColor,
  };
}

/**
 * A2A事件总线服务 —— 从节点注册中心拉取真实数据
 *
 * 数据源：幻16节点注册中心 (http://120.46.86.165:4174)
 * 协议：HTTP REST (GET /nodes, GET /health)
 *
 * 降级策略：
 * - 连接失败时返回空数据 + connectionStatus=disconnected
 * - 不回退到模拟数据（规范验收条件#7）
 */
export class EventBusService {
  private static readonly POLL_INTERVAL = 5000; // 5秒轮询
  private static readonly CONNECT_TIMEOUT = 5000;
  private static readonly READ_TIMEOUT = 5000;

  /** 拉取节点注册中心数据 */
  static async fetchDashboardData(): Promise<FetchResult> {
    const req = http.createHttp();
    try {
      // 1. 先检查健康状态
      const healthResp = await req.request(`${NODE_REGISTRY_URL}/health`, {
        method: http.RequestMethod.GET,
        connectTimeout: EventBusService.CONNECT_TIMEOUT,
        readTimeout: EventBusService.READ_TIMEOUT,
      });

      if (healthResp.responseCode !== 200) {
        hilog.warn(DOMAIN, TAG, `health check failed: HTTP ${healthResp.responseCode}`);
        return EventBusService.emptyResult(false);
      }

      const health = JSON.parse(healthResp.result as string) as HealthResponse;
      if (!health.ok) {
        hilog.warn(DOMAIN, TAG, 'health check: service not ok');
        return EventBusService.emptyResult(false);
      }

      hilog.info(DOMAIN, TAG, `registry healthy: ${health.nodesOnline}/${health.nodesTotal} nodes online`);

      // 2. 拉取节点列表
      const nodesResp = await req.request(`${NODE_REGISTRY_URL}/nodes`, {
        method: http.RequestMethod.GET,
        connectTimeout: EventBusService.CONNECT_TIMEOUT,
        readTimeout: EventBusService.READ_TIMEOUT,
      });

      if (nodesResp.responseCode !== 200) {
        hilog.warn(DOMAIN, TAG, `nodes query failed: HTTP ${nodesResp.responseCode}`);
        return EventBusService.emptyResult(false);
      }

      const registryData = JSON.parse(nodesResp.result as string) as RegistryResponse;
      if (!registryData.ok) {
        hilog.warn(DOMAIN, TAG, 'nodes query: response not ok');
        return EventBusService.emptyResult(false);
      }

      // 3. 转换数据格式
      const seats: SeatInfo[] = registryData.nodes
        .filter(n => n.status !== 'offline' || n.offlineReason === 'heartbeat_timeout')
        .map(nodeToSeatInfo);

      // 4. 生成事件日志（基于节点状态变化）
      const events: EventLogEntry[] = registryData.nodes.map(node => {
        const eventType = node.status === 'online' ? 'node_online' :
                          node.status === 'busy' ? 'node_busy' :
                          node.offlineReason === 'heartbeat_timeout' ? 'node_timeout' :
                          'node_offline';
        const priority = node.status === 'offline' && node.offlineReason === 'heartbeat_timeout' ? 'HIGH' : 'NORMAL';
        const description = node.status === 'online' ? `${node.seatName}已上线` :
                            node.status === 'busy' ? `${node.seatName}正在执行任务` :
                            node.offlineReason === 'heartbeat_timeout' ? `${node.seatName}心跳超时，已标记离线` :
                            `${node.seatName}已离线`;
        return {
          eventId: `evt_${node.nodeId}_${Date.now()}`,
          timestamp: node.lastHeartbeat || new Date().toISOString(),
          seatName: node.seatName,
          eventType: eventType,
          description: description,
          priority: priority as 'HIGH' | 'NORMAL',
        };
      });

      // 5. 生成审计轨迹（基于节点注册信息）
      const audits: AuditEntry[] = registryData.nodes
        .filter(n => n.status === 'online' || n.status === 'busy')
        .map(node => ({
          timestamp: node.lastHeartbeat || new Date().toISOString(),
          seatName: node.seatName,
          action: 'heartbeat',
          result: 'success' as const,
          detail: `状态: ${node.status}, 能力: ${node.capabilities.join(',')}`,
        }));

      hilog.info(DOMAIN, TAG, `fetched ${seats.length} seats, ${events.length} events, ${audits.length} audits`);

      return {
        ok: true,
        seats: seats,
        events: events,
        audits: audits,
        connectionStatus: 'connected',
      };

    } catch (e) {
      hilog.warn(DOMAIN, TAG, `fetch failed: ${(e as Error).message}`);
      return EventBusService.emptyResult(false);
    } finally {
      req.destroy();
    }
  }

  /** 生成空结果（连接失败时） */
  private static emptyResult(connected: boolean): FetchResult {
    return {
      ok: false,
      seats: [],
      events: [],
      audits: [],
      connectionStatus: connected ? 'connected' : 'disconnected',
    };
  }

  /** 获取轮询间隔 */
  static getPollInterval(): number {
    return EventBusService.POLL_INTERVAL;
  }
}