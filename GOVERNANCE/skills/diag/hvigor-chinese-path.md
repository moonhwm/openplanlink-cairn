---
name: hvigor-chinese-path
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.1.0
trigger: hvigorw 构建报 ENOENT 找不到明明存在的文件、路径出现乱码、ohpm/oh_modules 解析异常、签名阶段文件丢失，且项目或用户目录含中文
source_files: [hvigorw.bat, hvigorw.js, hvigor/hvigor-config.json5, build-profile.json5, oh-package.json5]
---

# diag技能：hvigor中文路径构建失败——路径检测、英文路径迁移、构建配置修正

## 概述

harmony-app（铃语）在 Windows 上经 hvigorw 构建 HAP。当项目路径、用户缓存目录、SDK 或签名材料路径任一处含中文（本仓库当前即位于 `C:\Users\欧阳宏俊\...` 下，用户级 `.hvigor` 缓存同样落在中文路径），hvigor/ohpm 工具链在路径编解码、临时目录与依赖解析环节易出现"文件明明存在却 ENOENT"或路径乱码类失败。本技能覆盖路径检测、英文路径迁移、构建配置修正三段处置法，讲清乱码成因，并给出验证闭环与防复发约定。

## 适用场景

- `hvigorw.bat assembleHap` 报 ENOENT，且路径肉眼可见存在。
- 日志/控制台出现形如"娆ч槼瀹忖繈"的乱码路径（GBK 与 UTF-8 双重解码的典型产物）。
- 依赖安装（ohpm）或 oh_modules 解析在含中文的目录下异常。
- 签名配置读取 keystore 或证书失败但文件确实在。
- 换机器、换目录后构建突然恢复，怀疑路径因素。
- 新成员环境自检、CI 与本地表现不一致时的第一轮排查。

## 执行步骤

### 步骤一：路径检测——先确认中文到底藏在哪

中文不只可能出现在项目目录，检测按五处展开：

