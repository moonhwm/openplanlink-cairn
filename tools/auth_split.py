#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
auth_split.py —— 「分流鉴权」参考实现（无凭据双因子 · 分层放行）。 v1.0.0

由来与定位
──────────
新目标任务：「**完善网络鉴权与开放为实时推演**（作为后续 MicroFish 等类似开源项目的直接 Pannel）」。
A2A 观测站的沙盘页已给出**它自己的范式**：
    「**真节点两证：①指纹在名册 ②链前驱衔接，缺一即红**」
⇒ 本器即把该范式**制度化成分流鉴权**：**按请求能出示的证明强度，分流到不同层**。
   ★ 全流程**不使用任何凭据/密钥**（照其范式：身份＝名册成员，完整性＝链衔接，升权＝第二位成员联署）。

分层（Tier）
────────────
  T0 public  ：不出示任何证明           ⇒ 只读【公开面】（如 status.js 同构的席位侧接口）
  T1 member  ：①指纹在名册 ∧ ②prev 与当前链末衔接 ⇒ 读【实名面】（带复算命令的明细）
  T2 admin   ：T1 ∧ ③**第二位名册成员联署**（且与首位不同） ⇒ 读【可处置面】
  ★ T3 以上不存在——**本器不设"超级权限"**（无凭据体系里，多一层就多一个不可证的口子）。

★ 三条写死的纪律
────────────────
  1. **不用凭据**：全流程只比【公开的名册】与【公开的链】；不引入 secret；
  2. **不接受"更高层"的自我声明**：层由【证明强度算出】，不由请求方指定（防越权自封）；
  3. **防重放**：prev 必须是【当前链末】；另加时间窗（默认 ±120s）。

★ 本器**不起服务、不监听端口、不写任何外部对象**——它是一组**纯函数 + 对抗测试**。
  要真起服务是【网络暴露】动作，按机主旧令须先议后点。

用法: auth_split.py --selftest
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

TIERS = ("T0", "T1", "T2")
WINDOW_S = 120

# ★ v1.1.0 新增：向 Star-Office-UI 学的两件（读其 backend/security_utils.py 与 app.py 所得，[原件直取]）
#   ① 授权有时效：其 /agent-approve 设 authExpiresAt = now + 24h（默认授权 24 小时）
#   ② 活性降级：其 authStatus=approved 而长期无 last_push ⇒ 自动置 offline
#   ⇒ 本器把这两件并进分层：**授权到期 ⇒ 降一级；长期不活跃 ⇒ 置 offline（T0）**。
AUTH_TTL_S = 24 * 3600          # 默认授权 24 小时（与其一致）
LIVENESS_MAX_GAP_S = 90         # 超过此间隔未见推送即视为不活跃（其页"每十五秒推一次"的 6 倍容差）


