# 云函数环境变量配置指南

> 编纂：砚坚（yan-jian@codearts-ide）
> 日期：2026-09-23
> 用途：CloudBase 云函数环境变量配置参考，含审计结果和 BROADCAST_API_KEY 配置指南

---

## 一、环境变量审计结果

### 1.1 全量环境变量清单

| 云函数 | 变量名 | 必需 | 默认值 | 敏感 | 说明 |
|--------|--------|------|--------|------|------|
| **fetch-tushare-data** | `TUSHARE_TOKEN` | ✅ | `''` | 🔴 | Tushare API token |
| | `ALERT_THRESHOLD` | ❌ | `'5.0'` | — | 异动筛选阈值（%） |
| | `DKNOWC_API_KEY` | ❌ | `''` | 🔴 | DKnowC内容安全API key |
| | `TCB_ENV` | ❌ | `'a2a-commonwealth-d2eepjr928e9c4d'` | — | CloudBase环境ID |
| **generate-tts** | `DASHSCOPE_API_KEY` | ✅ | `''` | 🔴 | 百炼/DashScope API key |
| | `BAILIAN_WORKSPACE_ID` | ❌ | `'ws-ay6o8osb22o9dc3t'` | — | 百炼工作空间ID |
| | `TCB_ENV` | ❌ | 同上 | — | 同上 |
| **broadcast-a2a** | `BROADCAST_API_KEY` | ✅ | `''` | 🔴 | HTTP鉴权API key |
| | `SUPABASE_URL` | ✅ | `''` | — | Supabase URL |
| | `SUPABASE_ANON_KEY` | ✅ | `''` | 🔴 | Supabase匿名key |
| | `PUSH_BUNDLE_NAME` | ❌ | `'com.yehang.stockpulse'` | — | Push bundle名称 |
| | `HUAWEI_PUSH_PROJECT_ID` | ❌ | `''` | 🔴 | 华为Push项目ID |
| | `HUAWEI_PUSH_CLIENT_ID` | ❌ | `''` | 🔴 | 华为Push客户端ID |
| | `HUAWEI_PUSH_CLIENT_SECRET` | ❌ | `''` | 🔴 | 华为Push客户端密钥 |
| | `HUAWEI_PUSH_TOKEN` | ❌ | `''` | 🔴 | 华为Push token |
| | `TCB_ENV` | ❌ | 同上 | — | 同上 |
| | `PORT` | ❌ | `9000` | — | HTTP监听端口 |
| **get-alerts** | `TCB_ENV` | ❌ | 同上 | — | 同上 |
| **push-token-register** | `TCB_ENV` | ❌ | 同上 | — | 同上 |
| **init-db** | `TCB_ENV` | ❌ | 同上 | — | 同上 |

### 1.2 审计发现

| # | 发现 | 风险 | 建议 |
|---|------|------|------|
| A1 | `.env` 文件包含所有敏感凭据（Tushare token、API keys、Supabase key） | 🟡 中危 | ✅ 已在.gitignore中，未被git跟踪 |
| A2 | `TCB_ENV` 默认值硬编码在6个云函数中 | 🟢 低危 | 生产环境应通过控制台配置覆盖 |
| A3 | `BROADCAST_API_KEY` 未在 `.env` 中配置 | 🟠 高危 | 需要生成并配置 |
| A4 | `HUAWEI_PUSH_*` 系列变量全部为空 | 🟢 低危 | AGC配置后填写 |
| A5 | `BAILIAN_WORKSPACE_ID` 有默认值 | 🟢 低危 | 可被环境变量覆盖 |

---

## 二、BROADCAST_API_KEY 配置指南

### 2.1 生成 API Key

```bash
# 生成 32 字节随机 API Key
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

示例输出：`a3f5e8b2c1d4f6a8e0b2c4d6f8a0e2b4c6d8f0a2e4b6c8d0f2a4b6c8e0d2f4`

### 2.2 配置步骤

1. **CloudBase 控制台配置**：
   - 进入 CloudBase 控制台 → 云函数 → broadcast-a2a → 环境变量
   - 添加 `BROADCAST_API_KEY` = 生成的 API Key

2. **本地 `.env` 配置**（开发环境）：
   ```bash
   # 在 cloudfunctions/.env 中添加
   BROADCAST_API_KEY=<生成的API Key>
   ```

3. **客户端配置**：
   - 调用 broadcast-a2a 的 HTTP 端点时，在请求头中携带：
   ```
   Authorization: Bearer <API Key>
   ```

### 2.3 验证

```bash
# 无 API Key → 应返回 401
curl https://<cloudbase-domain>/broadcast-a2a

# 有 API Key → 应返回 200
curl -H "Authorization: Bearer <API Key>" https://<cloudbase-domain>/broadcast-a2a

# 健康检查端点（无需鉴权）
curl https://<cloudbase-domain>/broadcast-a2a/healthz
```

---

## 三、生产环境配置清单

在 CloudBase 控制台为每个云函数配置以下环境变量：

### fetch-tushare-data
```
TUSHARE_TOKEN=<你的Tushare token>
ALERT_THRESHOLD=5.0
DKNOWC_API_KEY=<你的DKnowC API key>（可选，不配置则跳过合规检查）
TCB_ENV=a2a-commonwealth-d2eepjr928e9c4d
```

### generate-tts
```
DASHSCOPE_API_KEY=<你的DashScope API key>
BAILIAN_WORKSPACE_ID=ws-ay6o8osb22o9dc3t
TCB_ENV=a2a-commonwealth-d2eepjr928e9c4d
```

### broadcast-a2a
```
BROADCAST_API_KEY=<生成的32字节随机key>
SUPABASE_URL=https://ltdodcumoxiqsnakpqog.supabase.co
SUPABASE_ANON_KEY=<你的Supabase anon key>
PUSH_BUNDLE_NAME=com.yehang.stockpulse
TCB_ENV=a2a-commonwealth-d2eepjr928e9c4d
# 以下在AGC配置后填写
HUAWEI_PUSH_PROJECT_ID=
HUAWEI_PUSH_CLIENT_ID=
HUAWEI_PUSH_CLIENT_SECRET=
HUAWEI_PUSH_TOKEN=
```

### get-alerts / push-token-register / init-db
```
TCB_ENV=a2a-commonwealth-d2eepjr928e9c4d
```

---

## 四、安全注意事项

1. **`.env` 文件绝不入库**：已在 `.gitignore` 中排除
2. **敏感凭据不在日志中输出**：fetch-tushare-data 已对 Tushare token 脱敏
3. **API Key 使用 Bearer 认证**：broadcast-a2a 已实装 HTTP 鉴权
4. **凭据金库加密**：S2 修复方案已设计（AES-256-GCM），待实施
5. **密钥轮换**：M2 修复方案已设计（expires_at + rotation_reminder），待实施

---

## 五、关联文档

- README.md（云函数部署指南）
- CRYPTO_HARDENING_INTEGRATED.md（密码学加固方案 S1-S4）
- GOVERNANCE缺口清单（GAP-04 push-token-register鉴权方案）