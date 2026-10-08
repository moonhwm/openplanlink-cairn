#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""task_state.py —— 任务分发状态机（五态 + 幂等键 + 重试/超时）。

依《蓝图OTL主文档》第八章（一）第三节：task_id/幂等 key/状态机
queued-running-succeeded-failed-cancelled、重试上限 3、超时 120s。
纯标准库，Windows 直跑。
"""
import time

STATES = ("queued", "running", "succeeded", "failed", "cancelled")
MAX_RETRY = 3
TIMEOUT_S = 120


class TaskState:
    def __init__(self, task_id, idem_key):
        self.task_id = task_id
        self.idem_key = idem_key          # 幂等键：同键重复投递不产生重复副作用
        self.state = "queued"
        self.retries = 0
        self.ts = time.time()

    def transition(self, to):
        """状态机转移（带合法性约束）。"""
        legal = {
            "queued": ("running", "cancelled"),
            "running": ("succeeded", "failed", "cancelled"),
            "failed": ("running",),        # 重试回 running
            "succeeded": (),
            "cancelled": (),
        }
        if to not in legal.get(self.state, ()):
            return False, "非法转移 %s→%s" % (self.state, to)
        self.state = to
        self.ts = time.time()
        return True, "ok"

    def fail_retry(self):
        """失败后重试：未达上限则回 running，达上限保持 failed。"""
        if self.state != "failed":
            return False, "非 failed 态不可重试"
        if self.retries < MAX_RETRY:
            self.retries += 1
            self.state = "running"
            return True, "重试 %d/%d" % (self.retries, MAX_RETRY)
        return False, "已达重试上限 %d" % MAX_RETRY

    def timed_out(self):
        """是否超时（120s）。"""
        return self.state in ("queued", "running") and (time.time() - self.ts) > TIMEOUT_S


if __name__ == "__main__":
    t = TaskState("t-001", "idem-abc")
    print("  初态 =", t.state)
    print("  转 running =", t.transition("running"))
    print("  转 succeeded =", t.transition("succeeded"))
    print("  非法转 cancelled =", t.transition("cancelled"), "（succeeded 终态）")
    t2 = TaskState("t-002", "idem-def")
    t2.transition("running"); t2.transition("failed")
    print("  失败重试 3 次 =", [t2.fail_retry()[0] for _ in range(3)])
    print("  第4次重试 =", t2.fail_retry(), "（达上限）")
    print("  状态机五态 =", STATES, "｜ 重试上限 =", MAX_RETRY, "｜ 超时 =", TIMEOUT_S)
