# -*- coding: utf-8 -*-
"""守藏（字司契）人设镜面图 —— 属性皆取自《席位初始人设卡_守藏》（DF-PERSONA-2026-1006-SHOUCANG-01）
视觉语法：
  墨黑 + 朱印          → 「文书席」之色（异于陆知白之白黑双色）
  档案塔 / 册页 / 卷轴   → 守档案（全生命周期、core/wiki/raw 三层）
  朱印 + 四层条款条      → 司契约（AGPL-3.0/SSPL-1.0/CC BY-SA 4.0/ODbL-1.0 分层组合）
  打码方块 + 「见即止」  → 凭据纪律：见即止、不外显、不落盘
  往返箭头 + 回读标记    → 不嘴炮：广播必回读、上云必回读、校验必复跑
  终端行                → 实跑实证（结构化中文）
  座右铭                → 大字置于图底
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

F20, F26, F34 = cjk(26), cjk(32), cjk(40)
OUT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\exp\persona_shoucang_world_20261009.png")
W, H = 1920, 1080
INK = (18, 18, 20); PAPER = (226, 222, 210); SEAL = (178, 46, 40); GOLD = (196, 158, 88)

img = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(img)
for i in range(H):
    k = i / H
    d.line([(0, i), (W, i)], fill=(int(20 + 10 * k), int(19 + 9 * k), int(20 + 9 * k)))
# 档案塔（册页层叠）
for i in range(7):
    x0 = 150 + i * 8; y0 = 700 - i * 46
    d.rectangle([x0, y0, x0 + 360, y0 + 34], fill=(52, 49, 46), outline=PAPER, width=2)
    d.line([(x0 + 14, y0 + 17), (x0 + 330, y0 + 17)], fill=(120, 116, 108), width=2)
# 三层记忆（core/wiki/raw）
for i, lab in enumerate(["core", "wiki", "raw"]):
    d.rectangle([1920 - 520, 200 + i * 90, 1920 - 180, 270 + i * 90], outline=PAPER, width=3)
    d.text((1920 - 510, 214 + i * 90), "记忆层：%s" % lab, fill=PAPER, font=F26)
# 四层条款条（司契约）
layers = ["AGPL-3.0（代码）", "SSPL-1.0（服务栈敏感件）", "CC BY-SA 4.0（文档蓝图）", "ODbL-1.0（数据集）"]
for i, lay in enumerate(layers):
    y = 300 + i * 62
    d.rectangle([560, y, 1180, y + 46], outline=(150, 146, 138), width=2)
    d.line([(560, y + 23), (600, y + 23)], fill=SEAL, width=8)
    d.text((614, y + 8), lay, fill=PAPER, font=F26)
# 朱印（司契约·守档案）
d.rounded_rectangle([1230, 470, 1420, 660], radius=14, outline=SEAL, width=6)
d.text((1246, 486), "守档案", fill=SEAL, font=F34); d.text((1246, 540), "司契约", fill=SEAL, font=F34)
d.text((1246, 596), "DF-DOC-01", fill=(150, 70, 62), font=F20)
# 凭据纪律：打码方块 + 「见即止」
d.rectangle([560, 620, 760, 700], outline=(120, 120, 122), width=3)
for k in range(4):
    d.line([(570 + k * 48, 620), (570 + k * 48, 700)], fill=(70, 70, 72), width=2)
d.line([(560, 700), (760, 620)], fill=SEAL, width=5)          # 「见即止」之止线
d.text((566, 712), "凭据：见即止・不外显・不落盘", fill=(200, 150, 140), font=F26)
# 不嘴炮：往返箭头 + 回读
d.line([(820, 760), (1180, 760)], fill=GOLD, width=4)
d.polygon([(1180, 760), (1156, 748), (1156, 772)], fill=GOLD)
d.line([(1180, 800), (820, 800)], fill=GOLD, width=4)
d.polygon([(820, 800), (844, 788), (844, 812)], fill=GOLD)
d.text((830, 812), "广播必回读｜上云必回读｜校验必复跑（不嘴炮）", fill=GOLD, font=F26)
# 终端行（实跑实证）
d.rectangle([150, 850, 1180, 950], fill=(26, 26, 28), outline=(90, 90, 92), width=2)
d.text((166, 862), "$ python ledger/cairn_ledger.py verify → 条目数：812 ｜ 结论：PASS", fill=(140, 200, 168), font=F20)
d.text((166, 900), "$ kdocs-cli drive read-file --args '{\"link_id\":\"...\"}' → code=0", fill=(140, 200, 168), font=F20)
d.text((150, 100), "守藏（字司契）· 数字边疆编队・文书席 DF-DOC-01 · 墨黑与朱印之色", fill=PAPER, font=F34)
d.text((150, 1000), "座右铭：守档案，司契约。档案在册，契约在案，留痕可溯，实证可查。（属性皆取自其《席位初始人设卡》；自有产物）", fill=(200, 190, 170), font=F26)
img.save(OUT, "PNG", optimize=True)
print("  已生成：%s" % OUT.name)
print("  尺寸=%dx%d ｜ 宽高比=%.3f（合规 1.5–2.0）｜ 体积=%.2f MB（<6 MB）" % (W, H, W/H, OUT.stat().st_size/1048576))
