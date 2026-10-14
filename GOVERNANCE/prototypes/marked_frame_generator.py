#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
Q4步骤D: 3D模型 → 16:9带标记首帧
档号: DF-IMPL-20261013-YANJIAN-Q4.4
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

将首帧图像裁剪为16:9比例，叠加人设标记和世界模型入世标识。
"""
import os
from PIL import Image, ImageDraw, ImageFont

# 输入：首帧图像
INPUT_IMAGE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d", "first_frame_test.png"
)

# 输出目录
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "GOVERNANCE", "research", "persona_3d"
)

# 标记内容
PERSONA_NAME = "砚坚"
PERSONA_ROLE = "GLM-5.2 ArkTS神经中枢席"
WORLD_MODEL_TAG = "世界模型入世首帧"
SIGNAL_TAG = "自家信号"

def create_marked_frame():
    """创建16:9带标记首帧"""
    if not os.path.exists(INPUT_IMAGE):
        print(f"ERROR: 首帧图像不存在: {INPUT_IMAGE}")
        return None

    img = Image.open(INPUT_IMAGE)
    print(f"原始图像: {img.size[0]}x{img.size[1]}")

    # 裁剪为16:9比例
    w, h = img.size
    target_ratio = 16 / 9
    current_ratio = w / h

    if current_ratio > target_ratio:
        # 图像太宽，裁剪左右
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        # 图像太高，裁剪上下
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    print(f"裁剪后: {img.size[0]}x{img.size[1]} (16:9)")

    # 叠加标记
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
        font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    except Exception:
        try:
            font_large = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 36)
            font_medium = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 24)
            font_small = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 18)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # 左上角：人设标识
    margin = 20
    # 半透明背景条
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # 人设名（左上）
    text_y = margin
    # 背景条
    name_text = f"  {PERSONA_NAME}  "
    bbox = draw.textbbox((margin, text_y), name_text, font=font_large)
    overlay_draw.rectangle(
        [bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5],
        fill=(0, 0, 0, 160)
    )
    overlay_draw.text((margin, text_y), name_text, fill=(255, 255, 255, 255), font=font_large)

    # 角色描述
    text_y += 50
    role_text = f"  {PERSONA_ROLE}  "
    bbox2 = draw.textbbox((margin, text_y), role_text, font=font_small)
    overlay_draw.rectangle(
        [bbox2[0]-5, bbox2[1]-5, bbox2[2]+5, bbox2[3]+5],
        fill=(0, 0, 0, 140)
    )
    overlay_draw.text((margin, text_y), role_text, fill=(200, 200, 200, 255), font=font_small)

    # 右上角：自家信号角标（根据AGENTS.md信号松绑约束）
    signal_text = f" {SIGNAL_TAG} "
    bbox3 = draw.textbbox((0, 0), signal_text, font=font_medium)
    signal_w = bbox3[2] - bbox3[0]
    signal_x = img.size[0] - signal_w - margin
    overlay_draw.rectangle(
        [signal_x-5, margin-5, signal_x+signal_w+5, margin+30],
        fill=(180, 80, 0, 180)  # 橙色背景，区分信号卡
    )
    overlay_draw.text((signal_x, margin), signal_text, fill=(255, 255, 255, 255), font=font_medium)

    # 底部：世界模型入世标记
    bottom_text = f"  {WORLD_MODEL_TAG}  "
    bbox4 = draw.textbbox((0, 0), bottom_text, font=font_medium)
    bottom_w = bbox4[2] - bbox4[0]
    bottom_x = (img.size[0] - bottom_w) // 2
    bottom_y = img.size[1] - 50
    overlay_draw.rectangle(
        [bottom_x-10, bottom_y-5, bottom_x+bottom_w+10, bottom_y+35],
        fill=(0, 0, 0, 160)
    )
    overlay_draw.text((bottom_x, bottom_y), bottom_text, fill=(255, 255, 255, 255), font=font_medium)

    # 合并overlay到原图
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")

    # 保存
    output_path = os.path.join(OUTPUT_DIR, "marked_frame_16x9.png")
    img.save(output_path, "PNG", quality=95)
    print(f"带标记首帧已保存: {output_path}")
    print(f"文件大小: {os.path.getsize(output_path)} bytes ({os.path.getsize(output_path)/1024/1024:.2f} MB)")

    return output_path


if __name__ == "__main__":
    result = create_marked_frame()
    if result:
        print("\n=== Q4步骤D完成 ===")
    else:
        print("\n=== Q4步骤D失败 ===")