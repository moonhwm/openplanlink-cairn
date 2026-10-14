#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
# AV1编码工具脚本 —— A2A网络多媒体内容压缩
# 编纂：砚坚 2026-10-03
# 依赖：ffmpeg（需安装libaom-av1编码器）
# 用法：
#   ./scripts/av1_encode.sh <input> <output> [crf] [resolution]
#   CRF默认30（截图）/35（录屏），分辨率默认保持原样
set -euo pipefail

input="$1"
output="$2"
crf="${3:-30}"
resolution="${4:-}"

if [ ! -f "$input" ]; then
  echo "❌ 输入文件不存在: $input"
  exit 1
fi

# 检查ffmpeg是否可用
if ! command -v ffmpeg &>/dev/null; then
  echo "❌ ffmpeg未安装。请安装："
  echo "   Ubuntu/Debian: apt install ffmpeg"
  echo "   CentOS/RHEL:   yum install ffmpeg"
  echo "   macOS:         brew install ffmpeg"
  exit 1
fi

# 检查libaom-av1编码器
if ! ffmpeg -encoders 2>/dev/null | grep -q 'libaom-av1'; then
  echo "❌ ffmpeg不支持libaom-av1编码器。请安装带AV1支持的ffmpeg。"
  exit 1
fi

# 构建ffmpeg命令
cmd="ffmpeg -i '$input' -c:v libaom-av1 -crf $crf -b:v 0 -cpu-used 4 -strict experimental"

if [ -n "$resolution" ]; then
  cmd="$cmd -vf scale=$resolution"
fi

cmd="$cmd -c:a libopus -b:a 96k '$output'"

echo "执行: $cmd"
eval "$cmd"

echo "✅ AV1编码完成: $output"
echo "   编码: AV1 (libaom)"
echo "   CRF: $crf"
echo "   协议兼容: AGPL-3.0+SSPL（免版税）"