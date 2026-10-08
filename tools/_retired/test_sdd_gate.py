#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_sdd_gate.py —— SDD 门单测（stdlib unittest）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdd_gate as S


class SddGateTests(unittest.TestCase):
    def test_spec_modules_nonempty(self):
        self.assertGreaterEqual(len(S._spec_modules()), 20)

    def test_declared_functions_parse(self):
        spec = "## 关键函数\n- emit\n- on\n\n## 验收断言\nx"
        self.assertEqual(S._declared_functions(spec), ["emit", "on"])

    def test_verify_pass(self):
        ok, report = S.verify()
        self.assertTrue(ok, "SDD 门未通过: %s" % [r for r in report if not r["ok"]])

    def test_core_modules_covered(self):
        ok, report = S.verify()
        self.assertTrue(all(r["ok"] for r in report))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print("VERDICT=" + ("PASS" if result.wasSuccessful() else "BAD") + " tests=%d" % result.testsRun)
    sys.exit(0 if result.wasSuccessful() else 1)
