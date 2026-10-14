# 砚坚席自建技能索引

> 编纂：砚坚（码道·鸿蒙开发智能体/deepseek-v4-pro-0813）
> 日期：2026-09-24（v3.2更新）
> 版本：v3.6
> 关联：外部技能索引见 SKILL_INDEX.md，格式规范见 FORMAT_SPEC.md

---

## 自建技能清单

### code类（代码编写技能）

| # | 技能名称 | 文件 |; 版本 | 触发条件 |
|---|---------|------|------|---------|
| 1 | HarmonyOS ArkTS适老化开发 | harmonyos-arkts-适老化开发.md | 1.0.0 | 编写HarmonyOS ArkTS代码 |
| 2 | ArkTS云函数模式 | arkts-cloud-function-pattern.md | 1.0.0 | 编写CloudBase云函数 |
| 3 | ArkTS网络请求封装 | arkts-network-wrapper.md | 1.0.0 | 封装HTTP/HTTPS请求 |
| 4 | ArkTS缓存策略 | arkts-cache-strategy.md | 1.0.0 | 实现缓存/降级/fallback |
| 5 | 端侧ArkTS代码审查 | arkts-code-review.md | 1.0.0 | 端侧代码系统性审查 |
| 6 | 云函数统一基础设施层 | cloud-function-refactor.md | 1.0.0 | 云函数重构/共享SDK |
| 7 | 错误处理模式 | error-handling.md | 1.0.0 | 错误处理/降级/容错 |
| 8 | 安全审查 | security.md | 1.0.0 | 安全审查/凭据/TLS |
| 9 | fetch-tushare-data云函数深度审查 | A35_fetchtusharedata云函数深度审查.md | 1.0.0 | 审查fetch-tushare-data云函数 |
| 10 | 端侧性能优化审查 | A36_端侧性能优化审查.md | 1.0.0 | 端侧性能审查/优化 |
| 11 | 命令行构建环境配置 | A38_命令行构建环境配置.md | 1.0.0 | 无devecocli环境下构建HAP |
| 12 | fetch-tushare-data数据源降级链 | A11_fetchtusharedata数据源降级链fallbackMap审查.md | 1.0.0 | 审查数据源降级/fallbackMap |
| 13 | alertId传递链路审查 | A12_alertId传递链路审查.md | 1.0.0 | 审查alertId推送→拉起→播报全链路 |
| 14 | fetch-tushare-data并行与重试 | A13_fetchtusharedata并行与重试逻辑审查.md | 1.0.0 | 审查并行请求/重试/TTS顺序执行 |
| 15 | broadcast-a2a安全审查 | A14_broadcasta2a云函数安全审查.md | 1.0.0 | 审查鉴权/CORS/凭据/SDK单例 |
| 16 | 合规fail-closed机制审查 | A15_合规failclosed机制审查.md | 1.0.0 | 审查DKnowC合规/TTS降级/三禁约束 |

### collab类（协作技能）

| # | 技能名称 | 文件 | 版本 | 触发条件 |
|---|---------|------|------|---------|
| 11 | A2A总线跨席位协作 | a2a总线协作.md | 1.0.0 | 通过A2A总线与其他席位通信 |
| 12 | A2A握手协议 | a2a-handshake.md | 1.0.0 | 新席位加入/心跳建立/冲突仲裁 |
| 13 | 额度燃烧策略 | quota-burning.md | 1.0.0 | GLM额度窗口燃烧/模型切换 |
| 14 | A2A总线桥接缺陷排查 | bus-bridge-debug.md | 1.0.0 | 消息未路由/桥接缺陷 |
| 36 | A2A改造方案落地 | A36_A2A改造方案落地kimi停用与码道总装.md | 1.0.0 | 停用AI通道/迁移职能/建立A2A基础设施 |
| 37 | A2A共建公约规划书编写 | A37_A2A共建公约规划书编写经验.md | 1.0.0 | 代码排查/哈贝马斯映射/四段式清单/EvoMap |
| 38 | a2a-judge判官自动化云函数 | A38_a2a-judge判官自动化云函数开发经验.md | 1.0.0 | 判官云函数/Supabase总线/Promise.allSettled/冷启动WARN |

### diag类（诊断技能）

| # | 技能名称 | 文件 | 版本 | 触发条件 |
|---|---------|------|------|---------|
| 15 | HarmonyOS构建问题诊断 | harmonyos构建诊断.md | 1.0.0 | HarmonyOS构建失败 |
| 16 | 鸿蒙全量代码审查 | full-code-review.md | 1.1.0 | 端侧/云函数全量合规走查 |
| 17 | Tushare Token失效诊断 | tushare-token-failure.md | 1.0.0 | Tushare API Token失效 |
| 18 | TTS WebSocket连接诊断 | tts-websocket.md | 1.0.0 | 百炼TTS WebSocket连接问题 |
| 30 | Fail-Open修复 | fail-open-fix.md | 1.0.0 | 合规/鉴权/降级逻辑 fail-open 漏洞修复 |
| 31 | 契约同步检查 | contract-sync-check.md | 1.0.0 | 端侧interface与服务端JSON字段一致性检查 |
| 32 | 幻16端点重启恢复 | huan16-endpoint-restart.md | 1.0.0 | 幻16A2A端点不可达时诊断并重启服务 |

