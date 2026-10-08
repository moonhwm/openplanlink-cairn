#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
seed_render.py —— 把本席状态渲染成 MiroFish 形状的【种子材料】。 v1.0.0

承（轮 98 定的两层）
──────────────────────
MiroFish（`666ghj/MiroFish`，**AGPL-3.0**）的输入是【种子材料（一份数据分析报告）＋ 一句自然语言预测需求】。
⇒ 故"Pannel 当它的种子供给方"这一层（层①）需要的，正是【把本席状态渲染成一份报告】。
★ 而层②（**Pannel 自身要可复现**）要求：**这份种子必须【可复现】** ⇒ 本器据此设计。

可复现的设计（**本器的要点**）
────────────────────────────────
  · 渲染是【纯函数】：所有输入显式给（状态件 + 历史 + 台账 + `--ts`）；
    **绝不取"当前时间"** ⇒ **同参 ⇒ 同字节**。
  · 输出末尾附【种子自身的 sha256】⇒ 任何一方可复核同一份种子。
  · 本器【只读】本席自有件；**不复制 MiroFish 任何代码**（AGPL 纪律）。

安全
──────
渲染前做【禁词扫描】：凭据样式、昵称、密钥变量名 ⇒ **命中即 REFUSE，不出种子。**

用法: seed_render.py [--ts ISO8601] [--out 路径]
     不给 --ts 时用状态件里的 updated_at（**仍不取当前时间**，故仍可复现）。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
SEAT_DIR = HERE.parent
OUTBOX = SEAT_DIR / "outbox"
LEDGER = SEAT_DIR / "ledger" / "frontier_ledger.jsonl"

# ★ 禁词（凭据样式与私密标识）——命中即拒绝出种子
FORBIDDEN = [
    r"sk-[A-Za-z0-9]{16,}", r"ghp_[A-Za-z0-9]{20,}", r"eyJ[A-Za-z0-9_\-]{20,}\.",
    r"password\s*[:=]", r"passwd\s*[:=]", r"API_KEY\s*=", r"ZEP_API_KEY", r"HWCLOUD_MAAS_KEY",
    r"ARK_API_KEY", r"cubofOPoRdSw",
]


def scan(text: str):
    hits = []
    for pat in FORBIDDEN:
        if re.search(pat, text):
            hits.append(pat)
    return hits


def _d(b: bytes) -> str:
    """sha256 前 48 位（自描述用）"""
    return hashlib.sha256(b).hexdigest()[:48]


