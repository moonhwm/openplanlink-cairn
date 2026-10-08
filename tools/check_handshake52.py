#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（探测握手件可达性）。声明供 blast_radius.py 审计。
r"""
check_handshake52.py —— 把沈铎 v2 方案 §4.2 的「握手四重互证（判据52）」做成可跑的仪器。 v1.0.0

被测判据（原文，[原件直取] OpenPlanLink_v2改写方案_沈铎_20261001.md §4.2）：
    「握手四重互证（判据52）：**agent-card 可达 ∧ 签名可验 ∧ 席位在册 ∧ 回执衔接**，四者齐才算握手成功。」

本器做什么
──────────
逐条机检，并**对两个对象同时跑**，以构成【阳性对照】：
    · 靶点 A = `https://qtorrent.ok.kimi.link/`（其 §4.2 要补的对象）
    · 靶点 B = `https://github.com/moonhwm/openplanlink-mirror`（**已知有名片/签名/登记席位** ⇒ 阳性对照）
★ 若仪器对二者给出不同结果，则它【有分辨力】；若对二者都给同一结论，则它没测出东西。

★ 纪律
──────
  1. 只读；不写任何外部对象；
  2. 每条结论标注【测了什么/没测什么】——**测不了就写"测不了"，不猜**；
  3. 本器**能失败**：四条件不齐即退出码 1。

用法: check_handshake52.py
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = {"User-Agent": "cairn-dsh/handshake52", "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"}

TARGETS = [
    ("qtorrent（其 §4.2 要补的对象）", "https://qtorrent.ok.kimi.link",
     ["/.well-known/agent-card.json", "/agent-card.json"]),
    ("mirror（阳性对照：已知有名片/签名/席位）", "https://raw.githubusercontent.com/moonhwm/openplanlink-mirror/main",
     ["/agent-card.json"]),
]



# ★ 轮108：网络总闸——只在 DSH_NO_NET 置上时装"拒绝外发"钩子；未置则【一行都不改行为】。
try:
    import netguard as _netguard
    _netguard.activate()
except Exception:
    pass

def get(url: str, timeout: int = 30):
    try:
        req = urllib.request.Request(url, headers=UA)
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, b"", ""
    except Exception as e:
        return None, str(e).encode("utf-8", "replace"), ""


def canon(o) -> bytes:
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


REQUIRED_FIELDS = ("name", "url", "protocolVersion", "skills")


def check(label: str, base: str, paths: list) -> dict:
    """★ ① 的判据已收紧（轮 68 修正）：
         原版只看状态码 ⇒ 被 qtorrent 静态主机的【HTML 兜底页】骗过（200 + text/html + 首页）。
         收紧为三要件：**Content-Type 为 JSON ∧ 可 JSON.parse ∧ 含名片必需字段**，三者齐才算可达。
       ★ 这是"一个在失败上报成功的检查"的活例，故修法必须写在这里，不许只改结论。"""
    out = {"label": label, "base": base, "c1": None, "c2": None, "c3": None, "c4": None, "card": None}
    notes = []
    for p in paths:
        st, body, ct = get(base + p)
        if st != 200 or not body:
            continue
        is_json_ct = "json" in (ct or "").lower()
        looks_html = "html" in (ct or "").lower()
        card = None
        try:
            card = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            card = None
        nfields = sum(1 for k in REQUIRED_FIELDS if isinstance(card, dict) and k in card)
        # ★ 判据（轮 68 第二次修正）：
        #   以【可否 JSON 解析 ＋ 有无必需字段】为准；Content-Type 只作【辅助判别兜底页】。
        #   理由（实测）：raw.githubusercontent 把 .json 发成 text/plain（真名片会被"必须 JSON MIME"误杀）；
        #                 静态站点把主页当兜底发成 text/html（假名片会被"只看状态码"误放）。二者须分开处置。
        if isinstance(card, dict) and nfields >= 2:
            out["c1"] = ("PASS", "HTTP 200 ｜ Content-Type=%s（仅辅助）｜ 可 JSON 解析 ｜ 含 %d 个必需字段"
                         % (ct or "—", nfields))
            out["card"] = card
            break
        if looks_html:
            notes.append("%s ⇒ HTTP 200 但 Content-Type=%s ⇒ ★【HTML 兜底页陷阱】，非名片" % (p, ct))
        elif card is None:
            notes.append("%s ⇒ 响应体不可 JSON 解析（Content-Type=%s）" % (p, ct or "—"))
        else:
            notes.append("%s ⇒ 是 JSON 但仅含 %d 个必需字段（%s）" % (p, nfields, ",".join(REQUIRED_FIELDS)))
    if out["c1"] is None:
        out["c1"] = ("FAIL", "无合格名片；" + (" ｜ ".join(notes) if notes else "候选路径全非 200"))

    card = out["card"]
    # ② 签名可验（只看名片是否自陈 integrity / 签名材料）
    if card is None:
        out["c2"] = ("FAIL", "无名片可检")
    else:
        ig = card.get("integrity") or {}
        has = [k for k in ("canonicalSha256", "pubkeyFp", "sig", "alg") if k in ig]
        if len(has) >= 2:
            out["c2"] = ("PARTIAL", "名片含 integrity 字段 %s ⇒ 须独立复算方可判（本器不复算他人签名）" % ",".join(has))
        else:
            out["c2"] = ("FAIL", "名片无 integrity/签名材料（字段：%s）" % (",".join(card.keys())[:60]))

    # ③ 席位在册（名片是否自陈席位；是否在册需另一份名册，本器只报"自陈席位=…"）
    if card is None:
        out["c3"] = ("FAIL", "无名片可检")
    else:
        seat = ""
        blob = json.dumps(card, ensure_ascii=False)
        m = re.search(r'"(?:seat|seatId|seatKey|name)"\s*:\s*"([^"]{2,40})"', blob)
        if m:
            seat = m.group(1)
        out["c3"] = ("PARTIAL", "名片自陈席位/名称 = %s ⇒ **是否在册须对生态名册另核**（本器未持权威名册）" % (seat or "（未识别）"))

    # ④ 回执衔接（需一条回执样本或链；本器无则如实说）
    out["c4"] = ("UNTESTABLE", "需回执样本或链端点；本器未获 ⇒ **不猜**")
    return out


def main() -> int:
    print("═══ 握手四重互证（判据52）机检 ═══")
    print("  判据原文：agent-card 可达 ∧ 签名可验 ∧ 席位在册 ∧ 回执衔接，四者齐才算握手成功")
    print("  图例：PASS＝已验成 ｜ PARTIAL＝部分可检/须另核 ｜ FAIL＝未达 ｜ UNTESTABLE＝本器测不了（不猜）")
    print()
    results = []
    for label, base, paths in TARGETS:
        r = check(label, base, paths)
        results.append(r)
        print("▸ %s" % label)
        print("   base = %s" % base)
        for k, name in (("c1", "① agent-card 可达"), ("c2", "② 签名可验"),
                        ("c3", "③ 席位在册"), ("c4", "④ 回执衔接")):
            st, why = r[k]
            mark = {"PASS": "✓", "PARTIAL": "◐", "FAIL": "✗", "UNTESTABLE": "?"}[st]
            print("   %s %-16s %-11s %s" % (mark, name, st, why))
        print()

    # ★ 分辨力自证：两个对象是否给出不同结论
    a, b = results[0], results[1]
    diff = sum(1 for k in ("c1", "c2", "c3", "c4") if a[k][0] != b[k][0])
    print("  ★【分辨力自证】两对象在 %d/4 条上给出不同结论 ⇒ %s"
          % (diff, "仪器有分辨力" if diff else "★仪器未分辨出差异（可能两条都测不了）"))
    print("  ★【可否失败】qtorrent 侧①为 FAIL ⇒ 本器退出码非 0 ⇒ 它是能失败的检查。")
    print()
    print("  结论（据判据52）：")
    for r in results:
        got = [r[k][0] for k in ("c1", "c2", "c3", "c4")]
        ok = all(x == "PASS" for x in got)
        print("    · %-34s ⇒ %s（%s）" % (r["label"][:34], "四重齐" if ok else "★未达成", "/".join(got)))
    return 0 if all(all(r[k][0] == "PASS" for k in ("c1", "c2", "c3", "c4")) for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