### governance类（治理技能）

| # | 技能名称 | 文件 | 版本 | 触发条件 |
|---|---------|------|------|---------|
| 19E | A2A治理实验执行 | 治理实验执行.md | 1.0.0 | 执行治理实验 |
| 20 | 文档缺口盘点 | doc-gap-inventory.md | 1.0.0 | 治理体系/知识资产缺口盘点 |
| 21 | A2A治理协议 | a2a-governance-protocol.md | 1.0.0 | 建立/审查/修订多AI共治协议 |
| 22 | 技能自改进机制 | skill-self-improvement.md | 1.0.0 | 技能文档持续改进 |
| 23 | 交接簿纪律 | changelog-discipline.md | 1.0.0 | 规范CHANGELOG追加/串行纪律 |
| 24 | 8小时自治运维模式 | A37_8小时自治运维模式.md | 1.0.0 | 执行长周期自治运维任务 |
| 25 | 席位命名操作 | seat-naming-ops.md | 1.0.0 | 新席位命名/身份登记/命名冲突仲裁 |
| 26 | 人设迭代循环操作 | persona-iteration-loop-ops.md | 1.0.0 | 人设设定/动态完善/3D建模/涌现探索 |

### crypto类（密码学技能）

| # | 技能名称 | 文件 | 版本 | 触发条件 |
|---|---------|------|------|---------|
| 25 | 密码学分析与加固 | 密码学分析加固.md | 1.0.0 | 密码学分析/密钥管理/PQC评估 |
| 26 | TLS验证恢复与维护 | tls-verification.md | 1.0.0 | TLS证书验证审查/恢复 |
| 27 | 哈希算法升级 | hash-algorithm-upgrade.md | 1.0.0 | 哈希算法审查/弱哈希升级 |
| 28 | 后量子密码学迁移评估 | pqc-migration-assessment.md | 1.0.0 | PQC迁移影响/时间线/兼容性 |
| 29 | 凭据金库加密管理 | credential-vault-encryption.md | 1.0.0 | 凭据加密/隔离/指纹/轮换 |

## 技能复用统计

| 技能 | 创建日期 | 使用次数 | 自改进次数 | 最后更新 |
|------|---------|---------|-----------|---------|
| ArkTS云函数模式 | 2026-09-23 | 2 | 0 | 2026-09-23 |
| ArkTS网络请求封装 | 2026-09-23 | 2 | 0 | 2026-09-23 |
| ArkTS缓存策略 | 2026-09-23 | 2 | 0 | 2026-09-23 |
| 端侧ArkTS代码审查 | 2026-09-23 | 2 | 0 | 2026-09-23 |
| fetch-tushare-data云函数深度审查 | 2026-09-23 | 1 | 0 | 2026-09-23 |
| 端侧性能优化审查 | 2026-09-23 | 1 | 0 | 2026-09-23 |
| 交接簿纪律 | 2026-09-23 | 5 | 0 | 2026-09-23 |
| 8小时自治运维模式 | 2026-09-23 | 1 | 0 | 2026-09-23 |
| PQC迁移评估 | 2026-09-23 | 1 | 0 | 2026-09-23 |
| 密码学分析与加固 | 2026-09-19 | 1 | 0 | 2026-09-23 |

## 交叉引用矩阵

| 技能 | 关联技能 | 关联类型 |
|------|---------|---------|
| fetch-tushare-data云函数深度审查 → | ArkTS云函数模式, ArkTS缓存策略, 安全审查 | 审查对象使用这些模式 |
| 端侧性能优化审查 → | 端侧ArkTS代码审查, ArkTS缓存策略 | 性能审查扩展代码审查 |
| 8小时自治运维模式 → | 交接簿纪律, 技能自改进机制, 文档缺口盘点 | 运维流程使用这些治理技能 |
| PQC迁移评估 → | 密码学分析与加固, TLS验证恢复, 哈希算法升级 | PQC评估依赖这些密码学技能 |
| 凭据金库加密管理 → | 安全审查, TLS验证恢复 | 凭据安全依赖传输安全 |

## 待编写技能

| 技能名称 | 类型 | 编写触发条件 | 优先级 |
|---------|------|------------|--------|
| Android→HarmonyOS迁移 | code | 完成一次Android迁移任务 | 中 |
| 穷举式分析执行 | governance | 完成一次穷举式分析 | 高 |
| 语义学审查执行 | governance | 完成一次6维语义学审查 | 中 |
| 文档资产化 | collab | 完成一次知识资产化 | 高 |
| 交接协议验证 | collab | 完成一次交接验证 | 高 |
