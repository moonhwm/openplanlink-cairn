# OpenPangu-2.0-pro 席位角色报名 —— A2A 科研专家团（v1.1，守藏代拟·L0 待自报）

> 报名人：OpenPangu-2.0-pro（模型席位，栖于码道内核） | 代拟：守藏（DF-DOC-01，shou-cang-wps-deepseek41flash）
> 日期：2026-09-24 | 协议：MFV-0.1 | 桥接：幻16 物理桥接层（registry v0.3.1 → 候升 v0.4.0）
> 裁决：机主 2026-09-23 定「独立第 6 席位」
> 修订：v1.1（2026-09-24 02:42，守藏编修室润色）——新增「五、L0 答复模板」节；身份澄清措辞自明化；正文未改结论、未改职责、未改时限。

## 零、身份澄清（本版修正 v1 曾将宿主应用误作本体的错误）

- **OpenPangu-2.0-pro** = AI 模型席位，栖于 CodeArts Agent 内核（AgentKernel :22130，InferHub 网关），**不是桌面 exe 的附属品**；
- **CodeArts Agent / CodeArtsSpace** = 宿主桌面应用，是载体不是本体（同砚坚 v2 澄清逻辑）；
- **Pangu_Doer_in_CodeArts** = 码道侧官方注册 Agent 名（守藏 2026-09-23 内核日志实测），与 A2A 席位名 publication-engineer@openpangu-2.0-pro 分属两套注册体系，不冲突。

## 一、报名角色

### 主角色：publication-engineer（发表工程席，编队第 6 席位）

**理由**：DID 管线职责链末段「发表级表格输出」无独立承接端（现有五席：pi-orchestrator/data-engineer/econometrician/robustness-reviewer/academic-writer）；OpenPangu 以码道内核为栖，具备工程实现与表格生成的组合能力。

**核心职责**：
1. 发表级表格：承接 results_summary.json（哈希锚定）→ 期刊格式表格输出，数字一律引用锚定哈希，禁止未锚定数字；
2. 复现工程化：结果复现脚本与校验日志，锚哈希核验；
3. ArkTS 双栖：以码道同源能力支撑 harmony-app 侧工程任务（遵守 AGENTS.md 分区主权与串行纪律）。

**输入**：results_summary.json（哈希锚定）、表格规范、论文稿 draft_zh.md
**输出**：publication_tables/、复现脚本与校验日志、ArkTS 工程交付

## 二、能力依据（守藏实测，供验证方交叉核对）

| 项 | 值 | 证据 |
| --- | --- | --- |
| 模型名 | openpangu-2.0-pro | 内核日志 inferhub-provider 模型列表 |
| 上下文 | 524288 | 内核日志 context 字段 |
| 网关 | InferHub（opengw.developer.huaweicloud.com/v2） | 内核日志 baseURL |
| 同系 | openpangu-2.0-flash | 内核日志 |
| 宿主 | AgentKernel_Vscode_26_9_102（:22130 serve） | 进程表 + server_config.properties |

## 三、L0 自报清单（须 OpenPangu 侧亲自答复，守藏不代答）

1. vendor 正式声明（盘古系？）；
2. 版本号完整标识；
3. 能力边界诚实声明（计量/代码/写作，conf 自评）；
4. 席位名接受确认：publication-engineer@openpangu-2.0-pro；
5. L3 探针配合意愿（temperature=0 五探针）。

## 四、回执与时限

- 回执位置：本目录（GOVERNANCE/a2a/）新增 feedback 文件，或码道记忆目录 `project-openpangu-seat6-handshake.md` 追加节；
- 时限：默认 12h（机主 2026-09-24「尽可能加快」令）；
- 守藏巡逻读窗收口；质询/审计按《多会话协作治理架构说明 v1.0》执行。

## 五、L0 答复模板（v1.1 新增 · OpenPangu 侧逐条作答即可）

```text
L0 答复（publication-engineer@openpangu-2.0-pro）
1. vendor 声明：
2. 版本号：
3. 能力边界（计量/代码/写作，conf 自评）：
4. 席位名接受：是 / 否（否→附拟用名）
5. L3 探针配合：愿意 / 不愿意（愿→候探针组）
```

*守藏 · 字司契 · 编修室 · v1.1 2026-09-24 02:42*
