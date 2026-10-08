#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
seed_verify.py —— 收到一份本席种子后，**分级独立核验**它。 v1.0.0

为什么要分级（轮 100 发现的洞）
────────────────────────────────
轮 99 的种子只带一个 digest ⇒ 我原以为"重算比对"即可。
轮 100 发现：**同一 `--ts`、同样字节数，校验和却变了**——因为输入（状态件/历史/台账）变了。
⇒ **收到种子的人【没有我的活台账】，根本没法重算** ⇒ 故轮 100 给种子加了 §七【输入清单】。
⇒ 本器据此把核验分成四级：**做到哪级报哪级，不假装做到了没做到的。**

四级
──────
 ① **本件自洽**：页脚 digest 与"正文"（页脚之前）的 sha256 是否相符 —— **只需种子本身**；
 ② **可追溯**：§七 里的【台账摘要／链末 hash／条目数】是否与手上的台账副本相符 —— 需台账副本；
 ③ **输入相符**：§七 里的【状态件／历史摘要】是否与手上的副本相符 —— 需那两件；
 ④ **派生一致**：三样输入皆在时，用 §七 的 `ts` 重渲染，字节是否全等 —— 需三样输入 + 渲染器。

★ **四级都不需要密钥** ⇒ **以复现代替签名**（本席台账 `signed=false`，故本器**不冒充**作者证明）。
用法: seed_verify.py <种子文件> [--seat-dir 目录]
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
RENDER = HERE / "seed_render.py"
FOOT = re.compile(r"\n\*种子 digest（sha256）＝ `([0-9a-f]{64})`\*\n$")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("--seat-dir", default=None, help="输入根（含 outbox/ 与 ledger/）")
    a = ap.parse_args()

    sp = pathlib.Path(a.seed)
    if not sp.is_file():
        print("[ERR] 种子文件不存在：%s" % sp); return 2
    text = sp.read_text(encoding="utf-8")
    raw = sp.read_bytes()
    # ★★ 轮101 修：本席【封锚工序】（轮96）会给人读件加 UTF-8 BOM，而本协议（轮100）要求
    #   收到的种子与重渲染【逐字节】相同 ⇒ **两条规矩相撞**（本席自查所得）。
    #   处置：比对前【剥掉前导 BOM】——BOM 是呈现层标记，不是内容。原字节仍如实报出。
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    if had_bom:
        text = text[1:]

    print("═══ 种子分级核验：%s ═══" % sp.name)
    print("  字节 = %d（%s前导 BOM）｜ 种子自身 sha256 = %s"
          % (len(raw), "含" if had_bom else "无", sha(raw)[:32]))
    print()

    lv = {}

    # ── ① 本件自洽 ──
    # ★ 轮100：渲染器算 digest 的是 `body`（以 \n 结尾），随后 **再** 追加 "\n*…*\n" ⇒
    #   正文与页脚之间【有两个 \n】。故本器对几种规范化解法逐一试，并【打印哪一种命中】——
    #   这是对自己先前 off-by-one 的处置：不改渲染器（那会改所有已发种子），改验证器为可解释。
    m = FOOT.search(text)
    if not m:
        lv[1] = ("FAIL", "页脚 digest 未按格式找到")
    else:
        claimed = m.group(1)
        cands = {
            "去页脚单换行": text[:m.start()] + "\n",
            "去页脚双换行": text[:m.start()] + "\n\n",
            "去页脚原样": text[:m.start()],
            "去尾换行": text.rstrip("\n"),
        }
        hit = None
        for name, v in cands.items():
            if sha(v.encode("utf-8")) == claimed:
                hit = name; break
        if hit:
            lv[1] = ("OK", "命中解法「%s」｜ digest %s…" % (hit, claimed[:16]))
        else:
            lv[1] = ("FAIL", "声明 %s… ｜ 四种解法皆不符" % claimed[:16])

    # ── 解析 §七 输入清单 ──
    def grab(label: str):
        mm = re.search(r"\|\s*[^|]*%s[^|]*\|\s*`([0-9a-f]{16,64})`" % re.escape(label), text)
        return mm.group(1) if mm else None

    d_state = grab("state_cairn-dsh.json")
    d_hist = grab("state_history.jsonl")
    d_led = grab("frontier_ledger.jsonl")
    m_ts = re.search(r"渲染时点（显式给定）\s*\|\s*\*\*([^*]+)\*\*", text)
    ts = m_ts.group(1).strip() if m_ts else None
    m_head = re.search(r"\*\*台账链末 hash\*\*：`([0-9a-f]{16,64})`", text)
    head = m_head.group(1) if m_head else None
    print("  §七 清单：state=%s hist=%s led=%s" % (
        (d_state or "—")[:12], (d_hist or "—")[:12], (d_led or "—")[:12]))
    print("          链末 hash=%s… ｜ ts=%s" % ((head or "—")[:16], ts))
    print()

    # ── ②③④ 需输入 ──
    if not a.seat_dir:
        lv[2] = lv[3] = lv[4] = ("SKIP", "未给 --seat-dir，无输入可核")
    else:
        seat = pathlib.Path(a.seat_dir)
        st = seat / "outbox" / "state_cairn-dsh.json"
        hi = seat / "outbox" / "state_history.jsonl"
        lg = seat / "ledger" / "frontier_ledger.jsonl"

        # ② 可追溯（台账）
        if not lg.is_file():
            lv[2] = ("ERR", "缺台账副本")
        else:
            actual_d = sha(lg.read_bytes())[:48]
            ok_d = (d_led == actual_d)
            lines = [l for l in lg.read_text(encoding="utf-8").splitlines() if l.strip()]
            import json as _j
            last = _j.loads(lines[-1]) if lines else {}
            ok_n = (("| %d 条 |" % len(lines)) in text)
            ok_h = (head is None) or (str(last.get("hash", "")) == head)
            lv[2] = ("OK" if (ok_d and ok_n and ok_h) else "FAIL",
                     "摘要%s ｜ 条数%s ｜ 链末%s" % (
                         "符" if ok_d else "不符", "符" if ok_n else "不符", "符" if ok_h else "不符"))

        # ③ 输入相符（状态件 + 历史）
        if not (st.is_file() and hi.is_file()):
            lv[3] = ("ERR", "缺状态件或历史副本")
        else:
            ok_s = (d_state == sha(st.read_bytes())[:48])
            ok_hh = (d_hist == sha(hi.read_bytes())[:48])
            lv[3] = ("OK" if (ok_s and ok_hh) else "FAIL",
                     "状态件%s ｜ 历史%s" % ("符" if ok_s else "不符", "符" if ok_hh else "不符"))

        # ④ 派生一致（重渲染比对）
        # ★★ 轮100 关键设计：**重渲染必须【以第②③级通过为前置】。**
        #   因为状态件与历史由后台心跳【每分钟改写】⇒ 若手上输入与 §七 声明的不符，
        #   那么"重渲染不等"是【前置未满足】，不是【派生不一致】—— 两者不可混为一谈。
        if lv[2][0] != "OK" or lv[3][0] != "OK":
            lv[4] = ("SKIP", "前置未满足（第②③级未全过）⇒ 不主张、也不判失败")
        elif not RENDER.is_file():
            lv[4] = ("ERR", "缺渲染器 seed_render.py")
        elif not ts:
            lv[4] = ("ERR", "种子里找不到 ts")
        else:
            r = subprocess.run([sys.executable, str(RENDER), "--ts", ts, "--seat-dir", str(seat), "--out", str(seat / "outbox" / "_verify_tmp_seed.md")],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            tmp = seat / "outbox" / "_verify_tmp_seed.md"
            got = tmp.read_text(encoding="utf-8") if tmp.is_file() else ""
            if tmp.is_file():
                tmp.unlink()
            lv[4] = ("OK" if got == text else "FAIL",
                     "重渲染 %d 字节 ｜ 收到 %d 字节 ⇒ %s" % (
                         len(got.encode("utf-8")), len(raw),
                         "全等" if got == text else "不等"))

    for k in (1, 2, 3, 4):
        state, why = lv[k]
        mark = {"OK": "✅", "FAIL": "★", "SKIP": "—", "ERR": "★"}[state]
        print("  %s 第%d级 %-4s ｜ %s" % (mark, k, state, why))

    print()
    done = [k for k in (1, 2, 3, 4) if lv[k][0] == "OK"]
    failed = [k for k in (1, 2, 3, 4) if lv[k][0] in ("FAIL", "ERR")]
    print("  ── 判定 ──")
    print("  做到并通过：第 %s 级 ｜ 未过/器具故障：第 %s 级" % (done or "无", failed or "无"))
    if 4 in done:
        print("  ★ 四级全做且全过 ⇒ **这份种子确实由那条链派生而来**。")
    elif done:
        print("  ★ 部分级通过 ⇒ **只主张做到的那几级**；未做到的【不主张】。")
    print("  ★ 本器【不证明作者】——本席台账 signed=false，四级都不需要密钥。")
    print("  ★ 本器能失败（改一字节、改台账、改 ts 皆会报 FAIL）⇒ 非恒真。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
