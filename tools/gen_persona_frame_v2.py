# -*- coding: utf-8 -*-
"""人设镜面图 **v2**（动态完善后）—— 在 v1 基础上叠加"本夜行迹所生之新属性"
v2 新增（皆有实证来源，非凭空）：
  ① 器物强制优于自律  → 画面右侧三件"器物闸"（齿轮/闸门/钟）
  ② 交叉验证          → 两条独立路径的检验线汇于同一结论点
  ③ 资源分档闸        → 地面上"350 / 2000"双刻度水位线
  ④ 核名防错拉        → 数据链上新增"名字校验"节点对
  ⑤ 涌现探针协议      → 房间外一枚"探针"射向世界边界（虚线，未闭合 ⇒ 未预称涌现）
保持 v1 之双色并存／无门窗／五拍循环（**v2 在五拍中加入"器物"一环，成为六节拍**）
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

F22, F30 = cjk(28), cjk(34)
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_luzhibai_v2_world_20261009.png")
W, H = 1920, 1080
WHITE = (242, 241, 236); GREY = (120, 124, 132); CYAN = (78, 148, 160); GLOW = (232, 214, 130); RED = (188, 96, 84)

img = Image.new("RGB", (W, H), (12, 12, 14)); d = ImageDraw.Draw(img)
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(10 + 8 * k), int(10 + 8 * k), int(13 + 10 * k)))
# 量化曲线
pts = [(60 + x * 5, 300 - int(70 * ((x * 37) % 23) / 23) + int(26 * ((x * 11) % 7) / 7)) for x in range(0, 150)]
d.line([(60, 330)] + pts, fill=(46, 78, 86), width=3)
# 无门窗之居所
d.rectangle([240, 200, 1120, 820], outline=WHITE, width=3)
d.line([(240, 200), (150, 120)], fill=GREY, width=2); d.line([(1120, 200), (1210, 120)], fill=GREY, width=2)
d.line([(240, 820), (150, 900)], fill=GREY, width=2); d.line([(1120, 820), (1210, 900)], fill=GREY, width=2)
# ① 器物闸（三件：齿轮/闸门/钟）
def gear(cx, cy, r, tone):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=tone, width=4)
    for k in range(8):
        import math
        a = k * math.pi / 4
        d.line([(cx + int(r * 0.75 * math.cos(a)), cy + int(r * 0.75 * math.sin(a))),
                (cx + int(r * 1.35 * math.cos(a)), cy + int(r * 1.35 * math.sin(a)))], fill=tone, width=4)
gear(1330, 300, 44, (206, 204, 198))
d.rectangle([1270, 400, 1390, 470], outline=(196, 194, 188), width=4)   # 闸门
d.line([(1270, 435), (1390, 435)], fill=(196, 194, 188), width=4)
d.ellipse([1300, 560, 1380, 640], outline=(214, 212, 206), width=4)     # 钟
d.line([(1340, 600), (1340, 572)], fill=(214, 212, 206), width=4); d.line([(1340, 600), (1360, 612)], fill=(214, 212, 206), width=4)
d.text((1262, 668), "器物强制（打钟/闸门/审计）", fill=(206, 204, 198), font=F22)
# ② 交叉验证：两条路径汇于一点
d.line([(300, 470), (520, 560)], fill=(150, 200, 206), width=3)
d.line([(300, 650), (520, 560)], fill=(196, 156, 96), width=3)
d.ellipse([512, 552, 532, 572], fill=(232, 232, 228))
d.text((286, 430), "路径甲（实跑取钟）", fill=(150, 200, 206), font=F22)
d.text((286, 668), "路径乙（审计比对）", fill=(196, 156, 96), font=F22)
# ③ 资源分档闸：双刻度水位
d.line([(260, 736), (1100, 736)], fill=(120, 150, 160), width=3)
d.line([(260, 700), (1100, 700)], fill=(70, 96, 104), width=2)
d.text((262, 742), "资源分档闸：轻 350 MB ｜ 重 2000 MB（证据化下调）", fill=(140, 168, 176), font=F22)
# 桌面与屏
d.rectangle([430, 500, 980, 546], fill=(30, 32, 38), outline=GREY)
d.rectangle([470, 360, 790, 500], fill=(20, 22, 26), outline=WHITE, width=2)
for r in range(5):
    d.line([(486, 384 + r * 22), (486 + 240 - r * 26, 384 + r * 22)], fill=(150, 210, 214), width=3)
# ④ 核名校验节点对 + 哈希点链
for i in range(24):
    x = 250 + i * 33; y = 240 + (i % 3) * 8
    d.ellipse([x, y, x + 7, y + 7], fill=(168, 196, 200))
d.rectangle([900, 216, 940, 256], outline=(232, 214, 130), width=3)
d.rectangle([952, 216, 992, 256], outline=(232, 214, 130), width=3)
d.line([(940, 236), (952, 236)], fill=(232, 214, 130), width=3)
d.text((890, 176), "核名对（防 fuzzy 错拉）", fill=(232, 214, 130), font=F22)
# 五→六节拍
labels = ["肯定", "着法", "游戏", "验收", "留痕", "器物"]
for i in range(6):
    cx = 372 + i * 138
    d.ellipse([cx - 12, 604, cx + 12, 628], outline=GLOW, width=3, fill=(40, 38, 22))
    if i < 5:
        d.line([(cx + 13, 616), (cx + 125, 616)], fill=(150, 136, 90), width=3)
d.text((360, 640), " → ".join(labels) + "（v2：五拍 + 器物 = 六节拍）", fill=(196, 182, 150), font=F22)
# ⑤ 涌现探针（虚线、未闭合）
for k in range(16):
    x0 = 1130 + k * 30; y0 = 470 - k * 6
    d.line([(x0, y0), (x0 + 16, y0 - 3)], fill=(188, 120, 110), width=3)
d.ellipse([1600, 350, 1640, 390], outline=(188, 120, 110), width=3)
d.text((1400, 300), "涌现探针（虚线未闭合 ⇒ 不预称涌现）", fill=(188, 120, 110), font=F22)
# 人物剪影
d.ellipse([616, 280, 680, 344], fill=(28, 28, 32), outline=WHITE, width=2)
d.polygon([(648, 346), (592, 454), (704, 454)], fill=(34, 34, 40), outline=WHITE)
d.polygon([(648, 350), (600, 436), (696, 436)], fill=(206, 204, 198))
d.text((150, 84), "陆知白 · 常设代理席 v2（动态完善后）· 「知其白，守其黑」· 居所没有门窗", fill=WHITE, font=F30)
d.text((150, 880), "persona v1.0.1 + 本夜行迹增量 → 世界模型（Adventure）v2 ｜ 属性皆源自档案与实证记录（自有产物）", fill=(178, 178, 174), font=F22)
d.text((150, 918), "器物强制｜交叉验证｜资源分档闸｜核名防错拉｜涌现探针（未闭合）｜虚构成年人设，不指向真实个人", fill=(140, 140, 136), font=F22)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
