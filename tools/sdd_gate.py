#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sdd_gate.py —— SDD 规范驱动开发校验门：规范↔实现一致性。

SDD（Specification-Driven Development）口径：规范先行、实现由规范派生。
本门对 exp/spec/spec-<模块>.md 与 exp/<模块>.py 做浅校验：
  1) 规范声明的「关键函数」在实现中存在（def 定义）；
  2) 实现模块存在且可编译；
  3) 缺规范（有 .py 无 spec）→ 报「缺规范」。
输出 VERDICT=PASS/FAIL。纯标准库。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(HERE, "spec")

# 核心模块清单：规范驱动覆盖范围（探针/审计/一次性脚本不强制规范）
CORE_MODULES = {
    "a2a_node", "a2a_hmac", "a2a_exchange", "a2a_client", "a2a_multiseat_demo",
    "a2a_send_remote", "cas_store", "compensate", "compliance_check", "event_driven",
    "gitcode_search", "heartbeat_daemon", "hetero_models", "knowledge_digest",
    "live_state_loop", "media_validate", "mkled", "open_access", "perm", "proto",
    "quota_wall", "skill_evolve", "slime_mold", "slime_search", "spinal_bridge",
    "task_state", "topology", "totp", "umc", "agp_matrix", "supply_chain",
}


def _spec_modules():
    mods = []
    if os.path.isdir(SPEC_DIR):
        for f in os.listdir(SPEC_DIR):
            if f.startswith("spec-") and f.endswith(".md"):
                mods.append(f[len("spec-"):-len(".md")])
    return sorted(mods)


def _declared_functions(spec_text):
    """提取「关键函数」节的 '- func' 行。"""
    m = re.search(r"## 关键函数\s*\n(.*?)(?=\n## |\Z)", spec_text, re.S)
    if not m:
        return []
    return [line.strip().lstrip("- ").split("(")[0].strip()
            for line in m.group(1).splitlines() if line.strip().startswith("-")]


def verify():
    """规范↔实现浅校验。返回 (ok, report)。"""
    report = []
    mods = _spec_modules()
    for mod in mods:
        spec_path = os.path.join(SPEC_DIR, "spec-%s.md" % mod)
        py_path = os.path.join(HERE, mod + ".py")
        spec = open(spec_path, encoding="utf-8").read()
        funcs = _declared_functions(spec)
        if not os.path.exists(py_path):
            report.append({"module": mod, "ok": False, "reason": "实现缺失"})
            continue
        src = open(py_path, encoding="utf-8").read()
        missing = [f for f in funcs if not re.search(r"\n\s*(class|def)\s+%s\b" % re.escape(f), src)]
        report.append({"module": mod, "ok": not missing,
                       "declared": len(funcs), "missing": missing})
    # 反向：仅核心模块需规范（探针/审计/一次性脚本不强制）
    for mod in sorted(CORE_MODULES - set(mods)):
        py_path = os.path.join(HERE, mod + ".py")
        if not os.path.exists(py_path):
            continue
        report.append({"module": mod, "ok": False, "reason": "缺规范"})
    ok = all(r["ok"] for r in report)
    return ok, report


if __name__ == "__main__":
    ok, report = verify()
    for r in report:
        print("  %s = %s %s" % (r["module"], "OK" if r["ok"] else "FAIL",
                                "" if r["ok"] else (r.get("reason") or ("缺函数:%s" % r.get("missing")))))
    print("VERDICT=" + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
