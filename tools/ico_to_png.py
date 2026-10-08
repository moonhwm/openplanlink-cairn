#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ico_to_png.py —— 把改名成 .jpeg 的 ICO 图标还原成可读 PNG。  v1.0.0

来由
────
投件 `image13.jpeg`（4,286 B）read_image 报 `Unsupported or malformed image data`。
本席核文件头实测：它是 **ICO**（`00 00 01 00`），32×32、32 bpp、数据偏移 22、
bytesInRes=4264 —— 22 + 4264 = 4286 = 文件全长，分毫吻合。即：**不是坏图，是改了扩展名**。
本工具把它转成 PNG 供视觉通道识读。

★ 诚实边界
──────────
· 只做格式转换，不改一个像素；**放大只为看得清，不引入任何新信息**。
· 转换后须声明：源分辨率 32×32，视图为最近邻放大 N 倍。
· 若结构不符（非 ICO、非 32bpp）即如实报错，不猜、不补。
"""
from __future__ import annotations
import pathlib
import struct
import sys
import zlib


def chunk(t: bytes, d: bytes) -> bytes:
    c = t + d
    return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)


def convert(src: pathlib.Path, dst: pathlib.Path, scale: int) -> dict:
    b = src.read_bytes()
    if b[:4] != b"\x00\x00\x01\x00":
        raise ValueError("非 ICO 文件头（前 4 字节 %s）" % b[:4].hex(" "))
    count = int.from_bytes(b[4:6], "little")
    w0, h0 = b[6] or 256, b[7] or 256
    bitcount = int.from_bytes(b[12:14], "little")
    size = int.from_bytes(b[14:18], "little")
    off = int.from_bytes(b[18:22], "little")
    bi = b[off:off + 40]
    bw = int.from_bytes(bi[4:8], "little")
    bh = int.from_bytes(bi[8:12], "little") // 2          # ICO 存的是 2×高度
    bpp = int.from_bytes(bi[14:16], "little")
    if bpp != 32:
        raise ValueError("仅支持 32bpp，实测 %d bpp" % bpp)

    px = b[off + 40: off + size]
    need = bw * bh * 4
    if len(px) < need:
        raise ValueError("像素数据不足：需 %d，实有 %d" % (need, len(px)))

    rows = []
    for y in range(bh - 1, -1, -1):                       # ICO 行序自下而上
        base = y * bw * 4
        row = bytearray()
        for x in range(bw):
            bb, gg, rr, aa = px[base + x * 4: base + x * 4 + 4]
            row += bytes((rr, gg, bb, aa))
            if scale > 1:                                 # 最近邻横向放大
                row += bytes((rr, gg, bb, aa)) * (scale - 1)
        for _ in range(scale):                            # 最近邻纵向放大
            rows.append(b"\x00" + bytes(row))             # PNG 每行前置 filter 字节 0

    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", bw * scale, bh * scale, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    dst.write_bytes(png)
    return {"ico_count": count, "entry_w": w0, "entry_h": h0, "bpp_field": bitcount,
            "bmp_w": bw, "bmp_h": bh, "bpp": bpp, "bytesInRes": size,
            "offset": off, "total_bytes": len(b), "math_ok": off + size == len(b),
            "png": str(dst), "png_bytes": len(png), "scale": scale}


def main():
    if len(sys.argv) < 3:
        print("用法：ico_to_png.py <src.ico|伪装件> <dst.png> [放大倍数=8]")
        return 2
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    try:
        info = convert(src, dst, scale)
    except ValueError as e:
        print("[REFUSE] %s" % e)
        return 1
    print("[OK] 已转换（未改任何像素，仅格式转换 + 最近邻放大 %d×）" % scale)
    for k in ("entry_w", "entry_h", "bpp", "bmp_w", "bmp_h", "bytesInRes", "offset",
              "total_bytes", "math_ok", "png_bytes"):
        print("   %-12s = %s" % (k, info[k]))
    print("   ★ offset+bytesInRes == 文件全长 ⇒ %s" % ("成立，结构自洽" if info["math_ok"] else "不成立，结构存疑"))
    print("   src = %s" % src)
    print("   dst = %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
