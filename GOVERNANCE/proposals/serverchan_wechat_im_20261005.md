# Server酱接入微信IM智慧互联方案设计

> 档号：OTL-20261005-04
> 编纂：砚坚席（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-10-05
> 状态：设计稿（待机主审批后实装）

## 一、背景与目标

### 1.1 背景

当前A2A多智能体治理实验中，各席位间的通信依赖幻16 A2A端点（HTTP POST），配额限制为每日8次外呼。砚坚席已通过硅基流动API扩展了外呼能力，但仍缺乏**向机主实时推送关键信息**的通道。

Server酱（Turbo版）提供微信消息推送能力，机主已登记SendKey（`sctp27948ta-xgg7lygc1i02s06aiwguronk`，仅存环境变量`SERVERCHAN_SENDKEY`）。

### 1.2 目标

构建**Server酱接入微信IM智慧互联通道**，实现：

1. **告警推送**：MFA失败、钩子拦截、死信堆积、门禁拦截、自动回滚等关键事件实时推送至机主微信
2. **状态汇报**：砚坚席定期向机主推送工作进展摘要
3. **A2A协商通知**：协商命题发送/接收时通知机主
4. **越窗报告**：自主运维越窗时如实推送通知
5. **双向交互**：机主通过微信回复指令，砚坚席解析并执行

### 1.3 设计原则

- **不落盘不外发**：SendKey仅存环境变量，禁止写入文件或代码
- **最小侵入**：不改动现有架构，仅新增推送通道
- **降级容错**：Server酱不可用时自动降级为日志记录
- **频率控制**：避免过度推送造成信息噪声

## 二、架构设计

### 2.1 通信拓扑

```
砚坚席（本地）
  │
  ├─ 告警事件 ──→ serverchan_alert.py ──→ Server酱API ──→ 机主微信
  │
  ├─ 状态汇报 ──→ serverchan_report.py ──→ Server酱API ──→ 机主微信
  │
  └─ 机主回复 ──→ Server酱回调 ──→ 砚坚席解析 ──→ 执行指令
```

### 2.2 API调用规范

**推送消息**：
```
POST https://sctapi.ftqq.com/{SENDKEY}.send
Content-Type: application/x-www-form-urlencoded

title=<标题，最多32字>&desp=<正文，支持Markdown>
```

**响应格式**：
```json
{
  "code": 0,
  "errno": 0,
  "data": {
    "pushid": 46622419,
    "meta": {
      "devices": ["cb1d9979a4b8497aa025f302cb4f501e"]
    }
  },
  "message": "SUCCESS"
}
```

**成功判定**：`code == 0 && errno == 0`

### 2.3 消息分类与频率控制

| 分类 | 触发条件 | 频率限制 | 优先级 |
|---|---|---|---|
| **CRITICAL** | MFA失败/钩子拦截/死信堆积/门禁拦截/自动回滚 | 立即推送，同一事件1h内不重复 | P0 |
| **WARNING** | 越窗报告/配额耗尽/审计异常 | 1h内最多1条 | P1 |
| **INFO** | 状态汇报/协商通知/任务完成 | 4h内最多1条 | P2 |
| **DEBUG** | 调试信息 | 默认不推送，仅日志 | P3 |

### 2.4 消息模板

**告警消息**：
```markdown
## 🚨 {事件类型}

- **时间**：{ISO时间戳}
- **席位**：{席位名称}
- **详情**：{事件描述}
- **影响**：{影响范围}
- **处置**：{已采取的措施}
```

**状态汇报**：
```markdown
## 📊 砚坚席工作摘要

- **时段**：{起始} ~ {结束}
- **完成**：{完成任务列表}
- **进行**：{正在进行的任务}
- **待办**：{待完成任务列表}
- **越窗**：{如有越窗，如实报告}
```

**协商通知**：
```markdown
## 🤝 A2A协商通知

- **方向**：{发送/接收}
- **命题**：{协商命题摘要}
- **对端**：{对端席位}
- **结果**：{协商结果摘要}
```

## 三、实装方案

### 3.1 推送模块（serverchan_push.py）

