/**
 * A2A IM GUI 看板页面
 * 展示各席位状态、行为轨迹、审计信息
 * 数据源：幻16节点注册中心 (http://120.46.86.165:4174)
 * 规范：FS-20261005-01 A2A看板接入真实事件总线数据
 */

import { EventBusService, SeatState, SeatInfo, EventLogEntry, AuditEntry } from '../services/EventBusService';

// 状态颜色映射
function getStateColor(state: SeatState): string {
  switch (state) {
    case SeatState.IDLE:
      return '#888888';     // 灰色
    case SeatState.THINKING:
      return '#45B7D1';     // 蓝色
    case SeatState.ACTING:
      return '#4ECDC4';     // 绿色
    case SeatState.SYNCING:
      return '#FFD93D';     // 黄色
    case SeatState.ERROR:
      return '#FF6B6B';     // 红色
    default:
      return '#888888';
  }
}

// 状态图标映射
function getStateIcon(state: SeatState): string {
  switch (state) {
    case SeatState.IDLE:
      return '⏸';
    case SeatState.THINKING:
      return '🧠';
    case SeatState.ACTING:
      return '⚡';
    case SeatState.SYNCING:
      return '🔄';
    case SeatState.ERROR:
      return '❌';
    default:
      return '⏸';
  }
}

// 优先级颜色映射
function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'CRITICAL':
      return '#FF6B6B';
    case 'HIGH':
      return '#FF6B35';
    case 'NORMAL':
      return '#4ECDC4';
    case 'LOW':
      return '#888888';
    default:
      return '#888888';
  }
}

// 审计结果颜色映射
function getAuditResultColor(result: string): string {
  switch (result) {
    case 'success':
      return '#4ECDC4';
    case 'failure':
      return '#FF6B6B';
    case 'warning':
      return '#FFD93D';
    default:
      return '#888888';
  }
}

@Component
struct A2ADashboard {
  // 真实数据状态（从节点注册中心拉取）
  @State seats: SeatInfo[] = [];
  @State events: EventLogEntry[] = [];
  @State audits: AuditEntry[] = [];
  @State currentTab: number = 0; // 0=席位状态, 1=事件日志, 2=审计轨迹
  @State selectedSeat: string = '';
  @State isRefreshing: boolean = false;
  @State connectionStatus: 'connected' | 'disconnected' = 'disconnected';
  @State lastFetchTime: string = '';
  @State hasInitiallyLoaded: boolean = false;
  private navStack: NavPathStack | null = null;
  private pollTimerId: number = -1;

  // 5秒轮询拉取数据
  private startPolling(): void {
    this.fetchData();
    this.pollTimerId = setInterval(() => {
      this.fetchData();
    }, EventBusService.getPollInterval());
  }

  private stopPolling(): void {
    if (this.pollTimerId !== -1) {
      clearInterval(this.pollTimerId);
      this.pollTimerId = -1;
    }
  }

  // 拉取真实数据
  private async fetchData(): Promise<void> {
    const result = await EventBusService.fetchDashboardData();
    this.connectionStatus = result.connectionStatus;
    this.lastFetchTime = new Date().toLocaleTimeString();

    if (result.ok) {
      this.seats = result.seats;
      this.events = result.events;
      this.audits = result.audits;
    }
    // 连接失败时保留上次成功获取的数据（规范验收条件#3）
    this.hasInitiallyLoaded = true;
    this.isRefreshing = false;
  }

  // 手动刷新
  private async manualRefresh(): Promise<void> {
    this.isRefreshing = true;
    await this.fetchData();
  }

