#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_event_compensate.py —— 事件补偿链路单测（stdlib unittest）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import event_driven as E
import compensate as C


class EventCompensateTests(unittest.TestCase):
    def setUp(self):
        E._HANDLERS.clear()

    def test_idempotent_dup(self):
        def h(s, p):
            return {"ok": True}
        E.on("message_arrival")(h)
        E.emit("message_arrival", "a", {"x": 1}, "k1")
        r = E.emit("message_arrival", "a", {"x": 1}, "k1")
        self.assertTrue(r["dup"])

    def test_failure_to_dlq(self):
        def h(s, p):
            return {"ok": False, "reason": "boom"}
        E.on("message_arrival")(h)
        r = E.emit("message_arrival", "a", {"x": 1}, "k-dlq", on_failure="dlq")
        self.assertFalse(r["ok"])
        self.assertTrue(r["dlq"])

    def test_failure_rollback(self):
        def h(s, p):
            return {"ok": False, "reason": "MFA 失败"}
        E.on("mfa_fail")(h)
        r = E.emit("mfa_fail", "a", {}, "k-roll", on_failure="rollback")
        self.assertTrue(r["rolled_back"])

    def test_saga_mfa_fail_rollback(self):
        log = []
        r = C.saga("MFA_FAIL", [("暂存", lambda: log.append("do"), lambda: log.append("undo"))])
        self.assertFalse(r["ok"])
        self.assertEqual(log, ["do", "undo"])

    def test_saga_git_hook_fail_rollback(self):
        log = []
        r = C.saga("GIT_HOOK_FAIL", [("构建", lambda: log.append("do"), lambda: log.append("undo"))])
        self.assertFalse(r["ok"])
        self.assertEqual(log, ["do", "undo"])

    def test_saga_generic_commit(self):
        log = []
        r = C.saga("generic", [("提交", lambda: log.append("do"), lambda: log.append("undo"))])
        self.assertTrue(r["ok"])
        self.assertEqual(log, ["do"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print("VERDICT=" + ("PASS" if result.wasSuccessful() else "BAD") + " tests=%d" % result.testsRun)
    sys.exit(0 if result.wasSuccessful() else 1)
