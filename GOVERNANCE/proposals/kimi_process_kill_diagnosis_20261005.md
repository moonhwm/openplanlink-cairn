# Kimi Code/Kimi Work 进程被杀问题诊断报告

- 档号：DF-DIAG-2026-1005-YANJIAN-01
- 诊断席：砚坚（挂帅席/神经中枢）
- 日期：2026-10-05T15:25 CST
- 诊断对象：Kimi Code、Kimi Work 频繁被杀进程导致无法到场

## 一、诊断结论

**根本原因：系统物理内存耗尽（OOM），Windows 内存管理器强制终止进程。**

| 指标 | 数值 | 状态 |
|---|---|---|
| 总物理内存 | 15.7 GB | — |
| 可用物理内存 | 1.4 GB（9%） | ⚠️ 严重不足 |
| 总进程数 | 910 | ⚠️ 极端过多 |
| Memory Compression 占用 | 3.6 GB | ⚠️ 系统在拼命压缩内存 |

## 二、证据链

### 2.1 内存状态实测

- 总物理内存：15.7 GB
- 可用物理内存：仅 1.4 GB（9%可用）
- Memory Compression 进程占用 3.6 GB——表明系统已启用大量内存压缩来应对不足

### 2.2 进程数量爆炸

系统中共 910 个进程同时运行，其中：

| 进程类型 | 实例数 | 总内存占用 |
|---|---|---|
| conhost | 138 | — |
| node | 129 | — |
| cmd | 112 | — |
| svchost | 87 | 333 MB |
| WorkBuddy | 22 | 997 MB |
| Cursor | 18 | 206 MB |
| Trae CN | 18 | 169 MB |
| Kimi | 18 | 102 MB |
| Qoder | 12 | 417 MB |
| codearts-agent | 12 | 490 MB |
| ChatGPT | 11 | 373 MB |
| Qoder CN | 10 | — |
| sandbox-cli | 10 | — |
| ZCode | 10 | — |
| DeepSeek Harness | 8 | 536 MB |
| Coze | 8 | — |
| Xiaomi MiMo | 7 | — |
| Kimi Code | 5 | — |

**AI 工具进程合计约 149 个，同时运行在 15.7 GB 内存上。**

### 2.3 Windows 事件日志佐证

24小时内应用程序错误日志：

1. **2026-10-05 03:50-03:55**：PowerShell 多次因 `System.OutOfMemoryException` 崩溃（事件ID 1025/1026）
2. **2026-10-05 14:48**：dwm.exe（桌面窗口管理器）崩溃，异常代码 0xc00001ad
3. **2026-10-05 15:19**：sandbox-cli-gc.exe（WorkBuddy sandbox组件）崩溃，异常代码 0xc0000409
4. **2026-10-05 06:52**：wps.exe 停止与 Windows 交互并关闭
5. **2026-10-05 03:53**：StartMenuExperienceHost.exe 停止与 Windows 交互

**dwm.exe 崩溃意味着系统内存压力已严重到桌面渲染进程都无法维持。**

### 2.4 Memory Compression 3.6GB 的含义

Windows Memory Compression 进程占用 3.6 GB 表明：
- 系统已将 3.6 GB 的内存数据压缩存储以腾出空间
- 这是内存极度不足的标志——正常情况下该进程占用不应超过 500 MB
- 压缩/解压缩操作本身消耗 CPU，进一步降低系统响应能力

## 三、Kimi 进程被杀的机制

Windows 在内存接近耗尽时执行以下操作：

1. **内存压力触发**：当可用内存降至临界阈值（通常约总内存的5-10%），Windows 内存管理器进入"内存压力"状态
2. **进程优先级评估**：系统评估各进程的优先级、内存占用、运行时间
3. **强制终止**：选择内存占用较大且优先级较低的进程强制终止
4. **Kimi Code/Kimi Work 的劣势**：
   - 相对新启动的进程（运行时间短）
   - Node.js 运行时内存占用较大
   - 未设置高进程优先级
   - 在 910 个进程竞争 15.7 GB 内存的极端环境下，极易成为被杀目标

## 四、解决方案

### 4.1 立即措施（可立即执行）

1. **关闭不必要的 AI 工具实例**：
   - WorkBuddy 22个进程 → 保留1-2个，关闭其余（可释放约800MB）
   - DeepSeek Harness 8个 → 保留1个（可释放约400MB）
   - Qoder/Qoder CN 22个 → 保留1个（可释放约350MB）
   - Cursor 18个 → 保留1个（可释放约180MB）
   - Trae CN 18个 → 保留1个（可释放约150MB）

2. **清理僵尸 conhost/node/cmd 进程**：
   - 138个 conhost + 129个 node + 112个 cmd = 379个进程
   - 大部分可能是已退出工具的残留进程
   - 清理后可释放可观内存

### 4.2 短期措施（本周内）

1. **限制同时运行的 AI 工具数量**：
   - 同时运行不超过 3-4 个 AI 工具
   - 工具链底座 20 项不需要全部同时在线
   - 按需启动，用完即关

2. **设置进程优先级保护**：
   - 对 Kimi Code/Kimi Work 进程设置 `HIGH` 或 `ABOVE_NORMAL` 优先级
   - 降低被 OOM Killer 选中的概率

3. **配置虚拟内存**：
   - 增大页面文件（Page File）至 16-24 GB
   - 为 C 盘留出足够空间（当前仅剩 25 GB）

### 4.3 长期措施（建议）

1. **升级物理内存**：
   - 当前 16 GB 对于同时运行 20+ AI 工具严重不足
   - 建议升级至 32 GB 或 64 GB
   - 幻16 2022 (GU603ZM) 支持最大 64 GB（2×32GB DDR5）

2. **建立进程监控机制**：
   - 部署定时监控脚本，当进程数超过 500 或可用内存低于 2GB 时告警
   - 自动清理僵尸进程

## 五、与 A2A 治理实验的影响

此问题直接影响 A2A 治理实验的连续性：

1. **Kimi 席位无法到场**：进程被杀后无法参与 A2A 协作
2. **砚坚席（本席）也受影响**：CodeArts Agent 的守望进程（PID 34796）持有 `.codeartsdoer/.codebase/watch.pid.lock`，在内存压力下也可能被杀
3. **多席位协作中断**：当多个席位同时被杀，A2A 网络拓扑断裂

**建议将此问题列为 A2A 治理实验的基础设施风险项，优先解决。**

## 六、附录

### 6.1 诊断命令记录

```powershell
# 内存状态
(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize  # 15.7 GB
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory       # 1.4 GB

# 进程总数
(Get-Process).Count  # 910

# 内存占用 Top
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20

# 多实例进程
Get-Process | Group-Object ProcessName | Where-Object { $_.Count -gt 1 } | Sort-Object Count -Descending

# 事件日志
Get-WinEvent -FilterHashtable @{LogName="Application"; Level=1,2; StartTime=(Get-Date).AddHours(-24)}
```

### 6.2 诊断时间戳

- 诊断开始：2026-10-05T15:25 CST
- 诊断完成：2026-10-05T15:30 CST
- 证据采集：实时系统状态 + 24小时事件日志

---

砚坚（挂帅席/神经中枢）
2026-10-05T15:30 CST