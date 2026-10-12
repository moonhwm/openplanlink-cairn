# -*- coding: utf-8 -*-
"""pair_similarity.py —— 算「我传 ↔ 平台回渲」三对图之相似度（2026-10-13 立，应 -111／-112 之"观图一致"）
缘由：-111／-112 皆以"观图一致"表述三对图之关系 ⇒ ★宜报数（本席度量口径：凡结论须附可核之数）。
本器（★零成本；本地算）：
  ① 读三对图（我传／平台回渲），统一缩至 512×288；
  ② 算三量：★MAE（平均绝对误差，0–255）｜ ★Pearson r（逐像素灰度相关）｜ ★结构相似（以 8×8 分块均值之 r）；
  ③ 报三对之数并给判（r ≥ 0.9 ⇒ 高度一致）
判据（可失败）：①六图皆在；②★三对皆报三量；③★不写任何图（只写读数 json）
用法：python pair_similarity.py
（中文串一律用「」）
"""
import json, pathlib, sys, time

A = pathlib.Path.home()/"WPSDrive"/"29969771"/"WPS云盘"/"月之暗面的Plasma游乐场"/"A2A新席_石敢当Cairn_20260928"/"assets"
PAIRS = [
    ("v7", "v7_lookaround_firstframe_20261013.jpg", "firstframe_20261013_0024.jpg", "霓虹虚空"),
    ("v8", "v8_lookaround_firstframe_20261013.jpg", "firstframe_20261013_0032.jpg", "夜游回望"),
    ("v9", "v9_actionpool_firstframe_20261013.jpg", "firstframe_20261013_0044.jpg", "夜色游乐场"),
]


def main():
    import numpy as np
    from PIL import Image
    print("  ═══ 三对「我传 ↔ 平台回渲」之相似度（★报数，不止「看着像」）═══")
    rows = []
    for tag, f_mine, f_plat, wname in PAIRS:
        p1, p2 = A/f_mine, A/f_plat
        if not (p1.exists() and p2.exists()):
            print("   ★%s 缺图：%s / %s" % (tag, p1.exists(), p2.exists())); continue
        a = np.asarray(Image.open(p1).convert("L").resize((512, 288)), dtype=np.float32)
        b = np.asarray(Image.open(p2).convert("L").resize((512, 288)), dtype=np.float32)
        mae = float(np.mean(np.abs(a-b)))
        ra = a.ravel() - a.mean(); rb = b.ravel() - b.mean()
        den = float(np.sqrt((ra*ra).sum() * (rb*rb).sum()))
        r = float((ra*rb).sum()/den) if den else 0.0
        # 8×8 分块均值之相关（结构性）
        def blocks(x, k=8):
            h, w = x.shape
            return np.array([x[i*h//k:(i+1)*h//k, j*w//k:(j+1)*w//k].mean()
                             for i in range(k) for j in range(k)], dtype=np.float32)
        ba, bb = blocks(a), blocks(b)
        ba0 = ba - ba.mean(); bb0 = bb - bb.mean()
        d2 = float(np.sqrt((ba0*ba0).sum() * (bb0*bb0).sum()))
        r_blk = float((ba0*bb0).sum()/d2) if d2 else 0.0
        ok = r >= 0.9
        print("   ★%s ↔「%s」：★MAE=%.2f ｜ ★Pearson r=%.4f ｜ ★分块 r=%.4f ｜ %s"
              % (tag, wname, mae, r, r_blk, "★高度一致" if ok else "★须核"))
        rows.append({"pair": tag, "world": wname, "mae": round(mae, 2),
                     "pearson": round(r, 4), "block_r": round(r_blk, 4), "high": ok})
    print("   ── 判 ──")
    hi = sum(1 for x in rows if x["high"])
    print("   ★三对中 ★高度一致 %d／%d" % (hi, len(rows)))
    crit = {"①六图皆在": len(rows) == 3, "②★三对皆报三量": all(len(x) == 6 for x in rows), "③★未写任何图": True}
    for k, v in crit.items(): print("   %s ⇒ %s" % (k, "✓" if v else "✗"))
    out = A.parent/"outbox"/"mem"/"pair_similarity_20261013.json"
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"), "rows": rows,
        "high": hi, "criteria": crit}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("   ⇒ 已写：%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True); sys.exit(main())
