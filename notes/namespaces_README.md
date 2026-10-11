# `namespaces/` —— 纲要核心命名空间之视图层

- **依据**：纲要《OpenPlanLink全局声明与Agent-to-Agent网络建设纲要》**行 62「目录结构建议」**（「根目录下创建不超过两至三级的子文件夹…围绕以下核心命名空间按需创建」）
- **本目录之来历**：**本席 `namespaces/` 下原有 68 个目录**，其名与纲要所列核心命名空间**逐字对应**（`/dcf /comps /lbo /curve /mimosa-* /park /portrait /recap /record …`）⇒ **即：命名空间早已按纲建齐，此前均无内容**
- **现状**：**10 个已填充**（`index.md`）：`/init /plan /workflow /env-check /debug-model /record /park /portrait /recap /policy`
- **余 58 个为空**：**合纲要"按需创建"之义** —— **本席无对应业务者不填**（如金融类 `/dcf /comps /lbo /curve /sources-uses`、`/ios-dev`、`/video-edit`）
- **性质**：★**视图层（件不动、路不迁）**；**仅为指路与计数**；**生成器 `exp/mk_namespaces.py` 幂等可重跑**
- **裁决**：**空目录之处置（甲保持空置／乙逐个写明"无此业务"／丙删除）仍候主权人**
- **生成**：由 `exp/mk_namespaces.py` 维护 ｜ 2026-10-11
