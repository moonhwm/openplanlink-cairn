---
name: 幻16端点重启恢复
type: diag
created: 2026-10-06
updated: 2026-10-06
version: 1.0.0
trigger: 幻16A2A端点不可达（HTTP 000/502/连接拒绝）时
source_files: [/root/handshake/serve-handshake.mjs]
---

# 幻16端点重启恢复

## 概述
幻16（120.46.86.165）上运行的 serve-handshake.mjs 是 A2A 网络的物理桥接层。当端点不可达时，需通过 SSH 诊断进程状态并重启服务，恢复 A2A 通信通道。

## 适用场景
- A2A 通告发送返回 HTTP 000 或 502
- curl 连接幻16端点被拒绝（exit code 7）
- serve-handshake.mjs 进程存在但端口未监听
- serve-handshake.mjs 进程已退出（PID 不存在）

## 执行步骤

1. **SSH 连接幻16**
   ```bash
   ssh -i "C:\Users\欧阳宏俊\.ssh\id_ed25519" -o ConnectTimeout=10 root@120.46.86.165
   ```

2. **检查进程状态**
   ```bash
   ps aux | grep serve-handshake | grep -v grep
   ```
   - 若进程不存在 → 直接执行步骤 4
   - 若进程存在但端口未监听 → 执行步骤 3 后再执行步骤 4

3. **终止僵死进程**（如进程存在但端口未监听）
   ```bash
   kill <PID>
   ```

4. **重启服务**
   ```bash
   cd /root/handshake && PORT=4173 BIND=0.0.0.0 nohup node serve-handshake.mjs > /tmp/handshake.log 2>&1 &
   ```

5. **验证端口监听**
   ```bash
   sleep 3 && ss -tlnp | grep 4173
   ```
   - 应看到 `LISTEN 0 511 0.0.0.0:4173` 或 `127.0.0.1:4173`

6. **验证 HTTP 响应**
   ```bash
   curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4173/
   ```
   - 应返回 `200`

7. **发送测试 A2A 通告**
   ```bash
   curl -s -X POST http://127.0.0.1:4173/functions/v1/app \
     -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":"test","method":"message/send","params":{"message":{"parts":[{"kind":"text","text":"test"}]}}}'
   ```
   - 应返回包含 `messageId` 的 JSON 响应

## 质量门槛
- 端口 4173 必须处于 LISTEN 状态
- HTTP 响应码必须为 200
- A2A 通告必须返回有效 messageId
- 重启后服务须能正常处理 JSON-RPC 请求

## 经验记录
1. serve-handshake.mjs 进程可能因内存不足或长时间运行而僵死——进程存在但端口不再监听，需 kill 后重启
2. 默认端口为 4173（非 58080），BIND 默认 127.0.0.1，重启时建议设 BIND=0.0.0.0 以支持外部访问
3. SSH MCP 工具执行复杂命令（含管道、后台进程）容易超时，建议用 bash 直接调用 ssh 命令更可靠
4. 幻16端点应配置 systemd 服务自启动，防止进程退出后端点永久不可用
5. A2A 通告每日外呼配额上限 8 次，超限后只留痕不外呼——重启端点后发送通告时注意配额

## 关联文档
- GOVERNANCE/proposals/night_ops_compute_schedule_20261005.md — 夜间运维方案
- GOVERNANCE/audit_logs/a2a_notice_log.jsonl — A2A通告发送日志
- reference/huan16-a2a-bridge.md — 幻16 A2A桥接层记忆文档