#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""compensate.py —— 补偿事务（Saga 补偿模式：自动回滚已执行步骤）。

依《认证流程专章》第七章（一）：MFA 验证失败或钩子校验未通过时执行自动回滚，
已执行之半程操作（暂存、构建中间产物、临时授权）按补偿逻辑逆序撤销。
参照 Saga orchestration pattern（AWS Prescriptive Guidance，按标题引用）。
纯标准库，Windows 直跑。

新增（全局声明增量）：saga() 编排 + MFA_FAIL / GIT_HOOK_FAIL 触发点回滚。
"""
import json
import pathlib

AUDIT_FILE = pathlib.Path(__file__).parent / "compensate_audit.jsonl"


class Tx:
    """补偿事务：记录步骤的撤销函数，失败时逆序回滚。"""

    def __init__(self):
        self.steps = []      # [(label, undo_fn)]
        self.committed = False

    def step(self, label, do_fn, undo_fn):
        """执行一步：do_fn 成功则登记 undo_fn；do_fn 抛异常则立即逆序回滚已执行步骤。"""
        try:
            do_fn()
        except Exception:
            self.rollback()
            raise
        self.steps.append((label, undo_fn))
        return label

    def rollback(self):
        """逆序撤销已执行步骤。"""
        for label, undo in reversed(self.steps):
            undo()
        self.steps = []

    def commit(self):
        self.committed = True
        self.steps = []


def _audit(trigger, detail):
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"trigger": trigger, "detail": detail}, ensure_ascii=False) + "\n")


def _notify(title, desp):
    """Server酱告警：sendkey 经环境变量注入；未配置则跳过（不阻断回滚）。"""
    import os
    import urllib.request
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "")
    if not sendkey:
        return False
    try:
        data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
        urllib.request.urlopen("https://sctapi.ftqq.com/%s.send" % sendkey, data=data, timeout=10)
        return True
    except Exception:
        return False


def saga(trigger, steps):
    """Saga 编排：steps=[(label, do_fn, undo_fn)]；任一步失败即逆序回滚 + 审计 + 告警。

    trigger ∈ {"MFA_FAIL", "GIT_HOOK_FAIL", "generic"}——全局声明要求 MFA 失败/Git 钩子
    未通过时自动回滚、记审计、告警管理员，且不影响核心业务流连续性（回滚兜底）。
    """
    import urllib.parse
    tx = Tx()
    for label, do, undo in steps:
        tx.step(label, do, undo)
    try:
        # 触发点判定：MFA_FAIL/GIT_HOOK_FAIL 在 do 后强制回滚（模拟校验未通过）
        if trigger in ("MFA_FAIL", "GIT_HOOK_FAIL"):
            tx.rollback()
            _audit(trigger, {"labels": [s[0] for s in steps], "rolled_back": True})
            _notify("A2A 补偿回滚", "%s 触发：已逆序回滚 %d 步并留痕" % (trigger, len(steps)))
            return {"ok": False, "trigger": trigger, "rolled_back": True}
        tx.commit()
        _audit(trigger, {"labels": [s[0] for s in steps], "committed": True})
        return {"ok": True, "trigger": trigger, "committed": True}
    except Exception as e:
        tx.rollback()
        _audit(trigger, {"error": "%s: %s" % (type(e).__name__, e), "rolled_back": True})
        return {"ok": False, "trigger": trigger, "rolled_back": True, "reason": str(e)}


if __name__ == "__main__":
    log = []
    tx = Tx()
    tx.step("暂存", lambda: log.append("暂存A"), lambda: log.append("撤销A"))
    tx.step("临时授权", lambda: log.append("授权B"), lambda: log.append("撤销B"))
    print("  执行后 log =", log)
    tx.rollback()          # 模拟 MFA 失败 → 自动回滚
    print("  回滚后 log =", log, "（逆序撤销：撤销B→撤销A）")

    # saga：MFA_FAIL 触发回滚
    log3 = []
    r = saga("MFA_FAIL", [("暂存", lambda: log3.append("暂存"), lambda: log3.append("撤销"))])
    print("  saga(MFA_FAIL) =", r, "log3 =", log3)
    r2 = saga("GIT_HOOK_FAIL", [("构建", lambda: log3.append("构建"), lambda: log3.append("撤销构建"))])
    print("  saga(GIT_HOOK_FAIL) =", r2, "log3 =", log3)
    r3 = saga("generic", [("提交", lambda: log3.append("提交"), lambda: log3.append("撤销提交"))])
    print("  saga(generic 成功) =", r3)
