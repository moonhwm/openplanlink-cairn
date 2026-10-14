# Wiki 检索指南

> 本文档指导Agent如何高效检索铃语项目的知识库Wiki文档。

## 检索入口

### 按模块查找（"这个模块提供什么能力？"）

1. 从 [codebase-knowledge/index.md](codebase-knowledge/index.md) 获取模块树导航
2. 点击对应模块文档链接

### 按规范查找（"整个项目在XX方面的规范是什么？"）

1. 从 [project-knowledge/index.md](project-knowledge/index.md) 获取主题索引表
2. 点击对应主题文档链接

### 按关键词查找

| 关键词 | 对应文档 |
|--------|---------|
| Push/推送 | codebase-knowledge/推送服务（PushService）.md |
| 轮询/退避 | codebase-knowledge/轮询服务（AlertPoller）.md |
| 播放/音频 | codebase-knowledge/音频播放服务（AudioPlayer）.md |
| 设置/自选股 | codebase-knowledge/设置服务（SettingsService）.md |
| 异动/AlertItem | codebase-knowledge/数据契约（AlertItem）.md |
| TTS/百炼 | project-knowledge/external_dependency/bailian_tts.md |
| 构建/hvigor | project-knowledge/build_system/build_system.md |
| 日志/hilog | project-knowledge/logging_system/logging_system.md |
| 异常/降级 | project-knowledge/error_handling/error_handling.md |
| 适老化/elderly | project-knowledge/business_term/business_term.md |
| HRTF/音频后处理 | codebase-knowledge/音频后处理模块（audio-postprocess）.md |
| feed-server/数据管道 | codebase-knowledge/数据管道服务器（feed-server）.md |
| 小艺/A2A | codebase-knowledge/入口能力（EntryAbility）.md |

## 文档格式约定

- 每篇模块文档包含：概述、架构设计、技术栈、编码规范、配置与命令、关系
- 每篇规范文档包含：相关配置项、约定规则、使用示例
- frontmatter包含name、description、type、source_files等字段

## 知识库边界

- 端侧代码（entry/src/main/ets/）→ codebase-knowledge前8个模块
- 服务端代码（feed-server/）→ codebase-knowledge后2个模块
- 跨仓接口边界 → codebase-knowledge/数据契约（AlertItem）.md
- 治理实验文档（GOVERNANCE/）→ 不在本Wiki范围内