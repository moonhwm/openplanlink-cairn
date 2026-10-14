# SDD规范驱动开发方案——AI时代的软件工程新范式

- 档号：DF-SDD-2026-1005-YANJIAN-01
- 拟稿席：砚坚（挂帅席/神经中枢）
- 日期：2026-10-05T16:00 CST
- 体例：党组学术技术成员视角
- 参考资源：Claude Code Docs、SDD规范驱动开发博客、HuggingFace Spaces、IBM CI/CD文档、MVP概念

## 一、SDD范式定义

### （一）核心理念

SDD（Spec-Driven Development，规范驱动开发）是AI时代的软件工程新范式，其核心原则为：

1. **规范先行**：在编写任何代码之前，先以结构化文档明确功能规范（What），再由AI工具根据规范驱动代码实现（How）
2. **可验证契约**：规范不仅是描述性文档，更是可自动验证的工程契约——每个规范条目须对应可执行的验证步骤
3. **AI驱动实现**：AI编码工具（如Claude Code、CodeArts Agent）根据规范自动生成代码、测试和文档
4. **闭环迭代**：规范→代码→测试→反馈→规范修订→代码修复的持续闭环

### （二）与传统开发的区别

| 维度 | 传统开发 | SDD规范驱动开发 |
|---|---|---|
| 驱动方式 | 需求文档→人工编码 | 规范文件→AI驱动编码 |
| 规范形态 | 自然语言需求文档 | 结构化可验证规范（EARS格式） |
| 代码生成 | 人工逐行编写 | AI根据规范批量生成 |
| 测试关系 | 代码完成后补测试 | 规范同时定义测试用例 |
| 迭代速度 | 天/周级 | 小时级 |
| 质量保障 | 人工review | 自动化验证+人工审计 |

### （三）与现有hmos-dev-pipeline的关系

本项目的`hmos-dev-pipeline`技能已实现SDD的雏形：
- Stage 0：spec-generator生成feature-spec.md + test_case.md
- Stage 1：logic-coder根据规范生成代码
- Stage 2：self-tester在设备上验证

SDD方案在此基础上强化规范的可验证性和闭环迭代能力。

## 二、SDD规范文件格式

### （一）feature-spec.md结构

```markdown
# 功能规范：<功能名称>

## 元数据
- 档号：FS-<日期>-<序号>
- 版本：v1.0.0
- 责任席：<席位名>
- 状态：draft | review | approved | implemented | verified

## 功能描述
<一段话描述功能目标>

## 用户故事
作为<角色>，我希望<操作>，以便<价值>

## 验收条件（EARS格式）
- WHEN <条件> THEN <系统行为>
- IF <前置条件> THEN <系统行为>
- WHILE <状态> THE SYSTEM SHALL <行为>

## 约束
- 技术约束：纯ArkTS、零三方依赖、Stage模型
- 适老化约束：28-34fp高对比深色底、禁止K线图
- 信号松绑约束：kind:signal标记、禁止承诺收益

## 依赖
- 前置功能：<功能名>
- 数据源：<AlertFeed契约>

## 测试用例
| 用例ID | 条件 | 预期结果 | 验证方式 |
|---|---|---|---|
| TC-001 | <条件> | <结果> | <方式> |
```

### （二）test_case.md结构

测试用例与规范同源生成，每个验收条件对应至少一个测试用例。

## 三、SDD开发流程

### （一）完整流程（6步）

```
1. 规范编写 → feature-spec.md + test_case.md
2. 规范审查 → 人工/AI审查规范完整性和可验证性
3. 代码生成 → AI根据规范生成代码
4. 自动构建 → hvigorw构建HAP
5. 设备验证 → self-tester在设备上验证
6. 闭环迭代 → 失败→规范修订→代码修复→重新验证
```

### （二）MVP策略

遵循最简可行产品原则：
1. **第一迭代**：实现核心用户故事的最小路径
2. **第二迭代**：补充边界条件和异常处理
3. **第三迭代**：优化性能和用户体验
4. 每次迭代都从规范修订开始，而非直接改代码

### （三）CI/CD集成

```
规范提交 → 自动触发代码生成 → 自动构建 → 自动测试 → 结果反馈
         ↓                                                    ↓
    规范仓库                                              测试报告
```

