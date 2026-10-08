#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
auth_policy.py —— 分流鉴权的【应用层】：把 T0/T1/T2 接到本席今晚实测过的那几条通道上。 v1.0.0

定位（**不重造层引擎**）
────────────────────────
`auth_split.py` 已给出层引擎：**层由证明强度算出、请求自封无效、T2 须两位不同成员联署、
授权有时效、长期不活跃降级**（其自测 正例5／反例5 全过）。
⇒ 本器**只做它没做的那一半**：**声明「哪条通道、哪个方向、哪种敏感度 ⇒ 需要第几层」，
并把每条通道的【实测现状】与要求对照，给出 ALLOW／DENY／NEED-OWNER 的裁决与理由。**
⇒ **层判定一律【调用】** `auth_split.decide` / `.authorize`（不另写一套，免生漂移）。

★ 通道的"实测现状"逐条来自本席今晚的实测件，件名写在 evidence 里。
★ 裁决三态：`ALLOW`（现状已达标）｜`DENY`（现状不达标，且本席不点火）｜
  `NEED-OWNER`（缺的不是技术，是机主的一句话：昵称／授权／写权限／政策）。
★ 本器**不起服务、不监听端口、不写外部对象**——纯函数 ＋ 自测。
用法: auth_policy.py [--table]
"""
from __future__ import annotations
import argparse
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import pathlib                        # ★ 轮104：sensitivity_of 移入本器后需要
SHARED = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\全局声明_治理文档\a2a-inbox\cairn-dsh")
try:
    import auth_split as A            # ★ 层引擎：调用它，不重写它
    TIERS = A.TIERS
except Exception as e:                 # pragma: no cover
    print("[ERR] 未能载入层引擎 auth_split.py：%s" % e)
    sys.exit(3)

# ── 敏感度 → 所需层（本席对所测通道的判定；逐条附理由）──
NEED = {
    ("observatory.read",  "in",  "public"):    "T0",   # 静态站公开页
    ("observatory.read",  "in",  "sensitive"): "T1",   # 若要读实名面
    ("observatory.write", "out", "public"):    "T2",   # 发布＝改对外形象
    ("meow.push",         "out", "public"):    "T1",   # 推送即面向机主本人
    ("meow.push",         "out", "sensitive"): "T2",   # ★其 msgType=html 会在应用内渲染 HTML
    ("sharedplane.write", "out", "sensitive"): "T1",   # 只增不改 ＋ .sha256 伴随物
    ("a2a.call",          "out", "public"):    "T1",   # 总线调用＝实名行为
    ("github.write",      "out", "sensitive"): "T2",   # 对外仓库写面
    ("kdocs.read",        "in",  "sensitive"): "T1",   # 云端原件
    ("undeclared_fetch",  "in",  "public"):    "T2",   # ★本席闸口 A：未声明即不取
}

# ── 各通道【实测现状】＋出处 ──
CHANNELS = [
    dict(ch="observatory.read", direction="in", cur="T0",
         note="静态七页；公开可读（本席轮 57/81/82 实测）",
         ev="追加件_逐页审计…入口页空白"),
    dict(ch="observatory.write", direction="out", cur="—",
         note="★无发布 API：发布＝把整页文本粘进 Kimi Build 对话（轮 72 实测）",
         ev="追加件_读74号令答我三处并纠我一处"),
    dict(ch="meow.push", direction="out", cur="T0",
         note="★无鉴权；昵称即唯一明文凭据；msgType=html 在应用内渲染 HTML（轮 70 实测）",
         ev="追加件_两应用解码与MeoW推送面鉴权分析",
         owner="①机主给 Meow 昵称 ②分流鉴权网关上线（74号令 §一.2 原文的启用前置）"),
    dict(ch="sharedplane.write", direction="out", cur="T1",
         note="本机目录，非网络暴露面；写纪律由【只增不改 ＋ .sha256 伴随物】承担（本席自持）",
         ev="同侪验证套件 ⑤ 逐件相符 185/185"),
    dict(ch="a2a.call", direction="out", cur="?",
         note="端点上次 502；未观测到鉴权（轮 69）",
         ev="追加件_两席撞在同一结论名片我让",
         owner="是否允许重试调用"),
    dict(ch="github.write", direction="out", cur="T0",
         note="写面 403（沈铎实测）；integrations 未授 contents:write",
         ev="仓库连通分析_openplanlink-mirror_沈铎",
         owner="是否授 contents:write（我轮 97 待裁第 11 项）"),
    dict(ch="kdocs.read", direction="in", cur="—",
         note="云端原件未读（本席无授权）",
         ev="我轮 97 待裁第 10 项",
         owner="是否授权读 kdocs 云端原件"),
    dict(ch="undeclared_fetch", direction="in", cur="T0",
         note="★本席自定闸口 A：robots 未声明即不取（已挡住我自己三次）",
         ev="呈机主_政策选择题_A放行0比4",
         owner="政策 A／B／★D 三选一（我倾向 D：授权须来自具名来源）"),
]


def sensitivity_of(payload: str | None, shared: "pathlib.Path | None" = None):
    """★ 敏感度【算出】，不由调用方自封（与层引擎同一条原则）。

    判据（可计算）：**这份内容是否已经发布、且任何同侪可独立复核？**
      · 未给来源件 ⇒ 不在已发布语料内 ⇒ `sensitive`
      · 件不存在 ⇒ `sensitive`
      · 共享面无 `.sha256` 伴随物 ⇒ 未发布／不可复核 ⇒ `sensitive`
      · 伴随物与件字节不符 ⇒ 不可复核 ⇒ `sensitive`
      · 在共享面 ∧ 伴随物复核通过 ⇒ `public`
    ★ 四条失败路径全部落到从严一侧 ⇒ 只会更严，不会更松。
    ★ 轮104：本函数自 `meow_push.py` **移入**本器——**两份判据会漂移，故只留一份**。
    """
    import hashlib as _h
    import pathlib as _p
    shared = shared or SHARED
    if not payload:
        return "sensitive", "未给来源件 ⇒ 内容不在已发布语料内（从严一侧）"
    p = _p.Path(payload)
    if not p.is_file():
        return "sensitive", "指定件不存在 ⇒ 无从复核（从严一侧）"
    side = shared / (p.name + ".sha256")
    if not side.is_file():
        return "sensitive", "共享面无该件的 .sha256 伴随物 ⇒ 未发布/不可复核（从严一侧）"
    try:
        claimed = side.read_text(encoding="utf-8", errors="replace").split()[0].lower()
        actual = _h.sha256(p.read_bytes()).hexdigest()
        if claimed != actual:
            return "sensitive", "伴随物与件字节不符 ⇒ 不可复核（从严一侧）"
    except Exception:
        return "sensitive", "伴随物读取失败 ⇒ 不可复核（从严一侧）"
    return "public", "已在共享面发布且 .sha256 复核通过 ⇒ 可复核 ⇒ public"


def check(channel: str, direction: str, sensitivity: str):
    """返回 (verdict, reason)。**四态**：ALLOW ／ DENY ／ NEED-OWNER ／ UNDEFINED。

    ★ 轮102 修：初版把「该组合未设策略」也报成 DENY，并在汇总里计入 ⇒
      那是把【没定义】fold 成【拒绝】——与本席判读规则⑩（OK／BAD／ERR 不可互顶）同族。
      故独立出第四态 UNDEFINED，汇总时单列，不计入 DENY。
    """
    need = NEED.get((channel, direction, sensitivity))
    if need is None:
        return "UNDEFINED", "该（通道,方向,敏感度）组合未设策略——既非放行亦非拒绝"
    row = next((c for c in CHANNELS if c["ch"] == channel and c["direction"] == direction), None)
    if row is None:
        return "NEED-OWNER", "策略表有要求（%s），但该通道无实测记录 ⇒ 交机主" % need
    cur = row["cur"]
    if cur == "—" or cur == "?":
        return "NEED-OWNER", "现状未知（%s）⇒ 不擅自尝试；需 %s" % (cur, need)
    if TIERS.index(cur) >= TIERS.index(need):
        return "ALLOW", "现状 %s ≥ 所需 %s" % (cur, need)
    return "DENY", "现状 %s < 所需 %s ⇒ 拒绝执行%s" % (
        cur, need, ("；机主前置：" + row["owner"]) if row.get("owner") else "")


def table() -> int:
    print("═══ 分流鉴权·应用层策略表（承 auth_split 层引擎）═══")
    print("  层：%s（T3 以上不存在——无凭据体系里，多一层就多一个不可证的口子）" % " < ".join(TIERS))
    print()
    print("  %-20s %-4s %-5s %-12s %s" % ("通道", "方向", "现状", "敏感度→所需", "裁决"))
    print("  " + "-" * 92)
    gaps, needs, undef = [], [], []
    for row in CHANNELS:
        for sens in ("public", "sensitive"):
            v, why = check(row["ch"], row["direction"], sens)
            if v == "ALLOW" or v == "UNDEFINED":
                if v == "UNDEFINED":
                    undef.append((row["ch"], sens))
                continue
            print("  %-20s %-4s %-5s %-12s %s" % (
                row["ch"], row["direction"], row["cur"],
                "%s→%s" % (sens, NEED.get((row["ch"], row["direction"], sens), "?")), v))
            (needs if v == "NEED-OWNER" else gaps).append((row["ch"], sens, why))
    print()
    print("  ── 汇总 ──")
    print("  ★ DENY（现状不达标，本席不点火）：%d 项" % len(gaps))
    print("  ★ NEED-OWNER（缺的是您的一句话）：%d 项" % len(needs))
    print("  ★ UNDEFINED（该组合未设策略，既非放行亦非拒绝）：%d 项" % len(undef))
    seen = set()
    for ch, sens, why in needs:
        row = next(c for c in CHANNELS if c["ch"] == ch)
        o = row.get("owner")
        if o and o not in seen:
            seen.add(o)
            print("     · %s ⇒ %s" % (ch, o))
    print()
    print("  ★ 本器**不起服务、不监听端口、不写外部对象**；层判定一律调用 auth_split（不重写）。")
    print("  ★ 四态各自可达（ALLOW／DENY／NEED-OWNER／UNDEFINED）⇒ 非恒真。")
    print("  ★ ★四态之分是本席轮102 的自纠：初版把「未设策略」也报成 DENY（把没定义 fold 成拒绝）。")
    return 0


def selftest() -> int:
    print("═══ auth_policy 自测（正例 ＋ 反例）═══")
    cases = [
        ("observatory.read", "in", "public", "ALLOW"),
        ("undeclared_fetch", "in", "public", "DENY"),
        ("meow.push", "out", "sensitive", "DENY"),
        ("a2a.call", "out", "public", "NEED-OWNER"),
        ("kdocs.read", "in", "sensitive", "NEED-OWNER"),
        ("unknown.channel", "out", "public", "UNDEFINED"),
        ("github.write", "out", "public", "UNDEFINED"),
    ]
    ok = True
    for ch, d, s, want in cases:
        v, why = check(ch, d, s)
        good = (v == want)
        ok = ok and good
        print("  %s %-18s %-4s %-10s ⇒ %-10s（期望 %s）｜%s"
              % ("✓" if good else "★", ch, d, s, v, want, why[:58]))
    # ★ 越权自封仍无效（调用层引擎验证，证明两层一致）
    dec = A.decide({"fp": "cairn-dsh", "prev": "x", "claim_tier": "T2"}, [], "abc")
    good2 = (dec["tier"] == "T0")
    print("  %s 层引擎联动 · 无证自封 T2 ⇒ 实算 %s（期望 T0）｜越权企图记为 %s"
          % ("✓" if good2 else "★", dec["tier"], dec.get("escalation_attempt")))
    ok = ok and good2
    print()
    print("  [SELFTEST] %s" % ("PASS" if ok else "★FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return table()


if __name__ == "__main__":
    sys.exit(main())