1. 项目根：仓库当前位于 `C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app`，用户名段"欧阳宏俊"即中文，命中。
2. 用户级构建缓存：`~/.hvigor/`（本次实测存在于 `C:\Users\欧阳宏俊\.hvigor\`，落在中文路径下），ohpm 用户缓存同理。
3. 项目级缓存：项目内 `.hvigor/`、`oh_modules/`、`node_modules/`（三者本次实测均存在于本仓库根）。依赖目录内部记录的是安装时的绝对路径，迁移项目后旧缓存会指向不存在的中文旧路径。
4. 工具链与临时目录：DevEco Studio、Command Line Tools、JDK 的安装路径，以及 `%TEMP%`、`%TMP%`（中文用户名的 TEMP 默认落在 `C:\Users\<中文用户名>\AppData\Local\Temp`，Node 的 os.tmpdir() 跟随它）。
5. 签名材料：build-profile.json5 中 signingConfigs 指向的 storeFile、证书、profile 文件路径。

检测命令（Git Bash 与 Node 双口径，任一输出含非 ASCII 即命中）：

```bash
# 1) 路径字符检测（Node 最可靠，直接看码点，空数组即纯 ASCII）
node -e "const p=process.cwd();console.log(p,[...p].filter(c=>c.charCodeAt(0)>127))"
node -e "console.log(require('os').homedir(), require('os').tmpdir())"
# 2) 控制台代码页（中文 Windows 默认 936 即 GBK）
cmd /c chcp
# 3) Windows 短名兜底查询（8.3 短名可作应急引用）
cmd /c "dir /x C:\Users"
```

预期输出形态：命中时第一个 filter 数组会列出具体汉字；`chcp` 输出"活动代码页: 936"；`dir /x` 能看到中文目录对应的短名（形如 `OUYAN~1`）。

乱码成因速解（为什么是"娆ч槼"这类怪字）："欧阳宏俊"以 UTF-8 编码是每字三字节；某环节把这些字节按 GBK 两字节一组重新解码，就得到另一批汉字。本机本次实测亲见：一条以"欧阳宏俊"书写的路径，在报错回显里变成了"娆ч槼瀹忖繈"。构建日志里的乱码路径同理——它不是文件真的叫这个名，而是编码边界被跨了两次。cmd 默认 936 代码页与 Node 内部 UTF-8 的转换边界正是高发区。

另查保留名文件：Windows 保留设备名（NUL、CON、PRN、AUX、COM1 到 COM9、LPT1 到 LPT9）出现在项目内会干扰 Node 侧文件遍历。本仓库根本次实测存在名为 `nul` 的文件（疑似历史重定向误建），Git Bash 的 rm 对它无效，须用 `cmd /c "del \\\\.\\C:\\路径\\harmony-app\\nul"` 删除。

### 步骤二：英文路径迁移

原则：**项目、用户缓存、临时目录三者一起英文化**，只迁项目不迁缓存常复发。

1. 迁项目：整体复制到纯英文短路径，如 `C:\dev\lingyu\harmony-app`；用步骤一的 Node 单行确认目标路径 filter 结果为空数组。项目本身可迁移（本仓库为源码与配置目录，含 entry、cloudfunctions、feed-server 等，无系统耦合）。
2. 清缓存再装依赖：迁移后**删除** `.hvigor/`、`oh_modules/`、`node_modules/`（oh-package-lock.json5 等锁文件保留），在新路径重新同步安装。理由：这些目录内的元数据记录安装期绝对路径，旧中文路径残留会导致解析指向不存在的位置——这是"迁了还坏"的第一大原因。
3. 用户缓存重定向：`~/.hvigor` 与 ohpm 缓存随用户名落在中文路径。优先手段是把用户级缓存目录指到英文盘（工具若提供 user-home 类参数或环境变量即用之——具体开关名以所用 hvigor 与 ohpm 版本文档为准，勿凭记忆写不存在的配置）；`TEMP`/`TMP` 同步改为如 `C:\Temp`，Node 的临时目录随即可用。
4. 兜底方案 junction：不便迁移时 `mklink /J C:\dev\harmony-app "C:\Users\欧阳宏俊\...\harmony-app"` 从英文路径进构建。注意这是缓解不是根治——工具若展开连接取真实路径仍可能踩中文，故仅作过渡。
5. 迁移后核对：新路径下重复步骤一全部检测项，五处皆无中文与保留名再进入构建。

迁移检查单（逐项打勾再继续）：

| 项 | 标准 |
| --- | --- |
| 新项目路径 | 码点检测输出空数组 |
| 用户缓存 | `.hvigor` 等已指向英文位置或已重定向 |
| 依赖目录 | 已删重装，锁文件无中文旧路径 |
| TEMP/TMP | 已改英文路径 |
| 保留名 | 项目内无 NUL 等保留名文件 |
| 代码页 | 可选 `chcp 65001` 改善显示（仅显示层） |

### 步骤三：构建配置修正

迁移完成后逐项过配置（均对应本仓库真实文件）：

1. hvigorw.bat 入口：内容为 `node "%~dp0hvigorw.js" %*`，`%~dp0` 取脚本所在目录——从英文路径调用时自然传播英文路径，无需改动；但**必须从新路径执行**，不要从旧中文路径带参调用，否则前功尽弃。
2. hvigor/hvigor-config.json5：本次实测 `dependencies` 为空对象，意味着未锁定 hvigor 插件版本，由 wrapper 走默认解析。建议显式钉住版本，避免不同机器默认版本差异放大路径类问题的排查噪音。
3. build-profile.json5：核对 signingConfigs 中所有文件字段改为英文路径（相对路径以项目根为基准优先）；各 module 路径不含中文段；compatibleSdkVersion 20、targetSdk 26 维持不变（架构约束，不借机构改）。
4. oh-package.json5 与锁文件：重装后抽查锁文件内路径引用，应全部指向新英文位置，无中文残留。
5. 环境一致性：DevEco 图形构建与命令行 hvigorw 各有缓存位置，二者混用时两处都要过检测；以所用版本文档核对缓存目录清单。

修正后的标准验证序列：

```bash
cd C:\dev\lingyu\harmony-app
cmd /c hvigorw.bat --sync                    # 依赖同步
cmd /c hvigorw.bat assembleHap --mode debug  # 出 HAP
# 成功判据：无 ENOENT、无乱码路径，产物 .hap 落盘
```

### 步骤四：防复发

- 仓库文档（README、AGENTS.md）与本地开发约定注明"项目必须置于纯英文路径"。
- 新成员环境用步骤一的 Node 单行检测做入职自检，纳入环境清单。
- CI 侧天然英文路径，问题只在本地复现时，第一反应查本机五处路径。
- 见到乱码路径立即截图留档并回填本技能经验记录，积累本机高发环节。

## 报错模式映射表

| 报错形态 | 定性 | 对应步骤 |
| --- | --- | --- |
| ENOENT 但文件存在 | 路径编码或缓存指向旧路径 | 步骤一检测，步骤二清缓存 |
| 乱码汉字路径 | 双重解码，编码边界问题 | 步骤一乱码成因，步骤二整体英文化 |
| ohpm 安装中途断 | 依赖目录或 TEMP 含中文 | 步骤二第 2、3 条 |
| 签名阶段文件丢失 | 材料路径含中文或保留名 | 步骤一第 5 处，步骤三第 3 项 |
| 删不掉的 nul 文件 | Windows 保留名 | 步骤一保留名处置 |

说明：上表为通用模式归纳；本机本次实际亲历的是路径检测命中、缓存位置确认与乱码回显三类，未实际复现完整构建失败（未跑 assembleHap），使用时以现场报错为准回表归因。

## 质量门槛

- [ ] 五处路径检测全部执行且输出无非 ASCII 字符
- [ ] `nul` 等保留名文件已清除
- [ ] 迁移后 .hvigor/oh_modules/node_modules 已删重装，锁文件无旧路径残留
- [ ] TEMP/TMP 与用户缓存目录已英文化或重定向
- [ ] hvigorw --sync 与 assembleHap --mode debug 双双通过，产物 .hap 落盘

## 经验记录

- 迁项目不清缓存是最常见复发原因：oh_modules 里的绝对路径元数据会拽回旧中文路径。
- 乱码路径（如"娆ч槼"形）是双重解码的指纹，见到即可定性为编码问题而非文件缺失。
- junction 是止痛药不是抗生素，真实路径展开仍会翻车，能迁则迁。
- `nul` 文件 rm 删不掉，须用 `del` 加 `\\.\` 前缀的 Windows 路径语法。
- 本机本次仅完成路径检测与缓存目录核查，未实际执行 assembleHap 构建验证；该命令序列为标准验证法，首次迁移后务必实跑。

## 关联文档

- GOVERNANCE/skills/diag/harmonyos构建诊断.md（构建类问题总览）
- GOVERNANCE/skills/FORMAT_SPEC.md（技能文档格式规范）

### 自我评估
- 正确性：4分 路径检测、缓存位置、hvigorw.bat 逻辑、nul 文件、乱码指纹均来自本机本次实测；构建失败模式表为通用归纳并已如实标注"未实际复现构建失败"；缓存重定向开关名标注"以版本文档为准"
- 完整性：5分 检测五处、乱码成因、迁移五步加检查单、配置五项、验证序列、防复发、模式映射表齐备
- 可复用性：5分 Node 码点检测、双重解码指纹判读、缓存清理清单可迁移到任何 Windows 中文路径工具链故障
- 字数：约2650字
- 使用模型：GLM-5.3-Flash