def authorize(rec: dict, now: float | None = None) -> dict:
    """★ 授权生命周期：pending → approved（24h 到期）→ offline（长期不活跃）。

    rec 形如:
      {"fp":"cairn-dsh", "status":"approved", "approved_at":1696…, "last_push":1696…}
    """
    now = time.time() if now is None else now
    fp = rec.get("fp")
    status = rec.get("status", "pending")
    reasons = []
    if status == "pending":
        reasons.append("待批（pending）⇒ 仅 T0")
        return {"fp": fp, "status": "pending", "tier_cap": "T0", "reasons": reasons}
    age = now - float(rec.get("approved_at") or 0)
    if age > AUTH_TTL_S:
        reasons.append("★授权已过期（%.1fh > %dh）⇒ 降一级" % (age / 3600.0, AUTH_TTL_S // 3600))
        return {"fp": fp, "status": "expired", "tier_cap": "T1", "reasons": reasons}
    gap = now - float(rec.get("last_push") or 0)
    if gap > LIVENESS_MAX_GAP_S:
        reasons.append("★长期不活跃（%.0fs 无推送 > %ds）⇒ 置 offline（T0）" % (gap, LIVENESS_MAX_GAP_S))
        return {"fp": fp, "status": "offline", "tier_cap": "T0", "reasons": reasons}
    reasons.append("授权在期内且活跃")
    return {"fp": fp, "status": "approved", "tier_cap": "T2", "reasons": reasons}


def canon(o) -> bytes:
    """与生态总线口径同源：键排序 + 紧凑分隔（键序不同不得导致 hash 不同）。"""
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def decide(req: dict, roster: list, chain_end: str, now: float | None = None) -> dict:
    """★ 核心：由【证明强度】算出层级——**不接受请求方自封的 tier**。

    req 形如:
      {"fp": "…", "prev": "…", "cosign": "…", "ts": 1696…, "claimed_tier": "T2"(仅作对照)}
    """
    now = time.time() if now is None else now
    reasons = []
    fp = req.get("fp")
    prev = req.get("prev")
    ts = req.get("ts")

    # ① 时间窗（防重放第一层）★ 必须【使 T1 失效】——本器 v1.0.0 曾只记理由不失效，
    #    被本器自己的对抗测试抓出（"时间戳超窗"却仍放行 T1）⇒ 装饰性检查，已修。
    clock_ok = True
    if not isinstance(ts, (int, float)):
        reasons.append("无时间戳"); clock_ok = False
    elif abs(now - ts) > WINDOW_S:
        reasons.append("时间戳超出 ±%ds 窗口" % WINDOW_S); clock_ok = False

    # T1 要件（★ 两证 + 时钟）
    t1 = True
    if fp not in roster:
        t1 = False; reasons.append("指纹不在名册")
    if prev != chain_end:
        t1 = False; reasons.append("链前驱不衔接（疑重放或旧证）")
    if not clock_ok:
        t1 = False
    if not isinstance(ts, (int, float)) or abs(now - ts) > WINDOW_S:
        pass  # 理由已记；此处仅确保 t1 已置否

    # T2 要件：**必须真的拿到**第二位【不同】名册成员的联署；拿不到就退回 T1。
    # ★ 本器曾把「没有联署」当成「不降级」，致 t2 保持为真 ⇒ **无第二证也能升 T2（越权升级）**，
    #   由本器自己的对抗测试抓出 ⇒ 改为下面的显式肯定式：**默认 False，只有验证通过才置 True**。
    t2 = False
    cosign = req.get("cosign")
    if t1:
        if cosign in roster and cosign != fp:
            t2 = True
        elif cosign is None:
            reasons.append("无联署 ⇒ 仅 T1")
        elif cosign == fp:
            reasons.append("联署人与首位为同一成员（不构成第二证）")
        else:
            reasons.append("联署人不在名册")

    tier = "T2" if t2 else ("T1" if t1 else "T0")
    claimed = req.get("claimed_tier")
    escalate = bool(claimed and TIERS.index(claimed) > TIERS.index(tier))
    if escalate:
        reasons.append("★请求自封 %s，实算 %s ⇒ 越权企图已记" % (claimed, tier))
    return {"tier": tier, "reasons": reasons, "escalation_attempt": escalate}


def grant(tier: str) -> list:
    """各层可得的能力——**最小授权**。"""
    return {
        "T0": ["public_status"],                                  # status.js 同构接口
        "T1": ["public_status", "member_detail"],                 # 带复算命令的明细
        "T2": ["public_status", "member_detail", "action_propose"] # 可提议处置（仍非"代裁"）
    }[tier]


# ────────────────────────── 对抗测试 ──────────────────────────
def selftest() -> int:
    ROSTER = ["cairn-dsh", "workbuddy-hy4", "su-qinghe-coze"]
    END = sha256_hex(b"chain-end-demo")
    now = 1_700_000_000.0
    cases = [
        # (名, 请求, 期望层, 期望是否越权)
        ("T0 · 什么都不出示", {}, "T0", False),
        ("T1 · 两证齐（指纹在册 + 链衔接）",
         {"fp": "cairn-dsh", "prev": END, "ts": now}, "T1", False),
        ("T1 · 指纹不在名册 ⇒ 降为 T0",
         {"fp": "stranger", "prev": END, "ts": now}, "T0", False),
        ("T1 · 链前驱不衔接（旧证/重放）⇒ 降为 T0",
         {"fp": "cairn-dsh", "prev": sha256_hex(b"old"), "ts": now}, "T0", False),
        ("T1 · 时间戳超窗 ⇒ 降为 T0",
         {"fp": "cairn-dsh", "prev": END, "ts": now - 9999}, "T0", False),
        ("T2 · 两证齐 + 第二位成员联署",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "cosign": "workbuddy-hy4"}, "T2", False),
        ("T2 · 联署人与首位同一 ⇒ 不构成第二证 ⇒ T1",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "cosign": "cairn-dsh"}, "T1", False),
        ("T2 · 联署人不在名册 ⇒ T1",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "cosign": "stranger"}, "T1", False),
        ("★越权 · 自封 T2 但只有 T1 的证 ⇒ 实算 T1 且记越权",
         {"fp": "cairn-dsh", "prev": END, "ts": now, "claimed_tier": "T2"}, "T1", True),
        ("★越权 · 无证自封 T2 ⇒ 实算 T0 且记越权",
         {"fp": "stranger", "prev": "x", "ts": now, "claimed_tier": "T2"}, "T0", True),
    ]
    print("═══ 分流鉴权 · 对抗测试 ═══")
    ok = True
    pos = neg = 0
    for name, req, want_tier, want_esc in cases:
        r = decide(req, ROSTER, END, now=now)
        good = (r["tier"] == want_tier) and (r["escalation_attempt"] == want_esc)
        ok = ok and good
        if want_tier in ("T1", "T2"):
            pos += 1
        else:
            neg += 1
        print("  %s %-46s ⇒ %s（期望 %s）%s" % (
            "✓" if good else "★FAIL", name, r["tier"], want_tier,
            ("｜" + "; ".join(r["reasons"][:2])) if r["reasons"] else ""))
    print()
    print("  正例（应放行）%d 条 ｜ 反例（应拦）%d 条" % (pos, neg))
    print("  ★本器同时具备【放行】与【拦截】两种结果 ⇒ 测试非恒真。")
    print("  ★要点：**层由证明强度算出，请求自封无效**；且**升到 T2 必须两位【不同】成员**。")
    print("[SELFTEST] %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="分流鉴权参考实现（不起服务）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
