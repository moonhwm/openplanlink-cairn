#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""AV1编码工具 —— Python封装版
编纂：砚坚 2026-10-03
依赖：ffmpeg（需libaom-av1编码器）
"""
import subprocess
import sys
import os
import json
from pathlib import Path


def check_ffmpeg_av1() -> bool:
    """检查ffmpeg是否支持AV1编码"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        return "libaom-av1" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def encode_av1(input_path: str, output_path: str, crf: int = 30,
               resolution: str = "", audio_bitrate: str = "96k") -> dict:
    """AV1编码
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        crf: 质量因子（0-63，默认30，越小质量越高）
        resolution: 分辨率（如"1920:1080"，空则保持原样）
        audio_bitrate: 音频码率（默认96k）
    
    Returns:
        dict: 编码结果信息
    """
    if not Path(input_path).exists():
        return {"ok": False, "error": f"输入文件不存在: {input_path}"}
    
    if not check_ffmpeg_av1():
        return {"ok": False, "error": "ffmpeg不支持libaom-av1编码器"}
    
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libaom-av1",
        "-crf", str(crf),
        "-b:v", "0",
        "-cpu-used", "4",
        "-strict", "experimental",
    ]
    
    if resolution:
        cmd.extend(["-vf", f"scale={resolution}"])
    
    cmd.extend([
        "-c:a", "libopus",
        "-b:a", audio_bitrate,
        output_path
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr[-500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "编码超时（5分钟）"}
    
    output_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
    input_size = Path(input_path).stat().st_size
    
    return {
        "ok": True,
        "input": input_path,
        "output": output_path,
        "input_size": input_size,
        "output_size": output_size,
        "compression_ratio": round(input_size / max(output_size, 1), 2),
        "crf": crf,
        "codec": "AV1 (libaom)",
        "license_compatible": "AGPL-3.0+SSPL（免版税）"
    }


def batch_encode(input_dir: str, output_dir: str, crf: int = 30) -> list:
    """批量AV1编码
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        crf: 质量因子
    
    Returns:
        list: 每个文件的编码结果
    """
    results = []
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm", ".png", ".jpg"}
    
    for f in input_path.iterdir():
        if f.suffix.lower() in video_exts:
            out_file = output_path / f"{f.stem}.webm"
            result = encode_av1(str(f), str(out_file), crf=crf)
            results.append(result)
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python av1_encode.py <input> <output> [crf] [resolution]")
        print("  crf: 0-63，默认30（越小质量越高）")
        print("  resolution: 如1920:1080，空则保持原样")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    crf = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    resolution = sys.argv[4] if len(sys.argv) > 4 else ""
    
    result = encode_av1(input_path, output_path, crf=crf, resolution=resolution)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if not result["ok"]:
        sys.exit(1)