  // 构建席位状态卡片
  @Builder
  SeatCard(seat: SeatInfo) {
    Column() {
      // 头像 + 状态指示
      Row() {
        // 头像圆圈
        Stack() {
          Circle()
            .width(48)
            .height(48)
            .fill(seat.avatarColor)
          Text(seat.name.charAt(0))
            .fontSize(20)
            .fontColor(Color.White)
            .fontWeight(FontWeight.Bold)
        }
        .width(48)
        .height(48)

        // 状态指示灯
        Stack() {
          Circle()
            .width(12)
            .height(12)
            .fill(getStateColor(seat.state))
          if (seat.state === SeatState.THINKING || seat.state === SeatState.SYNCING) {
            Circle()
              .width(12)
              .height(12)
              .fill(getStateColor(seat.state))
              .opacity(0.4)
              .scale({ x: 1.5, y: 1.5 })
              .animation({
                duration: 1000,
                iterations: -1,
                curve: Curve.EaseInOut,
              })
          }
        }
        .width(12)
        .height(12)
        .margin({ left: 4 })

        // 席位名称和角色
        Column() {
          Text(seat.name)
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .fontColor('#E0E0E0')
          Text(seat.role)
            .fontSize(12)
            .fontColor('#AAAAAA')
        }
        .alignItems(HorizontalAlign.Start)
        .margin({ left: 8 })

        Blank()

        // 状态图标
        Text(getStateIcon(seat.state))
          .fontSize(20)
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 10, bottom: 6 })

      // 统计信息
      Row() {
        Column() {
          Text('已完成')
            .fontSize(10)
            .fontColor('#AAAAAA')
          Text(`${seat.tasksCompleted}`)
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor('#E0E0E0')
        }
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('进行中')
            .fontSize(10)
            .fontColor('#AAAAAA')
          Text(`${seat.tasksInProgress}`)
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor(getStateColor(seat.state))
        }
        .alignItems(HorizontalAlign.Center)
        .margin({ left: 20 })

        Blank()

        Text(seat.lastActive)
          .fontSize(10)
          .fontColor('#888888')
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 4, bottom: 10 })
    }
    .width('100%')
    .backgroundColor('#1A1A2E')
    .borderRadius(12)
    .border({
      width: 1,
      color: seat.state === SeatState.ACTING ? getStateColor(seat.state) : '#333355',
    })
    .margin({ bottom: 8 })
    .onClick(() => {
      this.selectedSeat = seat.name;
    })
  }

  // 构建事件日志条目
  @Builder
  EventLogEntryView(entry: EventLogEntry) {
    Row() {
      // 优先级指示条
      Column() {
        Rect()
          .width(3)
          .height('100%')
          .fill(getPriorityColor(entry.priority))
      }
      .width(3)
      .height(40)
      .margin({ right: 8 })

      // 时间戳
      Text(entry.timestamp)
        .fontSize(11)
        .fontColor('#888888')
        .width(60)

      // 席位名
      Text(entry.seatName)
        .fontSize(12)
        .fontWeight(FontWeight.Bold)
        .fontColor('#E0E0E0')
        .width(40)

      // 事件描述
      Column() {
        Text(entry.eventType)
          .fontSize(10)
          .fontColor(getPriorityColor(entry.priority))
        Text(entry.description)
          .fontSize(12)
          .fontColor('#CCCCCC')
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 4 })

      Blank()

      Text(entry.eventId)
        .fontSize(9)
        .fontColor('#666666')
    }
    .width('100%')
    .height(48)
    .padding({ left: 8, right: 8 })
    .backgroundColor('#1A1A2E')
    .borderRadius(8)
    .margin({ bottom: 4 })
  }

  // 构建审计轨迹条目
  @Builder
  AuditEntryView(entry: AuditEntry) {
    Row() {
      // 结果指示
      Circle()
        .width(8)
        .height(8)
        .fill(getAuditResultColor(entry.result))
        .margin({ right: 8 })

      // 时间戳
      Text(entry.timestamp)
        .fontSize(11)
        .fontColor('#888888')
        .width(60)

      // 席位名
      Text(entry.seatName)
        .fontSize(12)
        .fontWeight(FontWeight.Bold)
        .fontColor('#E0E0E0')
        .width(40)

      // 操作描述
      Column() {
        Text(entry.action)
          .fontSize(12)
          .fontColor('#CCCCCC')
          .fontWeight(FontWeight.Medium)
        Text(entry.detail)
          .fontSize(10)
          .fontColor('#888888')
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 4 })
    }
    .width('100%')
    .height(48)
    .padding({ left: 8, right: 8 })
    .backgroundColor('#1A1A2E')
    .borderRadius(8)
    .margin({ bottom: 4 })
  }

  // 空状态提示
  @Builder
  EmptyState(message: string) {
    Column() {
      Text('📋')
        .fontSize(32)
        .margin({ bottom: 8 })
      Text(message)
        .fontSize(14)
        .fontColor('#888888')
    }
    .width('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .padding({ top: 40, bottom: 40 })
  }

  // 连接中断提示
  @Builder
  DisconnectedBanner() {
    Row() {
      Circle()
        .width(8)
        .height(8)
        .fill('#FF6B6B')
      Text('连接中断 — 节点注册中心不可达，显示最后缓存数据')
        .fontSize(12)
        .fontColor('#FF6B6B')
        .margin({ left: 4 })
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 6, bottom: 6 })
    .backgroundColor('#2A1A1A')
    .borderRadius(8)
    .margin({ left: 16, right: 16, bottom: 8 })
  }

  build() {
    NavDestination() {
    Column() {
      // 标题栏
      Row() {
        // 返回按钮
        Text('← 返回')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor('#4ECDC4')
          .onClick(() => {
            if (this.navStack) {
              this.navStack.pop();
            }
          })
          .padding({ left: 8, right: 8, top: 8, bottom: 8 })
          .constraintSize({ minWidth: 48, minHeight: 48 })

        Text('A2A IM GUI 看板')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor('#E0E0E0')
          .margin({ left: 8 })

        Blank()

        // 刷新按钮
        Button() {
          Row() {
            if (this.isRefreshing) {
              LoadingProgress()
                .width(16)
                .height(16)
                .color('#4ECDC4')
            } else {
              Text('🔄')
                .fontSize(14)
            }
            Text('刷新')
              .fontSize(12)
              .fontColor('#E0E0E0')
              .margin({ left: 4 })
          }
        }
        .height(32)
        .backgroundColor('#333355')
        .borderRadius(8)
        .onClick(() => {
          this.manualRefresh();
        })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 8 })

      // 网络状态指示（连接中断时显示红色banner）
      if (this.connectionStatus === 'disconnected' && this.hasInitiallyLoaded) {
        this.DisconnectedBanner()
      }

      // 网络状态指示
      Row() {
        Circle()
          .width(8)
          .height(8)
          .fill(this.connectionStatus === 'connected' ? '#4ECDC4' : '#FF6B6B')
        Text(this.connectionStatus === 'connected' ? 'A2A网络：在线' : 'A2A网络：中断')
          .fontSize(12)
          .fontColor(this.connectionStatus === 'connected' ? '#4ECDC4' : '#FF6B6B')
          .margin({ left: 4 })

        Blank()

        if (this.lastFetchTime) {
          Text(`最后更新: ${this.lastFetchTime}`)
            .fontSize(12)
            .fontColor('#888888')
        }
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 4, bottom: 8 })

      // Tab切换
      Row() {
        ForEach(['席位状态', '事件日志', '审计轨迹'], (tabName: string, index?: number) => {
          Button(tabName)
            .fontSize(14)
            .fontColor(this.currentTab === index ? '#4ECDC4' : '#888888')
            .backgroundColor(this.currentTab === index ? '#1A3A3A' : '#1A1A2E')
            .borderRadius(8)
            .height(36)
            .onClick(() => {
              this.currentTab = index ?? 0;
            })
        }, (tabName: string) => tabName)
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceEvenly)
      .padding({ left: 8, right: 8, top: 4, bottom: 8 })

      // 内容区域
      Scroll() {
        Column() {
          if (this.currentTab === 0) {
            // 席位状态
            if (this.seats.length === 0 && this.hasInitiallyLoaded) {
              this.EmptyState('暂无在线席位')
            } else {
              ForEach(this.seats, (seat: SeatInfo) => {
                this.SeatCard(seat)
              }, (seat: SeatInfo) => seat.name)
            }

            // 选中席位详情
            if (this.selectedSeat) {
              Column() {
                Text(`${this.selectedSeat} 席位详情`)
                  .fontSize(14)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#E0E0E0')
                  .margin({ top: 12, bottom: 8 })

                // 席位行为轨迹
                const seatEvents = this.events.filter(e => e.seatName === this.selectedSeat);
                if (seatEvents.length === 0) {
                  Text('暂无该席位的事件记录')
                    .fontSize(12)
                    .fontColor('#888888')
                } else {
                  ForEach(seatEvents, (entry: EventLogEntry) => {
                    this.EventLogEntryView(entry)
                  }, (entry: EventLogEntry) => entry.eventId)
                }
              }
              .width('100%')
              .padding({ left: 16, right: 16 })
            }
          } else if (this.currentTab === 1) {
            // 事件日志
            if (this.events.length === 0 && this.hasInitiallyLoaded) {
              this.EmptyState('暂无事件')
            } else {
              ForEach(this.events, (entry: EventLogEntry) => {
                this.EventLogEntryView(entry)
              }, (entry: EventLogEntry) => entry.eventId)
            }
          } else {
            // 审计轨迹
            if (this.audits.length === 0 && this.hasInitiallyLoaded) {
              this.EmptyState('暂无审计记录')
            } else {
              ForEach(this.audits, (entry: AuditEntry) => {
                this.AuditEntryView(entry)
              }, (entry: AuditEntry) => entry.timestamp)
            }
          }
        }
        .padding({ left: 16, right: 16 })
      }
      .layoutWeight(1)
      .scrollBar(BarState.Auto)

      // 底部状态栏
      Row() {
        Text('砚坚席 · A2A治理实验')
          .fontSize(10)
          .fontColor('#666666')

        Blank()

        Text(this.lastFetchTime || '等待数据...')
          .fontSize(10)
          .fontColor('#666666')
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 6, bottom: 6 })
      .backgroundColor('#0F0F1A')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#0F0F1A')
    }
    .hideTitleBar(true)
    .onReady((context: NavDestinationContext) => {
      this.navStack = context.pathStack
    })
    .onShown(() => {
      this.startPolling();
    })
    .onHidden(() => {
      this.stopPolling();
    })
  }
}