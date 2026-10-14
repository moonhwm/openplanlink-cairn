---
name: 构建系统
description: hvigorw构建工具链、devecocli命令行构建、Stage模型
type: project-knowledge
category: build_system
---

# 构建系统

## 构建工具链

项目使用HarmonyOS官方构建工具hvigorw（hvigor wrapper），通过`hvigorw.js`/`hvigorw.bat`脚本驱动构建。构建配置文件为`hvigorfile.ts`。

**devecocli命令行构建**（推荐）：
```bash
devecocli build --build-mode debug    # debug模式构建
devecocli build --build-mode release  # release模式构建
```
产物路径：`entry/build/default/outputs/default/entry-default-unsigned.hap`

**云构建**（CodeArts Build）：
1. 上传至CodeArts Repo
2. CodeArts Build新建构建任务，选官方"HarmonyOS应用构建"模板
3. 产物`entry-default-signed.hap`下载后经`hdc install`装机

## 构建配置

`build-profile.json5`核心配置：
- `compatibleSdkVersion: 6.0.2(22)` / `targetSdkVersion: 6.0.2(22)`
- `runtimeOS: HarmonyOS`
- `strictMode: { caseSensitiveCheck: true, useNormalizedOHMUrl: true }`
- 单模块：entry（srcPath=./entry）
- 构建模式：debug + release

## 构建约束

- hvigor禁止中文路径——构建需纯英文路径，编译副本在`A:/DevEcoStudio/harmony-app/`
- 签名配置需在DevEco Studio中配置（build-profile.json5的signingConfigs）
- 未签名HAP可在模拟器上安装，真机需签名