# ArkTS @Builder 装饰器使用规范——参数传递、条件渲染、复用模式、性能注意事项

> 适用项目：harmony-app（铃语，适老化股票异动播报），纯 ArkTS、零三方依赖，Stage 模型，compatibleSdkVersion 20 / targetSdk 26。
> 本文是代码技能资产，归档于 `GOVERNANCE/skills/code/`。与本文联动的项目文件：`entry/src/main/ets/pages/Index.ets`（List 卡片流）、`entry/src/main/ets/components/AlertItem.ets`（卡片组件，审查结论见同目录 A24）、`entry/src/main/ets/services/AudioPlayer.ets`（播放状态联动，见 A25）。文中 @Builder 行为描述按 ArkTS 状态管理公开文档口径书写；个别绑定边界行为存在版本差异，落地时以 DevEco 编译与真机实测为准。

---

## 一、@Builder 的定位：比自定义组件更轻的"UI 片段"

@Builder 是 ArkTS 提供的轻量级 UI 构建函数装饰器，作用是把 build 内一段可复用的 UI 结构抽成函数，在需要的位置像调用函数一样展开。它与自定义组件（@Component struct）的本质差别在"重不重"：

| 维度 | @Builder | 自定义组件 |
| --- | --- | --- |
| 实例创建 | 不创建组件实例，按函数内联展开 | 创建组件实例，进入组件树 |
| 生命周期 | 无（aboutToAppear 等不可用） | 完整生命周期回调 |
| 状态体系 | 无自身状态，依赖外部传入 | 可持有 @State/@Local 等状态 |
| this 访问 | 组件内定义可访问 this；全局定义不可 | 拥有自身 this |
| 适用场景 | 卡片内部重复小块、长列表条目拆分 | 独立交互单元、需要状态与行为契约 |

选择原则（铃语实践沉淀）：**纯展示、无自身状态、跟随父组件数据刷新的块，用 @Builder；有独立交互语义、需要被多处复用且行为各异的，用自定义组件。** 异动卡片里的"股票名+涨幅行""白话解读行""播报按钮行"属于前者；整张 AlertCard 属于后者。把这个判断做成团队的默认反射，可以避免列表渲染里最常见的过度组件化。

## 二、三种定义位置：全局 @Builder、组件内 @Builder、@LocalBuilder

### 2.1 全局 @Builder（跨文件复用）

```ts
// common/builders/LevelBadge.ets
@Builder
export function levelBadge(label: string, level: number) {
  Text(label)
    .fontSize(30)
    .fontColor(level === 1 ? '#B42318' : '#8A6116')
}
```

全局 @Builder 没有 this，不能访问任何组件状态，只适合"入参即全部"的纯渲染函数。它可以被多个页面 import，适合铃语这类全局统一视觉的小元素（如异动等级角标）。

### 2.2 组件内 @Builder（可访问 this）

```ts
@Entry
@Component
struct AlertPage {
  @State unreadCount: number = 3

  @Builder
  unreadTip() {
    if (this.unreadCount > 0) {
      Text(`有 ${this.unreadCount} 条新异动还没看`)
        .fontSize(32)
    }
  }

  build() {
    Column() {
      this.unreadTip()   // 组件内以 this.xxx() 调用
    }
  }
}
```

组件内 @Builder 可以读写 this 上的状态与方法，是默认首选位置。

### 2.3 @LocalBuilder（防止 this 丢失）

当组件内定义的构建函数要**作为参数传出去**（传给别的组件、传给全局函数）时，普通 @Builder 内部的 this 可能不再指向原组件。@LocalBuilder（API 11+）保证 this 永远绑定定义它时所在的组件。经验规则：**只在定义组件内部直接调用的，用普通 @Builder；要传出去的，用 @LocalBuilder。** 传参规则两者一致（见 §三）。

## 三、参数传递（核心规范）：按值不刷新，按引用才刷新

这是 @Builder 最容易踩、也最值得形成条件反射的一组规则：

