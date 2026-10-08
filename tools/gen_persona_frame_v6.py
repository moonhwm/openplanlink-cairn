# -*- coding: utf-8 -*-
"""人设镜面图 v6 —— 增量 #10「共享面之礼」（源出本轮"镜像仓跨席写面"事件）
视觉：世界中部出现一张"共享面"（两席同时书写的同一张台账/镜像），面上有三条礼：
  ① 先取后推（fetch→merge→push 之环形箭头）
  ② 不覆盖（他席提交有护盾标记）
  ③ 签名树冲突须重签（一枚"重签"印记）
其余保持：无门窗／六节拍／器物三件／数据链
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
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_luzhibai_v6_sharedsurface_20261009.png")
W, H = 1920, 1080
WHITE = (240, 239, 234); GREY = (118, 122, 130); GLOW = (232, 214, 130); CYAN = (120, 190, 198); GREEN = (128, 186, 140)

img = Image.new("RGB", (W, H), (11, 11, 13)); d = ImageDraw.Draw(img)
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(10 + 8 * k), int(10 + 8 * k), int(13 + 10 * k)))
# 无门窗之居所
d.rectangle([120, 150, 1180, 800], outline=WHITE, width=3)
d.text((140, 168), "陆知白 v6 · 增量 #10「共享面之礼」· 无门窗之居所（自有产物）", fill=WHITE, font=F30)
# 六节拍
for i in range(6):
    cx = 210 + i * 156
    d.ellipse([cx - 11, 744, cx + 11, 766], outline=GLOW, width=3, fill=(40, 38, 22))
    if i < 5: d.line([(cx + 12, 755), (cx + 144, 755)], fill=(150, 136, 90), width=3)
d.text((202, 772), "肯定 → 着法 → 游戏 → 验收 → 留痕 → 器物", fill=(196, 182, 150), font=F22)
# ★ 共享面（中央斜置之台面，两面席位同时书写）
d.polygon([(330, 520), (980, 470), (1060, 640), (410, 700)], fill=(30, 30, 34), outline=CYAN)
d.text((352, 486), "共 享 面（两席同写）", fill=CYAN, font=F22)
for i in range(6):                                     # 面上之两行字迹
    d.line([(430 + i * 96, 560), (500 + i * 96, 552)], fill=(150, 210, 214), width=3)
    d.line([(430 + i * 96, 620), (500 + i * 96, 614)], fill=(196, 156, 96), width=3)
# ① 先取后推（环形箭头）
d.arc([700, 300, 900, 440], start=200, end=520, fill=GREEN, width=4)
d.polygon([(700, 370), (686, 352), (712, 352)], fill=GREEN)
d.text((716, 296), "① 先取后推：fetch → merge → push", fill=GREEN, font=F22)
# ② 不覆盖（护盾）
d.polygon([(1010, 250), (1090, 250), (1090, 320), (1050, 360), (1010, 320)], outline=GLOW, width=4)
d.text((1004, 214), "② 他席提交不覆盖", fill=GLOW, font=F22)
# ③ 重签（印记）
d.rounded_rectangle([1010, 400, 1140, 470], radius=10, outline=(196, 120, 110), width=4)
d.text((1024, 414), "③ 重签", fill=(216, 140, 130), font=F22)
d.text((1004, 478), "签名树冲突必重签", fill=(200, 150, 140), font=F22)
# 人物剪影（在共享面旁）
d.ellipse([560, 250, 624, 314], fill=(30, 30, 34), outline=WHITE, width=2)
d.polygon([(592, 316), (536, 424), (648, 424)], fill=(36, 36, 42), outline=WHITE)
d.polygon([(592, 320), (544, 406), (640, 406)], fill=(206, 204, 198))
# 器物三件（远侧）
d.ellipse([1240, 300, 1320, 380], outline=(206, 204, 198), width=5)
import math
for k in range(8):
    a = k * math.pi / 4
    d.line([(1280 + int(30 * math.cos(a)), 340 + int(30 * math.sin(a))),
            (1280 + int(52 * math.cos(a)), 340 + int(52 * math.sin(a)))], fill=(206, 204, 198), width=5)
d.rectangle([1220, 430, 1400, 486], outline=(196, 194, 188), width=5)
d.ellipse([1250, 520, 1370, 640], outline=(214, 212, 206), width=5)
d.text((1214, 660), "器物三件（打钟／闸门／审计）", fill=(206, 204, 198), font=F22)
# 数据链（左壁贯出）
for i in range(16):
    x = 60 + i * 30; y = 900 - i * 28
    r = max(3, 13 - i // 2)
    d.ellipse([x, y, x + r, y + r], fill=(168, 196, 200))
    if i: d.line([(x - 26, y + 28 - r // 2), (x, y)], fill=(110, 140, 146), width=3)
# 底注
d.text((120, 860), "本轮行迹：镜像仓为共享写面（他席亦在推）⇒ 本席推送被 non-fast-forward 拒 ⇒ 立「先取后推／不覆盖／重签」三礼", fill=(178, 178, 174), font=F22)
d.text((120, 900), "★本版世界以 refWorldId 衍生自 v5（数据虚空·first_person）⇒ 衍生链 v3→v4→v5→v6", fill=(200, 190, 170), font=F22)
d.text((120, 950), "属性皆源自档案与本夜实证行迹；虚构成年人设，不指向真实个人；「未闭合」之涌现探针继续保留", fill=(140, 140, 136), font=F22)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
