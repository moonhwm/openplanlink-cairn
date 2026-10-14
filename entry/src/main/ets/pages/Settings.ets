
import { hilog } from '@kit.PerformanceAnalysisKit';
import { SettingsService, FontSizeLevel, ThemeMode, ThemeColors, DEFAULT_FEED_URL, PlayHistoryItem } from '../services/SettingsService';

const TAG = 'StockPulse.Settings';
const DOMAIN = 0x0001;


@Component
export struct Settings {
  @State watchlist: string[] = [];
  @State broadcastEnabled: boolean = true;
  @State fontLevel: FontSizeLevel = 'standard';
  @State elderlyMode: boolean = true;
  @State themeMode: ThemeMode = 'night';
  @State autoThemeEnabled: boolean = true;
  @State dndEnabled: boolean = false;
  @State dndStartHour: number = 22;
  @State dndEndHour: number = 8;
  @State newStockInput: string = '';
  @State feedUrl: string = DEFAULT_FEED_URL;
  @State playHistory: PlayHistoryItem[] = [];
  private navStack: NavPathStack | null = null;

  // 字体档驱动字号
  private get titleSize(): number {
    return this.fontLevel === 'large' ? 40 : 34;
  }
  private get bodySize(): number {
    return this.fontLevel === 'large' ? 34 : 28;
  }
  private get labelSize(): number {
    return this.fontLevel === 'large' ? 26 : 22;
  }
  private get inputSize(): number {
    return this.fontLevel === 'large' ? 28 : 24;
  }

  // 主题颜色
  private get theme(): ThemeColors {
    return SettingsService.getThemeColors(this.themeMode);
  }

  aboutToAppear(): void {
    this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    this.watchlist = await SettingsService.getWatchlist();
    this.broadcastEnabled = await SettingsService.getBroadcastEnabled();
    this.elderlyMode = await SettingsService.getElderlyMode();
    this.fontLevel = await SettingsService.getFontSizeLevel();
    this.autoThemeEnabled = await SettingsService.getAutoThemeEnabled();
    if (this.autoThemeEnabled) {
      this.themeMode = SettingsService.computeAutoThemeMode();
    } else {
      this.themeMode = await SettingsService.getThemeMode();
    }
    this.dndEnabled = await SettingsService.getDndEnabled();
    this.dndStartHour = await SettingsService.getDndStartHour();
    this.dndEndHour = await SettingsService.getDndEndHour();
    this.feedUrl = await SettingsService.getFeedUrl();
    this.playHistory = await SettingsService.getPlayHistory();
  }

  private async addStock(): Promise<void> {
    const code = this.newStockInput.trim();
    if (code.length === 0) {
      return;
    }
    if (this.watchlist.includes(code)) {
      return;
    }
    this.watchlist = [...this.watchlist, code];
    this.newStockInput = '';
    await SettingsService.setWatchlist(this.watchlist);
    hilog.info(DOMAIN, TAG, `added stock ${code}, watchlist now ${this.watchlist.length} items`);
  }

  private async removeStock(code: string): Promise<void> {
    this.watchlist = this.watchlist.filter((s) => s !== code);
    await SettingsService.setWatchlist(this.watchlist);
    hilog.info(DOMAIN, TAG, `removed stock ${code}, watchlist now ${this.watchlist.length} items`);
  }

  private async toggleBroadcast(isOn: boolean): Promise<void> {
    this.broadcastEnabled = isOn;
    await SettingsService.setBroadcastEnabled(this.broadcastEnabled);
    hilog.info(DOMAIN, TAG, `broadcast ${this.broadcastEnabled ? 'enabled' : 'disabled'}`);
  }

  private async switchFontLevel(level: FontSizeLevel): Promise<void> {
    this.fontLevel = level;
    await SettingsService.setFontSizeLevel(level);
    hilog.info(DOMAIN, TAG, `font level set to ${level}`);
  }

