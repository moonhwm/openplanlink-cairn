#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_media.py —— 把 docx/pptx 内嵌媒体件抽出到本席领地，供逐一识读。  v1.0.0

来由
────
本席第 1 轮进度件里写着「22 个媒体（图片）件未抽取、未识读（本席不猜图）」。
但本席**有 read_image 视觉通道**——「不猜」是对的，「不看」不是。
故补此工具：抽出媒体件并给出尺寸/字节/在文档中的引用位置，供后续逐一识读。

纪律
────
· 只抽不猜：本工具**只导出与登记**，不对图像内容作任何判读。
· 抽出件落在本席领地内，并在 manifest 登记 sha256，供回溯。
· 超大媒体件（>12 MB）只登记不导出（OneDrive 同步面）。
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import struct
import sys
import zipfile

# ★ UTF-8 输出（2026-10-01 连坐普检补）：GBK 控制台下中文全乱码。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SEAT = pathlib.Path(__file__).resolve().parent.parent
ORIG = SEAT / "inbox" / "20260929_机主投件" / "原件"
OUT = SEAT / "inbox" / "20260929_机主投件" / "媒体"
BIG = 12 * 1024 * 1024

DOCS = [
    "2026-9-25-OpenPlanLink 润色-1 (3).docx",
    "2026-9-25-OpenPlanLink 润色-1 参考附录.docx",
    "golden-gate-bridge.pptx",
    "ops_report_20260929 积分燃烧战果与 GPT-6 接入预备.pptx",
]


def img_size(b: bytes):
    """只读文件头判尺寸，不依赖第三方库。"""
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", b[16:24])
            return ("png", w, h)
        if b[:2] == b"\xff\xd8":
            i = 2
            while i < len(b) - 9:
                if b[i] != 0xFF:
                    i += 1
                    continue
                m = b[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9,
                         0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", b[i + 5:i + 9])
                    return ("jpeg", w, h)
                if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
                    i += 2
                    continue
                ln = struct.unpack(">H", b[i + 2:i + 4])[0]
                i += 2 + ln
            return ("jpeg", None, None)
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            return ("webp", None, None)
        if b[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", b[6:10])
            return ("gif", w, h)
    except Exception:
        pass
    return ("unknown", None, None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in DOCS:
        src = ORIG / name
        if not src.is_file():
            print("[SKIP] 原件缺失：%s" % name)
            continue
        stem = src.stem
        sub = OUT / stem
        z = zipfile.ZipFile(src)
        media = [n for n in z.namelist() if "/media/" in n]
        if not media:
            print("[--] %s：无媒体件" % name)
            continue
        sub.mkdir(parents=True, exist_ok=True)
        print("═══ %s：媒体 %d 件 ═══" % (name, len(media)))
        for n in sorted(media):
            data = z.read(n)
            h = hashlib.sha256(data).hexdigest()
            kind, w, hh = img_size(data)
            rec = {"docx": name, "entry": n, "bytes": len(data), "sha256": h,
                   "kind": kind, "w": w, "h": hh}
            if len(data) <= BIG:
                dst = sub / pathlib.Path(n).name
                dst.write_bytes(data)
                rec["exported"] = str(dst.relative_to(SEAT))
            else:
                rec["exported"] = "(超 12 MB，只登记不导出)"
            manifest.append(rec)
            print("  %-22s %9d B  %-6s %sx%s" % (
                pathlib.Path(n).name, len(data), kind, w, hh))
    (OUT / "media_manifest.json").write_text(
        json.dumps({"schema": "cairn-media-manifest/1.0", "items": manifest},
                   ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("\n[OK] 媒体台账：%s（共 %d 件）" % (OUT / "media_manifest.json", len(manifest)))
    print("★ 本工具只抽不猜：图像内容未作任何判读。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
