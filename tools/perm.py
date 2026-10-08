#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""perm.py —— 权限四级模型（只读—执行—管理—审计）。

依《认证流程专章》第三章（一）：「只读—执行—管理—审计」四级权限与 MFA 状态矩阵化联动，
高危操作（管理/审计）要求即时因子。本模块定义四级 + 端点映射 + 判级。
纯标准库，Windows 直跑。
"""
LEVELS = ("read", "execute", "manage", "audit")          # 递进：read < execute < manage < audit
_ORDER = {l: i for i, l in enumerate(LEVELS)}

# 端点 → 所需权限级（节点 a2a_node.py 各端点的权限映射）
ENDPOINT_PERMS = {
    ("GET", "/"): "read",
    ("GET", "/.well-known/agent-card.json"): "read",
    ("GET", "/heartbeat"): "read",
    ("GET", "/mailbox"): "read",            # 信箱读取：只读（但需 TOTP 即时因子）
    ("POST", "/"): "execute",               # 消息发送：执行
    ("GET", "/dlq"): "audit",               # 死信查看：审计
    ("POST", "/dlq/retry"): "manage",       # 死信重试：管理（高危）
    ("GET", "/audit"): "audit",             # 审计日志：审计
}

# 高危操作（要求即时因子，而非会话缓存因子）
HIGH_RISK = {"manage", "audit"}


def check(level, required):
    """判级：level 是否满足 required。"""
    if level not in _ORDER or required not in _ORDER:
        return False
    return _ORDER[level] >= _ORDER[required]


def required_for(method, path):
    """给定端点返回所需权限级。"""
    for (m, p), lvl in ENDPOINT_PERMS.items():
        if m == method and (path == p or path.startswith(p + "/")):
            return lvl
    return "execute"  # 默认执行级


if __name__ == "__main__":
    print("  权限序：read < execute < manage < audit")
    print("  check(read, execute) =", check("read", "execute"), "（只读不可执行）")
    print("  check(manage, manage) =", check("manage", "manage"))
    print("  check(audit, manage)  =", check("audit", "manage"), "（审计高于管理）")
    print("  required_for(GET, /mailbox) =", required_for("GET", "/mailbox"))
    print("  required_for(POST, /dlq/retry) =", required_for("POST", "/dlq/retry"))
    print("  高危操作 =", HIGH_RISK)