  private async toggleElderlyMode(isOn: boolean): Promise<void> {
    this.elderlyMode = isOn;
    await SettingsService.setElderlyMode(isOn);
    this.fontLevel = await SettingsService.getFontSizeLevel();
    hilog.info(DOMAIN, TAG, `elderly mode ${isOn ? 'enabled' : 'disabled'}`);
  }

  private async toggleThemeMode(isDay: boolean): Promise<void> {
    // 手动选择夜间/白天时关闭自动主题
    this.autoThemeEnabled = false;
    this.themeMode = isDay ? 'day' : 'night';
    await SettingsService.setAutoThemeEnabled(false);
    await SettingsService.setThemeMode(this.themeMode);
    hilog.info(DOMAIN, TAG, `theme mode set to ${this.themeMode}, auto theme disabled`);
  }

  private async toggleAutoTheme(isOn: boolean): Promise<void> {
    this.autoThemeEnabled = isOn;
    await SettingsService.setAutoThemeEnabled(isOn);
    if (isOn) {
      this.themeMode = SettingsService.computeAutoThemeMode();
      hilog.info(DOMAIN, TAG, `auto theme enabled, computed mode: ${this.themeMode}`);
    } else {
      hilog.info(DOMAIN, TAG, `auto theme disabled`);
    }
  }

  private async adjustDndStartHour(delta: number): Promise<void> {
    let newHour = this.dndStartHour + delta;
    if (newHour < 0) { newHour = 23; }
    if (newHour > 23) { newHour = 0; }
    this.dndStartHour = newHour;
    await SettingsService.setDndStartHour(newHour);
    hilog.info(DOMAIN, TAG, `dnd start hour set to ${newHour}`);
  }

  private async adjustDndEndHour(delta: number): Promise<void> {
    let newHour = this.dndEndHour + delta;
    if (newHour < 0) { newHour = 23; }
    if (newHour > 23) { newHour = 0; }
    this.dndEndHour = newHour;
    await SettingsService.setDndEndHour(newHour);
    hilog.info(DOMAIN, TAG, `dnd end hour set to ${newHour}`);
  }

  private async saveFeedUrl(): Promise<void> {
    // F-004修复：URL格式校验——必须以http://或https://开头
    if (!this.feedUrl.startsWith('http://') && !this.feedUrl.startsWith('https://')) {
      hilog.warn(DOMAIN, TAG, `feed url invalid format: ${this.feedUrl}`);
      return;
    }
    await SettingsService.setFeedUrl(this.feedUrl);
    hilog.info(DOMAIN, TAG, `feed url set to ${this.feedUrl}`);
  }

  private async toggleDnd(isOn: boolean): Promise<void> {
    this.dndEnabled = isOn;
    await SettingsService.setDndEnabled(this.dndEnabled);
    hilog.info(DOMAIN, TAG, `dnd ${isOn ? 'enabled' : 'disabled'}`);
  }

  /** 相对时间格式化：将毫秒时间戳转为"刚刚/N分钟前/N小时前" */
  private relTime(ts: number): string {
    if (ts === 0) {
      return '';
    }
    const now = Date.now();
    const diff = Math.floor((now - ts) / 1000);
    if (diff < 60) {
      return '刚刚';
    }
    if (diff < 3600) {
      return `${Math.floor(diff / 60)}分钟前`;
    }
    if (diff < 86400) {
      return `${Math.floor(diff / 3600)}小时前`;
    }
    return `${Math.floor(diff / 86400)}天前`;
  }

