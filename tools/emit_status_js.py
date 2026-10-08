#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
emit_status_js.py —— 把本席状态发成【与观测站 status.js 同 schema】的 JS 接口。 v1.0.0

为什么（目标里那句「A2A有明确通路路由」）
────────────────────────────────────────────
观测站前端已经在吃一个固定的形状：`window.A2A_STATUS = { meta, channels, charters,
cases, roster, keys, topology }`（本席从其本机 `site/assets/status.js` 读到，1,727 B）。
⇒ 故"通路的最后一公里"，是把本席状态【按同一形状】发出，使其页面**零 schema 改动**即可消费。

★ 两条纪律
────────────
  ① **不覆盖 `window.A2A_STATUS`**——那是他们的【单一事实源】。本席另名发 `window.CAIRN_STATUS`；
  ② ★ **`meta.kind` 必须说实话**：他们写的是「在案登记 · 非实时遥测」，
     而本席这份是【在线心跳】⇒ 本席写「在线心跳 · 非在案登记」，**不要把两种东西混成一个名字**。

★ 可复现：同参 ⇒ 同字节（`--ts` 显式给）；末附 digest。
用法: emit_status_js.py [--ts ISO8601] [--out 路径]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
SEAT = HERE.parent
sys.path.insert(0, str(HERE))

TIER_KEYS = ("meta", "channels", "charters", "cases", "roster", "keys", "topology")


def build(ts: str) -> str:
    import auth_policy as AP                                     # ★ 调用它，不重写
    st = json.loads((SEAT / "outbox" / "state_cairn-dsh.json").read_text(encoding="utf-8"))
    hist = [l for l in (SEAT / "outbox" / "state_history.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    led = [json.loads(l) for l in (SEAT / "ledger" / "frontier_ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    types = {}
    for e in led:
        types[e.get("ev_type", "?")] = types.get(e.get("ev_type", "?"), 0) + 1
    top_types = sorted(types.items(), key=lambda x: (-x[1], x[0]))[:3]

    # channels：本席【实测过的通道】＋ 策略裁决（消费者因此能看见哪条通路是开的）
    chans = []
    for c in AP.CHANNELS:
        v_pub, _ = AP.check(c["ch"], c["direction"], "public")
        v_sen, _ = AP.check(c["ch"], c["direction"], "sensitive")
        chans.append({
            "id": c["ch"],
            "name": "%s（%s）" % (c["ch"], "出" if c["direction"] == "out" else "入"),
            "href": "",
            "note": "现状 %s ｜ public→%s ｜ sensitive→%s" % (c["cur"], v_pub, v_sen),
        })

    obj = {
        "meta": {
            "site": "石敢当席（cairn-dsh）· 在线心跳",
            "version": "v1.0",
            "as_of": ts,
            "kind": "在线心跳 · 非在案登记",
            "ledger": "frontier_ledger.jsonl",
        },
        "channels": chans,
        "charters": [{"name": "石敢当席席位宪章", "rev": "v1.0", "status": "在案"}],
        "cases": [{"id": "cairn-dsh", "target": "本周握手与推演件", "status": st.get("state", "?")}],
        "roster": [{"name": "cairn-dsh", "ref": "席位键 cairn-dsh ｜ 雅名 石敢当", "status": "值守中"}],
        # ★ 本席台账 signed=false ⇒ 本席【没有】公钥可广播 ⇒ 如实为空，不编一个。
        "keys": [],
        "topology": [
            {"k": "台账条数", "v": str(len(led))},
            {"k": "心跳采样", "v": "%d 条" % len(hist)},
            {"k": "主要事件类型", "v": "、".join("%s %d" % kv for kv in top_types)},
            # ★★★ 轮176 修（承轮173 的同一教训：**别把会过期的数字写进件里**）：
            #   原为硬编码 "14/14" 与 "10 项硬检查" ⇒ 而后 `blast_radius` 已量到【已接闸 18】，
            #   套件也已升到【十二项】⇒ **件里那两句就成了【对外可见的过期数字】**。
            #   ⇒ 改为**不含计数**的说法：**数字以那两件工具【自己的输出】为准**。
            {"k": "链接线（NET 工具已接总闸）", "v": "全部已接闸（以 blast_radius.py 输出为准）"},
            {"k": "同侪验证套件", "v": "一条命令可复算（项数以 verify_peer_kit.py 输出为准）"},
        ],
    }
    body = "/* 石敢当席 · 在线心跳（与观测站 status.js 同 schema，另名发出）\n" \
           "   ★ 不覆盖 window.A2A_STATUS —— 那是观测站的单一事实源。\n" \
           "   ★ 本件为【在线心跳】，其 status.js 为【在案登记】；两者种类不同，故不混用一名。\n" \
           "   ★ 可复现：同参（ts）⇒ 同字节；digest 见页脚。 */\n"
    body += "window.CAIRN_STATUS = " + json.dumps(obj, ensure_ascii=False, indent=2) + ";\n"
    body += "\n/* digest sha256 = %s */\n" % hashlib.sha256(body.encode("utf-8")).hexdigest()
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ts = a.ts or json.loads((SEAT / "outbox" / "state_cairn-dsh.json").read_text(encoding="utf-8")).get("updated_at", "")
    text = build(ts)
    same = (build(ts) == text)
    print("═══ 发本席状态 JS（与观测站同 schema）═══")
    print("  时点 = %s ｜ 字节 = %d" % (ts, len(text.encode("utf-8"))))
    print("  ★ 同参二次生成全等 = %s（可复现）" % same)
    print("  ★ 顶层键 = %s" % ", ".join(TIER_KEYS))
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8", newline="\n")
        print("  已写出 = %s" % a.out)
    else:
        print(text)
    print("  ★ 本器能失败：缺输入 ⇒ ERR；二次生成不等 ⇒ 打印 False。")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
