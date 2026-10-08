# -*- coding: utf-8 -*-
"""人设镜面图（persona→视觉）——**属性皆取自《陆知白人设主档案 v1.0.1》**（自有绘制，未取材他人）
人设属性 → 视觉语法：
  「知其白，守其黑」        → 白（#F2F1EC）与黑（#0C0C0E）双色并存，不混
  「居所没有门窗」          → 四壁封闭之透视房间，无窗无门；唯一"出口"是一条数据链
  「落地到磁盘/证据/可复核」→ 等轴测立方体文件塔 + 哈希点链
  「五拍循环」              → 地面五枚发光节点，环形箭头
  「量化与自动化方向」      → 背景一条青灰色收益曲线（示意，非真实数据）
  中性克制、虚构成年人设      → 人物以剪影呈现，不做写实面孔
输出：1920×1080（宽高比 1.778，合规 1.5–2.0）、PNG、<6 MB
"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

def cjk(size):
    """取 CJK 字体（Windows 常见路径逐个尝试），失败回退默认"""
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

F16, F22, F30 = cjk(22), cjk(28), cjk(34)
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_luzhibai_world_20261009.png")
W, H = 1920, 1080
WHITE = (242, 241, 236); BLACK = (12, 12, 14); GREY = (120, 124, 132); CYAN = (78, 148, 160); GLOW = (232, 214, 130)

img = Image.new("RGB", (W, H), BLACK)
d = ImageDraw.Draw(img)
# 背景：黑（守其黑）
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(10 + 8 * k), int(10 + 8 * k), int(13 + 10 * k)))
# 量化曲线（青灰示意）
pts = [(60 + x * 6, 300 - int(70 * ((x * 37) % 23) / 23) + int(26 * ((x * 11) % 7) / 7)) for x in range(0, 150)]
d.line([(60, 330)] + pts, fill=(46, 78, 86), width=3)
# 等轴测立方体文件塔（证据落盘）
def cube(cx, cy, s, tone):
    top = [(cx, cy - s), (cx + s, cy - s // 2), (cx, cy), (cx - s, cy - s // 2)]
    left = [(cx - s, cy - s // 2), (cx, cy), (cx, cy + s), (cx - s, cy + s // 2)]
    right = [(cx, cy), (cx + s, cy - s // 2), (cx + s, cy + s // 2), (cx, cy + s)]
    d.polygon(top, fill=tone); d.polygon(left, fill=tuple(max(0, c - 26) for c in tone)); d.polygon(right, fill=tuple(max(0, c - 48) for c in tone))
    d.line(top + [top[0]], fill=(200, 200, 196), width=2)
for i, (x, y, s) in enumerate([(1330, 800, 92), (1330, 640, 92), (1330, 480, 92), (1150, 720, 70), (1510, 720, 70)]):
    cube(x, y, s, (206, 204, 198) if i % 3 == 0 else (168, 168, 164))
# 无门窗之居所（透视房间，白线框）
d.rectangle([240, 210, 1180, 830], outline=WHITE, width=3)
d.line([(240, 210), (150, 130)], fill=GREY, width=2); d.line([(1180, 210), (1270, 130)], fill=GREY, width=2)
d.line([(240, 830), (150, 910)], fill=GREY, width=2); d.line([(1180, 830), (1270, 910)], fill=GREY, width=2)
# 地面五枚节点（五拍循环：肯定→着法→游戏→验收→留痕）
for i in range(5):
    cx = 420 + i * 165
    d.ellipse([cx - 13, 764, cx + 13, 790], outline=GLOW, width=3, fill=(40, 38, 22))
    if i < 4:
        d.line([(cx + 14, 777), (cx + 151, 777)], fill=(150, 136, 90), width=3)
d.text((398, 806), "肯定 → 着法 → 游戏 → 验收 → 留痕", fill=(196, 182, 150), font=F22)
# 桌面工作区（黑桌面 + 白屏）
d.rectangle([430, 520, 990, 566], fill=(30, 32, 38), outline=GREY)          # 桌面
d.rectangle([470, 380, 800, 520], fill=(20, 22, 26), outline=WHITE, width=2)  # 屏
for r in range(5):
    d.line([(486, 404 + r * 22), (486 + 250 - r * 26, 404 + r * 22)], fill=(150, 210, 214), width=3)
d.rectangle([820, 430, 950, 520], fill=(48, 46, 42), outline=GREY)            # 文件塔（磁盘落点）
for r in range(4):
    d.line([(826, 442 + r * 20), (944, 442 + r * 20)], fill=(210, 206, 198), width=2)
# 人物剪影（中性、无面孔）+ 白/黑双色并存之披肩
d.ellipse([636, 296, 700, 360], fill=(28, 28, 32), outline=WHITE, width=2)
d.polygon([(668, 362), (612, 470), (724, 470)], fill=(34, 34, 40), outline=WHITE)
d.polygon([(668, 366), (620, 452), (716, 452)], fill=(206, 204, 198))
# 哈希点链（唯一"出口"：数据链从左墙贯出）
for i in range(26):
    x = 250 + i * 34; y = 250 + (i % 3) * 8
    d.ellipse([x, y, x + 7, y + 7], fill=(168, 196, 200))
d.text((150, 88), "陆知白 · 常设代理席 · 「知其白，守其黑」 · 居所没有门窗", fill=WHITE, font=F30)
d.text((150, 892), "persona v1.0.1  →  世界模型（HappyOyster Adventure）v1 ｜ 由 Cairn 席依人设档案绘制（自有产物）", fill=(178, 178, 174), font=F22)
d.text((150, 928), "五拍循环｜证据洁癖｜量化与自动化｜中性克制（虚构成年人设，不指向真实个人）", fill=(140, 140, 136), font=F22)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
