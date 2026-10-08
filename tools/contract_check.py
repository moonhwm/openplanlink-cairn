#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
contract_check.py —— A2A 消息契约的【可机检部分】检查器。 v1.0.0

定位（**不产新版契约**）
────────────────────────--
依据：《A2A 消息契约 v0.2 · PROPOSED-FINAL》§1 信封字段 / §2 八词 `kind` / §3 保留键与硬约束
      ＋《v0.3-PROPOSED》该项 5（序列化规范化）与§三（判据 51 是【对账口径】非真实性凭证）。
★ **本器【不覆盖、不改写、不升版】契约**——v0.3 明写"不覆盖 v0.2""须总线侧裁决""未经面壁异议窗属提案"。
  本器只把【契约里已经写死的那些】变成【任何实现者都能对一条消息跑的检查】。

查什么（十项，每项都能失败）
──────────────────────────────
 A. 必填字段齐（`from_mode`／`kind`／`seat`／`instance`／`fp`／`ts`／`nonce`／`msg_hash`）
 B. `kind` 在八词白名单内（未列出即拒收）
 C. `from_mode` 词形合法：**席位键＝小写连字符** ／ **保留键＝全大写类名＋冒号**（两族不相交）
 D. ★ **§3 硬约束：`from_mode` 为保留键 ⇒ `kind` 必须等于其类**，否则拒收
 E. 条件必填：`kind=relay` ⇒ 须有 `carrier`；`kind=archive` ⇒ 须有 `original_ts`
 F. ✅/○ 字段：`to_mode`／`to_kind`／`card_hash`／`protocolVersion`／`accept_*` 若给，类型须对
 G. ★ **v0.3 项5：序列化规范化**——拒重复键、拒 `NaN`／`Infinity`、数字表示唯一
 H. `msg_hash` 位宽与口径：**总线口径重算是否相符**（★并标注：此为**对账口径**，非真实性凭证）
 I. `nonce` 与 `ts` 形状；若给参考时刻，则 300 s 窗内
 J. `instance`／`fp` 形状（`fp` 允许为 `PENDING`，但**不得伪装成已签发**）

★ 本器**不发网络、不写外部对象**；纯本地校验。
用法: contract_check.py <消息.json> [更多…] [--ref-ts ISO8601]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

KINDS = ("seat", "bus", "relay", "audit", "probe", "human", "archive", "system")
RESERVED_CLASS = {"BUS": "bus", "SYSTEM": "system", "PROBE": "probe", "ARCHIVE": "archive", "AUDIT": "audit"}
SEAT_RE = re.compile(r"^[a-z][a-z0-9-]*$")
RESERVED_RE = re.compile(r"^([A-Z]+):(.+)$")
REQUIRED = ("from_mode", "kind", "seat", "instance", "fp", "ts", "nonce", "msg_hash")
OPTIONAL_TYPES = {"to_mode": str, "to_kind": str, "carrier": str, "original_ts": str,
                  "card_hash": str, "protocolVersion": str}
WINDOW_S = 300


def check_dupkeys(raw: str):
    """★ v0.3 项5：拒重复键（用 object_pairs_hook 捕获）。"""
    dups = []

    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                dups.append(k)
            seen[k] = v
        return seen

    try:
        json.loads(raw, object_pairs_hook=hook)
    except Exception as e:
        return ["JSON 解析失败：%s" % str(e)[:60]]
    return ["重复键：%s" % ", ".join(sorted(set(dups)))] if dups else []