  build() {
    NavDestination() {
      Column() {
        // 顶栏：返回按钮 + 标题
        Row() {
          Text('← 返回')
            .fontSize(this.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.accentGold)
            .onClick(() => {
              if (this.navStack) {
                this.navStack.pop();
              }
            })
            .padding({ left: 8, right: 8, top: 8, bottom: 8 })
            .constraintSize({ minWidth: 48, minHeight: 48 })
          Text('设置')
            .fontSize(this.titleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.textPrimary)
            .margin({ left: 16 })
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 16, bottom: 12 })

        Scroll() {
          Column({ space: 24 }) {
            // ── 显示模式（夜间/白天/自动） ──
            Column({ space: 12 }) {
              Text('显示模式')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Button('自动')
                  .fontSize(this.labelSize)
                  .fontColor(this.autoThemeEnabled ? Color.White : this.theme.textPrimary)
                  .backgroundColor(this.autoThemeEnabled ? this.theme.accentGold : this.theme.cardBackground)
                  .borderWidth(1)
                  .borderColor(this.autoThemeEnabled ? this.theme.accentGold : this.theme.textSecondary)
                  .height(48)
                  .layoutWeight(1)
                  .onClick(() => this.toggleAutoTheme(true))
                Button('夜间')
                  .fontSize(this.labelSize)
                  .fontColor(!this.autoThemeEnabled && this.themeMode === 'night' ? Color.White : this.theme.textPrimary)
                  .backgroundColor(!this.autoThemeEnabled && this.themeMode === 'night' ? this.theme.accentGold : this.theme.cardBackground)
                  .borderWidth(1)
                  .borderColor(!this.autoThemeEnabled && this.themeMode === 'night' ? this.theme.accentGold : this.theme.textSecondary)
                  .height(48)
                  .layoutWeight(1)
                  .margin({ left: 8 })
                  .onClick(() => this.toggleThemeMode(false))
                Button('白天')
                  .fontSize(this.labelSize)
                  .fontColor(!this.autoThemeEnabled && this.themeMode === 'day' ? Color.White : this.theme.textPrimary)
                  .backgroundColor(!this.autoThemeEnabled && this.themeMode === 'day' ? this.theme.accentGold : this.theme.cardBackground)
                  .borderWidth(1)
                  .borderColor(!this.autoThemeEnabled && this.themeMode === 'day' ? this.theme.accentGold : this.theme.textSecondary)
                  .height(48)
                  .layoutWeight(1)
                  .margin({ left: 8 })
                  .onClick(() => this.toggleThemeMode(true))
              }
              .width('100%')

              Text(this.autoThemeEnabled ?
                '自动模式：6:00-18:00 白天，18:00-6:00 夜间，随系统时间自动切换' :
                this.themeMode === 'night' ?
                '夜间模式：深色底，高对比，护眼省电' :
                '白天模式：浅色底，清晰明亮，适合日间')
                .fontSize(this.labelSize)
                .fontColor(this.theme.textSecondary)
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 适老化模式 ──
            Column({ space: 12 }) {
              Text('适老化模式')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.elderlyMode ? '适老化已开' : '正常模式')
                  .fontSize(this.bodySize)
                  .fontColor(this.elderlyMode ? this.theme.accentGold : this.theme.textPrimary)
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.elderlyMode })
                  .onChange((isOn: boolean) => this.toggleElderlyMode(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              Text(this.elderlyMode ?
                '适老化模式：大字大卡，点卡即听，界面极简' :
                '正常模式：标准字体，紧凑布局，信息更密')
                .fontSize(this.labelSize)
                .fontColor(this.theme.textSecondary)
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 免打扰模式 ──
            Column({ space: 12 }) {
              Text('免打扰')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.dndEnabled ? '免打扰已开' : '免打扰关')
                  .fontSize(this.bodySize)
                  .fontColor(this.dndEnabled ? this.theme.accentGold : this.theme.textPrimary)
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.dndEnabled })
                  .onChange((isOn: boolean) => this.toggleDnd(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              if (this.dndEnabled) {
                // 时段调整：开始时间
                Row() {
                  Text('开始')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textSecondary)
                    .width(60)
                  Button('-')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textPrimary)
                    .backgroundColor(this.theme.pageBackground)
                    .borderWidth(1)
                    .borderColor(this.theme.textSecondary)
                    .width(48)
                    .height(48)
                    .onClick(() => this.adjustDndStartHour(-1))
                  Text(`${this.dndStartHour}:00`)
                    .fontSize(this.bodySize)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(this.theme.accentGold)
                    .textAlign(TextAlign.Center)
                    .layoutWeight(1)
                  Button('+')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textPrimary)
                    .backgroundColor(this.theme.pageBackground)
                    .borderWidth(1)
                    .borderColor(this.theme.textSecondary)
                    .width(48)
                    .height(48)
                    .onClick(() => this.adjustDndStartHour(1))
                }
                .width('100%')

                // 时段调整：结束时间
                Row() {
                  Text('结束')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textSecondary)
                    .width(60)
                  Button('-')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textPrimary)
                    .backgroundColor(this.theme.pageBackground)
                    .borderWidth(1)
                    .borderColor(this.theme.textSecondary)
                    .width(48)
                    .height(48)
                    .onClick(() => this.adjustDndEndHour(-1))
                  Text(`${this.dndEndHour}:00`)
                    .fontSize(this.bodySize)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(this.theme.accentGold)
                    .textAlign(TextAlign.Center)
                    .layoutWeight(1)
                  Button('+')
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textPrimary)
                    .backgroundColor(this.theme.pageBackground)
                    .borderWidth(1)
                    .borderColor(this.theme.textSecondary)
                    .width(48)
                    .height(48)
                    .onClick(() => this.adjustDndEndHour(1))
                }
                .width('100%')

                Text('免打扰时段内，推送通知的自动播报将静默；卡片仍可手动点按收听')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 自选股管理 ──
            Column({ space: 12 }) {
              Text('自选股管理')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                TextInput({ placeholder: '输入股票代码' })
                  .fontSize(this.inputSize)
                  .fontColor(this.theme.textPrimary)
                  .placeholderColor(this.theme.textSecondary)
                  .layoutWeight(1)
                  .height(48)
                  .onChange((value: string) => {
                    this.newStockInput = value;
                  })
                Button('添加')
                  .fontSize(this.labelSize)
                  .fontColor(Color.White)
                  .backgroundColor(this.theme.accentGold)
                  .height(48)
                  .margin({ left: 12 })
                  .onClick(() => this.addStock())
              }
              .width('100%')

              if (this.watchlist.length > 0) {
                ForEach(this.watchlist, (code: string) => {
                  Row() {
                    Text(code)
                      .fontSize(this.bodySize)
                      .fontColor(this.theme.textPrimary)
                      .layoutWeight(1)
                    Text('删除')
                      .fontSize(this.labelSize)
                      .fontColor(this.theme.riseRed)
                      .padding({ left: 12, right: 12, top: 8, bottom: 8 })
                      .constraintSize({ minWidth: 48, minHeight: 48 })
                      .onClick(() => this.removeStock(code))
                  }
                  .width('100%')
                  .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                  .backgroundColor(this.theme.pageBackground)
                  .borderRadius(12)
                }, (code: string) => code)
              } else {
                Text('暂无自选股，添加后只显示关注的股票')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
                  .textAlign(TextAlign.Center)
                  .padding({ top: 16, bottom: 16 })
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 播报开关 ──
            Column({ space: 12 }) {
              Text('播报开关')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.broadcastEnabled ? '播报已开' : '播报关')
                  .fontSize(this.bodySize)
                  .fontColor(this.broadcastEnabled ? this.theme.textPrimary : this.theme.riseRed)
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.broadcastEnabled })
                  .onChange((isOn: boolean) => this.toggleBroadcast(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              if (!this.broadcastEnabled) {
                Text('播报关后，通知拉起的自动播报将静默；卡片仍可手动点按收听')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 字体大小（适老化模式开启时锁定特大） ──
            Column({ space: 12 }) {
              Text('字体大小')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              if (this.elderlyMode) {
                Row() {
                  Text('特大（适老化模式锁定）')
                    .fontSize(this.bodySize)
                    .fontColor(this.theme.accentGold)
                    .layoutWeight(1)
                }
                .width('100%')
                .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                .backgroundColor(this.theme.pageBackground)
                .borderRadius(12)
              } else {
                Row() {
                  Button('标准')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'standard' ? Color.White : this.theme.textPrimary)
                    .backgroundColor(this.fontLevel === 'standard' ? this.theme.accentGold : this.theme.cardBackground)
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'standard' ? this.theme.accentGold : this.theme.textSecondary)
                    .height(48)
                    .layoutWeight(1)
                    .onClick(() => this.switchFontLevel('standard'))
                  Button('特大')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'large' ? Color.White : this.theme.textPrimary)
                    .backgroundColor(this.fontLevel === 'large' ? this.theme.accentGold : this.theme.cardBackground)
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'large' ? this.theme.accentGold : this.theme.textSecondary)
                    .height(48)
                    .layoutWeight(1)
                    .margin({ left: 12 })
                    .onClick(() => this.switchFontLevel('large'))
                }
                .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 数据源地址 ──
            Column({ space: 12 }) {
              Text('数据源地址')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              TextInput({ text: this.feedUrl, placeholder: 'http://...' })
                .fontSize(this.inputSize)
                .fontColor(this.theme.textPrimary)
                .placeholderColor(this.theme.textSecondary)
                .height(48)
                .width('100%')
                .onChange((value: string) => {
                  this.feedUrl = value;
                })

              Button('保存')
                .fontSize(this.labelSize)
                .fontColor(Color.White)
                .backgroundColor(this.theme.accentGold)
                .height(48)
                .width('100%')
                .onClick(() => this.saveFeedUrl())

              Text('X 服务器落地后替换为正式地址；本机联调可填局域网 IP')
                .fontSize(this.labelSize)
                .fontColor(this.theme.textSecondary)
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 播报历史 ──
            Column({ space: 12 }) {
              Text('播报历史')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              if (this.playHistory.length > 0) {
                ForEach(this.playHistory.slice(0, 20), (item: PlayHistoryItem) => {
                  Row() {
                    Column() {
                      Text(item.name)
                        .fontSize(this.labelSize)
                        .fontColor(this.theme.textPrimary)
                        .maxLines(1)
                        .textOverflow({ overflow: TextOverflow.Ellipsis })
                      Text(item.headline)
                        .fontSize(this.labelSize)
                        .fontColor(this.theme.textSecondary)
                        .maxLines(1)
                        .textOverflow({ overflow: TextOverflow.Ellipsis })
                        .margin({ top: 4 })
                    }
                    .layoutWeight(1)
                    .alignItems(HorizontalAlign.Start)

                    Text(this.relTime(item.ts))
                      .fontSize(this.labelSize)
                      .fontColor(this.theme.textSecondary)
                      .margin({ left: 8 })
                  }
                  .width('100%')
                  .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                  .backgroundColor(this.theme.pageBackground)
                  .borderRadius(12)
                }, (item: PlayHistoryItem) => item.alertId)

                if (this.playHistory.length > 20) {
                  Text(`共 ${this.playHistory.length} 条，仅显示最近 20 条`)
                    .fontSize(this.labelSize)
                    .fontColor(this.theme.textSecondary)
                    .width('100%')
                    .textAlign(TextAlign.Center)
                    .margin({ top: 8 })
                }
              } else {
                Text('暂无播报历史')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
                  .textAlign(TextAlign.Center)
                  .padding({ top: 16, bottom: 16 })
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)
          }
          .width('100%')
          .padding({ left: 16, right: 16 })
        }
        .width('100%')
        .layoutWeight(1)
      }
      .width('100%')
      .height('100%')
      .backgroundColor(this.theme.pageBackground)
    }
    .hideTitleBar(true)
    .onReady((context: NavDestinationContext) => {
      this.navStack = context.pathStack
    })
  }
}
