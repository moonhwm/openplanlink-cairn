---
name: 配置体系
description: build-profile.json5、module.json5、oh-package.json5、AppScope配置
type: project-knowledge
category: configuration_system
---

# 配置体系

## 配置文件组织

项目配置分三层：应用级（AppScope）、模块级（entry）、项目级（根目录）。

**应用级配置**（AppScope/）：
- `app.json5` — bundleName=com.yehang.stockpulse，应用显示名"铃语"
- `resources/` — 应用级资源（图标、字符串）

**模块级配置**（entry/src/main/）：
- `module.json5` — 模块配置，声明abilities、skills、permissions、pages
- `resources/` — 模块级资源（颜色、字符串、图片、profile）

**项目级配置**（根目录）：
- `build-profile.json5` — SDK版本、构建模式、签名配置、模块列表
- `oh-package.json5` — 包名stockpulse、版本0.1.0、依赖声明
- `hvigorfile.ts` — hvigor构建脚本

## 关键配置项

**module.json5**：
- `mainElement: EntryAbility` — 入口Ability
- `deviceTypes: ["phone"]` — 仅手机
- `pages: "$profile:main_pages"` — 页面路由配置
- `skills`：系统home + push.listener + 小艺A2A自定义action
- `requestPermissions`：INTERNET + KEEP_BACKGROUND_RUNNING（R3预留）

**build-profile.json5**：
- `signingConfigs: []` — 签名配置待机主在DevEco Studio中配置
- `products: [{ name: "default", signingConfig: "default" }]`

**运行时配置**（SettingsService管理）：
- 数据源地址、自选股列表、播报开关、字体档、显示模式、免打扰等
- 通过Preferences持久化，键名前缀`stockpulse_settings`