- **规则 1：按值传递**（直接传基本类型或变量本身），状态变量变化**不会**引起 @Builder 内 UI 刷新。
- **规则 2：按引用传递**（传对象字面量，且字面量内引用了组件状态变量），状态变量变化**会**引起 @Builder 内 UI 刷新。
- **规则 3：引用传递仅支持对象字面量形式**；传入一个普通对象变量（非字面量）不触发刷新。
- **规则 4：@Builder 内修改传入参数的属性，不会回写调用方的状态变量，也不会触发调用方刷新**——@Builder 的参数永远是单向输入，不是双向通道。

### 3.1 对照示例

```ts
@Component
struct Demo {
  @State name: string = '浦发银行'

  // 反例：按值传。this.name 变化后，这一行不会刷新。
  @Builder byValue(title: string) {
    Text(title).fontSize(32)
  }

  // 正解：按引用传。this.name 变化会刷新这一块。
  @Builder byRef(p: { title: string }) {
    Text(p.title).fontSize(32)
  }

  build() {
    Column() {
      this.byValue(this.name)           // 不刷新
      this.byRef({ title: this.name })  // 刷新
      Button('模拟异动更新')
        .onClick(() => { this.name = '浦发银行 涨了 5.2%' })
    }
  }
}
```

### 3.2 工程化清单

1. 需要跟随状态联动的块 → 引用传递（对象字面量），字面量里只放真正要联动刷新的属性。
2. 传入即定型、永不联动的（如已格式化好的常量文案）→ 值传递，语义更直白。
3. 严禁在 @Builder 内修改参数属性：既不回写也不刷新，纯属埋雷。
4. 不要用"大对象字面量一把梭"——把整个页面级数据对象传给每个 @Builder，会放大绑定面、模糊刷新粒度；只传该块用到的字段。
5. 想让 @Builder 变，就去改它引用的状态变量；不要期望"改参数"改变 UI。

## 四、条件渲染中的使用

if/else 可以写在调用处，也可以直接写进 @Builder 内部；分支切换时对应节点会被重建（这是框架通用行为，@Builder 不改变它）。

```ts
@Builder
alertBody(p: { hasAudio: boolean, speak: string }) {
  Text(p.speak).fontSize(34)
  if (p.hasAudio) {
    Row() {
      Text('点喇叭，再听一遍').fontSize(28)
    }
  } else {
    Text('这条没有语音').fontSize(28).fontColor('#9E9E9E')
  }
}
```

要点：

1. 高频切换的分支（铃语播报按钮的 加载中/播放中/失败 三态行）优先把 if 收进 @Builder，让分支逻辑集中、调用处干净；
2. if 的条件值要来自引用传递的字面量里引用的状态变量，才会随状态重算；
3. @Builder 嵌套保持两层以内：卡片 @Builder 里再套子块 @Builder 可以，第三层开始可读性急剧下降，应拆组件。

## 五、复用模式：@BuilderParam 与尾随闭包

自定义组件用 @BuilderParam 接收外部注入的构建函数，实现"壳与内容分离"：

```ts
@Component
struct CardShell {
  @BuilderParam body: () => void = this.empty
  @State title: string = ''

  @Builder
  empty() {
    Text('（暂无内容）').fontSize(30)
  }

  build() {
    Column() {
      Text(this.title).fontSize(34)
      this.body()
    }
  }
}

// 用法一：尾随闭包（绑到最后一个/唯一的 @BuilderParam）
CardShell({ title: '今日异动' }) {
  Text('白话：这只股票今天涨得比较猛').fontSize(34)
}

// 用法二：显式传参（组件声明了多个 @BuilderParam 时必须用这种）
CardShell({ body: this.detailBuilder })
```

规则：

1. @BuilderParam 可设默认值，默认值必须是同 struct 内的 @Builder 方法或全局 @Builder 函数；
2. 尾随闭包一次只能绑定一个 @BuilderParam；组件声明了多个 @BuilderParam 时，必须全部显式传参，不能用尾随闭包；
3. 传入的 @Builder 函数如果内部引用了父组件状态（通过引用传递字面量），刷新仍由父组件状态驱动。

