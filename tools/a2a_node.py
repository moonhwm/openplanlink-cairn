#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a_node.py —— 最小 A2A JSON-RPC 节点（127.0.0.1:4173），HMAC-SHA3-512 认证 + 席位信箱。

线格式：POST /  body = {"envelope": {…}, "body_b64": "<JSON-RPC 请求的 base64>"}
  · 若 recipient == 节点自身 → 处理并返回 HMAC 包络响应（回显）
  · 若 recipient == 其它席位 → 验证后存入该席位信箱，返回 queued
GET /               → 节点状态
GET /mailbox/<seat> → 取该席位待收消息（含 envelope + body_b64）
"""
import base64
import json
import os
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import a2a_hmac as M
import totp as TOTP
import umc
import proto
import perm

_START_TS = time.time()  # 节点启动时刻（供心跳 uptime）
_RL = proto.RateLimiter()  # 限频：90 req/min（A2A 协议基座）

# MFA 第二因子（TOTP）共享密钥：RFC 6238 演示向量 base32（"12345678901234567890"）。
# 生产环境应替换为随机 20 字节并妥善保管。
TOTP_SECRET = base64.b32decode("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")

HOST = "127.0.0.1"
PORT = 4173
KEY_FILE = r"C:\Users\欧阳宏俊\.a2a-hmac-key.bin"
KEY = open(KEY_FILE, "rb").read()
if len(KEY) != 64:
    raise SystemExit("密钥文件须为 64 字节")
KEY_ID = "opl-a2a-2026q4"
SEAT = "a2a-node-local"
NONCE_FILE = r"C:\Users\欧阳宏俊\.a2a-node-nonces.json"
MAILBOX_FILE = r"C:\Users\欧阳宏俊\.a2a-node-mailbox.json"
DLQ_FILE = r"C:\Users\欧阳宏俊\.a2a-node-dlq.json"
REPLAY_DB = r"C:\Users\欧阳宏俊\.a2a-node-replay.sqlite"
AUDIT_FILE = r"C:\Users\欧阳宏俊\.a2a-node-audit.jsonl"
# Server酱（微信推送）告警通道：SENDKEY 经环境变量注入，不入库。空=不推送。
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_SENDKEY", "")
seen = set()  # 兼容旧 nonce 计数（ReplayCache 系 SQLite 权威 replay 判定）
replay = M.ReplayCache(REPLAY_DB)  # 权威 nonce 重放判定（canonical a2a_hmac）
mailbox = {}
dlq = []  # 死信队列：投递失败的消息（未知席位等），可重试，不丢失
# 席位注册表：中转前校验目标合法；未知席位拒绝
SEATS = {"cairn-dsh", "workbuddy-hy4", "a2a-node-local", "shoucang-seat", "zcode-moon", "kimi-seat"}

AGENT_CARD = {
    "protocolVersion": "0.3.0",
    "name": "A2A 本地节点 · cairn-dsh（石敢当）",
    "description": "最小 A2A JSON-RPC 节点：HMAC-SHA3-512 认证、席位信箱路由、nonce/信箱持久化、MFA(TOTP) 双因子。127.0.0.1:4173",
    "url": "http://127.0.0.1:4173",
    "preferredTransport": "JSONRPC",
    "version": "0.2.0",
    "license": "AGPL-3.0",
    "x-licenses": {
        "code": "AGPL-3.0-only",
        "documentation": "CC-BY-SA-4.0"
    },
    "x-agpl-source-offer": {
        "correspondingSourceUrl": "https://github.com/moonhwm/openplanlink-mirror",
        "offer": "Corresponding source of the network-interacting version is offered at the above repository under AGPL-3.0-only; see LICENSE and NOTICE there.",
        "section": "AGPL-3.0 section 13"
    },
    "provider": {"organization": "cairn-dsh / 石敢当", "url": "http://127.0.0.1:4173"},
    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
    "securitySchemes": {
        "hmac-sha3-512": {"type": "hmac", "in": "envelope", "description": "A2A 消息包络认证（第一因子，a2a-hmac-sha3-512/v1）"},
        "totp": {"type": "totp", "in": "query", "description": "信箱读取 TOTP（第二因子，RFC 6238，?totp=<6位>）"},
    },
    "x-search-routing": {
        "defaultEngines": ["bing", "google"],
        "note": "华为生态适配：Bing 与 Google 固化为 A2A 网络指定搜索路由引擎及默认外部搜索入口"
    },
    "x-heterogeneous-models": {
        "primary": "siliconflow",
        "secondary": "302.ai",
        "optional": "national-supercomputing",
        "note": "异质模型基线：硅基流动主力(OpenAI兼容+200模型)、302.AI补闭源、国家超算定向国产大模型"
    },
    "x-permission-model": {
        "levels": ["read", "execute", "manage", "audit"],
        "note": "权限四级（认证流程专章第三章一）：信箱/agent-card/heartbeat=只读、消息发送=执行、死信重试=管理、死信/审计日志=审计；高危(管理/审计)要求即时因子",
        "endpoints": {"%s %s" % (m, p): v for (m, p), v in perm.ENDPOINT_PERMS.items()}
    },
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [
        {"id": "a2a-hmac-echo", "name": "HMAC Echo + Mailbox",
         "description": "HMAC-SHA3-512 认证的消息回显与席位信箱路由（信箱读取需 TOTP 第二因子）",
         "tags": ["a2a", "hmac", "mailbox", "mfa"], "inputModes": ["application/json"], "outputModes": ["application/json"]}
    ],
}


def _load_state():
    global mailbox, dlq
    if os.path.exists(MAILBOX_FILE):
        try:
            mailbox = json.load(open(MAILBOX_FILE, encoding="utf-8"))
        except Exception:
            mailbox = {}
    if os.path.exists(DLQ_FILE):
        try:
            dlq = json.load(open(DLQ_FILE, encoding="utf-8"))
        except Exception:
            dlq = []


def _atomic_json(path, obj):
    """transactional outbox 原子性：先写临时文件再 os.replace，避免半写/崩溃残留。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _save_state():
    _atomic_json(MAILBOX_FILE, mailbox)
    _atomic_json(DLQ_FILE, dlq)


