#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_compliance_layer.py —— 开源五层组合单测（stdlib unittest）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compliance_check as C


class ComplianceLayerTests(unittest.TestCase):
    def test_five_layers(self):
        self.assertEqual(C.license_layer("code"), "AGPL-3.0")
        self.assertEqual(C.license_layer("server-stack"), "SSPL-1.0")
        self.assertEqual(C.license_layer("docs"), "CC-BY-SA-4.0")
        self.assertEqual(C.license_layer("dataset"), "ODbL-1.0")
        self.assertEqual(C.license_layer("governance"), "不进许可体系")

    def test_gpl3_network_ineligible(self):
        self.assertIn("不适格", C.gpl3_ineligible_note(True))

    def test_cc_odbl_match(self):
        self.assertIn("CC-BY-SA-4.0", C.match_license("CC BY-SA 4.0")["matched"])
        self.assertIn("ODbL-1.0", C.match_license("Open Data Commons ODbL")["matched"])

    def test_terms_norm(self):
        r = C.check_terms("遵循党组纪律与学术技术规范，留痕审计")
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["covered_count"], 2)

    def test_format_issues(self):
        r = C.check_format("仅一行文本")
        self.assertFalse(r["ok"])
        self.assertTrue(any("修订记录" in i for i in r["issues"]))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print("VERDICT=" + ("PASS" if result.wasSuccessful() else "BAD") + " tests=%d" % result.testsRun)
    sys.exit(0 if result.wasSuccessful() else 1)
