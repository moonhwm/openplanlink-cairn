#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_agp_matrix.py —— AGP 矩阵断言单测（stdlib unittest）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agp_matrix as A


class AgpMatrixTests(unittest.TestCase):
    def test_matrix_hit(self):
        ok, r = A.assert_matrix("8.5.0", "8.7", True)
        self.assertTrue(ok)

    def test_matrix_drift_rejected(self):
        ok, _ = A.assert_matrix("9.9.0", "9.0", True)
        self.assertFalse(ok)

    def test_gradle_below_min_rejected(self):
        ok, _ = A.assert_matrix("8.5.0", "8.6", True)
        self.assertFalse(ok)

    def test_cache_hit_without_verify_rejected(self):
        ok, _ = A.cache_decouple_check(True, False)
        self.assertFalse(ok)

    def test_full_build_verified(self):
        ok, _ = A.cache_decouple_check(False, True)
        self.assertTrue(ok)

    def test_gate_summary(self):
        self.assertTrue(A.gate("8.5.0", "8.7", True, False, True)["ok"])
        self.assertFalse(A.gate("8.5.0", "8.7", True, True, False)["ok"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print("VERDICT=" + ("PASS" if result.wasSuccessful() else "BAD") + " tests=%d" % result.testsRun)
    sys.exit(0 if result.wasSuccessful() else 1)