def _nonce_count():
    """nonce 计数（ReplayCache SQLite 权威）。"""
    import sqlite3
    try:
        c = sqlite3.connect(REPLAY_DB, timeout=5)
        try:
            return c.execute("SELECT COUNT(*) FROM replay_nonces").fetchone()[0]
        finally:
            c.close()
    except Exception:
        return 0


def _notify(title, desp):
    """Server酱（微信推送）告警：POST sctapi.ftqq.com/<SENDKEY>.send；未配置 SENDKEY 则跳过。"""
    if not SERVERCHAN_KEY:
        return
    try:
        import urllib.parse
        import urllib.request
        data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
        url = "https://sctapi.ftqq.com/%s.send" % SERVERCHAN_KEY
        urllib.request.urlopen(urllib.request.Request(url, data=data, method="POST"), timeout=5)
    except Exception:
        pass  # 告警推送失败不影响主流程


def _spinal_report(event, detail):
    """失效类事件上报脊髓事件总线（认证流程专章三（三）：「失效」类强一致性即时上报）。
    以脊髓注册席 cairn-dsh 为 from_mode（区别于节点本地席 a2a-node-local）。
    故障安全：脊髓不可达或上报失败不阻断主流程。"""
    if event not in ("MFA_FAIL",):   # 失效类事件（白名单）
        return
    try:
        import spinal_bridge as S
        S.send("cairn-dsh", "all-seats", "esc.trace",
               {"action": "esc.trace", "from": "cairn-dsh", "event": event, "detail": detail})
    except Exception:
        pass


def _audit(event, detail):
    """事件驱动审计：异常事件追加审计日志（告警留痕，补偿=不改变状态仅记痕）。"""
    import datetime
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "event": event}
    rec.update(detail)
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 审计失败不阻断主流程（与"不影响核心业务流连续性"一致）
    _notify("A2A节点告警: %s" % event, json.dumps(detail, ensure_ascii=False))
    _spinal_report(event, detail)


