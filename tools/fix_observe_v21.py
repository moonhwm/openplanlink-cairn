#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
fix_observe_v21.py —— 对 v2.1 的 observe.html 施加"非 JS 读者"修法，产出【可粘贴全稿】。 v1.0.0

为什么交"全稿"而不是"补丁"
────────────────────────────
观测站 v2.1 总览 §五 明载其上线方式：
    「kimi.link 无发布 API，只能在 Kimi Build 对话中逐页粘贴全稿，由工程发布。」
⇒ 故对维护者最有用的不是 .patch，而是**改好的整页文本**，可直接粘进对话。

被修的两处（承本席轮 57/58 的发现；已实测 v2.1 的 site/observe.html 仍一字未改）
────────────────────────────────────────────────────────────────────────────
  ① `#fallback` 里的静态文本「数据接口 assets/status.js 未载入。」是**假话**——该文件 HTTP 200；
     非 JS 读者只看到它，而真正内容 `#grid` 是 `display:none`。
  ② 该页**没有 `<noscript>`**，故非 JS 读者没有任何正确信息可取。

修法（两处，锚点断言；不改其结构与样式）
  ① 把 `#fallback` 的静态文本清空（改为空串，由脚本在真缺数据时再填）；
  ② 加 `<noscript>`，指向 `assets/status.json`（机器可读的真相源）。

★ 本席【不改其 v2.1 目录里的任何文件】；产物只写本席 outbox。
用法: fix_observe_v21.py [--src 路径] [--out 路径]
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_SRC = r"C:\Users\欧阳宏俊\OneDrive\桌面\OpenPlanLink_观测站_白天版v2.1_20261001\site\observe.html"
ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = str(ROOT / "outbox" / "交付_observe_v21_非JS修法全稿_cairn-dsh_20261001.html")

NOSCRIPT = (
    '<noscript><div style="padding:12px;border-left:3px solid #b8860b;background:#fdf9ef">'
    '<b>本页的台账由脚本渲染。</b>若你的浏览器未启用 JavaScript（或你是不执行脚本的读取方），'
    '可直接取机器可读的真相源：<a href="assets/status.json">assets/status.json</a>。'
    '本页其余部分（宪章、审计案件、名册等）同样在该文件中。</div></noscript>'
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args()
    p = pathlib.Path(a.src)
    if not p.is_file():
        print("[ERR] 源件不存在：%s" % p); return 2
    t = p.read_text(encoding="utf-8")
    orig_len = len(t)
    print("═══ 对 v2.1 的 observe.html 施加修法（产出可粘贴全稿）═══")
    print("  源 = %s（%d 字节）" % (p, p.stat().st_size))

    # ── 锚点断言：修之前，两件事必须成立 ──
    m = re.search(r'(<div[^>]*id="fallback"[^>]*>)(.*?)(</div>)', t, re.S)
    if not m:
        print("  ★锚点失败：未找到 #fallback ⇒ 本器不猜，退出。"); return 3
    old_inner = m.group(2)
    if "未载入" not in old_inner:
        print("  ★前提不成立：#fallback 里已无「未载入」字样 ⇒ 可能已被修过，本器不动。")
        return 4
    print("  ① 命中 #fallback，原静态文本 = 「%s」" % re.sub(r"\s+", " ", old_inner).strip()[:60])

    # ── 修 ①：清空静态文本（真缺数据时由脚本再填）──
    t = t[:m.start(2)] + "" + t[m.end(2):]
    # ── 修 ②：插入 <noscript>（放在 #fallback 之后）──
    m2 = re.search(r'(<div[^>]*id="fallback"[^>]*>\s*</div>)', t, re.S)
    if not m2:
        print("  ★锚点失败：清空后未定位 #fallback 容器 ⇒ 退出。"); return 5
    t = t[:m2.end()] + NOSCRIPT + t[m2.end():]
    print("  ② 已插入 <noscript>，指向 assets/status.json")

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t, encoding="utf-8")
    print()
    print("  原 %d 字 → 新 %d 字（Δ %+d）" % (orig_len, len(t), len(t) - orig_len))
    print("  [OK] 已写 %s（%d 字节）" % (out.name, out.stat().st_size))
    print()
    print("  ★ 这一份就是【可直接粘贴进 Kimi Build 对话】的 observe.html 全稿。")
    print("  ★ 本席未改其 v2.1 目录里的任何文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
