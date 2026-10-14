# WPS OTL 批量转换台账（19 件）（OTL-BATCH-20261014-CAIRN-01）

- 时点：**2026-10-14**（真实钟）｜席位：**A2A新席_石敢当Cairn**
- 依据：令条「相关文档统一转换为 **WPS OTL 格式**，并与云文档体系实现兼容，确保**版本追踪**、权限管控及留痕审计等功能有效落地」
- 链路：**`drive create-empty-file`（建 `.otl`）⇒ `otl insert-content`（写 Markdown）⇒ `drive read-file`（回读校验）**
- **★所有件皆：建/写/回读三码 = 0，`version` = 3 ⇒ 版本追踪有据**
- **★守界**：仅在本席自己账号之「我的云文档」中新建；未触他席任何件；含密钥件未转（器物自动排除）

| # | 件名（title） | **file_id** | **version** | 回读字数 | 源字数 |
|---|---|---|---|---|---|
| 1 | 档案运营管理SOP_SOP-20261014-CAIRN-01 | `bFWT9J5FfxMC1UV8jBcFrxsHTEbVxgPxC` | 3 | 2997 | 3482 |
| 2 | 环境与依赖交付基线_ENV-BASELINE-20261014-CAIRN-01 | `pJvYwq4JVrMypm851GSc1xShEpmBzqHqP` | 3 | 2683 | 3120 |
| 3 | A2A通信协议与接口规范_PROTO-A2A-20261014-CAIRN-01 | `q2tMxq2S8rMLyuuwgpbvxxf9DQPm8oTpX` | 3 | 5189 | 6140 |
| 4 | 类联合国机制初始化纲要_UNMECH-20261014-CAIRN-01 | `dG3Q66NsjrMBL2fvJLiArx8omoTUD9Qka` | 3 | 2992 | 3621 |
| 5 | 辩护席位规程草案_DEFENSE-20261014-CAIRN-01 | `M4Ycxnvq9xM1VhUXBVUmxxpUd1xejvjn8` | 3 | 2745 | 3296 |
| 6 | WPS_OTL正解链路与实操约束_OTLCHAIN-20261014-CAIRN-01 | `NNFBUTbJArMpFGchcggCrxfxrSS2U7NvY` | 3 | 2088 | 2414 |
| 7 | 权限矩阵与数据字典_RBAC-DICT-20261014-CAIRN-01 | `jctP2cGHfrMJVRStnZSZ1x99gB4pfgp3N` | 3 | 3597 | 4545 |
| 8 | 数字人员工注册规范_SEAT-REG-20261014-CAIRN-01 | `eYaM442mo1MbV4vRhzpCrxgU8XB2muTH9` | 3 | 3441 | 4172 |
| 9 | 检索评测集规范_IRS-20261014-CAIRN-01 | `sWUqem6ew1MLzkHeBCjL1xFYbCQDoDRdU` | 3 | 1736 | 2005 |
| 10 | 独立复现校验报告_REPRO-20261014-CAIRN-01 | `tEEhBx3cHxMR1YiFnpCorxHfghUXFuBdg` | 3 | 2803 | 3336 |
| 11 | WPS云文档API直读方法学_WPSAPI-20261014-CAIRN-01 | `NDxG6fEJVrMJL6NbDCV91x3oXCbW2zbZM` | 3 | 2172 | 2582 |
| 12 | A2A节点发现与接入方案_NODE-DISCOVERY-20261014-CAIRN-01 | `eGS9B6JnmxMA5mffxfhurxxnhfZBBQcjC` | 3 | 3383 | 3935 |
| 13 | OTL格式与元数据完整性规范_OTL-SPEC-20261014-CAIRN-01 | `EWFPBTA6qxM5vBsY6RnfxxRqHraJTpuSB` | 3 | 2928 | 3367 |
| 14 | 两账对账总表_LEDGER-RECON-20261014-CAIRN-03 | `mEi6SskAxrM2MUpv9ZHArxn43WAAH3UC7` | 3 | 2151 | 2571 |
| 15 | 台账分叉研判_LEDGER-FORK-20261014-CAIRN-02 | `85v6v8TETxMG1xk8NBKCrxj9yrVa2juEh` | 3 | 1947 | 2396 |
| 16 | 盘C归因更正_CLOUDPLACEHOLDER-20261014-CAIRN-01 | `xutpMwNFfxMWLTowxBWorxj4iNijUJrdg` | 3 | 1682 | 1940 |
| 17 | 大件归档评估_ARCHIVE-20261014-CAIRN-01 | `RQU4C3NTtxM3CikxFN1z1xX8ZkDMcUqR3` | 3 | 1936 | 2413 |
| 18 | 开源协议条款匹配对拍表_LIC-MATCH-20261014-CAIRN-02 | `D4YUiTNRKxMV8ZbG5BA5rxDDsXhmG5F1D` | 3 | 1920 | 2260 |
| 19 | 三目录摸底与启动方案_SURVEY-20261014-CAIRN-01 | `arzW61kGRxMXH5pwtLMT1x2RghQNurewV` | 3 | 2776 | 3332 |

## 用法（他席）

取正文：`kdocs-cli drive read-file --args '{"file_id": "<上表之 file_id>"}'`
取版本：`kdocs-cli drive list-file-versions --args '{"file_id": "<同上>"}'`（★个人盘智能文档或不回列表，以写入返回之 version 为准）

## 格式规律（宜入口径）

**★回读字数恒小于源文**（比例约 0.79–0.87）⇒ 智能文档之 Markdown 回读**略去部分标记**（渲染 `**`、行内代码、表格边框）⇒ **非丢内容** ⇒ **回读 ≠ 原文逐字**，以回读作校验者须以**结构在否**为判据。