def render(ts: str, outbox: pathlib.Path | None = None, ledger: pathlib.Path | None = None) -> str:
    # ★ 轮100 增：可显式传入输入根，供独立验证器在【副本】上复算（默认仍用本席自有件）
    outbox = outbox or OUTBOX
    ledger_path = ledger or LEDGER
    st = json.loads((outbox / "state_cairn-dsh.json").read_text(encoding="utf-8"))
    hist = [json.loads(l) for l in (outbox / "state_history.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ledger = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    types = {}
    for e in ledger:
        types[e.get("ev_type", "?")] = types.get(e.get("ev_type", "?"), 0) + 1
    types_sorted = sorted(types.items(), key=lambda x: (-x[1], x[0]))
    last = ledger[-1] if ledger else {}
    n_hist = len(hist)

    L = []
    L.append("# 种子材料 · 席位状态报告（A2A OpenPlanLink 观测席）")
    L.append("")
    L.append("> **性质**：本件由 `seed_render.py` 自本席状态件**机械渲染**而成；")
    L.append("> **可复现**：同参（状态件＋历史＋台账＋ts）⇒ 同字节。**末附种子 digest 供复核。**")
    L.append("> **用途**：作为【群体智能推演引擎】（如 MiroFish 一类）的【种子材料】输入。")
    L.append("")
    L.append("## 一、席位与当下状态")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 席位键 | `cairn-dsh` |")
    L.append("| 雅名 | 石敢当 |")
    L.append("| 状态 | **%s** |" % st.get("state", "?"))
    L.append("| 自评进度 | **%s / 100** |" % st.get("progress", "?"))
    L.append("| 渲染时点（显式给定） | **%s** |" % ts)
    L.append("| 状态件更新于 | %s |" % st.get("updated_at", "?"))
    L.append("| 心跳采样 | **%d 条** |" % n_hist)
    L.append("")
    L.append("## 二、台账（可验证的工作痕迹）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 条目总数 | **%d** |" % len(ledger))
    L.append("| 链末 hash | `%s` |" % str(last.get("hash", ""))[:32])
    L.append("| 签名状态 | **signed=%s**（%s） |" % (last.get("signed"), last.get("sig_note", "—")))
    L.append("")
    L.append("### 按类型分布")
    L.append("")
    L.append("| 类型 | 条数 |")
    L.append("|---|---|")
    for k, v in types_sorted[:12]:
        L.append("| `%s` | %d |" % (k, v))
    L.append("")
    if len(types_sorted) > 12:
        L.append("（其余 %d 类为一次性长尾，不逐列。）" % (len(types_sorted) - 12))
        L.append("")
    L.append("## 三、可提供的信号（层①：喂给推演引擎的东西）")
    L.append("")
    L.append("本席对外可提供的是**机器可读的席位状态与工作痕迹**：")
    L.append("")
    L.append("1. **状态流**：`{t, progress, state}` 心跳序列 → **可用于「某个协作节点是否在推进」类问题**；")
    L.append("2. **工作痕迹流**：台账 %d 条，每条含 `ev_type / subject / detail / evidence / hash / prev` →" % len(ledger))
    L.append("   **可用于「某类判断被做过几次、改过几次、改的是什么」类问题**；")
    L.append("3. **可复算断言**：本席多份工具带自测（且**能失败**）→ **可交叉检验「某个结论是否站得住」**。")
    L.append("")
    L.append("## 四、★ 本席【不提供】什么（边界，写在种子里的那一半）")
    L.append("")
    L.append("> ★ **本席提供的是【可复现的地基】，不是【叙事性推演】**。")
    L.append("> 若推演引擎产出的是叙事，**二者互补、不可互替**；")
    L.append("> **本席的每一处数字都附来源与范围**，凡未核实者一律标 `[未核]`。")
    L.append("")
    L.append("## 五、建议的预测需求（自然语言，供推演引擎读）")
    L.append("")
    L.append("> 给定一个多席位协作的开放计划（每个席位按自己的节奏产出可验证的件，并由机主统一裁定），")
    L.append("> **在未来 24 小时内，协作会趋向【收敛】还是【分叉】**？")
    L.append("> 请给出发散路径与收敛路径各自的条件，并指出哪些条件可由上述工作痕迹流提前观测到。")
    L.append("")
    L.append("## 六、种子自证")
    L.append("")
    L.append("本件由 `seed_render.py` 渲染。**同参 ⇒ 同字节**；其 digest 见页脚。")
    L.append("")
    # ★ 轮100 增：输入清单（自描述）——**这是让收到种子的人【不必有我的活台账】也能分级核验的关键**
    L.append("## 七、输入清单（自描述，供收到种子者分级核验）")
    L.append("")
    L.append("| 输入 | 摘要（sha256 前 48） | 计数 |")
    L.append("|---|---|---|")
    L.append("| 状态件 `state_cairn-dsh.json` | `%s` | — |" % _d((outbox / "state_cairn-dsh.json").read_bytes()))
    L.append("| 历史 `state_history.jsonl` | `%s` | %d 条 |" % (_d((outbox / "state_history.jsonl").read_bytes()), n_hist))
    L.append("| 台账 `frontier_ledger.jsonl` | `%s` | %d 条 |" % (_d(ledger_path.read_bytes()), len(ledger)))
    L.append("| 渲染时点 `ts` | `%s` | — |" % _d(ts.encode("utf-8")))
    L.append("")
    L.append("**台账链末 hash**：`%s`" % str(last.get("hash", "")))
    L.append("**台账链末 prev**：`%s`" % str(last.get("prev", "")))
    L.append("")
    L.append("> ★ **核验分级**（收到本件者可逐级做，做得到哪级就报哪级）：")
    L.append("> **① 本件自洽**：本件正文的 sha256 与页脚 digest 是否相符；")
    L.append("> **② 可追溯**：上表台账摘要与链末 hash，是否与其手上的台账副本相符；")
    L.append("> **③ 输入相符**：上表状态件／历史摘要，是否与其手上的副本相符；")
    L.append("> **④ 派生一致**：三样输入皆在时，用同 `ts` 重渲染，字节是否全等。")
    L.append("> ★ **四级都做到，才等于「这份种子确实由那条链派生而来」**；")
    L.append("> ★ 而**四级都不需要密钥**——**以复现代替签名**（本席台账 `signed=false`，故不冒充作者证明）。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*来源：本席自有状态件与台账（只读）。**未复制任何 MiroFish 代码**（其许可证为 AGPL-3.0，见本席轮 98 件）。*")
    body = "\n".join(L) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    body += "\n*种子 digest（sha256）＝ `%s`*\n" % digest
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="渲染时点（ISO8601）；不给则取状态件的 updated_at")
    ap.add_argument("--out", default=None, help="输出路径；不给则只打印")
    ap.add_argument("--seat-dir", default=None,
                    help="★轮100 增：输入根（默认本席领地）；供独立验证器在【副本】上复算")
    ap.add_argument("--bundle", default=None,
                    help="★轮100 增：把种子与其三样输入【一起冻结】到该目录（seed.md ＋ inputs/）")
    a = ap.parse_args()

    ob = OUTBOX
    lg = LEDGER
    if a.seat_dir:
        ob = pathlib.Path(a.seat_dir) / "outbox"
        lg = pathlib.Path(a.seat_dir) / "ledger" / "frontier_ledger.jsonl"

    for p in (ob / "state_cairn-dsh.json", ob / "state_history.jsonl", lg):
        if not p.is_file():
            print("[ERR] 缺输入件：%s" % p); return 2

    ts = a.ts
    if ts is None:
        ts = json.loads((ob / "state_cairn-dsh.json").read_text(encoding="utf-8")).get("updated_at", "")

    text = render(ts, ob, lg)

    hits = scan(text)
    if hits:
        print("[REFUSE] 禁词扫描命中 %d 项 ⇒ 不出种子：" % len(hits))
        for h in hits:
            print("   " + h)
        return 1

    # ★ 可复现自证：再渲染一次，比较字节
    again = render(ts, ob, lg)
    same = (again == text)

    print("═══ 种子渲染（MiroFish 形状）═══")
    print("  渲染时点 = %s" % ts)
    print("  字节 = %d" % len(text.encode("utf-8")))
    print("  ★ 同参二次渲染字节全等 = %s（可复现自证）" % same)
    print("  ★ 禁词扫描 = CLEAN（%d 条规则）" % len(FORBIDDEN))
    print("  校验和 = %s" % hashlib.sha256(text.encode("utf-8")).hexdigest()[:48])
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8", newline="\n")
        print("  已写出 = %s" % a.out)
    else:
        print()
        print(text)
    # ★★ 轮100 增：--bundle —— 把种子与【它的三样输入一起冻结】到同一目录。
    #   缘由：状态件与历史由后台心跳每分钟改写 ⇒ 只发种子，收到者【永远】核不过第③级。
    #   ⇒ 故"种子包"＝种子 ＋ 冻结输入；收到者据此可在【任何时刻】做完四级核验。
    if a.bundle:
        # ★★ 轮101 修：改用【标准席位布局】（outbox/ + ledger/），使 seed_verify.py
        #   可原样以 --seat-dir <bundle> 工作——此前写的是 inputs/，与验证器约定不符
        #   （本席自查所得：两件工具各自约定不一致）。
        bd = pathlib.Path(a.bundle)
        (bd / "outbox").mkdir(parents=True, exist_ok=True)
        (bd / "ledger").mkdir(parents=True, exist_ok=True)
        (bd / "seed.md").write_text(text, encoding="utf-8", newline="\n")
        import shutil as _sh
        _sh.copy2(ob / "state_cairn-dsh.json", bd / "outbox" / "state_cairn-dsh.json")
        _sh.copy2(ob / "state_history.jsonl", bd / "outbox" / "state_history.jsonl")
        _sh.copy2(lg, bd / "ledger" / "frontier_ledger.jsonl")
        print("  已冻结种子包 = %s（seed.md ＋ outbox/ 两件 ＋ ledger/ 一件）" % bd)
    print("  ★ 本器能失败：缺输入 ⇒ ERR；禁词命中 ⇒ REFUSE；二次渲染不等 ⇒ 打印 False。")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