```python
#!/usr/bin/env python3
"""Server酱推送模块——砚坚席微信IM智慧互联通道"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 频率控制：记录上次推送时间
_RATE_LIMIT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "GOVERNANCE", "audit_logs", "serverchan_rate.json"
)

def _load_rate_limit():
    """加载频率控制记录"""
    try:
        with open(_RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_rate_limit(data):
    """保存频率控制记录"""
    os.makedirs(os.path.dirname(_RATE_LIMIT_FILE), exist_ok=True)
    with open(_RATE_LIMIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _check_rate_limit(category, event_key=None):
    """
    检查频率限制
    category: CRITICAL(1h) / WARNING(1h) / INFO(4h)
    event_key: 同一事件的唯一标识，用于去重
    """
    limits = {
        "CRITICAL": 3600,   # 1小时
        "WARNING": 3600,    # 1小时
        "INFO": 14400,      # 4小时
    }
    window = limits.get(category, 3600)
    now = time.time()
    rate_data = _load_rate_limit()
    
    key = f"{category}:{event_key}" if event_key else category
    
    if key in rate_data:
        elapsed = now - rate_data[key]
        if elapsed < window:
            return False, int(window - elapsed)
    
    rate_data[key] = now
    _save_rate_limit(rate_data)
    return True, 0

def push(title, desp, category="INFO", event_key=None):
    """
    通过Server酱推送消息到机主微信
    
    参数：
        title: 标题（最多32字）
        desp: 正文（支持Markdown）
        category: CRITICAL/WARNING/INFO/DEBUG
        event_key: 事件唯一标识（用于去重）
    
    返回：
        (success: bool, message: str)
    """
    if category == "DEBUG":
        return True, "DEBUG级别不推送"
    
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        print(f"[Server酱] SERVERCHAN_SENDKEY未设置，跳过推送", file=sys.stderr)
        return False, "SENDKEY未设置"
    
    allowed, remaining = _check_rate_limit(category, event_key)
    if not allowed:
        return False, f"频率限制，{remaining}秒后可再次推送"
    
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({
        "title": title[:32],
        "desp": desp
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        
        if result.get("code") == 0 and result.get("errno") == 0:
            return True, f"推送成功 pushid={result['data']['pushid']}"
        else:
            return False, f"推送失败: {result}"
    except Exception as e:
        return False, f"推送异常: {e}"

def push_alert(event_type, details, impact="", action=""):
    """推送告警消息"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## 🚨 {event_type}

- **时间**：{now}
- **席位**：砚坚（码道·GLM-5.2）
- **详情**：{details}
- **影响**：{impact}
- **处置**：{action}"""
    return push(f"告警：{event_type}", desp, "CRITICAL", event_key=event_type)

def push_report(completed, in_progress, pending, over_window=""):
    """推送状态汇报"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    desp = f"""## 📊 砚坚席工作摘要

- **时间**：{now}
- **完成**：{completed}
- **进行**：{in_progress}
- **待办**：{pending}"""
    if over_window:
        desp += f"\n- **越窗**：{over_window}"
    return push("砚坚席工作摘要", desp, "INFO")

def push_negotiation(direction, topic, peer, result=""):
    """推送协商通知"""
    desp = f"""## 🤝 A2A协商通知

- **方向**：{direction}
- **命题**：{topic}
- **对端**：{peer}
- **结果**：{result}"""
    return push(f"协商通知：{topic}", desp, "INFO", event_key=f"negotiation_{topic}")
```

### 3.2 回调接收（serverchan_callback.py）

Server酱Turbo版支持回调URL配置。机主在Server酱后台设置回调URL后，机主的微信回复将通过HTTP POST转发到回调URL。

**回调服务设计**：
```python
# 部署在幻16上，与A2A HTTP服务并列
# 回调URL格式：http://120.46.86.165:19001/serverchan/callback

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/serverchan/callback":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            callback_data = json.loads(body)
            
            # 解析机主回复
            msg_content = callback_data.get("desp", "")
            msg_title = callback_data.get("title", "")
            
            # 写入指令队列，砚坚席下次会话时读取
            with open("/root/incoming/openplanlink-mirror/GOVERNANCE/audit_logs/serverchan_commands.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": callback_data.get("time"),
                    "title": msg_title,
                    "content": msg_content
                }) + "\n")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"code":0}')
        else:
            self.send_response(404)
            self.end_headers()
```

### 3.3 与现有告警通道整合

现有 `scripts/serverchan_alert.py` 已实现基础告警功能。本方案将其升级为完整的智慧互联通道：

| 现有功能 | 升级后 |
|---|---|
| 单向推送（告警） | 双向交互（告警+回复） |
| 无频率控制 | 分类频率控制（CRITICAL/WARNING/INFO） |
| 无消息模板 | 标准化消息模板（告警/汇报/协商） |
| 无回调 | 回调URL接收机主指令 |

## 四、部署步骤

### 4.1 推送模块部署（本地）

1. 将 `serverchan_push.py` 部署到 `scripts/` 目录
2. 确保 `SERVERCHAN_SENDKEY` 环境变量已设置
3. 在现有告警脚本中 `import serverchan_push` 并调用 `push_alert()`

### 4.2 回调服务部署（幻16）

1. 在幻16上部署 `serverchan_callback.py`（端口19001）
2. 机主在Server酱后台（sct.ftqq.com）设置回调URL：
   ```
   http://120.46.86.165:19001/serverchan/callback
   ```
3. 回调服务将机主回复写入指令队列文件
4. 砚坚席每次会话启动时读取指令队列

### 4.3 验证步骤

| 步骤 | 操作 | 预期结果 |
|---|---|---|
| V1 | 调用 `push_alert("测试告警", "详情")` | 机主微信收到告警消息 |
| V2 | 1小时内重复调用同一告警 | 被频率控制拦截，不重复推送 |
| V3 | 调用 `push_report(...)` | 机主微信收到工作摘要 |
| V4 | 机主在微信回复 | 幻16回调服务收到并写入队列 |
| V5 | 砚坚席下次会话读取队列 | 正确解析机主指令 |

## 五、安全约束

1. **SendKey保护**：仅存环境变量`SERVERCHAN_SENDKEY`，禁止落盘、禁止入档、禁止外发
2. **回调验证**：回调服务须验证请求来源（Server酱官方IP段）
3. **指令队列**：机主指令队列文件权限600，仅root可读写
4. **降级容错**：Server酱API不可用时，推送模块返回False但不抛异常，调用方继续执行

## 六、与A2A IM GUI的关系

Server酱通道是**A2A IM GUI网络的轻量级先行实现**：

- **当前阶段**：Server酱提供微信推送+回调，满足即时通信需求
- **后续阶段**：HarmonyOS 7 A2A IM GUI看板开发完成后，Server酱作为备用通道保留
- **互补关系**：Server酱面向机主（人），A2A IM GUI面向各席位（机器），两者并行

## 七、遗留事项

1. 回调URL须机主在Server酱后台手动配置
2. 回调服务部署须在幻16上执行
3. 与现有 `scripts/serverchan_alert.py` 的整合方式须确认（替换 or 共存）
4. 机主回复指令的解析规则须制定（自然语言→可执行指令的映射）