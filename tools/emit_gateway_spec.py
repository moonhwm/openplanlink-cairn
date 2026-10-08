#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NONE —— 本件只读本机两件鉴权表并写出一个 JSON；不触网。
r"""emit_gateway_spec.py —— 从本席鉴权两层【生成】分流鉴权网关的接口规格。 v1.0.0

为什么要生成而不是手写
────────────────────────
目标 ⑬ 写「公网能够访问，**我尝试做个分流鉴权**」——**那座网关是机主在做**。
而本席这一侧的活是「完善网络鉴权」，**已建两层**（`auth_split` 层引擎 ＋ `auth_policy` 应用层）。
⇒ 但**网关那一侧【不知道】我这侧要什么**。
★ **手写的接口说明会漂移**（表改了、说明没改）⇒ **故本器【从表里生成】**：
  **直接 import `auth_split` 与 `auth_policy`，把它们的数据结构原样输出。**

★ 只有一处是【引文】：T0/T1/T2 各自的证明要求写在 `auth_split` 的**文档字符串**里，
  本器**照抄并标明它是引文**，不另作解释。
"""
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auth_policy            # noqa: E402
import auth_split             # noqa: E402

OUT = HERE.parent / "outbox" / "gateway_spec.json"

# ★ 引文：T0/T1/T2 的证明要求——**照抄 auth_split 的文档字符串**（标明为引文，不另解释）
TIER_DOC = {
    "T0": "不出示任何证明 ⇒ 只读【公开面】（如 status.js 同构的席位侧接口）",
    "T1": "①指纹在名册 ∧ ②prev 与当前链末衔接 ⇒ 读【实名面】（带复算命令的明细）",
    "T2": "T1 ∧ ③第二位名册成员联署（且与首位不同）⇒ 读【可处置面】",
}


def main() -> int:
    spec = {
        "schema": "cairn-gateway-spec/1",
        "_generated_by": "exp/emit_gateway_spec.py（**从表里生成，非手写**）",
        "_purpose": "本席（cairn-dsh）与本席策略层之间，对【分流鉴权网关】的接口约定。",
        "_side_note": "★ 网关由机主建；本件只说明【我这侧要什么、给什么、期望什么答复】。",

        "tiers": {
            "_source": "auth_split.TIERS ＋ 其文档字符串（★下列 requirement 为【引文】）",
            "values": list(auth_split.TIERS),
            "requirement_quoted": TIER_DOC,
            "core_rule": "★ 层由【证明强度】算出——**不接受请求方自封的 tier**。",
            "degradation": {
                "pending": "待批 ⇒ 仅 T0",
                "expired": "授权到期 ⇒ 降一级",
                "offline": "长期不活跃 ⇒ 置 offline（T0）",
            },
        },

        "what_i_send": {
            "T1": ["fp（指纹）", "prev（我所持链的上一环）", "ts"],
            "T2": ["fp", "prev", "cosign（第二位名册成员的联署）", "ts"],
            "_note": "★ `claimed_tier` 可附带，但【仅作对照】——不得据以放行。",
        },

        "verdicts": {
            "_source": "auth_policy.check() 的四态（★第四态单列，不并入 DENY）",
            "values": ["ALLOW", "DENY", "NEED-OWNER", "UNDEFINED"],
            "meaning": {
                "ALLOW": "现状已达标",
                "DENY": "现状不达标，且本席不点火",
                "NEED-OWNER": "缺的不是技术，是机主的一句话（昵称／授权／写权限／政策）",
                "UNDEFINED": "该（通道,方向,敏感度）组合未设策略——既非放行亦非拒绝",
            },
            "gateway_expectation": "★ 网关若无法判定，应回 UNDEFINED 或 NEED-OWNER，**不得默认放行、也不得把'未定义'说成'拒绝'**。",
        },

        "need_table": [
            {"channel": k[0], "direction": k[1], "sensitivity": k[2], "required_tier": v}
            for k, v in sorted(auth_policy.NEED.items())
        ],

        "channels_measured": [
            {"channel": c["ch"], "direction": c["direction"], "current_tier": c.get("cur"),
             "note": c.get("note", "")}
            for c in auth_policy.CHANNELS
        ],

        "_honest_boundary": (
            "★ 本件是【我这侧对网关的期望】，不是【网关的规格书】；"
            "网关的实际能力由其作者定义。"
            "★ 且 need_table 与 channels_measured **原样取自 auth_policy 的数据结构**——"
            "若那两处变了而本件未重生成，本件即过期（**故应随时重跑本器**）。"
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print("═══ 生成分流鉴权网关接口规格（从表里生成）═══")
    print("  写出 = %s（%d B）" % (OUT.name, OUT.stat().st_size))
    print("  层        = %s" % "、".join(spec["tiers"]["values"]))
    print("  裁决四态  = %s" % "、".join(spec["verdicts"]["values"]))
    print("  need 表   = %d 条" % len(spec["need_table"]))
    for r in spec["need_table"]:
        print("     %-14s %-4s %-10s ⇒ %s" % (r["channel"], r["direction"], r["sensitivity"], r["required_tier"]))
    print("  实测通道  = %d 条" % len(spec["channels_measured"]))
    for c in spec["channels_measured"]:
        print("     %-14s %-4s 现状=%s" % (c["channel"], c["direction"], c["current_tier"]))
    print()
    print("  ★ 本器能失败：导入失败即 ERR；数据为空即写出空表（可被下游发现）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
