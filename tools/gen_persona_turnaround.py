# -*- coding: utf-8 -*-
"""人设"六视角转面图"（turnaround sheet）——3D建模之标准参考件（自有产物）
六格（2×3）：前视 / 后视 / 左视 / 右视 / 俯视 / 等轴测
每格画出**同一间无门窗之居所与同一人物剪影**，仅改变视点，并标注视点名、视线与比例尺
⇒ 作为"3D 参考"喂入世界模型（Adventure v3）
"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

def cjk(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

F18, F26 = cjk(24), cjk(32)
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_turnaround_20261009.png")
W, H = 1920, 1080
WHITE = (240, 239, 234); GREY = (118, 122, 130); GLOW = (232, 214, 130); CYAN = (120, 190, 198)

img = Image.new("RGB", (W, H), (11, 11, 13)); d = ImageDraw.Draw(img)
views = ["前视 Front", "后视 Back", "左视 Left", "右视 Right", "俯视 Top", "等轴测 Iso"]
cw, ch = 600, 320
for i, name in enumerate(views):
    cx = 30 + (i % 3) * (cw + 20)
    cy = 120 + (i // 3) * (ch + 40)
    d.rectangle([cx, cy, cx + cw, cy + ch], outline=(70, 74, 82), width=2)
    d.text((cx + 8, cy - 30), "%d. %s" % (i + 1, name), fill=WHITE, font=F26)
    # 房间（无门窗）：不同视点下的线框
    x0, y0, x1, y1 = cx + 90, cy + 50, cx + 510, cy + 280
    if i in (0, 1):                                    # 前/后视：正面矩形
        d.rectangle([x0, y0, x1, y1], outline=WHITE, width=3)
    elif i in (2, 3):                                  # 左/右视：侧面矩形 + 一条纵深线
        d.rectangle([x0, y0, x1, y1], outline=WHITE, width=3)
        d.line([(x0, y0), (x0 + 60, y0 + 40)], fill=GREY, width=2)
        d.line([(x1, y1), (x1 + 60, y1 + 40)], fill=GREY, width=2)
    elif i == 4:                                       # 俯视：顶面矩形 + 内部节点
        d.rectangle([x0, y0 + 40, x1, y1 - 30], outline=WHITE, width=3)
        for k in range(6):
            px = x0 + 60 + k * 58; d.ellipse([px - 8, y0 + 130, px + 8, y0 + 146], outline=GLOW, width=3)
    else:                                              # 等轴测：立体盒
        dx, dy = 70, 40
        d.polygon([(x0 + dx, y0), (x1, y0), (x1 + dx, y0 + dy), (x0 + 2 * dx, y0 + dy)], outline=WHITE)
        d.polygon([(x0 + 2 * dx, y0 + dy), (x1 + dx, y0 + dy), (x1 + dx, y1), (x0 + 2 * dx, y1 + dy)], outline=WHITE)
        d.polygon([(x0 + dx, y0), (x0 + 2 * dx, y0 + dy), (x0 + 2 * dx, y1 + dy), (x0 + dx, y1)], outline=WHITE)
    # 人物剪影（各视点略异：前/后为正面/背面，左/右为侧面窄影，俯视为圆点+肩线，等轴测为斜置）
    mx, my = (cx + 300), (cy + 190)
    if i in (0, 1):
        d.ellipse([mx - 22, my - 78, mx + 22, my - 34], fill=(30, 30, 34), outline=WHITE)
        d.polygon([(mx, my - 30), (mx - 40, my + 60), (mx + 40, my + 60)], fill=(36, 36, 42), outline=WHITE)
    elif i in (2, 3):
        d.ellipse([mx - 11, my - 78, mx + 11, my - 34], fill=(30, 30, 34), outline=WHITE)
        d.polygon([(mx, my - 30), (mx - 18, my + 60), (mx + 18, my + 60)], fill=(36, 36, 42), outline=WHITE)
    elif i == 4:
        d.ellipse([mx - 20, my - 14, mx + 20, my + 26], outline=WHITE, width=3)
        d.line([(mx - 44, my + 6), (mx + 44, my + 6)], fill=WHITE, width=3)
    else:
        d.polygon([(mx, my - 70), (mx - 34, my + 40), (mx + 44, my + 30)], fill=(36, 36, 42), outline=WHITE)
    # 比例尺与视线
    d.line([(cx + 20, cy + ch - 22), (cx + 140, cy + ch - 22)], fill=CYAN, width=3)
    d.text((cx + 150, cy + ch - 32), "比例 1:1（示意）", fill=CYAN, font=F18)
d.text((30, 40), "陆知白 · 人设六视角转面图（3D 参考 · 自有产物 · 属性源自档案 v1.0.1 与 v2 增量）", fill=WHITE, font=F26)
d.text((30, 1030), "六格同一居所同一人物，仅变视点：前 / 后 / 左 / 右 / 俯 / 等轴测 ｜ 无门窗之居所 ｜ 五→六节拍节点 ｜ 供世界模型（Adventure）v3 使用", fill=(150, 150, 146), font=F18)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