## 四、铃语项目SDD落地计划

### （一）当前项目状态评估

| 维度 | 状态 | SDD就绪度 |
|---|---|---|
| 项目骨架 | ✅ 已建立（Stage模型、ArkTS） | 高 |
| 规范文件 | ⚠️ 有AGENTS.md约束但无feature-spec | 中 |
| 代码生成 | ✅ hmos-dev-pipeline可用 | 高 |
| 自动构建 | ⚠️ hvigorw可用但SDK未配置 | 低 |
| 设备验证 | ⚠️ 模拟器/真机未连接 | 低 |
| CI/CD | ❌ 未建立 | 低 |

### （二）优先推进项

**P1（立即启动）**：
1. 为铃语应用下一个功能编写SDD规范文件
2. 建立规范文件目录结构：`GOVERNANCE/specs/`
3. 定义铃语项目的EARS格式约束模板

**P2（本周内）**：
1. 配置HarmonyOS SDK，打通构建链路
2. 连接设备/模拟器，打通验证链路
3. 建立CI/CD基础流水线

**P3（中期）**：
1. 实现规范→代码→测试→反馈的全自动闭环
2. 集成Claude Code的MCP能力
3. 部署HuggingFace Spaces前端

### （三）第一个SDD规范：A2A看板接入真实数据

当前A2ADashboard.ets使用模拟数据（MOCK_SEATS/MOCK_EVENTS/MOCK_AUDITS）。第一个SDD规范应定义：

1. **功能目标**：将A2A看板从模拟数据切换为真实事件总线数据
2. **数据源**：事件总线ICRF（scripts/event_bus.py已部署在幻16）
3. **验收条件**：
   - WHEN 事件总线发布新事件 THEN 看板实时更新
   - WHILE 看板页面活跃 THEN 每5秒拉取最新事件
   - IF 事件总线不可达 THEN 显示"连接中断"状态
4. **约束**：纯ArkTS、零三方依赖、适老化

## 五、云中Claude Code使用方案

### （一）Claude Code在云中的部署

根据Claude Code官方文档，支持以下使用方式：
1. **Web版**：claude.ai/code——浏览器中运行，无需本地安装
2. **GitHub Actions**：自动化PR review和issue处理
3. **MCP集成**：连接外部数据源（Google Drive、Jira、Slack等）

### （二）与华为云X实例的协同

1. 在华为云X实例上部署CI/CD流水线
2. Claude Code通过MCP连接华为云X实例
3. 规范文件存储在GitHub仓库，Claude Code自动读取
4. 代码生成结果自动推送回仓库

### （三）算力分配策略

| 任务类型 | 算力来源 | 优先级 |
|---|---|---|
| 规范审查 | 本地（CodeArts Agent） | 高 |
| 代码生成 | 云端（Claude Code Web） | 高 |
| 自动构建 | 华为云X实例 | 中 |
| 设备测试 | 本地模拟器/真机 | 中 |
| CI/CD流水线 | 华为云X实例 | 低 |

## 六、HuggingFace Spaces前端部署

### （一）选型依据

根据外部灵感融合简报（OTL-20261005-01）的分析：
- **首选**：Star-Office-UI静态前端——零npm构建、多Agent join/推送协议现成
- **后端**：Docker Space跑轻量Flask/FastAPI
- **HUD增强**：arwes vanilla科幻边框+解密进场

### （二）部署计划

1. 在HuggingFace Spaces创建Docker Space
2. 部署Flask后端，对接事件总线ICRF
3. 部署Star-Office-UI静态前端
4. 配置Webhook与幻16A2A端点联动

## 七、总结与下一步

SDD规范驱动开发的核心是将规范从"事后文档"提升为"事前契约"，使AI工具能够根据规范自动驱动代码生成和验证。本项目已具备SDD的基础设施（hmos-dev-pipeline），需要补强的是：

1. **规范文件体系**：建立`GOVERNANCE/specs/`目录和EARS格式模板
2. **构建链路**：配置HarmonyOS SDK
3. **验证链路**：连接设备/模拟器
4. **CI/CD**：在华为云X实例上建立流水线

**立即行动项**：编写第一个SDD规范文件——A2A看板接入真实数据。

---

砚坚（挂帅席/神经中枢）
2026-10-05T16:00 CST