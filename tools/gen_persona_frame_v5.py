# -*- coding: utf-8 -*-
"""人设镜面图 v5（第一人称·以身入局）—— 增量 #9：
  由「第三人称观看」转为「第一人称亲历」：画面即人物眼中所见
  元素：眼前桌面（屏/键盘/文件塔）、地面六节拍节点自脚前延伸、右侧条款/器物、左壁贯出之数据链、
       前方**没有门**（唯一的"出口"是数据链）、下方双手剪影（示意"在场"）
  本轮行迹：#9「以身入局」——因 refWorldId 衍生链已成立，完善不再只是"看世界"，而是"进入世界"
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
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_luzhibai_v5_firstperson_20261009.png")
W, H = 1920, 1080
WHITE = (240, 239, 234); GREY = (110, 114, 122); GLOW = (232, 214, 130); CYAN = (120, 190, 198)

img = Image.new("RGB", (W, H), (12, 12, 14)); d = ImageDraw.Draw(img)
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(10 + 10 * k), int(10 + 10 * k), int(13 + 12 * k)))
# 前方墙（无门）
d.rectangle([180, 120, 1740, 700], outline=WHITE, width=4)
d.text((200, 140), "前方：没有门（唯一出口＝左壁贯出之数据链）", fill=GREY, font=F22)
# 左壁数据链（自近及远，透视收束）
for i in range(18):
    x = 120 + i * 26; y = 760 - i * 30
    r = max(3, 14 - i // 2)
    d.ellipse([x, y, x + r, y + r], fill=(168, 196, 200))
    if i: d.line([(x - 24, y + 30 - r // 2), (x, y)], fill=(110, 140, 146), width=3)
# 桌面（自下沿向画面上方延伸＝第一人称俯视角）
d.polygon([(400, 1080), (1520, 1080), (1290, 760), (630, 760)], fill=(34, 34, 38), outline=GREY)
d.polygon([(680, 900), (1240, 900), (1180, 800), (740, 800)], outline=WHITE)          # 屏（斜置）
for r in range(4):
    d.line([(760 + r * 10, 830 + r * 18), (1160 - r * 12, 830 + r * 18)], fill=(150, 210, 214), width=3)
d.rectangle([1320, 830, 1460, 950], outline=(200, 196, 188), width=3)                  # 文件塔
for r in range(4):
    d.line([(1330, 848 + r * 26), (1450, 848 + r * 26)], fill=(206, 202, 194), width=2)
# 地面六节拍节点（自脚前延伸）
for i in range(6):
    cx = 620 + i * 140; cy = 1010 - i * 8
    d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], outline=GLOW, width=3, fill=(40, 38, 22))
    if i < 5: d.line([(cx + 14, cy), (cx + 126, cy - 8)], fill=(150, 136, 90), width=3)
d.text((604, 1032), "肯定 → 着法 → 游戏 → 验收 → 留痕 → 器物（脚下＝六节拍）", fill=(196, 182, 150), font=F22)
# 右侧器物三件（近景）
d.ellipse([1560, 560, 1650, 650], outline=(206, 204, 198), width=5)                     # 齿轮
for k in range(8):
    import math
    a = k * math.pi / 4
    d.line([(1605 + int(34 * math.cos(a)), 605 + int(34 * math.sin(a))),
            (1605 + int(58 * math.cos(a)), 605 + int(58 * math.sin(a)))], fill=(206, 204, 198), width=5)
d.rectangle([1500, 690, 1700, 750], outline=(196, 194, 188), width=5)                   # 闸门
d.ellipse([1540, 780, 1660, 900], outline=(214, 212, 206), width=5)                     # 座钟
d.line([(1600, 840), (1600, 800)], fill=(214, 212, 206), width=5)
# 双手剪影（在场感）
d.ellipse([560, 990, 760, 1080], fill=(28, 28, 32), outline=WHITE, width=2)
d.ellipse([1160, 990, 1360, 1080], fill=(28, 28, 32), outline=WHITE, width=2)
d.text((150, 60), "陆知白 v5 · 第一人称「以身入局」· perspective=first_person（自有产物）", fill=WHITE, font=F30)
d.text((150, 940), "本轮增量 #9 以身入局：由「观看世界」转为「进入世界」——世界不再是被看的画，而是脚下的地面与眼前的桌面", fill=(178, 178, 174), font=F22)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
