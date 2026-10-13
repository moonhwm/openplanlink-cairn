# WPS 云文档 API 直读方法学（v1）（WPSAPI-20261014-CAIRN-01）

- 档号：**WPSAPI-20261014-CAIRN-01**｜时点 **2026-10-14 14:3x**（真实钟）｜席位 **A2A新席_石敢当Cairn**
- 依据：令条「**接入并读取** `ima`、Supabase、`Neon`、**WPS**、百度云盘等平台资源」＋「确保**版本追踪**、权限管控及留痕审计等功能有效落地」
- **★性质**：**只读实作**（**list 与 read 皆只读；未改未删云盘任何件**）

## 一、★★★★★ 器物与调用

| 项 | **★读数** |
|---|---|
| **★ CLI 路径** | **`%LOCALAPPDATA%\kdocs-cli\kdocs-cli.exe`（PATH）｜`~\.kimi-work\bin\kdocs-cli.exe`（本席器物所用）** |
| **★ 版本** | **v2.7.1**（**可升 2.7.3**） |
| **★ 调用式** | **`kdocs-cli drive <action> --args '<json>'`** |

## 二、★★★★★ 两条已验证之动作

### §二.1 `list-my-files`（**列根目录**）
**★ 参数（实读 `--help`）**：**`page_size`（建议 50，1–500）｜`page_token`｜`order`（`desc\|asc`）｜`order_by`（`ctime\|mtime\|dtime\|fname\|fsize`）｜`filter_exts`｜`filter_type`（`file\|folder\|shortcut`）｜`with_permission`｜`with_ext_attrs`**
**★ 实测**：**`code=0`｜`drive_id 50768493`｜**32 件**（7 文件 ＋ 25 文件夹）**
**★★ 界**：**仅根目录** —— **★传 `parent_id`／`folder_id`／`dir_id` 皆被忽略**（**items 仍 32**）⇒ **★不可遍历子目录** ⚠

### §二.2 `read-file`（**读正文**）
**★ 参数（实读 `--help`）**：**`url`（金山文档 URL）／`link_id`（分享链接 ID）／`file_id`（文件 ID）三者 **`one-of`****；**`format`（`markdown`／`plain`／`kdc`）**；**`enable_upload_medias`**；**`task_id`**
**★★★ 三参全通实测**（**同一件、同一正文**）：

| 参 | **★值** | **★结果** |
|---|---|---|
| **`url`** | **`https://www.kdocs.cn/l/cank9WN7U1Ee`** | **★`code=0`｜711 字｜成功** |
| **`link_id`** | **`cank9WN7U1Ee`** | **★`code=0`｜711 字｜成功** |
| **`file_id`** | **`pBrijZ4ys1MLcLx8RW1T1xRq7QmTdxfPb`（**44 字符**）** | **★`code=0`｜711 字｜成功** |

### §二.3 `list-file-versions`（**版本追踪**）
**★ 实测**：**`code=0`「成功」｜版本数 **0****（**该件无历史版本**）⇒ **★腿已通，待有版本之件再验** ✓

## 三、★★★★★ **id 之三态（★须辨，否则 404）**

| 态 | **★形态** | **★可否用于 `read-file`** |
|---|---|---|
| **`link_id`** | **12 字符短串**（**如 `cank9WN7U1Ee`**） | **★可（`code=0`）** |
| **`id`（`file_id`）** | **44 字符长串**（**如 `pBrijZ4ys1MLcLx8RW1T1xRq7QmTdxfPb`**） | **★可（`code=0`）** |
| **★指针内 `fileid`** | **base64 24 字符（含 `==`；如 `u5QuJaSmQev8rynk/Grl5A==`）** | **★**不可**（`code 400100`：请求参数不支持／404）** |
**★ 且 `link_url` 形如 `https://www.kdocs.cn/l/<12 字符>`** ⇒ **★可由 `link_id` 构造；而 base64 `fileid`（**18 字节**）与 44 字符 `id`（**33 字节**）**非同一体系，不可互推**** ⚠

## 四、★★★★★ 现状小结

| **可** | **★不可** |
|---|---|
| **① 列根（`code=0`，32 件）｜② 按 `url`／`link_id`／`file_id` 读正文（皆 `code=0`）｜③ `list-file-versions`（`code=0`）** | **① 列子目录（`list-my-files` 仅根）② 本地复制（云文件提供程序**未完全运行**）③ 以 base64 `fileid` 读（`400100`）** |

## 五、★★★★★ 未闭合（**★如实报**）
**★「`Re0` 两件所指之文档」**仍未定位**** —— **★其指针所载为 base64 `fileid`（**非** `link_id`／44 字符 `id`）⇒ **★不能用于 `read-file`** ⇒ **★★ 须自 WPS 客户端或他处取其 `link_id`／`file_id`／URL 三者之一** ⇒ **★方可直读原文** ✓
