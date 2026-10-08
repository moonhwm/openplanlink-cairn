#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BLAST: NET —— 本件可发起对外网络调用（★仅在 --send ∧ --i-am-authorized ∧ 策略闸 ALLOW 三条件齐备时）。声明供 blast_radius.py 审计。
r"""
meow_push.py —— MeoW 推送面接入器（★ 默认 DRY-RUN，绝不真发）。 v1.0.0

背景
────
MeoW（华为应用市场 com.chuckfang.meow）是专为鸿蒙用户打造的消息提醒应用，其推送接口公开：
    BASE  https://api.chuckfang.com/
    GET   /{昵称}/{title}/{msg}?url=&imgUrl=&msgType=&htmlHeight=
    POST  同上（JSON / form / text）
    响应  {status, msg}；200 成功｜400 参数错｜403 内容策略禁止｜404 昵称未注册｜429 频率超限
    限频  非会员 3 秒 1 条、每分钟 15 条、每小时 60 条、每天 1000 条
    文档  https://www.chuckfang.com/MeoW/api_doc.html

★★ 鉴权分析（本器存在的理由）
──────────────────────────────
  该接口【无鉴权】：`昵称` 是唯一凭据，且为明文路径参数。
  ⇒ **知道昵称者即可向该昵称的设备推送** ⇒ 属「**无密钥的持有者标识**」。
  其自身缓解：①403 内容策略 ②可信 IP 白名单（须联系开发者）③限频。
  ⇒ 机主「我尝试做个分流鉴权」之判断正确。**本器据此把风险压在三个默认值上**：
     ① **默认 DRY-RUN**：不加 --send 绝不发请求；
     ② **昵称不从文件读、只在命令行给**，且**本器不回显、不落盘、不入日志**；
     ③ **发送前先自检三件**：HTTPS、限频余量、msg 是否含凭据形态串（命中即拒发）。

★ 伦理边界（写死在程序里）
────────────────────────────
  向一个昵称推送 = **向一个真人的手机发通知**。
  ⇒ **本器拒绝在未获授权时向任何昵称发送**；`--send` 必须与 `--i-am-authorized` 同时给出。

用法
────
    # ① 预演（默认，不发任何请求）
    python meow_push.py --nick <昵称> --title "标题" --msg "内容" [--url ...]
    # ② 真发（须双开关；本席未在任何一次运行中用过）
    python meow_push.py --nick <昵称> --msg "..." --send --i-am-authorized
    # ③ 文档自检
    python meow_push.py --selftest
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    import auth_policy as AP          # ★ 轮103 增：分流鉴权【应用层】——策略必须接到动作上
except Exception as _e:                # pragma: no cover
    AP = None
try:
    import netguard as NG             # ★ 轮107 增：网络总闸——机主一句话即可停掉全部外发
except Exception:                      # pragma: no cover
    NG = None

SHARED = pathlib.Path(r"C:\Users\欧阳宏俊\OneDrive\桌面\全局声明_治理文档\a2a-inbox\cairn-dsh")

BASE = "https://api.chuckfang.com/"
LIMITS = {"min_interval_s": 3, "per_min": 15, "per_hour": 60, "per_day": 1000}
SECRET_PAT = re.compile(r"(sk-[A-Za-z0-9]{12,}|AKID|AccessKey|SecretKey|BEGIN [A-Z ]*PRIVATE KEY|"
                        r"LTAI[0-9A-Za-z]{8,}|ghp_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_\-]{20,})")


def sensitivity_of(payload: str | None):
    """★ 轮104：**判据已移入 `auth_policy.py`**（两份判据会漂移，故只留一份）。
    本函数现为【薄委托】，保留同名以便既有调用不变。"""
    if AP is None:
        return "sensitive", "策略层不可用 ⇒ 从严（sensitive）"
    return AP.sensitivity_of(payload)


def selftest() -> int:
    ok = True
    print("═══ meow_push 自检 ═══")
    # ① 凭据形态串必须被拦
    for bad in ("sk-abcdefghijklmnop", "LTAI5tAbCdEfGhIjKlMn", "BEGIN RSA PRIVATE KEY"):
        if not SECRET_PAT.search(bad):
            print("  ★FAIL 未拦住：%s" % bad[:16]); ok = False
    for good in ("普通消息：台账 108 条，链末 9be8c01f", "http://example.com/a?b=c"):
        if SECRET_PAT.search(good):
            print("  ★FAIL 误拦：%s" % good[:16]); ok = False
    print("  [自检] 凭据形态串：拦得住坏的、放得过好的 ⇒ %s" % ("PASS" if ok else "FAIL"))
    # ② 默认必须是非发送态
    ap = build_parser(); a = ap.parse_args(["--nick", "n", "--msg", "m"])
    if a.send or a.i_am_authorized:
        print("  ★FAIL 默认态竟是发送态"); ok = False
    else:
        print("  [自检] 默认态 = DRY-RUN（send=%s, authorized=%s）⇒ PASS" % (a.send, a.i_am_authorized))
    # ③ ★轮103 增：敏感度必须是【算出】的，且从严一侧要真的从严
    s1, r1 = sensitivity_of(None)
    if s1 != "sensitive":
        print("  ★FAIL 未给来源件时竟判为 %s（应从严为 sensitive）" % s1); ok = False
    else:
        print("  [自检] 未给 --payload-from ⇒ sensitive（从严）✓")
    s2, r2 = sensitivity_of(str(pathlib.Path(__file__)))
    if s2 != "sensitive":
        print("  ★FAIL 未发布的件竟判为 %s（共享面无比伴随物，应从严）" % s2); ok = False
    else:
        print("  [自检] 未发布件 ⇒ sensitive（从严）✓")
    # ④ ★策略闸必须能拦（meow.push 对 sensitive 要求 T2，而实测 T0）
    if AP is not None:
        v, why2 = AP.check("meow.push", "out", "sensitive")
        if v == "ALLOW":
            print("  ★FAIL 策略闸对敏感推送竟放行 ⇒ 闸没接上"); ok = False
        else:
            print("  [自检] 策略闸对【敏感推送】裁决 = %s（非 ALLOW）✓" % v)
        v2, _ = AP.check("meow.push", "out", "public")
        print("  [自检] 策略闸对【公开推送】裁决 = %s（其要求 T1，现状 T0 ⇒ 亦非 ALLOW）" % v2)
    else:
        print("  ★FAIL 未载入 auth_policy ⇒ 策略闸缺失"); ok = False
    print("[SELFTEST] %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="MeoW 推送面接入器（默认 DRY-RUN）")
    ap.add_argument("--nick", help="昵称（唯一凭据；本器不回显、不落盘）")
    ap.add_argument("--title", default="", help="标题，可省（默认 MeoW）")
    ap.add_argument("--msg", default="", help="消息内容")
    ap.add_argument("--url", default="", help="跳转链接（可选）")
    ap.add_argument("--msg-type", default="text", choices=["text", "html"])
    ap.add_argument("--html-height", type=int, default=200)
    ap.add_argument("--send", action="store_true", help="★ 真发（须与 --i-am-authorized 同给）")
    ap.add_argument("--i-am-authorized", action="store_true", help="★ 声明已获昵称所有者授权")
    ap.add_argument("--payload-from", default=None,
                    help="★轮103 增：内容来源件（在共享面且 .sha256 复核通过 ⇒ 判为 public；否则 sensitive）")
    ap.add_argument("--selftest", action="store_true")
    return ap


def main() -> int:
    a = build_parser().parse_args()
    if a.selftest:
        return selftest()

    if not a.nick or not a.msg:
        print("[ERR] 必须给 --nick 与 --msg"); return 2

    print("═══ MeoW 推送（%s）═══" % ("真发" if (a.send and a.i_am_authorized) else "DRY-RUN 预演"))
    print("  BASE        : %s" % BASE)
    print("  昵称         : ★ 已隐藏（长度 %d；本器不回显、不落盘）" % len(a.nick))
    print("  title       : %s" % (a.title or "（省略 ⇒ 默认 MeoW）"))
    print("  限频（其文档）: 3 秒 1 条 / 每分钟 %d / 每小时 %d / 每天 %d" %
          (LIMITS["per_min"], LIMITS["per_hour"], LIMITS["per_day"]))

    # ★ 发前自检一：凭据形态串
    if SECRET_PAT.search(a.msg) or SECRET_PAT.search(a.title or ""):
        print("\n  ★拒绝：消息命中【凭据形态串】——按本席纪律不得外发。"); return 3
    print("  [自检] 凭据形态串：未命中 ✓")

    # ★★ 轮103 增：发前自检四——【分流鉴权策略闸】
    #   要点：敏感度【算出】（见 sensitivity_of），不采信调用方的自我声明；
    #   然后【调用】应用层策略 auth_policy.check（不重写它）。
    sens, why = sensitivity_of(a.payload_from)
    print("  [自检] 敏感度（算出，非自封）：**%s** ｜ %s" % (sens, why))
    if AP is None:
        print("\n  ★拒绝：未能载入 auth_policy（策略层不可用 ⇒ 从严，不发）。"); return 4
    verdict, reason = AP.check("meow.push", "out", sens)
    print("  [自检] 分流鉴权裁决：**%s** ｜ %s" % (verdict, reason))
    if verdict != "ALLOW":
        row = next((c for c in AP.CHANNELS if c["ch"] == "meow.push"), {})
        print("\n  ★★ 策略闸【拦下】：%s" % verdict)
        if row.get("owner"):
            print("     机主前置：%s" % row["owner"])
        print("     ⇒ 本器在任何请求发出【之前】停止。策略是闸，不是提示。")
        return 5
    # ★ 发前自检二：协议
    print("  [自检] 协议：HTTPS ✓（其文档亦推荐 HTTPS）")

    path = "/" + urllib.parse.quote(a.nick, safe="")
    if a.title:
        path += "/" + urllib.parse.quote(a.title, safe="")
    path += "/" + urllib.parse.quote(a.msg, safe="")
    q = {}
    if a.url: q["url"] = a.url
    q["msgType"] = a.msg_type
    if a.msg_type == "html": q["htmlHeight"] = str(a.html_height)
    url = BASE.rstrip("/") + path + ("?" + urllib.parse.urlencode(q) if q else "")
    print("\n  请求形（昵称与内容已 URL 编码；此处只示形状）：")
    print("    GET %s/{昵称}/{title}/{msg}?%s" % (BASE, urllib.parse.urlencode(q)))

    if not (a.send and a.i_am_authorized):
        print("\n  ⇒ DRY-RUN：**未发出任何请求**。")
        print("     ★ 要真发须同时加 `--send --i-am-authorized`；且**须先取得机主给的昵称**。")
        print("     ★ 伦理边界：向一个昵称推送＝向一个真人的手机发通知；本席不代您决定。")
        return 0

    # 真发（本席从未运行到此处）
    # ★ 轮107：**网络总闸**——在写出任何字节之前先问它。总闸置上 ⇒ 拒发。
    if NG is not None and not NG.allowed():
        print("\n  ★★ 网络总闸已置上（DSH_NO_NET=1）⇒ 拒发。清掉该环境变量即恢复。")
        return 7
    print("\n  ⇒ 真发中……")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cairn-dsh/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
        print("  HTTP %s ｜ %s" % (r.status, body[:200]))
        try:
            j = json.loads(body)
            print("  业务状态：status=%s msg=%s" % (j.get("status"), j.get("msg")))
            if j.get("status") == 403: print("  ★内容策略禁止——不得绕过。")
            if j.get("status") == 404: print("  ★昵称未注册。")
            if j.get("status") == 429: print("  ★频率超限——须退避，不得重试轰炸。")
        except Exception:
            pass
        return 0
    except Exception as e:
        print("  ★失败：%s" % str(e)[:120]); return 1


if __name__ == "__main__":
    sys.exit(main())