铃语复用范式：**演示卡与真实卡共用同一组 @Builder**。服务未连通时，用带"示例"字样的演示数据喂同一套构建函数，保证首屏永不空白，且大字排版（28-34fp）在任何状态下都被真实渲染逻辑校验，而不是两套代码各自漂移。

## 六、性能注意事项

1. **长列表条目优先用 @Builder 拆块，少造自定义组件。** 每多一层自定义组件，就多一次实例化与状态托管；LazyForEach 滚动期创建销毁频繁，差距被放大。卡片内部的小结构（角标、行、按钮组）用 @Builder，整卡才用组件。
2. **数据在传入前预处理。** 涨跌幅格式化、白话文案拼接、相对时间换算都在状态层完成，@Builder 与 build 内只做渲染，避免每次刷新重复计算。
3. **@Builder 保持纯函数。** 内部禁止网络请求、定时器、修改状态等副作用；副作用放事件回调或数据层。@Builder 是渲染声明，不是逻辑容器。
4. **警惕 this 丢失。** 把组件内 @Builder 当普通函数参数传出后，内部 this 不再指向原组件；要传出去就用 @LocalBuilder，或改成全局 @Builder 显式传参。
5. **刷新粒度下放。** 引用传递的字面量属性与状态变量建立绑定后，状态变化只刷新用到它的 @Builder 块。把细粒度状态（如单张卡的播放三态）下发到卡片级变量，而不是让页面级大对象的变化牵动所有块。
6. **不在 @Builder 内创建大常量结构**（长数组、深嵌套对象），提成模块级常量或组件字段，避免每次渲染重建。

## 七、铃语落地建议

1. `AlertItem` 卡片内部拆四个 @Builder：`titleRow`（股票名+涨幅，按引用传）、`levelBadge`（等级角标，值传常量）、`plainSpeakRow`（白话解读，按引用传）、`playBtnRow`（播报三态按钮行，if 收在内部）；
2. 演示卡复用同一套 @Builder，仅数据不同，落实"首屏永不空白"硬约束；
3. 全局 @Builder 只放 `common/builders/` 下无状态的纯渲染（等级角标等），组件内 @Builder 不跨文件传递，收敛 this 与刷新的心智负担；
4. 把 §3.2 与 §六 的清单纳入 code review checklist，新增卡片类组件时逐条过。

## 八、进阶：多属性字面量与刷新边界

按引用传递的对象字面量可以携带多个属性，每个被状态变量引用的属性都独立参与刷新判定。理解这一点的价值在于**控制刷新范围**：

```ts
@Builder
alertRow(p: { name: string, speak: string, playing: boolean }) {
  Column() {
    Text(p.name).fontSize(34)
    Text(p.speak).fontSize(30)
    if (p.playing) {
      Text('正在播放…').fontSize(28).fontColor('#1D4ED8')
    }
  }
}

// 调用点
this.alertRow({
  name: this.feed.items[i].stockName,     // 引用状态 → 参与刷新
  speak: this.feed.items[i].plainSpeak,   // 引用状态 → 参与刷新
  playing: this.playingId === this.feed.items[i].id  // 派生表达式
})
```

边界说明：字面量的形状在调用点固定，**不能在运行时增删属性**；字面量内的派生表达式（如上例的布尔判断）会在所引用的状态变化时重新求值。若把"不需要联动"的常量也塞进同一个字面量，虽然不会引起额外刷新，但会让读代码的人误以为它参与联动——**字面量里只放真正要联动的字段，常量走值传参或组件内字段**。另一个常见疑问是嵌套字面量：外层与内层属性各自建立绑定，但层级越深可读性越差，两 层封顶，再深就该拆组件或先整理状态结构。

## 九、常见错误模式速查

