#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""media_validate.py —— AV1/H265 编码校验规则（声明式 + 独立阶段，与构建缓存解耦）。

依《认证流程专章》第六章：①编码校验规则声明式配置入库并版本化；②校验规则与 AGP 构建缓存解耦、
作为独立阶段执行、不随增量命中短路；③缓存键值与校验结果关联断言。
本仓库当前 0 媒体文件、0 Gradle 面（已如实盘点），本模块将规则固化、留待有媒体产物时启用。
纯标准库，Windows 直跑。
"""
import os
import sys

# ① 声明式编码校验规则（入库版本化，规则变更须过双重校验钩子 + 全量回归）
RULES = {
    "av1": {
        "encoders": ["aom", "rav1e", "svt-av1"],     # 编码器标识白名单
        "containers": [".mp4", ".mkv", ".webm"],      # 容器封装一致性
        "profile": "main",
    },
    "h265": {
        "encoders": ["x265", "svt-hevc"],
        "containers": [".mp4", ".mkv"],
        "profile": "main",
    },
}


def classify(path):
    """按扩展名初判编码族（av1/h265/未知）。"""
    ext = os.path.splitext(path)[1].lower()
    for codec, r in RULES.items():
        if ext in r["containers"]:
            return codec
    return None


def validate(path, codec=None):
    """独立阶段编码校验（与构建缓存解耦：无论缓存命中与否，产物必经此校验）。

    诚实边界：本机无 ffprobe，深校验（编码器标识/码流合规/分辨率码率）需 ffprobe，
    此处仅做存在性 + 容器白名单 + 体积非空；深校验留待有媒体产物时接 ffprobe。
    """
    if not os.path.exists(path):
        return False, "文件不存在"
    if os.path.getsize(path) == 0:
        return False, "空文件"
    if codec is None:
        codec = classify(path)
    if codec is None:
        return False, "容器不在 AV1/H265 白名单"
    if not codec in RULES:
        return False, "未知编码族"
    # 独立阶段标记：本校验不依附增量编译流程，缓存命中亦不短路
    return True, "容器合规（%s）｜深校验待 ffprobe" % codec


def assertion(validate_result_ok, rule_version, cache_rule_version):
    """缓存键值关联断言：缓存条目内嵌校验结果摘要 + 规则版本须一致，否则缓存失效。"""
    return validate_result_ok and rule_version == cache_rule_version


if __name__ == "__main__":
    import tempfile
    f = os.path.join(tempfile.gettempdir(), "demo.mp4")
    open(f, "wb").write(b"\x00\x00\x00\x18ftypmp42")  # 伪造 mp4 头
    ok, msg = validate(f)
    print("  classify(demo.mp4) =", classify(f))
    print("  validate =", ok, "｜", msg)
    print("  断言(通过+版本一致) =", assertion(True, "v1", "v1"))
    print("  断言(版本漂移)     =", assertion(True, "v1", "v2"))
