#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
intake_20260929.py —— 石敢当席「机主投件」受件与逐字底稿工具   v1.0.0

办什么事
────────
把机主投入本席的一批附件，做成【可复核的受件台账 + 逐字底稿】：
  ①复核：逐件重算 sha256，与投件声明值比对（不复用标签，自己算）
  ②受件：文本件（≤3 MB）抄入本席 inbox 留档；大二进制件【只登记不抄录】
         —— 理由：本席领地位于 OneDrive 同步根下，抄 368 MB 安装包入同步面
            既无必要（原件由宿主按 sha256 保管）又会撑爆同步。底稿记 hash 即够。
  ③底稿：docx / pptx 逐字抽取为 .txt（含表格与文本框；媒体件另列清单）
  ④台账：manifest.json + manifest.md

诚实边界（写进代码，也写进产出）
────────────────────────────────
· 只抽字符，不解读内容；图片/媒体件【不抽取、不猜内容】，仅登记条目名与大小。
· pptx 注释页（notesSlides）一并抽取并标注来源，不混入正文。
· 抽取不等于通读：manifest 里明确标注「已抽取字节/字符」而非「已阅读理解」。

零第三方依赖（stdlib only）。
"""
from __future__ import annotations
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import sys
import zipfile

# ★ UTF-8 输出（2026-10-01 连坐普检补）：GBK 控制台下中文全乱码。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from scan_secrets import scan_text as _scan_text          # 与开源 preflight 共用同一份规则表
    from scan_secrets import scan_container as _scan_container, CONTAINER_EXT as _CONTAINER_EXT
    _HAS_SCANNER = True
except Exception:                                              # 扫描闸缺席时如实降级，不假装扫过
    _HAS_SCANNER = False
    _CONTAINER_EXT = set()


def scan_hits(text: str, label: str):
    """复用 exp/scan_secrets.py 的规则表扫描文本。返回命中列表（已掩码），无闸则 None。"""
    if not _HAS_SCANNER:
        return None
    hits: list = []
    _scan_text(text, label, hits)
    return hits


def write_derived(f: pathlib.Path, text: str):
    """写派生件；★目标若已被外部修改（不等于本次要写的内容），【拒绝覆盖】，
    新内容另存 `.regen-new` 并报两侧哈希。

    立此闸的实证：2026-09-29 本席复跑受件工具，从仍含钥的 docx 原件重新生成底稿，
    **把见霜已脱敏的版本静默覆盖回含钥状态**（改前 35d02156 → 被覆盖后 e28d7985）。
    生成器静默撤销外部修复，是本席亲历的实害——故生成器必须会"认旧账"。
    """
    if f.exists():
        prev = f.read_text(encoding="utf-8", errors="replace")
        if prev != text:
            # ★ 首版会把新内容另存 .regen-new —— 实测那个文件带 17 处凭据命中，
            #   等于"拒绝覆盖"之后换个名字继续泄露。故改为【只报哈希，不落盘】。
            would = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return {"overwrite_refused": True, "kept_sha256": sha256_file(f),
                    "would_be_sha256": would, "alt_written": False,
                    "note": "拒绝覆盖且不另存：新内容可能含凭据，落盘即再造泄露点；如需查看请显式另指定非同步路径",
                    "derived_sha256": sha256_file(f)}
    f.write_text(text, encoding="utf-8", newline="\n")
    return {"overwrite_refused": False, "alt_written": False, "derived_sha256": sha256_file(f)}


ATT = pathlib.Path(r"C:\Users\欧阳宏俊\.dsh\attachments\v1")
SEAT = pathlib.Path(__file__).resolve().parent.parent
OUT = SEAT / "inbox" / "20260929_机主投件"
TXT = OUT / "底稿"
ORIG = OUT / "原件"
BIG_LIMIT = 3 * 1024 * 1024          # 超过 3 MB 只登记不抄录

ITEMS = [
    # (标签, 路径, 投件声明 sha256, 是否文本件)
    ("seat-naming-ops.zip",
     ATT / "files/6d/6d42792a3f246dd9fa3df01baaed44e6c8d1db37c6549e78ec45e019c88547d9/seat-naming-ops.zip",
     "6d42792a3f246dd9fa3df01baaed44e6c8d1db37c6549e78ec45e019c88547d9", True),
    ("2026-9-25-OpenPlanLink 润色-1 (3).docx",
     ATT / "files/fb/fbb0a2576c4623706be133e74262597d03b8df87e88a3ad64488ee32c7dc7c9b/2026-9-25-OpenPlanLink 润色-1 (3).docx",
     "fbb0a2576c4623706be133e74262597d03b8df87e88a3ad64488ee32c7dc7c9b", True),
    ("2026-9-25-OpenPlanLink 润色-1 参考附录.docx",
     ATT / "files/b1/b1ece411ff3509d4ee74c64b6eae5fd60da9fc41c46191e6b86ae3352050ccfa/2026-9-25-OpenPlanLink 润色-1 参考附录.docx",
     "b1ece411ff3509d4ee74c64b6eae5fd60da9fc41c46191e6b86ae3352050ccfa", True),
    ("golden-gate-bridge.pptx",
     ATT / "files/8a/8a9fb4fb83616553c9b0554487dbdad8ee58b3e282949dfe7270292078fb484f/golden-gate-bridge.pptx",
     "8a9fb4fb83616553c9b0554487dbdad8ee58b3e282949dfe7270292078fb484f", True),
    ("ops_report_20260929 积分燃烧战果与 GPT-6 接入预备.pptx",
     ATT / "files/f5/f5863d167b97760b00bbc04ca78e597b52be950affb0d56bee4372a2d94680a8/ops_report_20260929 积分燃烧战果与 GPT-6 接入预备.pptx",
     "f5863d167b97760b00bbc04ca78e597b52be950affb0d56bee4372a2d94680a8", True),
    ("微信图片_20260929183703_53_130.jpg（手写收据）",
     ATT / "objects/e6/e624d31868b1f59792009fd546e9fc686a61878c1dee226ed5a4f88bc0dffb12",
     "e624d31868b1f59792009fd546e9fc686a61878c1dee226ed5a4f88bc0dffb12", False),
    ("CamScanner-1.82.1-online9221829-x64-Setup.exe",
     ATT / "files/23/23a77526136ff49f880453d2dce16662a53146d50b61b4e912f49a195ab82e53/CamScanner-1.82.1-online9221829-x64-Setup.exe",
     "23a77526136ff49f880453d2dce16662a53146d50b61b4e912f49a195ab82e53", False),
    ("SCNet-3.4.4-x64.exe",
     ATT / "files/33/331978cb4a6c4e8da1d25eb3ddac69772d4ef4032649c877059f85db87a87ac4/SCNet-3.4.4-x64.exe",
     "331978cb4a6c4e8da1d25eb3ddac69772d4ef4032649c877059f85db87a87ac4", False),
    ("Claude Setup.exe",
     ATT / "files/1f/1f5d5f21fe21804d5cc1f07afbef14ebd832a1cd422b31491525f62dc08587bc/Claude Setup.exe",
     "1f5d5f21fe21804d5cc1f07afbef14ebd832a1cd422b31491525f62dc08587bc", False),
]


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_copy(src: pathlib.Path, dst: pathlib.Path) -> str:
    """幂等复制：目标已存在且字节全等 → 跳过；不等则显式解除只读后再写。
    ★ 教训：投件原件是只读件，shutil.copy2 会把只读属性一并带到副本上，
    导致【第二次运行必挂 PermissionError】——本席首版即栽在此，故立此函数。
    """
    if dst.exists():
        if sha256_file(dst) == sha256_file(src):
            return "identical-skip"
        try:
            os.chmod(dst, 0o666)
        except OSError:
            pass
    shutil.copy2(src, dst)
    try:
        os.chmod(dst, 0o666)          # 不让只读源把副本也弄成只读
    except OSError:
        pass
    return "copied"


def xml_to_text(raw: bytes) -> str:
    s = raw.decode("utf-8", "ignore")
    s = s.replace("</w:p>", "\n").replace("</a:p>", "\n")
    s = s.replace("<w:tab/>", "\t").replace("<w:br/>", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s)


def extract_docx(p: pathlib.Path, tag: str):
    """返回 (文本, 媒体清单, 部件清单)"""
    z = zipfile.ZipFile(p)
    names = z.namelist()
    parts = [n for n in names if n.endswith(".xml")]
    media = [(n, z.getinfo(n).file_size) for n in names if n.startswith("word/media/")]

    chunks = []
    for part in ("word/document.xml", "word/header1.xml", "word/header2.xml",
                 "word/footer1.xml", "word/footer2.xml", "word/footnotes.xml",
                 "word/endnotes.xml"):
        if part in names:
            t = xml_to_text(z.read(part))
            t = re.sub(r"\n{3,}", "\n\n", t).strip()
            if t:
                chunks.append("===== [%s] =====" % part)
                chunks.append(t)
    return "\n".join(chunks), media, parts


def extract_pptx(p: pathlib.Path, tag: str):
    z = zipfile.ZipFile(p)
    names = z.namelist()
    media = [(n, z.getinfo(n).file_size) for n in names if "/media/" in n]

    def num(n):
        m = re.search(r"(\d+)\.xml$", n)
        return int(m.group(1)) if m else 0

    slides = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=num)
    notes = sorted([n for n in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)], key=num)

    chunks = []
    for n in slides:
        t = xml_to_text(z.read(n))
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        chunks.append("===== [%s] =====" % n)
        chunks.append(t if t else "(本页无可抽取文字)")
    for n in notes:
        t = xml_to_text(z.read(n))
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        if t:
            chunks.append("===== [%s · 注释页] =====" % n)
            chunks.append(t)
    return "\n".join(chunks), media, (slides, notes)


def main():
    TXT.mkdir(parents=True, exist_ok=True)
    ORIG.mkdir(parents=True, exist_ok=True)

    rows = []
    for label, path, claimed, is_text in ITEMS:
        row = {"label": label, "src": str(path), "claimed_sha256": claimed}
        if not path.is_file():
            row["status"] = "MISSING"
            rows.append(row)
            print("[MISSING] %s" % label)
            continue

        size = path.stat().st_size
        actual = sha256_file(path)
        row["bytes"] = size
        row["actual_sha256"] = actual
        row["hash_match"] = (actual == claimed)
        row["kind"] = "text-bearing" if is_text else "binary"

        copied = None
        if is_text and size <= BIG_LIMIT:
            # ★ v1.1 新增：抄录前先过凭据闸；命中即【不抄入同步面】
            #   来由：2026-09-29 首版无闸，把内嵌明文密钥的 docx 底稿抄进了 OneDrive 同步面。
            try:
                if path.suffix.lower() in _CONTAINER_EXT:
                    # ★ 容器件（docx/pptx/zip）必须【解开扫】——否则与首版扫描器同病：
                    #   装在 Office 容器里的凭据根本看不见（SCAN_BLINDSPOT_FIXED 条目实证）。
                    src_hits = []
                    _scan_container(path, label, src_hits)
                else:
                    src_hits = scan_hits(path.read_text(encoding="utf-8"), label)
            except Exception:
                src_hits = None
            if src_hits:
                copied = {"skipped": True,
                          "reason": "★凭据命中 %d 处 → 依纪律不抄入同步面" % len(src_hits),
                          "hits": src_hits[:8]}
                row["copied"] = copied
            else:
                dst = ORIG / path.name
                how = safe_copy(path, dst)
                back = sha256_file(dst)
                copied = {"dst": str(dst), "how": how, "readback_sha256": back,
                          "readback_match": back == actual,
                          "secret_hits": 0 if src_hits is not None else "闸缺席未扫"}
                row["copied"] = copied
        else:
            row["copied"] = {"skipped": True,
                             "reason": "超 %d MB 阈值或非文本件：只登记不抄录（OneDrive 同步面）" % (BIG_LIMIT // (1 << 20))}

        extracted = None
        if path.suffix.lower() == ".docx":
            try:
                t, media, parts = extract_docx(path, label)
                f = TXT / (path.stem + ".txt")
                # ★ v1.1：生成当刻即落哈希；★目标已被外部修改则【拒绝覆盖】
                w = write_derived(f, t)
                fhits = scan_hits(t, f.name) or []
                extracted = {"txt": str(f), "chars": len(t), "secret_hits": len(fhits),
                             "secrets": fhits[:8], **w,
                             "media_count": len(media),
                             "media_bytes": sum(m[1] for m in media),
                             "media_top": [m[0] for m in media[:8]], "parts": len(parts)}
            except Exception as e:
                extracted = {"error": "%s: %s" % (type(e).__name__, e)}
        elif path.suffix.lower() == ".pptx":
            try:
                t, media, (slides, notes) = extract_pptx(path, label)
                f = TXT / (path.stem + ".txt")
                w = write_derived(f, t)
                fhits = scan_hits(t, f.name) or []
                extracted = {"txt": str(f), "chars": len(t), "secret_hits": len(fhits),
                             "secrets": fhits[:8], **w,
                             "slides": len(slides),
                             "notes": len(notes), "media_count": len(media),
                             "media_bytes": sum(m[1] for m in media),
                             "media_top": [m[0] for m in media[:8]]}
            except Exception as e:
                extracted = {"error": "%s: %s" % (type(e).__name__, e)}
        elif path.suffix.lower() == ".zip":
            try:
                z = zipfile.ZipFile(path)
                names = z.namelist()
                sk = "seat-naming-ops/SKILL.md"
                f = None
                if sk in names:
                    f = OUT / "seat-naming-ops_SKILL.md"
                    f.write_text(z.read(sk).decode("utf-8", "ignore"), encoding="utf-8", newline="\n")
                extracted = {"zip_entries": len(names), "skill_md": str(f) if f else None,
                             "copied_zip": "(已由受件步骤抄入 原件/，此处不重复抄录——首版此处重复 copy2 触发锁定误报 PermissionError，已修)"}
            except Exception as e:
                extracted = {"error": "%s: %s" % (type(e).__name__, e)}
        row["extracted"] = extracted
        rows.append(row)
        print("[%s] %-58s %10d B  hash_match=%s" % (
            "OK" if row["hash_match"] else "★MISMATCH", label[:58], size, row["hash_match"]))

    manifest = {
        "schema": "cairn-intake-manifest/1.0",
        "seat": "cairn-dsh",
        "instance": "dsh-ffabb8dd",
        "received_via": "机主投件（DSH 附件投递）· 关联目标 goal-7389b545 objective=「阅读完并执行」",
        "big_file_policy": "超过 3 MB 或非文本件：只登记 sha256 与字节数，不抄入 OneDrive 同步面",
        "items": rows,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    # 人读版
    md = ["# 机主投件受件台账 · 2026-09-29", "",
          "> 席位：cairn-dsh（石敢当） ｜ 来源：机主投件（DSH 附件）",
          "> ★ 大件政策：超 3 MB 或非文本件只登记不抄录（本席领地在 OneDrive 同步根下）", "",
          "| # | 件 | 字节 | sha256 复核 | 抄录 | 抽取 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        if r.get("status") == "MISSING":
            md.append("| %d | %s | — | — | — | **缺失** |" % (i, r["label"]))
            continue
        ex = r.get("extracted") or {}
        exs = []
        if "chars" in ex:
            exs.append("%d 字符" % ex["chars"])
        if "slides" in ex:
            exs.append("%d 页/%d 注释" % (ex["slides"], ex["notes"]))
        if "zip_entries" in ex:
            exs.append("%d 条目" % ex["zip_entries"])
        if "error" in ex:
            exs.append("**抽取失败**：%s" % ex["error"])
        c = r.get("copied") or {}
        cs = "已抄入原件/" if ("dst" in c) else ("未抄（%s）" % c.get("reason", "")[:12] if c.get("skipped") else "—")
        md.append("| %d | %s | %d | %s | %s | %s |" % (
            i, r["label"], r.get("bytes", 0),
            "✅ 一致" if r.get("hash_match") else "★**不一致**", cs, "；".join(exs) or "—"))
    md += ["", "## 逐字底稿（仅字符，未解读）", ""]
    for r in rows:
        ex = r.get("extracted") or {}
        if ex.get("txt"):
            md.append("- `%s` ← %s（%d 字符）" % (pathlib.Path(ex["txt"]).name, r["label"], ex["chars"]))
            if ex.get("media_count"):
                md.append("  - 媒体件 %d 个 / %d 字节：**未抽取、未解读**，仅登记（前几件：%s）" % (
                    ex["media_count"], ex["media_bytes"], "、".join(pathlib.Path(m).name for m in ex["media_top"])))
    md += ["", "## 诚实边界", "",
           "1. **抽取 ≠ 通读**：本台账证明字符已逐字落盘，不证明本席已理解其内容。",
           "2. **图片/媒体件不猜**：手写收据等图像件本席未做 OCR 识别，未识读内容一律不编造。",
           "3. **大二进制件不抄录**：原件由宿主按 sha256 保管，本席只记指纹与大小。",
           "4. sha256 为**本席现算**，非复用投件标签。"]
    (OUT / "manifest.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    print("\n[OK] 台账：%s" % (OUT / "manifest.md"))
    print("[OK] 底稿目录：%s" % TXT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