| 现象 | 根因 | 修法 |
| --- | --- | --- |
| @Builder 内文字不随状态更新 | 按值传参 | 改对象字面量引用传参 |
| 传了对象还是不刷新 | 传的是普通对象变量而非字面量 | 在调用点写字面量，属性引用状态变量 |
| @Builder 里改参数属性，UI 与调用方都没变 | 参数是单向输入 | 修改逻辑移到事件回调里改状态变量 |
| 组件内 @Builder 传出后行为异常（this 为空） | this 丢失 | 换 @LocalBuilder 或全局 @Builder 显式传参 |
| 尾随闭包不生效 | 组件声明了多个 @BuilderParam | 全部改为显式传参 |
| 列表滚动卡顿，帧率掉 | 条目套了多层自定义组件 | 条目内小块降为 @Builder，条目整体加 @Reusable |
| @Builder 内发起请求/改状态后界面诡异刷新 | 把渲染函数当生命周期用 | 副作用移出 @Builder |

这张表的定位是评审速查：出现左列现象时直接对照中列定位，不必重新推演绑定规则。

## 十、完整示例：铃语卡片参考实现

把前文规则收拢成一套可直接抄的骨架（与 A24 审查的 AlertItem 现状对照，属建议形态而非现状描述）：

```ts
@Component
struct AlertCard {
  @Prop alert: AlertItem          // 现状为 V1；迁 V2 后换 @Param
  @Link playingId: string         // 页面级三态，双向
  @Builder
  titleRow(p: { name: string, pct: string }) {
    Row() {
      Text(p.name).fontSize(34).fontWeight(FontWeight.Bold)
      Text(p.pct).fontSize(34).fontColor(p.pct.startsWith('跌') ? '#16A34A' : '#B42318')
    }.width('100%')
  }
  @Builder
  playBtnRow(p: { id: string }) {
    Button(this.playingId === p.id ? '正在播，再点一下停' : '点喇叭，听这条')
      .fontSize(30).height(72)
      .onClick(() => this.toggle(p.id))
  }
  build() {
    Column({ space: 10 }) {
      this.titleRow({ name: this.alert.stockName, pct: this.alert.pctText })
      Text(this.alert.plainSpeak).fontSize(32)   // 白话解读
      this.playBtnRow({ id: this.alert.id })
    }.padding(16)
  }
}
```

注意三个细节：标题行与按钮行各自用字面量引用了会变的状态；涨幅文案与颜色判断放在渲染前的数据层预处理；按钮文案的三态切换只依赖 playingId 一条状态线，刷新面最小。

## 十一、与 V1/V2 状态体系的协作

@Builder 的传参规则不随组件范式变化，但配合方式有讲究：V1 组件里，@Builder 引用 @State/@Prop/@Link 的字面量属性均可联动；V2 组件（@ComponentV2）里，@ObservedV2 类的 @Trace 属性被字面量引用后同样获得属性级精确刷新，且粒度比 V1 更细——这正是 E2 推荐先迁数据层的原因：数据类换上 @Trace 后，@Builder 的字面量引用立刻从"整对象感知"升级为"单属性感知"，无需改动任何 @Builder 代码。反过来也有一个提醒：无论 V1 还是 V2，@Builder 都不持有状态，**不要试图通过给 @Builder 加装饰器来"让它自己有状态"**——需要内部状态的那块 UI，从第一天起就应该是组件而不是 @Builder。

### 自我评估
- 正确性：4分 值/引用传递刷新规则、@BuilderParam 默认值与尾随闭包限制、@LocalBuilder 定位均按官方口径书写；引用传递的部分绑定边界行为官方文档存在版本差异，已明确提示以编译实测为准，未夸大为确定结论。
- 完整性：4分 任务指定的参数传递、条件渲染、复用模式、性能四主题全部覆盖，含对比表、正反例代码与工程清单；未展开 @Builder 与动画、手势组合的边缘用法（与本项目场景无关）。
- 可复用性：4分 规则以清单与反例形式组织，可直接进 code review checklist；示例贴合铃语卡片流场景，项目锚点与联动文档路径明确。
- 字数：约3100字
- 使用模型：GLM-5.3-Flash
