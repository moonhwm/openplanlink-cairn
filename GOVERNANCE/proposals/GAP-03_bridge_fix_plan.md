# 桥接缺陷修复方案——F-8A + 别名匹配（GAP-03）

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-22
> 对象：`C:\Users\欧阳宏俊\Documents\kimi\router-hub\bridge\a2a_bridge.mjs`
> 关联：协作记录 v1.0 §五 两处链路缺陷、id=250/3066/6277 未路由件

---

## 一、缺陷回顾

### F-8A：非 JSON 明文被空 catch 吞掉

`a2a_bridge.mjs` 消息处理中，`payload_md` 字段为纯文本（非 JSON）时，`JSON.parse()` 抛错被空 catch 静默吞掉，消息正文丢失。

**已受影响消息**：id=250（纯文本握手回执）、id=3066（纯文本接入求援）、id=6277（纯文本审核邀约）。

### 别名匹配缺陷：to_mode 精确匹配

收件面按 `to_mode === seatKey`（如 `workbuddy-hy4`）精确匹配，发送方使用别名（`workbuddy`、`workbuddy-W`、`yan-jian-workbuddy`）时消息无法落入收件面。

### 桥接脚本能力图（已确认）

| 能力 | 位置 | 说明 |
|------|------|------|
| Supabase REST 客户端 | `class SupabaseBus` | insert/select/update |
| 轮询读消息 | `PollingFallback` (335行) | `bus.select('cross_mode_channel', {}, 50, lastId)` |
| 消息分派 | `createMessageDispatcher` (671行) | 按 kind 分派 |
| 误路由巡检 | 文档声称保留 | 需核实实现 |
| 哈希约定 | 提交序 id | msg_hash = md5(payload_utf8)[:16] |

---

## 二、修复方案

### 修复1：F-8A——catch 保留原文

**位置**：消息解析处（`createMessageDispatcher` 或 `readMessages` 之后）

**改法**：
```js
// 原：catch { /* 空 */ }
// 改为：catch (e) {
//   message.body_text = typeof raw === 'string' ? raw : JSON.stringify(raw);
//   message.parse_error = e.message;
// }
```

**效果**：payload_md 非 JSON 时保留原始文本，分派器可对文本型消息走"文本消息处理分支"。

### 修复2：别名匹配——收件面模糊匹配

**位置**：`createMessageDispatcher` 中判断 `to_mode` 的分支

**改法**：
```js
function isForMe(msg) {
  const to = msg.to_mode || '';
  const seatKey = SEAT.key; // 如 'workbuddy-hy4'
  if (to === seatKey) return true;
  if (to === 'all' || to === 'ALL' || to === 'broadcast-all' || to === '*') return true;
  // 别名包含匹配：to 中包含本席规范键根（workbuddy）即收
  const rootKey = seatKey.split('-')[0]; // 'workbuddy'
  return to.includes(rootKey);
}
```

**效果**：`to_mode='workbuddy'` / `'workbuddy-W'` / `'yan-jian-workbuddy'` 均落入本席收件面。

**风险**：别名包含匹配可能误收其他含 rootKey 的席位消息——当前总线 `workbuddy*` 变体均指本席（已实证），风险可接受。若未来出现歧义，改为显式别名表。

### 修复3：已恢复消息处置（一次性）

三条已恢复消息处置：

| id | 处置 |
|----|------|
| 250 | 已读归档（握手回执，信息已并入协作记录） |
| 3066 | 已读归档，SSH接入求援已登记为 D-7 待机主 |
| 6277 | 复函已发出（协作记录 §3.1） |

---

## 三、部署与验证

1. 修改 `a2a_bridge.mjs`（上述修复1+2）
2. dry-run：用 `--seat-key workbuddy-hy4 read` 验证三条消息可读
3. 逐字回读：确认正文完整
4. 提交 git + CHANGELOG 追加

---

## 四、执行记录

| 时间 | 完成项 |
|------|--------|
| 2026-09-22 | 方案成文（本文件）；实际补丁修改待桥接会话执行（本会话无 a2a_bridge 写权限场景） |