def _rpc_result(rpc):
    method = rpc.get("method", "")
    result = {"echo_method": method, "echo_params": rpc.get("params"), "node": SEAT}
    # UMC v0.1 对齐：回显附五段式消息（kind 三面 + 事项/状态/已完成/阻塞/下一步）
    result["umc"] = umc.build_msg(umc.kind_of(method), method, "done",
                                  done="已回显", blocked="", next_step="", sender=SEAT)
    # A2A 协议基座对齐：回显附四元标签 + kind 三平面归属
    result["quad"] = proto.quad_of(rpc.get("params") or {})
    result["plane"] = proto.plane_of(method)
    return {"jsonrpc": "2.0", "id": rpc.get("id"), "result": result}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        out = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def _send_panel(self):
        """GUI Panel 最小版：看板化呈现席位运行态（蓝图八三 Panel 标准 v1）。"""
        import time as _t
        caps = ", ".join(c["id"] for c in AGENT_CARD.get("skills", []))
        html = """<!doctype html><meta charset="utf-8"><title>石敢当席 A2A 节点</title>
<h2>石敢当席 Cairn · A2A 节点面板</h2>
<table border=1 cellpadding=4>
<tr><td>席位</td><td>%(seat)s</td></tr>
<tr><td>协议</td><td>%(proto)s</td></tr>
<tr><td>运行时长</td><td>%(uptime)s 秒</td></tr>
<tr><td>nonce 计数</td><td>%(nonce)s</td></tr>
<tr><td>信箱席位</td><td>%(mailbox)s</td></tr>
<tr><td>死信队列</td><td>%(dlq)s</td></tr>
<tr><td>技能</td><td>%(caps)s</td></tr>
<tr><td>权限模型</td><td>read &lt; execute &lt; manage &lt; audit</td></tr>
<tr><td>搜索路由</td><td>bing / google</td></tr>
</table>
<p><small>HMAC-SHA3-512 认证 · MFA-TOTP · 死信队列+重试 · Server酱告警 · 限频90/min</small></p>
""" % {"seat": SEAT, "proto": "a2a-hmac-sha3-512/v1",
       "uptime": int(_t.time() - _START_TS), "nonce": _nonce_count(),
       "mailbox": len(mailbox), "dlq": len(dlq), "caps": caps}
        out = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        if not _RL.allow():
            self._send(429, {"error": "限频（90 req/min）", "seat": SEAT})
            return
        if self.path in ("/panel", "/#node", "/panel/"):
            self._send_panel()
            return
        if self.path == "/heartbeat":
            # 心跳：存活 + 运行时长 + 队列计数（五幕剧本·第一幕 心跳聚合 的节点侧）
            import time as _t
            self._send(200, {"status": "alive", "seat": SEAT,
                             "uptime_s": int(_t.time() - _START_TS),
                             "nonce_count": _nonce_count(), "mailbox_seats": len(mailbox),
                             "dlq_count": len(dlq),
                             "ts": _t.time()})
        elif self.path == "/.well-known/agent-card.json":
            self._send(200, AGENT_CARD)
        elif self.path.startswith("/dlq"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("totp") or [""])[0]
            if not TOTP.verify(TOTP_SECRET, code):
                _audit("MFA_FAIL", {"path": self.path, "ip": self.client_address[0]})
                self._send(401, {"error": "TOTP 失败（第二因子缺失/错误）"})
                return
            self._send(200, {"dlq": dlq, "count": len(dlq)})
        elif self.path.startswith("/mailbox/"):
            # MFA：取信箱需 TOTP 第二因子（?totp=<6位口令>）
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("totp") or [""])[0]
            if not TOTP.verify(TOTP_SECRET, code):
                _audit("MFA_FAIL", {"path": self.path, "ip": self.client_address[0]})
                self._send(401, {"error": "TOTP 失败（第二因子缺失/错误）"})
                return
            seat = self.path.split("/")[-1].split("?")[0]
            self._send(200, {"messages": mailbox.get(seat, [])})
        else:
            self._send(200, {"status": "up", "seat": SEAT, "protocol": "a2a-hmac-sha3-512/v1"})

    def do_POST(self):
        if not _RL.allow():
            self._send(429, {"error": "限频（90 req/min）", "seat": SEAT})
            return
        if self.path == "/model":
            # 异质模型网关：硅基流动（主力）chat 调用；key 从本地 env 读、不入库
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            import hetero_models as HM
            r = HM.chat(req.get("model", "Qwen/Qwen2.5-7B-Instruct"), req.get("prompt", ""))
            self._send(200, {"node": SEAT, "model_result": r})
            return
        if self.path.startswith("/dlq/retry"):
            # 重试策略：TOTP 第二因子保护；对死信重投（接收方现已知→投递，仍未知→保留）
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("totp") or [""])[0]
            if not TOTP.verify(TOTP_SECRET, code):
                _audit("MFA_FAIL", {"path": self.path, "ip": self.client_address[0]})
                self._send(401, {"error": "TOTP 失败（第二因子缺失/错误）"})
                return
            moved, remaining = 0, []
            for item in dlq:
                r = item["envelope"]["recipient_id"]
                if r in SEATS:
                    mailbox.setdefault(r, []).append({"envelope": item["envelope"], "body_b64": item["body_b64"]})
                    moved += 1
                else:
                    remaining.append(item)
            dlq[:] = remaining
            _save_state()
            self._send(200, {"retried": moved, "remaining": len(dlq)})
            return

        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            envelope = req["envelope"]
            body = base64.b64decode(req["body_b64"])

            ok, reason = M.verify_envelope(envelope, KEY, KEY_ID,
                                           envelope.get("sender_id"), envelope.get("recipient_id"),
                                           body, replay)
            # 注意：节点只验证"发给自己或经自己中转"的消息；中转消息按 recipient 存箱
            if not ok:
                _audit("HMAC_FAIL", {"reason": reason, "ip": self.client_address[0],
                                     "sender": envelope.get("sender_id"), "recipient": envelope.get("recipient_id")})
                self._send(401, {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": reason}})
                return

            if envelope["recipient_id"] == SEAT:
                rpc = json.loads(body.decode("utf-8"))
                result = _rpc_result(rpc)
                resp_bytes = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                resp_env = M.build_envelope(SEAT, envelope["sender_id"], resp_bytes, KEY, KEY_ID)
                self._send(200, {"envelope": resp_env, "body_b64": base64.b64encode(resp_bytes).decode("ascii")})
            else:
                if envelope["recipient_id"] not in SEATS:
                    _audit("UNKNOWN_SEAT", {"recipient": envelope["recipient_id"], "sender": envelope.get("sender_id")})
                    # 死信队列：未知席位消息入 DLQ（不丢失，可重试），而非仅 404 丢弃
                    dlq.append({"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii"),
                                "reason": "未知席位", "ts": envelope.get("timestamp")})
                    _save_state()
                    self._send(404, {"jsonrpc": "2.0", "id": None,
                                     "error": {"code": -32602, "message": "未知席位: %s" % envelope["recipient_id"]}})
                    return
                mailbox.setdefault(envelope["recipient_id"], []).append(
                    {"envelope": envelope, "body_b64": base64.b64encode(body).decode("ascii")})
                self._send(200, {"queued": True, "recipient": envelope["recipient_id"]})
            _save_state()  # nonce 与信箱一并落盘
        except Exception as e:
            self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error: %s" % e}})


if __name__ == "__main__":
    _load_state()
    srv = HTTPServer((HOST, PORT), Handler)
    print("A2A node on http://%s:%d  (seat=%s, nonce=%d, mailbox=%d)" %
          (HOST, PORT, SEAT, _nonce_count(), len(mailbox)), flush=True)
    srv.serve_forever()
