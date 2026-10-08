# -*- coding: utf-8 -*-
"""人设镜面图 v4（衍生版）—— 叠加本轮行迹增量：
  #6 跨席感知（发现他席亦在用世界模型）  → 画面右侧两枚"他席世界"名牌（虚线连出、不指认归属）
  #7 痕迹识别与不指认                    → 名牌外有问号框（不指认）与"只陈事实"注记
  #8 代理指标意识（代理≠判定）           → 一条刻度尺，两端标"代理检验"与"未判定"，**未闭合**
并在图底标注"以 refWorldId 衍生"字样
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
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_luzhibai_v4_world_20261009.png")
W, H = 1920, 1080
WHITE = (240, 239, 234); GREY = (118, 122, 130); GLOW = (232, 214, 130); CYAN = (120, 190, 198); ORANGE = (206, 140, 84)

img = Image.new("RGB", (W, H), (11, 11, 13)); d = ImageDraw.Draw(img)
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(10 + 8 * k), int(10 + 8 * k), int(13 + 10 * k)))
# 主房间（无门窗）＋六节拍
d.rectangle([150, 180, 980, 760], outline=WHITE, width=3)
for i in range(6):
    cx = 240 + i * 132
    d.ellipse([cx - 11, 700, cx + 11, 722], outline=GLOW, width=3, fill=(40, 38, 22))
    if i < 5:
        d.line([(cx + 12, 711), (cx + 120, 711)], fill=(150, 136, 90), width=3)
d.text((232, 730), "肯定 → 着法 → 游戏 → 验收 → 留痕 → 器物（六节拍）", fill=(196, 182, 150), font=F22)
# 人物剪影 + 器物三件小标
d.ellipse([524, 300, 588, 364], fill=(30, 30, 34), outline=WHITE, width=2)
d.polygon([(556, 366), (500, 474), (612, 474)], fill=(36, 36, 42), outline=WHITE)
d.polygon([(556, 370), (508, 456), (604, 456)], fill=(206, 204, 198))
d.text((200, 210), "陆知白 v4（衍生版）· 「知其白，守其黑」· 居所没有门窗", fill=WHITE, font=F30)
# ★ #6/#7 他席世界名牌（虚线连出、问号框、不指认）
d.text((1120, 250), "#6 跨席感知：#7 痕迹识别与不指认", fill=ORANGE, font=F22)
for i, nm in enumerate(["Moonlit Plaza", "Geometric Void"]):
    y = 300 + i * 110
    d.rectangle([1180, y, 1560, y + 70], outline=ORANGE, width=3)
    d.text((1196, y + 18), nm, fill=(232, 214, 180), font=F22)
    d.text((1576, y + 18), "？", fill=ORANGE, font=F30)          # 不指认归属
    for k in range(7):                                            # 虚线连出
        x0 = 990 + k * 26
        d.line([(x0, y + 35 - k * 3), (x0 + 14, y + 33 - k * 3)], fill=(150, 110, 80), width=3)
d.text((1120, 540), "只陈事实与时刻；不指认归属；不代改他席件", fill=(190, 150, 120), font=F22)
d.text((1120, 590), "跨席清单互认（建议）：免重复建世界与命名冲突", fill=(200, 180, 150), font=F22)
# ★ #8 代理指标刻度（未闭合）
d.line([(1120, 700), (1740, 700)], fill=CYAN, width=4)
d.line([(1120, 680), (1120, 720)], fill=CYAN, width=4)
d.line([(1740, 680), (1740, 720)], fill=CYAN, width=4)
d.text((1120, 730), "代理检验（命名/首帧）", fill=CYAN, font=F22)
d.text((1560, 730), "未判定（须进房）", fill=(188, 120, 110), font=F22)
for k in range(6):
    d.line([(1300 + k * 60, 690), (1300 + k * 60, 710)], fill=(80, 120, 128), width=2)
d.text((1120, 790), "★「未闭合」——不预称涌现", fill=(188, 120, 110), font=F22)
# 底注
d.text((150, 860), "本轮增量：跨席感知｜痕迹识别与不指认｜代理指标意识（代理≠判定）", fill=(178, 178, 174), font=F22)
d.text((150, 900), "★本版世界以平台原生参数「refWorldId」**衍生自 v3（数据虚空）** ⇒ 动态完善改用平台本征机制（自有产物）", fill=(200, 190, 170), font=F22)
d.text((150, 950), "属性皆源自档案 v1.0.1、v2 增量与本夜行迹（跨席并用之实证）；虚构成年人设，不指向真实个人", fill=(140, 140, 136), font=F22)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