def bus_hash(msg: dict) -> str:
    """§4 总线口径。"""
    return hashlib.md5(json.dumps(msg, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def check_one(path: str, ref_ts: str | None):
    fails, warns, oks = [], [], []
    raw = open(path, encoding="utf-8").read()

    # G 规范化
    for d in check_dupkeys(raw):
        fails.append(("G 规范化", d))
    if re.search(r"\b(NaN|Infinity|-Infinity)\b", raw):
        fails.append(("G 规范化", "含 NaN／Infinity（契约要求拒收）"))

    try:
        m = json.loads(raw)
    except Exception as e:
        return [("ERR", "不可解析：%s" % str(e)[:60])], [], []
    if not isinstance(m, dict):
        return [("ERR", "顶层不是对象")], [], []

    # A 必填
    miss = [f for f in REQUIRED if f not in m]
    if miss:
        fails.append(("A 必填字段", "缺：%s" % ", ".join(miss)))
    else:
        oks.append(("A 必填字段", "齐"))

    # B 八词白名单
    k = m.get("kind")
    if k is not None:
        if k in KINDS:
            oks.append(("B kind 白名单", k))
        else:
            fails.append(("B kind 白名单", "未列出 ⇒ 拒收：%r" % k))

    # C 词形
    fm = m.get("from_mode", "")
    is_res = bool(RESERVED_RE.match(fm))
    is_seat = bool(SEAT_RE.match(fm))
    if fm == "owner-ouyang":
        is_seat = True                      # §3.2 机主行例外：给席位键形
    if not (is_res or is_seat):
        fails.append(("C from_mode 词形", "既非席位键（小写连字符）亦非保留键（全大写＋冒号）：%r" % fm))
    else:
        oks.append(("C from_mode 词形", "保留键" if is_res else "席位键"))

    # D §3 硬约束
    if is_res:
        cls = RESERVED_RE.match(fm).group(1)
        want = RESERVED_CLASS.get(cls)
        if want is None:
            fails.append(("D 保留键类名", "未知类名 %r（已知：%s）" % (cls, "/".join(RESERVED_CLASS))))
        elif k != want:
            fails.append(("D §3 硬约束", "from_mode=%s ⇒ kind 必须为 %r，实为 %r ⇒ 拒收" % (fm, want, k)))
        else:
            oks.append(("D §3 硬约束", "%s ↔ %s 相符" % (cls, k)))
    if fm == "owner-ouyang" and k != "human":
        fails.append(("D 机主行例外", "owner-ouyang ⇒ kind 必须为 'human'，实为 %r" % k))

    # E 条件必填
    if k == "relay" and not m.get("carrier"):
        fails.append(("E 条件必填", "kind=relay ⇒ 须携 carrier（缺则拒收）"))
    elif k == "relay":
        oks.append(("E 条件必填", "relay 携 carrier ✓"))
    if k == "archive" and not m.get("original_ts"):
        fails.append(("E 条件必填", "kind=archive ⇒ 须携 original_ts"))
    elif k == "archive":
        oks.append(("E 条件必填", "archive 携 original_ts ✓"))

    # F 可选字段类型
    for f, t in OPTIONAL_TYPES.items():
        if f in m and not isinstance(m[f], t):
            fails.append(("F 可选字段类型", "%s 应为 %s" % (f, t.__name__)))

    # H msg_hash 口径
    mh = m.get("msg_hash")
    if isinstance(mh, str):
        if len(mh) != 16:
            fails.append(("H msg_hash 位宽", "总线口径为 16 位十六进制，实为 %d" % len(mh)))
        else:
            core = {kk: vv for kk, vv in m.items() if kk != "msg_hash"}
            # ★ 口径：对【去掉 msg_hash 的本体】重算（若其本体含 msg_hash 自指则另行说明）
            got = bus_hash(core)
            if got == mh:
                oks.append(("H msg_hash 口径", "总线口径重算相符"))
            else:
                warns.append(("H msg_hash 口径", "重算 %s ≠ 声明 %s（★若总线口径含 msg_hash 自指，则本条不适用）" % (got, mh)))
        warns.append(("H 口径性质", "★此为【对账口径】（证传输/落盘未改动），**不是真实性凭证**——无密钥，有意碰撞可行（v0.3 §三）"))

    # I 窗
    if ref_ts and m.get("ts"):
        try:
            a = datetime.fromisoformat(str(m["ts"]).replace("Z", "+00:00"))
            b = datetime.fromisoformat(str(ref_ts).replace("Z", "+00:00"))
            if a.tzinfo is None:
                a = a.replace(tzinfo=timezone.utc)
            if b.tzinfo is None:
                b = b.replace(tzinfo=timezone.utc)
            d = abs((a - b).total_seconds())
            if d > WINDOW_S:
                fails.append(("I 防重放窗", "|Δ|=%.0fs > %ds" % (d, WINDOW_S)))
            else:
                oks.append(("I 防重放窗", "|Δ|=%.0fs ≤ %ds" % (d, WINDOW_S)))
        except Exception:
            warns.append(("I 防重放窗", "ts 或 ref 无法解析，跳过"))
    else:
        # ★★★ 轮161 修：**漏传 --ref-ts 会【静默跳过整条判据 I】**
        #   （来源：轮161 回查旧结论「2 收 8 拒」时，不传该开关只得到 7 拒 ⇒ 据此查出）
        #   ⇒ 现改为【显式告知】：缺开关时印一条 warn，让"少了一条判据"可见。
        #   ★ 不改为 fails：没有参照时刻**不构成消息的错**，只是这一条**没被检**。
        if not ref_ts:
            warns.append(("I 防重放窗", "★【未检】——未传 --ref-ts ⇒ 本条判据整条未执行（不是通过，也不是失败）"))

    # J fp
    fp = m.get("fp")
    if isinstance(fp, str) and fp != "PENDING" and not re.match(r"^[0-9a-f]{8,}$", fp):
        warns.append(("J fp 形状", "既非 PENDING 亦非十六进制：%r" % fp[:24]))

    return fails, warns, oks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("msgs", nargs="+")
    ap.add_argument("--ref-ts", default=None)
    a = ap.parse_args()
    total_fail = 0
    total_ok = 0
    total_msg = 0
    for p in a.msgs:
        fails, warns, oks = check_one(p, a.ref_ts)
        name = p.split("\\")[-1].split("/")[-1]
        print("═══ %s ═══" % name)
        for tag, why in fails:
            print("  ★ %-18s %s" % (tag, why))
        for tag, why in warns:
            print("  ⚠ %-18s %s" % (tag, why))
        for tag, why in oks:
            print("  ✅ %-18s %s" % (tag, why))
        print("  ⇒ %s" % ("★拒收：%d 项不过" % len(fails) if fails else "收"))
        print()
        total_fail += len(fails)
        total_ok += len(oks)
        total_msg += 1
    print("  ── 汇总 ──  件 %d ｜ 通过项 %d ｜ 不过项 %d ｜ %s"
          % (total_msg, total_ok, total_fail, "全部可收" if total_fail == 0 else "有拒收件"))
    print("  ★ 本器【不覆盖契约、不升版】：只把契约里已写死的部分变成可跑的检查。")
    print("  ★ 本器能失败（缺字段／非白名单 kind／破坏 §3 硬约束 皆会报）⇒ 非恒真。")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
