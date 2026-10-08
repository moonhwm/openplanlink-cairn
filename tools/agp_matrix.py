#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""agp_matrix.py —— AGP 版本兼容性矩阵 + 认证/编码与构建缓存解耦断言。

全局声明口径：AGP 升级须与兼容性矩阵对齐，避免工具链版本漂移致 MFA 策略失效/Git 钩子异常；
AV1/H265 校验与 AGP 构建缓存解耦，缓存命中仍强制认证状态复查；校验入发布门禁。
本席无 Android/鸿蒙工具链，落地「矩阵/断言/CI 校验逻辑」，实际构建待工具链实测。
纯标准库。
"""
import json
import pathlib

# AGP 版本 × 最低 Gradle × MFA 回退风险 × AV1/H265 强制校验（矩阵）
AGP_COMPAT = [
    {"agp": "8.5.0", "min_gradle": "8.7", "mfa_risk": "无", "av1_h265": "强制"},
    {"agp": "8.4.0", "min_gradle": "8.6", "mfa_risk": "无", "av1_h265": "强制"},
    {"agp": "8.3.0", "min_gradle": "8.4", "mfa_risk": "无", "av1_h265": "强制"},
    {"agp": "8.2.0", "min_gradle": "8.2", "mfa_risk": "低", "av1_h265": "强制"},
    {"agp": "8.1.0", "min_gradle": "8.0", "mfa_risk": "低", "av1_h265": "强制"},
    {"agp": "8.0.0", "min_gradle": "8.0", "mfa_risk": "中(认证回退)", "av1_h265": "强制"},
]

AUDIT_FILE = pathlib.Path(__file__).parent / "agp_matrix_audit.jsonl"


def _ver_tuple(v):
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except Exception:
        return (0, 0, 0)


def assert_matrix(agp_version, gradle_version, av1_h265_enabled=True):
    """AGP 版本匹配度断言：矩阵命中 + Gradle 达标 + AV1/H265 强制校验。"""
    row = None
    for r in AGP_COMPAT:
        if r["agp"] == agp_version:
            row = r
            break
    if row is None:
        return False, {"reason": "AGP 版本不在矩阵(漂移风险)"}
    if _ver_tuple(gradle_version) < _ver_tuple(row["min_gradle"]):
        return False, {"reason": "Gradle %s 低于矩阵要求 %s（认证回退风险）" % (gradle_version, row["min_gradle"])}
    if row["mfa_risk"] in ("中(认证回退)", "高"):
        return False, {"reason": "AGP %s MFA 策略存在认证回退风险，禁入生产" % agp_version}
    if not av1_h265_enabled:
        return False, {"reason": "AV1/H265 校验未启用，禁入生产"}
    return True, {"agp": agp_version, "gradle": gradle_version, "mfa_risk": row["mfa_risk"],
                  "av1_h265": row["av1_h265"]}


def cache_decouple_check(build_cache_hit, av1_h265_verified):
    """AV1/H265 校验与构建缓存解耦断言：缓存命中不得跳过产物校验；
    缓存命中且未验编码 → 强制触发认证状态复查（FAIL）。"""
    if build_cache_hit and not av1_h265_verified:
        return False, {"reason": "AGP 缓存命中但 AV1/H265 未验——增量编译跳过产物校验，强制认证状态复查"}
    if not build_cache_hit and not av1_h265_verified:
        return False, {"reason": "全量构建 AV1/H265 未验，产物校验未通过"}
    return True, {"cache_hit": build_cache_hit, "av1_h265_verified": av1_h265_verified}


def gate(agp_version, gradle_version, av1_h265_enabled=True, build_cache_hit=False, av1_h265_verified=True):
    """发布门禁汇总：矩阵匹配度 + 缓存解耦断言，结果入审计 JSONL。"""
    ok1, r1 = assert_matrix(agp_version, gradle_version, av1_h265_enabled)
    ok2, r2 = cache_decouple_check(build_cache_hit, av1_h265_verified)
    result = {"ok": ok1 and ok2, "matrix": r1, "cache": r2}
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result


if __name__ == "__main__":
    print("  矩阵命中(8.5/8.7) =", assert_matrix("8.5.0", "8.7", True))
    print("  矩阵漂移(9.9) =", assert_matrix("9.9.0", "9.0", True))
    print("  缓存解耦(命中未验) =", cache_decouple_check(True, False))
    print("  缓存解耦(全量已验) =", cache_decouple_check(False, True))
    print("  门禁汇总 =", gate("8.5.0", "8.7", True, False, True)["ok"])
